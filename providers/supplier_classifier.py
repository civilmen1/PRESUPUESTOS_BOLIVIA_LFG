"""Clasificación de proveedores por rubro a partir de texto."""
from __future__ import annotations

from core.text_cleaner import normalizar
from models.supplier import TIPOS_PROVEEDOR

# keywords por categoría de proveedor
_REGLAS = {
    "ferreteria": ["ferreteria", "ferreteria", "herramienta", "clavo", "tornillo"],
    "cemento": ["cemento", "hormigon", "premezclado", "concreto", "soboce", "fancesa"],
    "acero": ["acero", "fierro", "hierro", "varilla", "siderurgica", "barra"],
    "aridos": ["arido", "arena", "grava", "ripio", "agregado", "cantera"],
    "tuberias": ["tuberia", "pvc", "plastiforte", "tuberias", "conducto"],
    "valvulas": ["valvula", "valvulas", "grifería", "griferia", "hidraulico"],
    "electricos": ["electrico", "cable", "iluminacion", "tablero", "luminaria"],
    "acabados": ["pintura", "ceramica", "porcelanato", "acabado", "revestimiento"],
    "alquiler_maquinaria": ["alquiler", "maquinaria", "retroexcavadora", "equipo pesado"],
    "transporte": ["transporte", "volqueta", "flete", "camion", "logistica"],
    "mano_obra": ["cuadrilla", "mano de obra", "constructora", "albañil", "contratista"],
}


def clasificar(texto: str) -> str:
    """Devuelve la categoría de proveedor más probable según el texto."""
    n = normalizar(texto)
    mejor, mejor_score = "otros", 0
    for categoria, kws in _REGLAS.items():
        score = sum(1 for k in kws if normalizar(k) in n)
        if score > mejor_score:
            mejor, mejor_score = categoria, score
    return mejor if mejor in TIPOS_PROVEEDOR else "otros"
