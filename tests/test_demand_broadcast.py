"""Pruebas de la difusión de demanda de materiales a proveedores."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["APU_DB_PATH"] = str(Path(tempfile.gettempdir()) / "apu_demand_test.db")

from core.database import init_db  # noqa: E402
from core import apu_engine, auth, repositories  # noqa: E402
from models.item import Item  # noqa: E402
from models.project import Proyecto  # noqa: E402
from models.supplier import Proveedor  # noqa: E402
from providers import demand_broadcast, supplier_service  # noqa: E402


def _setup():
    from config import settings
    p = Path(settings.DB_PATH)
    if p.exists():
        p.unlink()
    init_db()
    u = auth.Usuario(perfil="contratista", nombre_empresa="ABC SRL",
                     email="c@abc.bo", encargado_nombre="Ana", encargado_whatsapp="77")
    uid, tok = auth.registrar_usuario(u, "x")
    auth.verificar_email("c@abc.bo", tok)
    usr, _ = auth.login("c@abc.bo", "x")
    supplier_service.alta_manual(Proveedor(
        nombre="Cementos Sur", email="v@cem.bo", categoria="cemento",
        materiales_servicios="cemento portland"))
    pid = repositories.crear_proyecto(Proyecto(nombre="Obra", usuario_id=usr.id))
    mod = repositories.obtener_o_crear_modulo(pid, "Estructura")
    iid = repositories.crear_item(Item(proyecto_id=pid, modulo_id=mod, numero="1",
                                       descripcion="Hormigón armado zapatas",
                                       unidad="m3", cantidad=10))
    apu_engine.armar_recursos_desde_analisis(repositories.obtener_item(iid))
    return usr, pid


def test_consolida_materiales():
    _usr, pid = _setup()
    mats = demand_broadcast.consolidar_materiales(pid)
    assert mats
    # cemento: 7 bolsas/m3 * 10 m3 = 70
    cemento = [m for m in mats if "cemento" in m["descripcion"].lower()]
    assert cemento and cemento[0]["cantidad"] == 70.0


def test_difunde_y_registra_con_datos_comprador():
    usr, pid = _setup()
    comp = demand_broadcast.comprador_desde_usuario(usr)
    resumen = demand_broadcast.difundir_demanda(pid, comp, enviar_email=True)
    assert resumen["solicitudes"] >= 1
    assert resumen["correos_enviados"] >= 1   # llegó a Cementos Sur
    sols = demand_broadcast.solicitudes_de_proyecto(pid)
    assert sols
    s = sols[0]
    assert s["empresa_compradora"] == "ABC SRL"
    assert s["encargado_nombre"] == "Ana"
    assert s["encargado_email"] == "c@abc.bo"
