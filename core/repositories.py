"""Repositorios de persistencia para entidades del dominio (excepto proveedores).

Centraliza CRUD de proyectos, módulos, ítems, fuentes/secciones técnicas,
vínculos, recursos APU, resultados y cotizaciones.
"""
from __future__ import annotations

import json
from typing import List, Optional

from core.database import db_session
from models.apu_resource import RecursoAPU
from models.apu_result import ResultadoAPU
from models.item import Item
from models.project import Proyecto
from models.quotation import Cotizacion
from models.technical_source import FuenteTecnica, SeccionTecnica, VinculoTecnico


# --------------------------------------------------------------------------- #
# Proyectos / Módulos
# --------------------------------------------------------------------------- #
def crear_proyecto(p: Proyecto) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO proyectos
               (nombre, region, moneda, factor_indirectos, factor_utilidad,
                factor_impuestos, estado)
               VALUES (?,?,?,?,?,?,?)""",
            (p.nombre, p.region, p.moneda, p.factor_indirectos, p.factor_utilidad,
             p.factor_impuestos, p.estado),
        )
        return cur.lastrowid


def listar_proyectos() -> List[Proyecto]:
    with db_session() as conn:
        filas = conn.execute("SELECT * FROM proyectos ORDER BY id DESC").fetchall()
        return [Proyecto(**{k: r[k] for k in r.keys()}) for r in filas]


def obtener_proyecto(pid: int) -> Optional[Proyecto]:
    with db_session() as conn:
        r = conn.execute("SELECT * FROM proyectos WHERE id=?", (pid,)).fetchone()
        return Proyecto(**{k: r[k] for k in r.keys()}) if r else None


def crear_modulo(proyecto_id: int, nombre: str, orden: int = 0) -> int:
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO modulos (proyecto_id, nombre, orden) VALUES (?,?,?)",
            (proyecto_id, nombre, orden))
        return cur.lastrowid


def obtener_o_crear_modulo(proyecto_id: int, nombre: str) -> Optional[int]:
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    with db_session() as conn:
        r = conn.execute(
            "SELECT id FROM modulos WHERE proyecto_id=? AND nombre=?",
            (proyecto_id, nombre)).fetchone()
        if r:
            return r["id"]
        cur = conn.execute(
            "INSERT INTO modulos (proyecto_id, nombre) VALUES (?,?)",
            (proyecto_id, nombre))
        return cur.lastrowid


# --------------------------------------------------------------------------- #
# Ítems
# --------------------------------------------------------------------------- #
def crear_item(item: Item) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO items
               (modulo_id, proyecto_id, numero, codigo, descripcion, unidad,
                cantidad, observaciones, estado, palabras_clave)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (item.modulo_id, item.proyecto_id, item.numero, item.codigo,
             item.descripcion, item.unidad, item.cantidad, item.observaciones,
             item.estado, item.palabras_clave))
        return cur.lastrowid


def actualizar_item(item: Item) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE items SET numero=?, codigo=?, descripcion=?, unidad=?,
               cantidad=?, observaciones=?, estado=?, palabras_clave=?, modulo_id=?
               WHERE id=?""",
            (item.numero, item.codigo, item.descripcion, item.unidad, item.cantidad,
             item.observaciones, item.estado, item.palabras_clave, item.modulo_id,
             item.id))


def listar_items(proyecto_id: int) -> List[Item]:
    with db_session() as conn:
        filas = conn.execute(
            "SELECT * FROM items WHERE proyecto_id=? ORDER BY id", (proyecto_id,)
        ).fetchall()
        return [Item(**{k: r[k] for k in r.keys()}) for r in filas]


def obtener_item(item_id: int) -> Optional[Item]:
    with db_session() as conn:
        r = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return Item(**{k: r[k] for k in r.keys()}) if r else None


