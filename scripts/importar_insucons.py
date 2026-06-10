"""Importador de Analisis de Precios Unitarios desde insucons.com al banco.

QUE HACE Y QUE NO (igual criterio que importar_cwicr):
  - CONSERVA los RENDIMIENTOS (descripcion, unidad y cantidad de cada material,
    mano de obra y equipo por unidad de obra).
  - DESCARTA los precios de insucons: cada recurso entra con precio 0, para
    repreciarlo con TUS tarifas bolivianas.
  - Normaliza la mano de obra (sin 'peon' -> 'ayudante', unidad en horas).
  - Marca el origen con  "fuente": "Insucons"  para que quede atribuido.

IMPORTANTE (uso responsable):
  insucons.com es una plataforma comercial. Que puedas navegarla no implica
  derecho a copiar su base completa. Usa esto para tomar RENDIMIENTOS de
  referencia (normas tecnicas) para uso interno, repreciando con tus tarifas,
  y revisa antes su robots.txt y sus terminos. La responsabilidad es de quien
  lo ejecuta.

USO (en TU PC, que si tiene salida a internet):
  # Prueba con UNA pagina guardada (Ctrl+S) sin tocar la red:
  python -m scripts.importar_insucons --html pagina_apu.html

  # Recorre los grupos y trae solo lo que te interese (no guarda, solo resumen):
  python -m scripts.importar_insucons \
      https://www.insucons.com/analisis-precio-unitario/hh/grupos \
      --contiene hormigon,acero,pintura --max 50

  # Lo mismo pero AGREGANDO al banco (sin reemplazar):
  python -m scripts.importar_insucons <url_grupos> --contiene hormigon --guardar

NOTA: el parser de la TABLA es generico (detecta columnas por encabezado y
secciones por 'MATERIALES/MANO DE OBRA/EQUIPO'). Si la pagina real difiere,
ajusta los sinonimos de _H_* / _SECCIONES o pasa una muestra para afinarlo.
"""
from __future__ import annotations

import re
import sys
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

from config import settings
from config.logging_config import get_logger
from core.text_cleaner import normalizar

logger = get_logger(__name__)

# --- Sinonimos de encabezado de columna (se comparan normalizados) ----------
_H_DESC = ("descripcion", "insumo", "detalle", "recurso", "material", "concepto")
_H_UND = ("unidad", "und", "unid", "u.")
_H_CANT = ("cantidad", "cant", "rendimiento", "consumo", "coeficiente")

# --- Encabezados de seccion dentro de la tabla ------------------------------
_SECCIONES = (
    ("mano de obra", "mano_obra"),
    ("obrero", "mano_obra"),
    ("equipo", "equipo"),
    ("maquinaria", "equipo"),
    ("herramient", "equipo"),
    ("material", "materiales"),  # va al final: 'material' es subcadena amplia
)

# --- Filas que NO son recursos sino totales/calculo -------------------------
_EXCLUIR = (
    "total", "subtotal", "sub total", "costo", "precio unitario",
    "gastos generales", "utilidad", "impuesto", "beneficios sociales",
    "cargas sociales", "descripcion", "insumo",
)

# Palabras para clasificar un recurso cuando la tabla no trae secciones.
_KW_MANO_OBRA = ("obrero", "peon", "peón", "ayudante", "oficial", "albanil",
                 "albañil", "maestro", "capataz", "operario", "plomero",
                 "electricista", "pintor", "fierrista", "soldador", "carpintero")
_KW_EQUIPO = ("maquina", "máquina", "equipo", "mezcladora", "vibrador",
              "excavadora", "grua", "grúa", "compresor", "retroexcavadora",
              "volqueta", "camion", "camión", "cargador", "herramient")


def _txt(nodo) -> str:
    return " ".join(nodo.get_text(" ", strip=True).split()) if nodo else ""


def _num(v) -> float:
    """Convierte '1.234,56' o '350,00' o '0.55' a float (estilo es/us)."""
    s = re.sub(r"[^\d,.\-]", "", str(v or "").strip())
    if not s or s in ("-", ".", ","):
        return 0.0
    if "," in s and "." in s:
        # el ultimo separador manda como decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # europeo
        else:
            s = s.replace(",", "")                      # us (coma = miles)
    else:
        s = s.replace(",", ".")                         # solo coma -> decimal
    try:
        return float(s)
    except ValueError:
        return 0.0


def _seccion_de(texto: str) -> Optional[str]:
    n = re.sub(r"^[\d\.\)\-\s>°º]+", "", normalizar(texto)).strip()
    if not n:
        return None
    for clave, destino in _SECCIONES:
        if n.startswith(clave) or n == clave:
            return destino
    return None


def _clasificar(desc: str) -> str:
    n = normalizar(desc)
    if any(k in n for k in _KW_MANO_OBRA):
        return "mano_obra"
    if any(k in n for k in _KW_EQUIPO):
        return "equipo"
    return "materiales"


def _es_excluible(desc: str) -> bool:
    n = normalizar(desc)
    return (not n) or "%" in desc or any(n.startswith(k) for k in _EXCLUIR)


def _mapear_columnas(celdas_norm: list[str]):
    """Dada la fila de encabezado normalizada, ubica desc/unidad/cantidad."""
    col_desc = col_und = col_cant = None
    for j, n in enumerate(celdas_norm):
        if col_und is None and any(n.startswith(h) for h in _H_UND):
            col_und = j
        elif col_cant is None and any(n.startswith(h) for h in _H_CANT):
            col_cant = j
        elif col_desc is None and any(n.startswith(h) for h in _H_DESC):
            col_desc = j
    if col_desc is None and col_und is not None:
        col_desc = max(0, col_und - 1)
    return col_desc, col_und, col_cant


def _es_encabezado(celdas_norm: list[str]) -> bool:
    tiene_desc = any(any(n.startswith(h) for h in _H_DESC) for n in celdas_norm)
    tiene_und = any(any(n.startswith(h) for h in _H_UND) for n in celdas_norm)
    return tiene_desc and tiene_und


def _filas(tabla):
    for tr in tabla.find_all("tr"):
        celdas = tr.find_all(["td", "th"])
        yield [_txt(c) for c in celdas]


def parsear_tabla(tabla) -> dict:
    """Extrae materiales/mano_obra/equipo de UNA tabla de APU. Precio = 0."""
    grupos = {"materiales": [], "mano_obra": [], "equipo": []}
    col_desc = col_und = col_cant = None
    seccion = None
    for cols in _filas(tabla):
        if not any(cols):
            continue
        norm = [normalizar(c) for c in cols]

        if _es_encabezado(norm):
            col_desc, col_und, col_cant = _mapear_columnas(norm)
            continue

        # Fila de seccion: una sola celda (o casi) con la palabra clave y sin
        # numeros (cantidad/precio vacios).
        texto_fila = " ".join(c for c in cols if c)
        sec = _seccion_de(texto_fila)
        celdas_con_texto = [c for c in cols if c]
        if sec and len(celdas_con_texto) <= 2:
            seccion = sec
            continue

        if col_desc is None:
            continue
        desc = cols[col_desc] if col_desc < len(cols) else ""
        if _es_excluible(desc):
            continue
        und = cols[col_und] if col_und is not None and col_und < len(cols) else ""
        cant = _num(cols[col_cant]) if col_cant is not None and \
            col_cant < len(cols) else 0.0

        destino = seccion or _clasificar(desc)
        recurso = {"codigo": "", "descripcion": desc, "unidad": und,
                   "cantidad": cant, "precio": 0}   # PRECIO DESCARTADO a proposito
        if destino == "mano_obra":
            from core import mano_obra
            recurso["descripcion"] = mano_obra.limpiar_descripcion(desc)
            recurso["unidad"] = "HR"
        grupos[destino].append(recurso)
    return grupos


def _titulo_y_unidad(soup) -> tuple[str, str]:
    """Heuristica: actividad = primer h1/h2/title; unidad = texto 'Unidad: X'
    que aparezca antes de la primera tabla."""
    actividad = ""
    for sel in ("h1", "h2", "title"):
        nodo = soup.find(sel)
        if nodo and _txt(nodo):
            actividad = _txt(nodo)
            break
    # texto de cabecera (antes de la primera tabla) para buscar la unidad
    cabecera = ""
    for el in soup.find_all(string=True):
        if el.find_parent("table"):
            continue
        cabecera += " " + str(el)
    m = re.search(r"\b(?:unidad|und)\.?\s*[:=]?\s*([A-Za-z0-9²³/\.]{1,8})",
                  cabecera, re.IGNORECASE)
    unidad = m.group(1).strip(" .") if m else ""
    return actividad, unidad


def parsear_apu(html: str, url: str = "") -> Optional[dict]:
    """Parsea UNA pagina de APU de insucons y devuelve el dict del banco."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tablas = soup.find_all("table")
    if not tablas:
        return None
    # Elige la tabla con mas filas (la del detalle del APU).
    tabla = max(tablas, key=lambda t: len(t.find_all("tr")))
    grupos = parsear_tabla(tabla)
    if not (grupos["materiales"] or grupos["mano_obra"] or grupos["equipo"]):
        return None
    actividad, unidad = _titulo_y_unidad(soup)
    return {"actividad": actividad or "APU sin titulo", "unidad": unidad,
            "cantidad": 1.0, **grupos, "fuente": "Insucons", "url": url}


# --------------------------------------------------------------------------- #
#  Recorrido en red (se ejecuta en TU PC; este entorno no tiene salida)
# --------------------------------------------------------------------------- #
# Prefijo de la seccion de APUs en insucons.
_PREFIJO_APU = "/analisis-precio-unitario/"
# Una pagina de LISTADO de grupo termina en  /grupos/<id>/<slug>  (sin mas
# segmentos). Los APUs individuales cuelgan mas abajo o por otra ruta.
_RE_GRUPO_LISTADO = re.compile(r"/grupos/\d+/[^/]+/?$")

# insucons bloquea User-Agents de bot (403). Hay que parecer un navegador.
_HEADERS_NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _descubrir_enlaces(html: str, base_url: str,
                       patron: Optional[str] = None) -> list[str]:
    """Saca de la pagina de grupo los enlaces a APUs individuales.

    Por defecto toma los enlaces bajo /analisis-precio-unitario/ que NO sean a
    su vez paginas de listado de grupo y que no sean la propia pagina. Con
    `patron` (regex) se filtra exactamente por la ruta del item."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    re_patron = re.compile(patron) if patron else None
    seed = urlparse(base_url).path.rstrip("/")
    vistos: dict[str, None] = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"]).split("#")[0]
        path = urlparse(full).path
        if re_patron:
            if re_patron.search(path):
                vistos.setdefault(full, None)
            continue
        if (_PREFIJO_APU in path and path.rstrip("/") != seed
                and not _RE_GRUPO_LISTADO.search(path)):
            vistos.setdefault(full, None)
    return list(vistos)


