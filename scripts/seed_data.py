"""Carga datos de ejemplo (mock) para probar el sistema rápidamente.

Crea proveedores bolivianos de muestra, precios de referencia, un proyecto
demo con ítems y genera sus APUs.

Uso:  python -m scripts.seed_data
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import apu_engine, repositories  # noqa: E402
from core.database import init_db  # noqa: E402
from core.text_cleaner import extraer_keywords  # noqa: E402
from models.item import Item  # noqa: E402
from models.project import Proyecto  # noqa: E402
from models.supplier import Proveedor  # noqa: E402
from providers import supplier_repository  # noqa: E402

PROVEEDORES = [
    Proveedor(nombre="Ferretería La Económica", email="ventas@economica.bo",
              region="Santa Cruz", ciudad="Santa Cruz", categoria="ferreteria",
              materiales_servicios="cemento, fierro, clavos", verificado=True),
    Proveedor(nombre="SOBOCE Distribuidor", email="contacto@soboce.bo",
              region="La Paz", ciudad="La Paz", categoria="cemento",
              materiales_servicios="cemento portland, hormigón", verificado=True),
    Proveedor(nombre="Aceros Bolivia SRL", email="ventas@acerosbolivia.bo",
              region="Cochabamba", ciudad="Cochabamba", categoria="acero",
              materiales_servicios="acero corrugado, varillas", verificado=True),
    Proveedor(nombre="Áridos del Valle", email="info@aridosvalle.bo",
              region="Cochabamba", ciudad="Cochabamba", categoria="aridos",
              materiales_servicios="arena, grava, ripio", verificado=False),
    Proveedor(nombre="Plastiforte Distribuidor", email="ventas@plastiforte.bo",
              region="Santa Cruz", ciudad="Santa Cruz", categoria="tuberias",
              materiales_servicios="tubería pvc, accesorios", verificado=True),
]

# (descripcion, categoria, unidad, precio BOB)
PRECIOS = [
    ("Cemento Portland IP-30", "cemento", "bolsa", 58.0),
    ("Acero corrugado fy=4200", "acero", "kg", 9.5),
    ("Arena fina", "aridos", "m3", 120.0),
    ("Grava común", "aridos", "m3", 140.0),
    ("Ladrillo gambote 6 huecos", "ceramicos", "pieza", 1.2),
    ("Tubería PVC 4'' desagüe", "tuberias", "ml", 35.0),
    ("Pintura látex interior", "acabados", "lt", 28.0),
    ("Cerámica esmaltada piso", "acabados", "m2", 75.0),
]

ITEMS_DEMO = [
    ("Obras preliminares", "1", "Excavación manual para cimientos", "m3", 45.0),
    ("Estructura", "2", "Hormigón armado para zapatas H21", "m3", 18.5),
    ("Albañilería", "3", "Muro de mampostería de ladrillo gambote", "m2", 220.0),
    ("Instalaciones", "4", "Provisión y tendido de tubería PVC 4''", "ml", 85.0),
    ("Acabados", "5", "Pintura látex en muros interiores", "m2", 340.0),
    ("Acabados", "6", "Revestimiento cerámico de pisos", "m2", 160.0),
]


def main() -> None:
    init_db()

    print("→ Cargando proveedores...")
    for p in PROVEEDORES:
        supplier_repository.crear_proveedor(p)

    print("→ Cargando precios de referencia (BD interna)...")
    for desc, cat, und, precio in PRECIOS:
        supplier_repository.registrar_precio(desc, cat, und, precio,
                                             region="Santa Cruz", fuente="bd")

    print("→ Creando proyecto demo...")
    proyecto = Proyecto(nombre="Proyecto Demo Vivienda", region="Santa Cruz",
                        moneda="BOB", factor_indirectos=0.10,
                        factor_utilidad=0.10, factor_impuestos=0.0)
    pid = repositories.crear_proyecto(proyecto)
    proyecto.id = pid

    for modulo, numero, desc, unidad, cantidad in ITEMS_DEMO:
        mod_id = repositories.obtener_o_crear_modulo(pid, modulo)
        repositories.crear_item(Item(
            proyecto_id=pid, modulo_id=mod_id, numero=numero, descripcion=desc,
            unidad=unidad, cantidad=cantidad,
            palabras_clave=", ".join(extraer_keywords(desc, 8))))

    print("→ Generando APUs (cotizador jerárquico)...")
    resultados = apu_engine.generar_apu_proyecto(proyecto, permitir_web=True,
                                                 permitir_email=False)

    total = sum(r.precio_unitario_total * it.cantidad
                for it, r in zip(repositories.listar_items(pid),
                                 resultados.values()))
    print(f"✅ Demo lista. Proyecto id={pid}, {len(ITEMS_DEMO)} ítems, "
          f"costo total estimado: {total:,.2f} BOB")
    print("   Ejecuta:  streamlit run app.py")


if __name__ == "__main__":
    main()