# --------------------------------------------------------------------------- #
# Fuentes y secciones técnicas
# --------------------------------------------------------------------------- #
def crear_fuente(f: FuenteTecnica) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO fuentes_tecnicas
               (proyecto_id, tipo_documento, nombre_archivo, ruta, texto_extraido)
               VALUES (?,?,?,?,?)""",
            (f.proyecto_id, f.tipo_documento, f.nombre_archivo, f.ruta,
             f.texto_extraido))
        return cur.lastrowid


def listar_fuentes(proyecto_id: int) -> List[FuenteTecnica]:
    with db_session() as conn:
        filas = conn.execute(
            "SELECT * FROM fuentes_tecnicas WHERE proyecto_id=? ORDER BY id",
            (proyecto_id,)).fetchall()
        return [FuenteTecnica(**{k: r[k] for k in r.keys()}) for r in filas]


def crear_seccion(s: SeccionTecnica) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO secciones_tecnicas
               (fuente_id, titulo, contenido, pagina_inicio, pagina_fin, keywords)
               VALUES (?,?,?,?,?,?)""",
            (s.fuente_id, s.titulo, s.contenido, s.pagina_inicio, s.pagina_fin,
             s.keywords))
        return cur.lastrowid


def listar_secciones(proyecto_id: int) -> List[SeccionTecnica]:
    with db_session() as conn:
        filas = conn.execute(
            """SELECT s.* FROM secciones_tecnicas s
               JOIN fuentes_tecnicas f ON s.fuente_id = f.id
               WHERE f.proyecto_id=? ORDER BY s.id""", (proyecto_id,)).fetchall()
        return [SeccionTecnica(**{k: r[k] for k in r.keys()}) for r in filas]


def obtener_seccion(seccion_id: int) -> Optional[SeccionTecnica]:
    with db_session() as conn:
        r = conn.execute("SELECT * FROM secciones_tecnicas WHERE id=?",
                         (seccion_id,)).fetchone()
        return SeccionTecnica(**{k: r[k] for k in r.keys()}) if r else None


# --------------------------------------------------------------------------- #
# Vínculos técnicos
# --------------------------------------------------------------------------- #
def guardar_vinculo(v: VinculoTecnico) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO vinculos_tecnicos
               (item_id, seccion_id, score_confianza, validado_manual, observaciones)
               VALUES (?,?,?,?,?)""",
            (v.item_id, v.seccion_id, v.score_confianza, int(v.validado_manual),
             v.observaciones))
        return cur.lastrowid


def listar_vinculos(item_id: int) -> List[VinculoTecnico]:
    with db_session() as conn:
        filas = conn.execute(
            """SELECT vt.*, s.titulo AS titulo_seccion, s.contenido AS contenido
               FROM vinculos_tecnicos vt
               JOIN secciones_tecnicas s ON vt.seccion_id = s.id
               WHERE vt.item_id=? ORDER BY vt.score_confianza DESC""",
            (item_id,)).fetchall()
        out = []
        for r in filas:
            out.append(VinculoTecnico(
                id=r["id"], item_id=r["item_id"], seccion_id=r["seccion_id"],
                score_confianza=r["score_confianza"],
                validado_manual=bool(r["validado_manual"]),
                observaciones=r["observaciones"] or "",
                titulo_seccion=r["titulo_seccion"] or "",
                extracto=(r["contenido"] or "")[:300]))
        return out


def borrar_vinculos_item(item_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM vinculos_tecnicos WHERE item_id=?", (item_id,))


# --------------------------------------------------------------------------- #
# Recursos APU
# --------------------------------------------------------------------------- #
def guardar_recurso(r: RecursoAPU) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO recursos_apu
               (item_id, tipo, descripcion, unidad, rendimiento, cantidad_apu,
                precio_unitario, subtotal, fuente_precio, cotizacion_id, bloqueado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (r.item_id, r.tipo, r.descripcion, r.unidad, r.rendimiento,
             r.cantidad_apu, r.precio_unitario, r.subtotal, r.fuente_precio,
             r.cotizacion_id, int(r.bloqueado)))
        return cur.lastrowid


def listar_recursos(item_id: int) -> List[RecursoAPU]:
    with db_session() as conn:
        filas = conn.execute(
            "SELECT * FROM recursos_apu WHERE item_id=? ORDER BY tipo, id",
            (item_id,)).fetchall()
        out = []
        for r in filas:
            out.append(RecursoAPU(
                id=r["id"], item_id=r["item_id"], tipo=r["tipo"],
                descripcion=r["descripcion"], unidad=r["unidad"],
                rendimiento=r["rendimiento"], cantidad_apu=r["cantidad_apu"],
                precio_unitario=r["precio_unitario"], subtotal=r["subtotal"],
                fuente_precio=r["fuente_precio"] or "",
                cotizacion_id=r["cotizacion_id"], bloqueado=bool(r["bloqueado"])))
        return out


def actualizar_recurso(r: RecursoAPU) -> None:
    with db_session() as conn:
        conn.execute(
            """UPDATE recursos_apu SET tipo=?, descripcion=?, unidad=?, rendimiento=?,
               cantidad_apu=?, precio_unitario=?, subtotal=?, fuente_precio=?,
               cotizacion_id=?, bloqueado=? WHERE id=?""",
            (r.tipo, r.descripcion, r.unidad, r.rendimiento, r.cantidad_apu,
             r.precio_unitario, r.subtotal, r.fuente_precio, r.cotizacion_id,
             int(r.bloqueado), r.id))


def borrar_recurso(recurso_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM recursos_apu WHERE id=?", (recurso_id,))


def borrar_recursos_item(item_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            "DELETE FROM recursos_apu WHERE item_id=? AND bloqueado=0", (item_id,))


# --------------------------------------------------------------------------- #
# Resultados APU
# --------------------------------------------------------------------------- #
def guardar_resultado(res: ResultadoAPU) -> int:
    alertas = json.dumps(res.alertas, ensure_ascii=False)
    with db_session() as conn:
        conn.execute("DELETE FROM resultados_apu WHERE item_id=?", (res.item_id,))
        cur = conn.execute(
            """INSERT INTO resultados_apu
               (item_id, costo_materiales, costo_mano_obra, costo_equipos,
                costo_directo, indirectos, utilidad, impuestos,
                precio_unitario_total, alertas)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (res.item_id, res.costo_materiales, res.costo_mano_obra,
             res.costo_equipos, res.costo_directo, res.indirectos, res.utilidad,
             res.impuestos, res.precio_unitario_total, alertas))
        return cur.lastrowid


