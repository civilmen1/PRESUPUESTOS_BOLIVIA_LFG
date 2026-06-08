"""Banco de APU de referencia (rendimientos y precios reales de Bolivia).

Carga data/banco_apu.json (importado de formularios B-2 oficiales) y lo expone
para:
  - buscar un APU de referencia por similitud con la descripcion de un item,
  - alimentar precios elementales reales (Nivel 1 del cotizador),
  - dar contexto/ejemplos a la IA.
"""
from __future__ import annotations

from functools import lru_cache

from config import settings
from config.logging_config import get_logger
from core.text_cleaner import normalizar, tokenizar

logger = get_logger(__name__)

# Semilla versionada en el repo (banco inicial) y copia PERSISTENTE en el disco.
_RUTA_SEED = settings.DATA_DIR / "banco_apu.json"
_RUTA = settings.PERSIST_DIR / "banco_apu.json"


def respaldar(ruta=None, etiqueta: str = "") -> None:
    """Guarda una copia de seguridad del banco ANTES de reescribirlo.

    Crea  banco_apu.<fecha>-<etiqueta>.bak.json  junto al banco y conserva
    solo los 10 respaldos mas recientes. Asi ninguna reescritura (auto-saneo,
    reemplazo de banco, aprobacion de aportes) puede destruir datos sin red."""
    from datetime import datetime
    ruta = ruta or _RUTA
    try:
        if not ruta.exists() or ruta.stat().st_size == 0:
            return
        sello = datetime.now().strftime("%Y%m%d-%H%M%S")
        suf = f"-{etiqueta}" if etiqueta else ""
        destino = ruta.with_name(f"{ruta.stem}.{sello}{suf}.bak.json")
        if not destino.exists():
            destino.write_text(ruta.read_text(encoding="utf-8"),
                               encoding="utf-8")
        respaldos = sorted(ruta.parent.glob(f"{ruta.stem}.*.bak.json"))
        for viejo in respaldos[:-10]:
            try:
                viejo.unlink()
            except Exception:
                pass
    except Exception:
        pass


def ruta_persistente():
    """Ruta del banco en el disco persistente; la siembra desde el repo la
    primera vez (para no perder los APU iniciales)."""
    try:
        if not _RUTA.exists() and _RUTA_SEED.exists() and _RUTA != _RUTA_SEED:
            _RUTA.write_text(_RUTA_SEED.read_text(encoding="utf-8"),
                             encoding="utf-8")
    except Exception:
        pass
    return _RUTA


def listar_respaldos() -> list:
    """Respaldos disponibles del banco, del mas reciente al mas antiguo."""
    try:
        return sorted(_RUTA.parent.glob(f"{_RUTA.stem}.*.bak.json"),
                      reverse=True)
    except Exception:
        return []


def contar_apus_archivo(ruta) -> int:
    """Cuantos APU tiene un archivo de banco (para mostrar en la UI)."""
    import json
    try:
        return len(json.loads(ruta.read_text(encoding="utf-8")).get("apus", []))
    except Exception:
        return 0


def restaurar(ruta_bak) -> int:
    """Restaura el banco desde un respaldo. Antes guarda copia del actual.
    Devuelve cuantos APU quedaron tras restaurar."""
    respaldar(_RUTA, "previo-restaurar")
    _RUTA.write_text(ruta_bak.read_text(encoding="utf-8"), encoding="utf-8")
    _cargar.cache_clear()
    return len(listar_apus())


@lru_cache(maxsize=1)
def _cargar() -> dict:
    import json
    for ruta in (ruta_persistente(), _RUTA_SEED):
        try:
            if ruta.exists():
                banco = json.loads(ruta.read_text(encoding="utf-8"))
                _normalizar_mano_obra(banco, ruta)
                return banco
        except Exception:
            continue
    return {"apus": []}


