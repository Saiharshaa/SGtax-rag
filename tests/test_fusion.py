import pytest

from rag.fusion import RRF_K, rrf


def test_score_is_sum_of_reciprocal_ranks():
    scores = rrf([["a", "b"], ["b", "c"]])
    assert scores["a"] == pytest.approx(1 / (RRF_K + 1))
    assert scores["b"] == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert scores["c"] == pytest.approx(1 / (RRF_K + 2))


def test_agreement_between_lists_beats_one_first_place():
    scores = rrf([["a", "b", "c"], ["c", "b", "a"], ["b", "d"]])
    assert max(scores, key=scores.get) == "b"


def test_empty_rankings():
    assert rrf([]) == {}
    assert rrf([[], ["a"]]) == {"a": pytest.approx(1 / (RRF_K + 1))}