def obtener_resultado(item_id: int) -> Optional[ResultadoAPU]:
    with db_session() as conn:
        r = conn.execute("SELECT * FROM resultados_apu WHERE item_id=?",
                         (item_id,)).fetchone()
        if not r:
            return None
        return ResultadoAPU(
            id=r["id"], item_id=r["item_id"], costo_materiales=r["costo_materiales"],
            costo_mano_obra=r["costo_mano_obra"], costo_equipos=r["costo_equipos"],
            costo_directo=r["costo_directo"], indirectos=r["indirectos"],
            utilidad=r["utilidad"], impuestos=r["impuestos"],
            precio_unitario_total=r["precio_unitario_total"],
            alertas=json.loads(r["alertas"] or "[]"),
            fecha_generacion=r["fecha_generacion"])


# --------------------------------------------------------------------------- #
# Cotizaciones
# --------------------------------------------------------------------------- #
def guardar_cotizacion(c: Cotizacion) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO cotizaciones
               (recurso_id, proveedor_id, descripcion, nivel_busqueda, precio_bruto,
                unidad_origen, factor_conversion, precio_adoptado, moneda,
                vigencia_dias, url_fuente, estado, nivel_confianza, observaciones)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (c.recurso_id, c.proveedor_id, c.descripcion, c.nivel_busqueda,
             c.precio_bruto, c.unidad_origen, c.factor_conversion, c.precio_adoptado,
             c.moneda, c.vigencia_dias, c.url_fuente, c.estado, c.nivel_confianza,
             c.observaciones))
        return cur.lastrowid


def listar_cotizaciones(proyecto_id: int) -> List[dict]:
    with db_session() as conn:
        filas = conn.execute(
            """SELECT c.*, r.descripcion AS recurso_desc, p.nombre AS proveedor_nombre
               FROM cotizaciones c
               LEFT JOIN recursos_apu r ON c.recurso_id = r.id
               LEFT JOIN items i ON r.item_id = i.id
               LEFT JOIN proveedores p ON c.proveedor_id = p.id
               WHERE i.proyecto_id=? ORDER BY c.id DESC""",
            (proyecto_id,)).fetchall()
        return [dict(f) for f in filas]
