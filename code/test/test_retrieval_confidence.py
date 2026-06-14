import pytest

from agent_triager.retrieval_bootstrap import normalize_company
from agent_triager.retrieval_confidence import evaluate_retrieval_confidence


def _hit(distance: float | None, chunk_id: str = "a") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": "sample",
        "rel_path": "docs/sample.md",
        "source_url": "",
        "title": "Sample",
        "corpus": "hackerrank",
        "distance": distance,
    }


def test_confident_with_three_low_distance_hits():
    hits = [_hit(0.2, "a"), _hit(0.25, "b"), _hit(0.3, "c"), _hit(0.4, "d")]
    result = evaluate_retrieval_confidence(hits)

    assert result.is_confident is True
    assert result.reason == "confident"
    assert result.best_distance == 0.2
    assert result.hit_count == 4


def test_no_hits_not_confident():
    result = evaluate_retrieval_confidence([])

    assert result.is_confident is False
    assert result.reason == "no_hits"
    assert result.best_distance is None
    assert result.hit_count == 0


def test_missing_distance_not_confident():
    hits = [{"chunk_id": "a", "text": "sample"}, _hit(None, "b")]
    result = evaluate_retrieval_confidence(hits)

    assert result.is_confident is False
    assert result.reason == "missing_distance"
    assert result.best_distance is None
    assert result.hit_count == 2


def test_high_best_distance_not_confident():
    hits = [_hit(0.5, "a"), _hit(0.52, "b"), _hit(0.55, "c")]
    result = evaluate_retrieval_confidence(hits)

    assert result.is_confident is False
    assert result.reason == "best_distance_above_threshold"
    assert result.best_distance == 0.5


def test_high_mean_top3_not_confident():
    hits = [_hit(0.45, "a"), _hit(0.60, "b"), _hit(0.62, "c")]
    result = evaluate_retrieval_confidence(hits)

    assert result.is_confident is False
    assert result.reason == "mean_top3_above_threshold"
    assert result.best_distance == 0.45


def test_malformed_hits_ignored_safely():
    hits = ["bad", _hit(0.2, "a"), None, _hit(0.25, "b")]
    result = evaluate_retrieval_confidence(hits)

    assert result.is_confident is True
    assert result.hit_count == 2


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HackerRank", "hackerrank"),
        ("Claude", "claude"),
        ("Visa", "visa"),
        ("None", "none"),
        ("none", "none"),
        ("", "none"),
        (None, "none"),
        ("  HACKERRANK  ", "hackerrank"),
        ("Other", "none"),
    ],
)
def test_normalize_company(raw, expected):
    assert normalize_company(raw) == expected
