"""Importador de presupuestos en formato BC3 / FIEBDC-3 al Banco de APU.

FIEBDC-3 (extension .bc3) es el estandar de intercambio de bases de precios y
presupuestos usado por CYPE (Generador de precios Bolivia), Arquimedes, Presto,
etc. Permite alimentar el banco con APUs reales SIN consumir tokens.

Estructura del formato (texto plano):
  - Separador de registro: '~'  ·  de campo: '|'  ·  de subcampo: '\\'
  - ~C : Concepto -> CODIGO | UNIDAD | RESUMEN | PRECIO | FECHA | TIPO
  - ~D : Descomposicion -> CODIGO_PADRE | HIJO1 \\ FACTOR1 \\ RENDIMIENTO1 \\ HIJO2 ...
  - ~T : Texto/descripcion larga -> CODIGO | TEXTO
  - ~V : Cabecera/version (propiedades del fichero)

Un concepto SIN descomposicion es un recurso elemental (material, mano de obra o
equipo). Un concepto CON descomposicion cuyos hijos son elementales es un APU
(partida). Los capitulos descomponen en sub-capitulos o partidas.

Clasificacion de recursos (convencion CYPE y comun en Bolivia):
  - codigo que empieza con 'mo' -> mano de obra
  - 'mq' -> equipo / maquinaria
  - 'mt' -> material
  - '%'  -> medios auxiliares / costes indirectos (se ignora)
  - otro -> material por defecto (si es elemental)
"""
from __future__ import annotations

from core.text_cleaner import normalizar  # noqa: F401  (consistencia con banco)


def _num(v: str) -> float:
    """Convierte a float aceptando coma o punto decimal."""
    s = (v or "").strip().replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def _decodificar(datos: bytes) -> str:
    """Los .bc3 suelen venir en Latin-1 / Windows-1252; se intenta UTF-8 antes."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return datos.decode(enc)
        except UnicodeDecodeError:
            continue
    return datos.decode("latin-1", errors="replace")


def _registros(texto: str):
    """Itera (tipo, campos[]) por cada registro '~' del fichero."""
    # El formato permite que un registro abarque varias lineas; se unen y luego
    # se parte por '~'. Se respeta el separador de campo '|'.
    cuerpo = texto.replace("\r\n", "\n").replace("\r", "\n")
    for bruto in cuerpo.split("~"):
        bruto = bruto.strip("\n").strip()
        if not bruto:
            continue
        # El tipo es la(s) letra(s) antes del primer '|'.
        cabeza, _, resto = bruto.partition("|")
        tipo = cabeza.strip().upper()[:1]
        if not tipo:
            continue
        # Campos del registro (se quitan saltos de linea internos).
        campos = [c.replace("\n", " ").strip() for c in resto.split("|")]
        yield tipo, campos


def _clasificar(codigo: str) -> str | None:
    """material | mano_obra | equipo | None (auxiliar/ignorar)."""
    c = (codigo or "").strip().lower()
    if not c:
        return None
    if c.startswith("%"):
        return None
    if c.startswith("mo") or c.startswith("o"):
        return "mano_obra"
    if c.startswith("mq") or c.startswith("q") or c.startswith("m_"):
        return "equipo"
    if c.startswith("mt") or c.startswith("p"):
        return "material"
    return "material"  # elemental sin prefijo conocido -> material


def parsear(datos: bytes) -> tuple[dict, dict]:
    """Devuelve (conceptos, descomposiciones).

    conceptos: {codigo: {unidad, resumen, precio}}
    descomposiciones: {codigo_padre: [(codigo_hijo, rendimiento), ...]}
    """
    texto = _decodificar(datos)
    conceptos: dict[str, dict] = {}
    descomp: dict[str, list[tuple[str, float]]] = {}

    for tipo, campos in _registros(texto):
        if tipo == "C" and campos:
            codigo = campos[0].split("\\")[0].strip()
            if not codigo:
                continue
            unidad = campos[1].strip() if len(campos) > 1 else ""
            resumen = campos[2].strip() if len(campos) > 2 else ""
            # El precio puede traer varios valores por '\' (monedas/regiones).
            precio = 0.0
            if len(campos) > 3:
                precio = _num(campos[3].split("\\")[0])
            conceptos[codigo] = {"unidad": unidad, "resumen": resumen,
                                 "precio": precio}
        elif tipo == "D" and len(campos) >= 2:
            padre = campos[0].split("\\")[0].strip()
            if not padre:
                continue
            partes = [p.strip() for p in campos[1].split("\\")]
            hijos: list[tuple[str, float]] = []
            # Grupos de 3: hijo, factor, rendimiento.
            for k in range(0, len(partes) - 2, 3):
                hijo = partes[k]
                rend = _num(partes[k + 2])
                if hijo:
                    hijos.append((hijo, rend))
            if hijos:
                descomp.setdefault(padre, []).extend(hijos)
        elif tipo == "T" and len(campos) >= 2:
            # Texto largo: completa el resumen si estaba vacio.
            codigo = campos[0].split("\\")[0].strip()
            txt = campos[1].strip()
            if codigo in conceptos and not conceptos[codigo]["resumen"] and txt:
                conceptos[codigo]["resumen"] = txt[:200]
    return conceptos, descomp


def extraer_apus(datos: bytes) -> list[dict]:
    """Extrae APUs (partidas con descomposicion en recursos elementales) en el
    mismo formato que usa el Banco de APU."""
    conceptos, descomp = parsear(datos)
    apus: list[dict] = []

    for padre, hijos in descomp.items():
        concepto = conceptos.get(padre)
        if not concepto:
            continue
        materiales: list[dict] = []
        mano_obra: list[dict] = []
        equipo: list[dict] = []
        for codigo_hijo, rend in hijos:
            hijo = conceptos.get(codigo_hijo)
            if not hijo:
                continue
            # Si el hijo tiene su propia descomposicion es una sub-partida:
            # se omite aqui (se exporta por si misma como APU).
            if codigo_hijo in descomp:
                continue
            clase = _clasificar(codigo_hijo)
            if clase is None:
                continue
            recurso = {"codigo": codigo_hijo,
                       "descripcion": hijo.get("resumen", "") or codigo_hijo,
                       "unidad": hijo.get("unidad", ""),
                       "cantidad": rend,
                       "precio": hijo.get("precio", 0.0)}
            if clase == "mano_obra":
                mano_obra.append(recurso)
            elif clase == "equipo":
                equipo.append(recurso)
            else:
                materiales.append(recurso)

        # Es un APU solo si tiene al menos un recurso elemental.
        if materiales or mano_obra or equipo:
            apus.append({
                "actividad": concepto.get("resumen", "") or padre,
                "unidad": concepto.get("unidad", ""),
                "cantidad": 1.0,
                "materiales": materiales,
                "mano_obra": mano_obra,
                "equipo": equipo})
    return apus
