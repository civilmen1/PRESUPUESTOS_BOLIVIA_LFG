"""Vinculación semántica ítem ↔ sección técnica (motor de búsqueda jerárquico).

Estrategia de búsqueda (como un motor con IA, en dos etapas):

  Etapa 1 — MÓDULO: localiza en el documento técnico la sección que corresponde
            al módulo/capítulo al que pertenece el ítem (p. ej. "OBRA GRUESA",
            "INSTALACIONES SANITARIAS").
  Etapa 2 — ÍTEM:   dentro del ámbito de ese módulo, busca la especificación
            concreta del ítem y devuelve solo esa.

El ranking combina:
  - Similitud TF-IDF + coseno (recuperación base, offline).
  - Solape de bigramas (frases) para precisión semántica.
  - Bonus por pertenecer al módulo detectado en la Etapa 1.
  - Bonus por coincidencia de número de ítem / numeral en el título.

Funciona sin modelos pesados; la interfaz permite sustituirlo por embeddings.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Optional, Sequence

from core.text_cleaner import normalizar, tokenizar
from models.item import Item
from models.technical_source import SeccionTecnica, VinculoTecnico

_NUMERAL = re.compile(r"\b\d+(?:\.\d+){0,3}\b")


def _bigramas(tokens: List[str]) -> set:
    return {f"{a}_{b}" for a, b in zip(tokens, tokens[1:])}


class SemanticMatcher:
    """Indexa secciones técnicas y busca las más relevantes por ítem (jerárquico)."""

    def __init__(self, secciones: Sequence[SeccionTecnica]):
        self.secciones = list(secciones)
        self._docs_tokens: List[Counter] = []
        self._docs_bigramas: List[set] = []
        self._idf: dict[str, float] = {}
        self._construir_indice()

    def _construir_indice(self) -> None:
        n = len(self.secciones)
        df: Counter = Counter()
        for sec in self.secciones:
            texto = f"{sec.titulo} {sec.titulo} {sec.contenido} {sec.keywords}"
            toks = tokenizar(texto)
            tokens = Counter(toks)
            self._docs_tokens.append(tokens)
            self._docs_bigramas.append(_bigramas(toks))
            for term in tokens:
                df[term] += 1
        for term, d in df.items():
            self._idf[term] = math.log((1 + n) / (1 + d)) + 1.0

    def _vector(self, tokens: Counter) -> dict[str, float]:
        return {t: f * self._idf.get(t, 1.0) for t, f in tokens.items()}

    @staticmethod
    def _coseno(v1: dict[str, float], v2: dict[str, float]) -> float:
        if not v1 or not v2:
            return 0.0
        comunes = set(v1) & set(v2)
        num = sum(v1[t] * v2[t] for t in comunes)
        n1 = math.sqrt(sum(x * x for x in v1.values()))
        n2 = math.sqrt(sum(x * x for x in v2.values()))
        return num / (n1 * n2) if n1 and n2 else 0.0

    # --------------------------------------------------------------------- #
    # Etapa 1: detectar el módulo del ítem dentro del documento
    # --------------------------------------------------------------------- #
    def detectar_modulo(self, modulo_nombre: str) -> Optional[int]:
        """Devuelve el índice de la sección que mejor representa el módulo."""
        if not modulo_nombre:
            return None
        q = Counter(tokenizar(modulo_nombre))
        if not q:
            return None
        q_vec = self._vector(q)
        mejor_idx, mejor = None, 0.15  # umbral mínimo para aceptar el módulo
        for i, (sec, toks) in enumerate(zip(self.secciones, self._docs_tokens)):
            # el módulo suele coincidir con el TÍTULO de una sección
            score = self._coseno(q_vec, self._vector(Counter(tokenizar(sec.titulo))))
            score = max(score, 0.5 * self._coseno(q_vec, self._vector(toks)))
            if score > mejor:
                mejor_idx, mejor = i, score
        return mejor_idx

    # --------------------------------------------------------------------- #
    # Etapa 2: buscar la especificación del ítem
    # --------------------------------------------------------------------- #
    def buscar(self, item: Item, top_k: int = 3, umbral: float = 0.05,
               modulo_nombre: str = "") -> List[VinculoTecnico]:
        """Busca la especificación del ítem.

        Si se da `modulo_nombre`, primero localiza el módulo (Etapa 1) y aplica
        un bonus a las secciones cercanas a ese módulo en el documento (Etapa 2).
        """
        consulta = f"{item.descripcion} {item.descripcion} {item.palabras_clave}"
        q_toks = tokenizar(consulta)
        q_vec = self._vector(Counter(q_toks))
        q_bigr = _bigramas(q_toks)
        num_item = item.numero.strip() if item.numero else ""

        # Etapa 1: ámbito del módulo
        idx_modulo = self.detectar_modulo(modulo_nombre)

        resultados: List[VinculoTecnico] = []
        for i, (sec, toks) in enumerate(zip(self.secciones, self._docs_tokens)):
            score = self._coseno(q_vec, self._vector(toks))

            # precisión por frases (bigramas compartidos)
            solape_bg = len(q_bigr & self._docs_bigramas[i])
            if solape_bg:
                score += 0.05 * solape_bg

            # bonus por número de ítem presente en el título de la sección
            if num_item and num_item in (sec.titulo or ""):
                score += 0.30

            # bonus por pertenecer al ámbito del módulo (secciones contiguas)
            if idx_modulo is not None and abs(i - idx_modulo) <= 3:
                score += 0.15 - 0.03 * abs(i - idx_modulo)

            if score >= umbral:
                resultados.append(VinculoTecnico(
                    item_id=item.id, seccion_id=sec.id,
                    score_confianza=round(min(score, 1.0), 4),
                    titulo_seccion=sec.titulo,
                    extracto=(sec.contenido or "")[:300]))
        resultados.sort(key=lambda v: v.score_confianza, reverse=True)
        return resultados[:top_k]


def vincular_items(items: Sequence[Item], secciones: Sequence[SeccionTecnica],
                   top_k: int = 3, modulos: Optional[dict] = None
                   ) -> dict[int, List[VinculoTecnico]]:
    """Vincula ítems contra secciones. `modulos` = {item_id: nombre_modulo}."""
    matcher = SemanticMatcher(secciones)
    modulos = modulos or {}
    out: dict[int, List[VinculoTecnico]] = {}
    for item in items:
        if item.es_modulo:
            continue  # los módulos no se vinculan: solo agrupan
        out[item.id] = matcher.buscar(item, top_k=top_k,
                                      modulo_nombre=modulos.get(item.id, ""))
    return out
