"""Repositorio de proveedores y precios de referencia (Nivel 1 del cotizador)."""
from __future__ import annotations

from typing import List, Optional

from core.database import db_session
from core.text_cleaner import normalizar
from models.supplier import Proveedor

logger_name = __name__


def _row_a_proveedor(row) -> Proveedor:
    return Proveedor(
        id=row["id"],
        nombre=row["nombre"],
        razon_social=row["razon_social"] or "",
        nit=row["nit"] or "",
        email=row["email"] or "",
        telefono=row["telefono"] or "",
        whatsapp=row["whatsapp"] or "",
        region=row["region"] or "",
        ciudad=row["ciudad"] or "",
        direccion=row["direccion"] or "",
        sitio_web=row["sitio_web"] or "",
        categoria=row["categoria"] or "otros",
        materiales_servicios=row["materiales_servicios"] or "",
        estado=row["estado"] or "activo",
        verificado=bool(row["verificado"]),
        fuente_alta=row["fuente_alta"] or "manual",
        observaciones=row["observaciones"] or "",
        fecha_creacion=row["fecha_creacion"],
        ultima_actualizacion=row["ultima_actualizacion"],
    )


# --------------------------------------------------------------------------- #
# Proveedores
# --------------------------------------------------------------------------- #
def crear_proveedor(p: Proveedor) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO proveedores
            (nombre, razon_social, nit, email, telefono, whatsapp, region, ciudad,
             direccion, sitio_web, categoria, materiales_servicios, estado,
             verificado, fuente_alta, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p.nombre, p.razon_social, p.nit, p.email, p.telefono, p.whatsapp,
             p.region, p.ciudad, p.direccion, p.sitio_web, p.categoria,
             p.materiales_servicios, p.estado, int(p.verificado), p.fuente_alta,
             p.observaciones),
        )
        return cur.lastrowid


def actualizar_proveedor(p: Proveedor) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE proveedores SET nombre=?, razon_social=?, nit=?, email=?,
               telefono=?, whatsapp=?, region=?, ciudad=?, direccion=?, sitio_web=?,
               categoria=?, materiales_servicios=?, estado=?, verificado=?,
               fuente_alta=?, observaciones=?, ultima_actualizacion=datetime('now')
               WHERE id=?""",
            (p.nombre, p.razon_social, p.nit, p.email, p.telefono, p.whatsapp,
             p.region, p.ciudad, p.direccion, p.sitio_web, p.categoria,
             p.materiales_servicios, p.estado, int(p.verificado), p.fuente_alta,
             p.observaciones, p.id),
        )


def listar_proveedores(categoria: Optional[str] = None,
                       region: Optional[str] = None) -> List[Proveedor]:
    sql = "SELECT * FROM proveedores WHERE 1=1"
    params: list = []
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if region:
        sql += " AND region = ?"
        params.append(region)
    sql += " ORDER BY nombre"
    with db_session() as conn:
        return [_row_a_proveedor(r) for r in conn.execute(sql, params).fetchall()]


def obtener_proveedor(proveedor_id: int) -> Optional[Proveedor]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM proveedores WHERE id=?",
                           (proveedor_id,)).fetchone()
        return _row_a_proveedor(row) if row else None


def buscar_proveedores_por_categoria(categoria: str,
                                     region: Optional[str] = None) -> List[Proveedor]:
    """Para Nivel 3: detecta proveedores candidatos por categoría/región."""
    return [p for p in listar_proveedores(categoria=categoria, region=region)
            if p.email]


# --------------------------------------------------------------------------- #
# Precios de referencia (BD interna - Nivel 1)
# --------------------------------------------------------------------------- #
def registrar_precio(descripcion: str, categoria: str, unidad: str, precio: float,
                     moneda: str = "BOB", region: str = "", proveedor_id=None,
                     url: str = "", fuente: str = "bd") -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO precios_referencia
               (proveedor_id, descripcion, categoria, unidad, precio, moneda,
                region, url_fuente, fuente)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (proveedor_id, descripcion, categoria, unidad, precio, moneda,
             region, url, fuente),
        )
        return cur.lastrowid


def buscar_precios(descripcion: str, categoria: Optional[str] = None,
                   region: Optional[str] = None) -> List[dict]:
    """Busca precios en la BD interna por coincidencia de palabras (Nivel 1).

    Devuelve lista de dicts con precio, unidad, fecha, proveedor, etc.
    """
    termino = normalizar(descripcion)
    palabras = [w for w in termino.split() if len(w) >= 3]
    with db_session() as conn:
        filas = conn.execute(
            "SELECT pr.*, pv.nombre AS proveedor_nombre, pv.region AS proveedor_region "
            "FROM precios_referencia pr "
            "LEFT JOIN proveedores pv ON pr.proveedor_id = pv.id "
            "WHERE pr.vigente = 1"
        ).fetchall()

    resultados: List[dict] = []
    for f in filas:
        desc_norm = normalizar(f["descripcion"] or "")
        cat = (f["categoria"] or "")
        coincide_cat = categoria and normalizar(cat) == normalizar(categoria)
        coincide_desc = any(p in desc_norm for p in palabras) if palabras else False
        if coincide_cat or coincide_desc:
            if region and f["region"] and normalizar(f["region"]) != normalizar(region):
                # se permite pero con menor relevancia; aquí solo no filtramos duro
                pass
            resultados.append({
                "precio": f["precio"],
                "unidad": f["unidad"],
                "moneda": f["moneda"],
                "fecha": f["fecha_precio"],
                "region": f["region"],
                "proveedor_id": f["proveedor_id"],
                "proveedor": f["proveedor_nombre"],
                "url": f["url_fuente"],
                "categoria": cat,
                "score": 1.0 if coincide_cat else 0.6,
            })
    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados
