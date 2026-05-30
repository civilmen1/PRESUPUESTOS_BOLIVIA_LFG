"""Vinculación semántica ítem ↔ sección técnica.

Implementa un matcher ligero basado en TF-IDF + similitud coseno sobre
tokens, sin dependencias de modelos pesados, para funcionar offline.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import List, Sequence

from core.text_cleaner import tokenizar
from models.item import Item
from models.technical_source import SeccionTecnica, VinculoTecnico


class SemanticMatcher:
    """Indexa secciones técnicas y permite buscar las más relevantes por ítem."""

    def __init__(self, secciones: Sequence[SeccionTecnica]):
        self.secciones = list(secciones)
        self._docs_tokens: List[Counter] = []
        self._idf: dict[str, float] = {}
        self._construir_indice()

    def _construir_indice(self) -> None:
        n = len(self.secciones)
        df: Counter = Counter()
        for sec in self.secciones:
            texto = f"{sec.titulo} {sec.contenido} {sec.keywords}"
            tokens = Counter(tokenizar(texto))
            self._docs_tokens.append(tokens)
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
        if n1 == 0 or n2 == 0:
            return 0.0
        return num / (n1 * n2)

    def buscar(self, item: Item, top_k: int = 3, umbral: float = 0.05) -> List[VinculoTecnico]:
        """Devuelve los vínculos técnicos más relevantes para un ítem."""
        consulta = f"{item.descripcion} {item.palabras_clave}"
        q_tokens = Counter(tokenizar(consulta))
        q_vec = self._vector(q_tokens)

        resultados: List[VinculoTecnico] = []
        for sec, doc_tokens in zip(self.secciones, self._docs_tokens):
            score = self._coseno(q_vec, self._vector(doc_tokens))
            if score >= umbral:
                resultados.append(
                    VinculoTecnico(
                        item_id=item.id,
                        seccion_id=sec.id,
                        score_confianza=round(score, 4),
                        titulo_seccion=sec.titulo,
                        extracto=(sec.contenido or "")[:300],
                    )
                )
        resultados.sort(key=lambda v: v.score_confianza, reverse=True)
        return resultados[:top_k]


def vincular_items(
    items: Sequence[Item], secciones: Sequence[SeccionTecnica], top_k: int = 3
) -> dict[int, List[VinculoTecnico]]:
    """Vincula una lista de ítems contra secciones; retorna {item_id: [vinculos]}."""
    matcher = SemanticMatcher(secciones)
    out: dict[int, List[VinculoTecnico]] = {}
    for item in items:
        out[item.id] = matcher.buscar(item, top_k=top_k)
    return out