def _normalizar_mano_obra(banco: dict, ruta) -> None:
    """Aplica las reglas de mano de obra al banco completo al cargarlo:
    sin 'peón', siempre en horas (HR) y costo horario dentro de 20-50 Bs.

    Si corrige algo, reescribe el archivo (auto-saneo de bancos importados,
    p.ej. los 4000 APU traídos del servidor)."""
    import json
    from core import mano_obra
    cambios = 0
    for apu in banco.get("apus", []):
        for r in apu.get("mano_obra", []) or []:
            if not isinstance(r, dict):
                continue
            desc = mano_obra.limpiar_descripcion(r.get("descripcion", ""))
            precio = mano_obra.precio_valido(desc, r.get("precio", 0))
            if (desc != r.get("descripcion") or precio != r.get("precio")
                    or r.get("unidad") != "HR"):
                r["descripcion"], r["precio"], r["unidad"] = desc, precio, "HR"
                cambios += 1
    if cambios:
        try:
            respaldar(ruta, "saneo")
            ruta.write_text(json.dumps(banco, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        except Exception:
            pass


def hay_banco() -> bool:
    return bool(_cargar().get("apus"))


def listar_apus() -> list[dict]:
    return _cargar().get("apus", [])


def _limpiar_desc(actividad: str) -> str:
    """Quita la numeracion inicial '3.- ' de la actividad."""
    txt = actividad.split("-", 1)[-1] if "-" in actividad[:6] else actividad
    return txt.strip()


# Cache en memoria de los vectores (embeddings) de las actividades del banco.
_emb_banco: dict = {"firma": None, "vectores": None}


def _vectores_banco(apus: list[dict]):
    """Embeddings de las actividades del banco, cacheados por firma del contenido.
    Devuelve None si no hay proveedor de embeddings."""
    import hashlib
    from core import embeddings
    firma = hashlib.sha1(
        "\n".join(a.get("actividad", "") for a in apus).encode("utf-8")
    ).hexdigest()
    if _emb_banco["firma"] == firma:
        return _emb_banco["vectores"]
    descs = [_limpiar_desc(a.get("actividad", "")) for a in apus]
    vects = embeddings.embed(descs)
    _emb_banco["firma"], _emb_banco["vectores"] = firma, vects
    return vects


def buscar_apu(descripcion: str, umbral: float = 0.3) -> dict | None:
    """Devuelve el APU del banco mas parecido a la descripcion (o None).

    1) Si hay embeddings disponibles, busca por SIGNIFICADO (coseno).
    2) Si no, cae a similitud de palabras (Jaccard), como siempre.
    """
    apus = listar_apus()
    if not apus:
        return None

    # 1) Busqueda semantica (embeddings) ------------------------------------
    try:
        from core import embeddings
        if embeddings.disponible():
            qv = embeddings.embed_uno(descripcion)
            vects = _vectores_banco(apus)
            if qv and vects:
                mejor, mejor_cos = None, 0.55  # umbral de coseno semantico
                for a, v in zip(apus, vects):
                    s = embeddings.coseno(qv, v)
                    if s > mejor_cos:
                        mejor, mejor_cos = a, s
                if mejor is not None:
                    return mejor
    except Exception:
        logger.debug("Busqueda semantica no disponible; uso TF-IDF", exc_info=True)

    # 2) Respaldo por palabras (Jaccard) ------------------------------------
    q = set(tokenizar(descripcion))
    if not q:
        return None
    mejor, mejor_score = None, umbral
    for a in apus:
        toks = set(tokenizar(_limpiar_desc(a.get("actividad", ""))))
        if not toks:
            continue
        inter = len(q & toks)
        union = len(q | toks) or 1
        score = inter / union
        if score > mejor_score:
            mejor, mejor_score = a, score
    return mejor


def precios_elementales() -> dict:
    """Diccionario {descripcion_normalizada: {precio, unidad, descripcion}} con
    todos los insumos del banco (para usar como precios de referencia)."""
    out: dict[str, dict] = {}
    for a in listar_apus():
        for grupo in ("materiales", "mano_obra", "equipo"):
            for r in a.get(grupo, []):
                desc = r.get("descripcion", "").strip()
                if not desc or not r.get("precio"):
                    continue
                clave = normalizar(desc)
                # conservar el de mayor precio si se repite (mas conservador)
                if clave not in out or r["precio"] > out[clave]["precio"]:
                    out[clave] = {"precio": float(r["precio"]),
                                  "unidad": r.get("unidad", ""),
                                  "descripcion": desc}
    return out


def a_markdown(max_apus: int = 0) -> str:
    """Devuelve el banco en Markdown compacto (para usar como contexto de IA
    con bajo consumo de tokens). max_apus=0 incluye todos."""
    apus = listar_apus()
    if max_apus:
        apus = apus[:max_apus]
    lineas = ["# Banco de APU de referencia (Bolivia)"]
    for a in apus:
        lineas.append(f"\n## {_limpiar_desc(a.get('actividad',''))} "
                      f"[{a.get('unidad','')}]")
        for grupo, etq in (("materiales", "MAT"), ("mano_obra", "MO"),
                           ("equipo", "EQ")):
            for r in a.get(grupo, []):
                lineas.append(f"- {etq}: {r.get('descripcion','')} | "
                              f"{r.get('unidad','')} | {r.get('cantidad',0)} | "
                              f"Bs {r.get('precio',0)}")
    return "\n".join(lineas)


def guardar_markdown() -> str:
    """Guarda el banco en Markdown (data/banco_apu.md) y devuelve la ruta."""
    ruta = settings.PERSIST_DIR / "banco_apu.md"
    ruta.write_text(a_markdown(), encoding="utf-8")
    return str(ruta)


def buscar_precio(descripcion: str) -> dict | None:
    """Busca el precio de un insumo en el banco por coincidencia de palabras."""
    elem = precios_elementales()
    desc_norm = normalizar(descripcion)
    # coincidencia exacta
    if desc_norm in elem:
        return elem[desc_norm]
    # coincidencia por palabras clave
    palabras = [w for w in desc_norm.split() if len(w) >= 4]
    if not palabras:
        return None
    mejor, mejor_score = None, 0
    for clave, info in elem.items():
        score = sum(1 for w in palabras if w in clave)
        if score > mejor_score:
            mejor, mejor_score = info, score
    return mejor if mejor_score >= 1 else None
