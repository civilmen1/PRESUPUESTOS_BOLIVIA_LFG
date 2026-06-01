"""Extractor de información técnica por ítem.

A partir del texto de las especificaciones vinculadas a un ítem (módulo → ítem),
extrae información estructurada para enriquecer cada actividad:

  - alcance / descripción del trabajo
  - materiales mencionados
  - mano de obra / personal mencionado
  - equipo y herramientas mencionados
  - normas y ensayos citados
  - unidad y forma de medición / pago

Funciona offline con reglas y diccionarios (sin LLM). Devuelve un objeto
InfoTecnica que la UI muestra y que el motor de APU usa para inferir mejor
los recursos de cada ítem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from core.text_cleaner import limpiar_texto, normalizar

# --------------------------------------------------------------------------- #
# Diccionarios de detección (ampliables)
# --------------------------------------------------------------------------- #
_MATERIALES = {
    "cemento": ["cemento", "portland"], "arena": ["arena"],
    "grava": ["grava", "ripio", "gravilla"], "piedra": ["piedra", "bolon"],
    "acero": ["acero", "fierro", "varilla", "barra corrugada"],
    "ladrillo": ["ladrillo", "gambote", "bloque"],
    "madera": ["madera", "tabla", "encofrado", "cimbra"],
    "tuberia": ["tuberia", "tubería", "pvc", "caneria", "cañería"],
    "pintura": ["pintura", "latex", "látex", "esmalte", "barniz"],
    "ceramica": ["ceramica", "cerámica", "azulejo", "porcelanato", "baldosa"],
    "vidrio": ["vidrio", "cristal"], "yeso": ["yeso", "estuco"],
    "cable": ["cable", "conductor", "alambre"], "pegamento": ["pegamento", "cola"],
    "clavos": ["clavo", "tornillo", "alambre de amarre"],
    "impermeabilizante": ["impermeabilizante", "membrana", "asfalto"],
    "agua": ["agua"], "aditivo": ["aditivo", "acelerante", "plastificante"],
}
_MANO_OBRA = {
    "albañil": ["albañil", "albanil", "maestro albañil"],
    "ayudante": ["ayudante", "peon", "peón"],
    "maestro": ["maestro mayor", "maestro de obra"],
    "fierrista": ["fierrista", "armador"],
    "encofrador": ["encofrador", "carpintero de obra"],
    "plomero": ["plomero", "gasfiter", "instalador sanitario"],
    "electricista": ["electricista"],
    "pintor": ["pintor"], "soldador": ["soldador"],
    "operador": ["operador"],
}
_EQUIPO = {
    "mezcladora": ["mezcladora", "hormigonera", "trompo"],
    "vibradora": ["vibradora", "vibrador"],
    "retroexcavadora": ["retroexcavadora", "excavadora"],
    "volqueta": ["volqueta", "camion", "camión"],
    "compactadora": ["compactadora", "plancha", "rodillo", "vibrocompactador"],
    "amoladora": ["amoladora", "esmeril"], "soldadora": ["equipo de soldadura", "soldadora"],
    "andamios": ["andamio", "andamiaje"],
    "herramienta_menor": ["herramienta menor", "herramientas menores"],
}
_NORMAS = re.compile(
    r"\b(?:NB[\s\-]?\d+[\w\-/]*|ASTM[\s\-]?\w+|ACI[\s\-]?\d+|ISO[\s\-]?\d+|"
    r"AASHTO[\s\-]?\w+|DIN[\s\-]?\d+)\b", re.IGNORECASE)

# Secciones típicas de una especificación técnica boliviana
_SEC_ALCANCE = re.compile(r"(?:definici[oó]n|alcance|descripci[oó]n|generalidades)",
                          re.IGNORECASE)
_SEC_MEDICION = re.compile(r"(?:medici[oó]n|forma de pago|unidad de pago|"
                           r"medida y pago)", re.IGNORECASE)


@dataclass
class InfoTecnica:
    item_id: int = 0
    alcance: str = ""
    materiales: List[str] = field(default_factory=list)
    mano_obra: List[str] = field(default_factory=list)
    equipo: List[str] = field(default_factory=list)
    normas: List[str] = field(default_factory=list)
    medicion: str = ""
    resumen: str = ""
    tiene_especificacion: bool = False

    def como_texto(self) -> str:
        """Texto plano para alimentar el motor de APU (inferencia de recursos)."""
        return " ".join([self.alcance, " ".join(self.materiales),
                         " ".join(self.mano_obra), " ".join(self.equipo),
                         self.medicion])


def _detectar(texto_norm: str, diccionario: dict) -> List[str]:
    encontrados = []
    for nombre, claves in diccionario.items():
        if any(normalizar(k) in texto_norm for k in claves):
            encontrados.append(nombre)
    return encontrados


def _extraer_seccion(texto: str, patron: re.Pattern, max_chars: int = 400) -> str:
    """Extrae el párrafo que sigue a un encabezado tipo 'Alcance', 'Medición'."""
    for m in patron.finditer(texto):
        ini = m.start()
        fragmento = texto[ini:ini + max_chars].strip()
        # corta en el siguiente doble salto de línea
        corte = fragmento.find("\n\n")
        return fragmento[:corte] if corte > 40 else fragmento
    return ""


def extraer_info(item_descripcion: str, texto_especificacion: str,
                 item_id: int = 0) -> InfoTecnica:
    """Extrae información estructurada del texto de especificación de un ítem."""
    texto = limpiar_texto(texto_especificacion or "")
    base = f"{item_descripcion}\n{texto}"
    norm = normalizar(base)

    info = InfoTecnica(
        item_id=item_id,
        materiales=_detectar(norm, _MATERIALES),
        mano_obra=_detectar(norm, _MANO_OBRA),
        equipo=_detectar(norm, _EQUIPO),
        normas=sorted(set(m.group(0).upper() for m in _NORMAS.finditer(base))),
        tiene_especificacion=bool(texto.strip()),
    )

    info.alcance = _extraer_seccion(texto, _SEC_ALCANCE) or texto[:300]
    info.medicion = _extraer_seccion(texto, _SEC_MEDICION)

    partes = []
    if info.materiales:
        partes.append(f"Materiales: {', '.join(info.materiales)}")
    if info.mano_obra:
        partes.append(f"Mano de obra: {', '.join(info.mano_obra)}")
    if info.equipo:
        partes.append(f"Equipo: {', '.join(info.equipo)}")
    if info.normas:
        partes.append(f"Normas: {', '.join(info.normas)}")
    if info.medicion:
        partes.append(f"Medición/pago: {info.medicion[:120]}")
    info.resumen = " · ".join(partes) if partes else (
        "Sin especificación vinculada; se usarán mínimos por contexto."
        if not info.tiene_especificacion else "Especificación sin recursos explícitos.")
    return info
