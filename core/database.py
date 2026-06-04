"""Capa de acceso a base de datos (SQLite).

Provee la conexión, el esquema completo y utilidades de inicialización.
Preparado para migrar a PostgreSQL en producción manteniendo SQL estándar.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS proyectos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    region TEXT,
    moneda TEXT DEFAULT 'BOB',
    tipo_cambio REAL DEFAULT 6.96,
    factor_indirectos REAL DEFAULT 0.10,
    factor_utilidad REAL DEFAULT 0.10,
    factor_impuestos REAL DEFAULT 0.0,
    factor_beneficios_sociales REAL DEFAULT 0.55,
    factor_iva_mano_obra REAL DEFAULT 0.1494,
    factor_herramientas REAL DEFAULT 0.05,
    factor_iva_equipo REAL DEFAULT 0.0,
    factor_gastos_generales REAL DEFAULT 0.10,
    factor_utilidad_sabs REAL DEFAULT 0.10,
    factor_it REAL DEFAULT 0.0309,
    entidad TEXT DEFAULT '',
    proponente TEXT DEFAULT '',
    representante_legal TEXT DEFAULT '',
    ci_representante TEXT DEFAULT '',
    plazo_dias INTEGER DEFAULT 180,
    solicita_anticipo INTEGER DEFAULT 0,
    porcentaje_anticipo REAL DEFAULT 0.0,
    fecha_creacion TEXT DEFAULT (datetime('now')),
    estado TEXT DEFAULT 'activo'
);

CREATE TABLE IF NOT EXISTS modulos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    orden INTEGER DEFAULT 0,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id INTEGER,
    proyecto_id INTEGER NOT NULL,
    numero TEXT,
    codigo TEXT,
    descripcion TEXT NOT NULL,
    unidad TEXT,
    cantidad REAL DEFAULT 0,
    observaciones TEXT,
    estado TEXT DEFAULT 'pendiente',
    palabras_clave TEXT,
    validado_tecnico INTEGER DEFAULT 0,
    FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE SET NULL,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fuentes_tecnicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL,
    tipo_documento TEXT,
    nombre_archivo TEXT,
    ruta TEXT,
    texto_extraido TEXT,
    fecha_carga TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS secciones_tecnicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente_id INTEGER NOT NULL,
    titulo TEXT,
    contenido TEXT,
    pagina_inicio INTEGER,
    pagina_fin INTEGER,
    keywords TEXT,
    FOREIGN KEY (fuente_id) REFERENCES fuentes_tecnicas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vinculos_tecnicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    seccion_id INTEGER NOT NULL,
    score_confianza REAL DEFAULT 0,
    validado_manual INTEGER DEFAULT 0,
    observaciones TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (seccion_id) REFERENCES secciones_tecnicas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    razon_social TEXT,
    nit TEXT,
    email TEXT,
    telefono TEXT,
    whatsapp TEXT,
    region TEXT,
    ciudad TEXT,
    direccion TEXT,
    sitio_web TEXT,
    categoria TEXT,
    materiales_servicios TEXT,
    estado TEXT DEFAULT 'activo',
    verificado INTEGER DEFAULT 0,
    fuente_alta TEXT DEFAULT 'manual',
    observaciones TEXT,
    fecha_creacion TEXT DEFAULT (datetime('now')),
    ultima_actualizacion TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS precios_referencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER,
    descripcion TEXT NOT NULL,
    categoria TEXT,
    unidad TEXT,
    precio REAL,
    moneda TEXT DEFAULT 'BOB',
    region TEXT,
    fecha_precio TEXT DEFAULT (datetime('now')),
    url_fuente TEXT,
    fuente TEXT DEFAULT 'bd',
    vigente INTEGER DEFAULT 1,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recurso_id INTEGER,
    proveedor_id INTEGER,
    descripcion TEXT,
    nivel_busqueda INTEGER,
    precio_bruto REAL,
    unidad_origen TEXT,
    factor_conversion REAL DEFAULT 1.0,
    precio_adoptado REAL,
    moneda TEXT DEFAULT 'BOB',
    fecha_consulta TEXT DEFAULT (datetime('now')),
    vigencia_dias INTEGER DEFAULT 30,
    url_fuente TEXT,
    estado TEXT DEFAULT 'obtenida',
    nivel_confianza REAL DEFAULT 0,
    observaciones TEXT,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS recursos_apu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    tipo TEXT,
    descripcion TEXT,
    unidad TEXT,
    rendimiento REAL DEFAULT 1,
    cantidad_apu REAL DEFAULT 0,
    precio_unitario REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    fuente_precio TEXT,
    cotizacion_id INTEGER,
    bloqueado INTEGER DEFAULT 0,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS resultados_apu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    costo_materiales REAL DEFAULT 0,
    costo_mano_obra REAL DEFAULT 0,
    costo_equipos REAL DEFAULT 0,
    costo_directo REAL DEFAULT 0,
    indirectos REAL DEFAULT 0,
    utilidad REAL DEFAULT 0,
    impuestos REAL DEFAULT 0,
    precio_unitario_total REAL DEFAULT 0,
    alertas TEXT,
    fecha_generacion TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contactos_email (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER,
    asunto TEXT,
    cuerpo TEXT,
    fecha_envio TEXT DEFAULT (datetime('now')),
    estado TEXT DEFAULT 'enviado',
    respondio INTEGER DEFAULT 0,
    fecha_respuesta TEXT,
    interesado_registro INTEGER DEFAULT 0,
    recordatorio_enviado INTEGER DEFAULT 0,
    observaciones TEXT,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS respuestas_cotizacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contacto_id INTEGER,
    proveedor_id INTEGER,
    descripcion TEXT,
    unidad TEXT,
    precio REAL,
    moneda TEXT DEFAULT 'BOB',
    plazo_entrega TEXT,
    disponibilidad TEXT,
    vigencia_dias INTEGER DEFAULT 30,
    observaciones TEXT,
    fecha_respuesta TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (contacto_id) REFERENCES contactos_email(id) ON DELETE CASCADE,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil TEXT DEFAULT 'contratista',     -- contratista | entidad | proveedor
    nombre_empresa TEXT NOT NULL,
    nit TEXT,
    seprec TEXT,
    direccion TEXT,
    email TEXT NOT NULL UNIQUE,
    encargado_nombre TEXT,
    encargado_whatsapp TEXT,
    password_hash TEXT NOT NULL,
    email_verificado INTEGER DEFAULT 0,
    token_verificacion TEXT,
    nit_verificado INTEGER DEFAULT 0,
    nit_razon_social TEXT,
    nit_estado TEXT,
    estado TEXT DEFAULT 'activo',
    fecha_creacion TEXT DEFAULT (datetime('now')),
    ultimo_acceso TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite con row_factory tipo dict y FK activas."""
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Context manager que hace commit/rollback automáticamente."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Error en transacción de base de datos")
        raise
    finally:
        conn.close()