def _descargar(url: str, sesion=None) -> Optional[str]:
    import requests
    # Permite forzar un UA propio por entorno; si no, usa el de navegador.
    headers = dict(_HEADERS_NAVEGADOR)
    ua_env = settings.SCRAPER_USER_AGENT
    if ua_env and "Bot" not in ua_env:
        headers["User-Agent"] = ua_env
    cliente = sesion or requests
    try:
        r = cliente.get(url, headers=headers, timeout=settings.SCRAPER_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        logger.warning("No se pudo descargar %s: %s", url, exc)
        return None


def importar_insucons(url_grupos: str, contiene: Optional[list] = None,
                      max_apus: Optional[int] = None,
                      demora: float = 1.0,
                      patron: Optional[str] = None) -> list[dict]:
    """Recorre la pagina de grupos -> cada APU -> rendimientos (precio 0)."""
    import requests
    contiene = [c.strip().lower() for c in (contiene or []) if c.strip()]
    sesion = requests.Session()
    html = _descargar(url_grupos, sesion)
    if not html:
        logger.warning("Sin HTML de %s (¿403 anti-bot? prueba SCRAPER_USER_AGENT "
                       "de navegador o el modo --html).", url_grupos)
        return []
    enlaces = _descubrir_enlaces(html, url_grupos, patron=patron)
    logger.info("APUs encontrados en la pagina de grupos: %d", len(enlaces))
    apus: list[dict] = []
    for i, enlace in enumerate(enlaces):
        if max_apus and len(apus) >= max_apus:
            break
        pagina = _descargar(enlace, sesion)
        if not pagina:
            continue
        apu = parsear_apu(pagina, url=enlace)
        if not apu:
            continue
        if contiene and not any(p in apu["actividad"].lower() for p in contiene):
            continue
        apus.append(apu)
        if demora:
            time.sleep(demora)  # cortesia con el servidor
    return apus


def diagnostico(url_grupos: str, patron: Optional[str] = None,
                ruta_salida: str = "insucons_muestra.html") -> None:
    """Baja el grupo + el PRIMER APU, guarda su HTML y describe que contiene.

    Sirve para afinar el parser cuando 'APUs obtenidos: 0': muestra cuantas
    tablas hay, los encabezados de cada una y si la pagina parece traer la
    tabla en el HTML o cargarla por JavaScript."""
    import requests
    from bs4 import BeautifulSoup
    sesion = requests.Session()
    html = _descargar(url_grupos, sesion)
    if not html:
        print("No se pudo bajar la pagina de grupos (revisa red / 403).")
        return
    enlaces = _descubrir_enlaces(html, url_grupos, patron=patron)
    print(f"Enlaces a APU encontrados: {len(enlaces)}")
    for e in enlaces[:5]:
        print("   ", e)
    if not enlaces:
        return
    pagina = _descargar(enlaces[0], sesion)
    if not pagina:
        print("No se pudo bajar el primer APU.")
        return
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(pagina)
    print(f"\nHTML del primer APU guardado en: {ruta_salida}"
          f"  ({len(pagina)} caracteres)")
    soup = BeautifulSoup(pagina, "html.parser")
    tablas = soup.find_all("table")
    print(f"Tablas <table> en la pagina: {len(tablas)}")
    for i, t in enumerate(tablas):
        filas = t.find_all("tr")
        prim = filas[0].get_text(" | ", strip=True)[:120] if filas else ""
        print(f"  tabla #{i}: {len(filas)} filas | 1a fila: {prim}")
    # Pistas de render por JavaScript (la tabla no viene en el HTML plano).
    bajo = pagina.lower()
    if not tablas:
        for pista in ("vue", "react", "ng-", "data-v-", "__next", "axios",
                      "vue.js", "app.js"):
            if pista in bajo:
                print(f"  (posible carga por JavaScript: aparece '{pista}')")
                break
    # Que ve el parser actual:
    apu = parsear_apu(pagina, url=enlaces[0])
    if apu:
        print(f"\nParser actual -> actividad='{apu['actividad'][:50]}' "
              f"unidad='{apu['unidad']}' M:{len(apu['materiales'])} "
              f"MO:{len(apu['mano_obra'])} EQ:{len(apu['equipo'])}")
    else:
        print("\nParser actual -> no reconocio la tabla (0 recursos).")
    print("\n>>> Pega aqui el contenido de", ruta_salida,
          "(o un trozo con la tabla) para afinar el parser.")


def _resumen(apus: list[dict]) -> None:
    print(f"APUs obtenidos (rendimientos, sin precios): {len(apus)}")
    for a in apus[:8]:
        print(f"  - {a['actividad'][:55]} [{a.get('unidad','')}] "
              f"M:{len(a['materiales'])} MO:{len(a['mano_obra'])} "
              f"EQ:{len(a['equipo'])}")
    if len(apus) > 8:
        print(f"  ... y {len(apus) - 8} mas")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    contiene = None
    if "--contiene" in args:
        contiene = args[args.index("--contiene") + 1].split(",")
    max_apus = None
    if "--max" in args:
        max_apus = int(args[args.index("--max") + 1])
    patron = None
    if "--patron" in args:
        patron = args[args.index("--patron") + 1]

    # Modo diagnostico: baja un APU, guarda su HTML y describe que contiene.
    if "--diag" in args:
        diagnostico(args[0], patron=patron)
        return

    # Modo offline: parsear un HTML guardado (para probar sin red).
    if "--html" in args:
        ruta = args[args.index("--html") + 1]
        with open(ruta, encoding="utf-8") as f:
            apu = parsear_apu(f.read(), url=ruta)
        apus = [apu] if apu else []
    else:
        url = args[0]
        apus = importar_insucons(url, contiene=contiene, max_apus=max_apus,
                                 patron=patron)

    if contiene and "--html" in args and apus:
        apus = [a for a in apus
                if any(p.strip().lower() in a["actividad"].lower()
                       for p in contiene)]
    _resumen(apus)

    if "--guardar" in args and apus:
        from scripts.importar_apu_banco import guardar_banco
        from core import banco_apu
        res = guardar_banco(apus, proyecto="Insucons", reemplazar=False)
        banco_apu._cargar.cache_clear()
        print(f"\nAgregados {res['agregados']}, actualizados "
              f"{res['actualizados']}, omitidos {res['omitidos']}. "
              f"Total en banco: {res['total']}.")
        print("Recuerda REPRECIAR con tus tarifas bolivianas (precios en 0).")


if __name__ == "__main__":
    main()
