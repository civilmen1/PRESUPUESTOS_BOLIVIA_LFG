"""Secuenciamiento lógico de obra para el cronograma (A-8 / A-9 / B-5).

Clasifica cada ítem en una FASE constructiva y construye un cronograma con
secuencia lógica boliviana:

  1. Trabajos preliminares (replanteo, instalación de faenas, limpieza)
  2. Movimiento de tierras (excavaciones, rellenos, nivelación)
  3. Obra gruesa / estructura — de abajo hacia arriba (cimientos → sobrecimiento
     → columnas/muros → losas → cubierta)
  4. Instalaciones (sanitaria, agua, eléctrica, gas)
  5. Acabados (revoques, pisos, pintura, carpintería)
  6. Obras exteriores y limpieza final

Cada fase se programa en ventanas de tiempo solapadas siguiendo precedencias
(estilo CPM/Gantt), distribuidas dentro del PLAZO CONTRACTUAL en días.
La duración de cada ítem es proporcional a su incidencia económica (peso),
de modo que las actividades más costosas duran más (ruta crítica aproximada).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from core.text_cleaner import normalizar

# Orden de fases y palabras clave para clasificar cada ítem.
FASES = [
    ("Trabajos preliminares",
     ["replanteo", "trazado", "instalacion de faenas", "faena", "letrero",
      "cartel", "limpieza inicial", "desbroce", "demolicion", "cerco", "campamento"]),
    ("Movimiento de tierras",
     ["excavacion", "relleno", "nivelacion", "movimiento de tierra", "corte",
      "terraplen", "compactacion", "zanja", "perfilado"]),
    ("Obra gruesa / estructura",
     ["cimiento", "zapata", "sobrecimiento", "hormigon", "hormigon armado",
      "columna", "viga", "losa", "muro", "mamposteria", "ladrillo", "estructura",
      "encofrado", "fierro", "acero", "cubierta", "techo", "cercha", "impermeab"]),
    ("Instalaciones",
     ["instalacion sanitaria", "agua potable", "alcantarillado", "desague",
      "tuberia", "electrica", "electrico", "cableado", "luminaria", "gas",
      "artefacto", "griferia", "inodoro", "lavamanos"]),
    ("Acabados",
     ["revoque", "revestimiento", "ceramica", "piso", "porcelanato", "pintura",
      "latex", "estuco", "cielo", "carpinteria", "puerta", "ventana", "vidrio",
      "zocalo", "acabado", "yeso", "enlucido"]),
    ("Obras exteriores y limpieza",
     ["acera", "vereda", "jardin", "exterior", "limpieza final", "limpieza general",
      "retiro", "pavimento", "enlosetado"]),
]

_FASE_INDEX = {nombre: i for i, (nombre, _) in enumerate(FASES)}


@dataclass
class ActividadProgramada:
    item: object
    fase: str
    fase_orden: int
    dia_inicio: int       # día calendario de inicio (1..plazo)
    dia_fin: int          # día calendario de fin
    mes_inicio: int       # 1..n_meses
    mes_fin: int
    peso: float = 0.0      # incidencia económica (0..1)
    monto: float = 0.0


def clasificar_fase(descripcion: str) -> tuple[str, int]:
    """Devuelve (nombre_fase, orden) para una descripción de actividad."""
    texto = normalizar(descripcion)
    mejor, mejor_orden, mejor_score = "Obra gruesa / estructura", 2, 0
    for nombre, claves in FASES:
        score = sum(1 for k in claves if normalizar(k) in texto)
        if score > mejor_score:
            mejor, mejor_orden, mejor_score = nombre, _FASE_INDEX[nombre], score
    return mejor, mejor_orden


def construir_cronograma(items, plazo_dias: int,
                         montos_por_item: dict) -> tuple[int, List[ActividadProgramada]]:
    """Construye el cronograma lógico.

    Args:
        items: lista de Item.
        plazo_dias: plazo contractual en días calendario.
        montos_por_item: {item_id: monto_total} para ponderar duraciones.

    Returns:
        (n_meses, lista de ActividadProgramada en orden de ejecución)
    """
    plazo = max(int(plazo_dias or 180), 30)
    n_meses = max(1, math.ceil(plazo / 30))

    reales = [it for it in items if getattr(it, "descripcion", "")]
    if not reales:
        return n_meses, []

    # Clasifica y ordena por fase (y dentro de la fase, por número de ítem)
    clasificados = []
    for it in reales:
        fase, orden = clasificar_fase(it.descripcion)
        monto = float(montos_por_item.get(it.id, 0.0))
        clasificados.append({"item": it, "fase": fase, "orden": orden,
                             "monto": monto})
    clasificados.sort(key=lambda x: (x["orden"], _num(x["item"].numero)))

    total_monto = sum(c["monto"] for c in clasificados) or 1.0

    # Reparto del plazo por fase: cada fase recibe una ventana proporcional al
    # monto de sus actividades, pero con solape del 20% entre fases consecutivas
    # (las fases no son estrictamente secuenciales: se encadenan tipo Gantt).
    fases_presentes = []
    for nombre, _ in FASES:
        grupo = [c for c in clasificados if c["fase"] == nombre]
        if grupo:
            fases_presentes.append((nombre, grupo))

    programadas: List[ActividadProgramada] = []
    cursor_dia = 1.0
    solape = 0.20
    for fi, (nombre, grupo) in enumerate(fases_presentes):
        monto_fase = sum(c["monto"] for c in grupo) or 1.0
        # ventana de la fase proporcional a su incidencia, mínimo ~ medio mes
        dur_fase = max(plazo * (monto_fase / total_monto), plazo / (len(fases_presentes) * 2))
        inicio_fase = cursor_dia
        # las actividades dentro de la fase se reparten secuencialmente
        sub_cursor = inicio_fase
        for c in grupo:
            peso_item = c["monto"] / monto_fase if monto_fase else 1.0 / len(grupo)
            dur_item = max(dur_fase * peso_item, 1.0)
            d_ini = int(round(sub_cursor))
            d_fin = int(round(min(plazo, sub_cursor + dur_item)))
            d_ini = max(1, min(d_ini, plazo))
            d_fin = max(d_ini, min(d_fin, plazo))
            programadas.append(ActividadProgramada(
                item=c["item"], fase=nombre, fase_orden=c["orden"],
                dia_inicio=d_ini, dia_fin=d_fin,
                mes_inicio=_mes(d_ini), mes_fin=_mes(d_fin),
                peso=c["monto"] / total_monto, monto=c["monto"]))
            sub_cursor += dur_item
        # la siguiente fase arranca con solape (no espera a terminar del todo)
        cursor_dia = inicio_fase + dur_fase * (1 - solape)

    # Garantiza que la última actividad cierre en el plazo
    if programadas:
        ult = max(programadas, key=lambda a: a.dia_fin)
        if ult.dia_fin < plazo:
            ult.dia_fin = plazo
            ult.mes_fin = _mes(plazo)

    return n_meses, programadas


def _mes(dia: int) -> int:
    return max(1, math.ceil(dia / 30))


def _num(numero) -> float:
    """Convierte el número de ítem en valor ordenable (1, 1.1, 2 ...)."""
    try:
        return float(str(numero).replace(",", ".").split()[0])
    except (ValueError, IndexError):
        return 9999.0
