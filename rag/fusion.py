"""Reciprocal rank fusion: merge ranked lists by rank, not score, so BM25 and cosine scores
(different scales) never need normalising. score(d) = sum over lists of 1 / (k + rank of d)."""

RRF_K = 60   # the constant from Cormack et al. (2009); damps the gap between ranks 1 and 2


def rrf(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Fused score per id. Ranks are 1-based; an id missing from a list gets nothing from it."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return scores