# Columnas añadidas tras la versión inicial -> migración no destructiva.
_MIGRACIONES = {
    "proyectos": {
        "tipo_cambio": "REAL DEFAULT 6.96",
        "factor_beneficios_sociales": "REAL DEFAULT 0.55",
        "factor_iva_mano_obra": "REAL DEFAULT 0.1494",
        "factor_herramientas": "REAL DEFAULT 0.05",
        "factor_iva_equipo": "REAL DEFAULT 0.0",
        "factor_gastos_generales": "REAL DEFAULT 0.10",
        "factor_utilidad_sabs": "REAL DEFAULT 0.10",
        "factor_it": "REAL DEFAULT 0.0309",
        "entidad": "TEXT DEFAULT ''",
        "proponente": "TEXT DEFAULT ''",
        "representante_legal": "TEXT DEFAULT ''",
        "ci_representante": "TEXT DEFAULT ''",
        "plazo_dias": "INTEGER DEFAULT 180",
        "solicita_anticipo": "INTEGER DEFAULT 0",
        "porcentaje_anticipo": "REAL DEFAULT 0.0",
    },
    "items": {
        "validado_tecnico": "INTEGER DEFAULT 0",
    },
}


def _migrar(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a bases existentes (ALTER TABLE idempotente)."""
    for tabla, columnas in _MIGRACIONES.items():
        existentes = {row["name"] for row in
                      conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
        for col, definicion in columnas.items():
            if col not in existentes:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {definicion}")
                logger.info("Migración: columna %s.%s agregada", tabla, col)


def init_db() -> None:
    """Crea el esquema completo si no existe y aplica migraciones."""
    with db_session() as conn:
        conn.executescript(SCHEMA)
        _migrar(conn)
    logger.info("Esquema de base de datos inicializado en %s", settings.DB_PATH)


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada en {settings.DB_PATH}")
