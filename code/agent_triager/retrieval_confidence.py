from __future__ import annotations

from dataclasses import dataclass

from config import RAG_MAX_BEST_DISTANCE, RAG_MAX_MEAN_TOP3_DISTANCE


@dataclass
class RetrievalConfidence:
    is_confident: bool
    reason: str
    best_distance: float | None
    hit_count: int
    top_hits: list[dict]


def _parse_distance(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_retrieval_confidence(hits: list[dict]) -> RetrievalConfidence:
    valid_hits: list[dict] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        valid_hits.append(hit)

    if not valid_hits:
        return RetrievalConfidence(
            is_confident=False,
            reason="no_hits",
            best_distance=None,
            hit_count=0,
            top_hits=[],
        )

    hit_count = len(valid_hits)
    ranked: list[tuple[float, dict]] = []
    for hit in valid_hits:
        distance = _parse_distance(hit.get("distance"))
        if distance is not None:
            ranked.append((distance, hit))

    if not ranked:
        return RetrievalConfidence(
            is_confident=False,
            reason="missing_distance",
            best_distance=None,
            hit_count=hit_count,
            top_hits=valid_hits[:3],
        )

    ranked.sort(key=lambda item: item[0])
    best_distance = ranked[0][0]
    top_hits = [hit for _, hit in ranked[:3]]

    if best_distance > RAG_MAX_BEST_DISTANCE:
        return RetrievalConfidence(
            is_confident=False,
            reason="best_distance_above_threshold",
            best_distance=best_distance,
            hit_count=hit_count,
            top_hits=top_hits,
        )

    if hit_count >= 3 and len(ranked) >= 3:
        mean_top3 = sum(distance for distance, _ in ranked[:3]) / 3
        if mean_top3 > RAG_MAX_MEAN_TOP3_DISTANCE:
            return RetrievalConfidence(
                is_confident=False,
                reason="mean_top3_above_threshold",
                best_distance=best_distance,
                hit_count=hit_count,
                top_hits=top_hits,
            )

    return RetrievalConfidence(
        is_confident=True,
        reason="confident",
        best_distance=best_distance,
        hit_count=hit_count,
        top_hits=top_hits,
    )
