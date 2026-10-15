"""BM25 keyword index over chunk texts (Okapi BM25, k1=1.5, b=0.75).

Hand-rolled rather than rank_bm25: it is ~60 lines, needs no numpy at query time and saves to
plain JSON. Section numbers survive tokenisation ("s 14Q(2)" -> "14q", "2"), so a query that
names a section matches chunks whose path names it.
"""

import functools
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import snowballstemmer

_WORD_RE = re.compile(r"[a-z0-9]+")
_STEMMER = snowballstemmer.stemmer("english")
STOPWORDS = frozenset("""
a an and any are as at be been by can do does for from has have if in into is it its may must
no not of on or other shall such than that the their then there these this those to under was
were what when where which who whom will with would i my we our you your how
""".split())


@functools.cache
def _stem(word: str) -> str:
    # The stemmer is pure Python; caching per word makes indexing the corpus ~30x faster.
    return _STEMMER.stemWord(word)


def tokenize(text: str) -> list[str]:
    """Lower-case, split on non-alphanumerics, drop stopwords and single letters, stem."""
    words = _WORD_RE.findall(text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS and (len(w) > 1 or w.isdigit())]


@dataclass
class BM25Index:
    ids: list[str]
    doc_lens: list[int]
    postings: dict[str, dict[int, int]]   # term -> {doc index: term frequency}
    k1: float = 1.5
    b: float = 0.75

    @classmethod
    def build(cls, ids: list[str], texts: list[str], k1: float = 1.5, b: float = 0.75) -> "BM25Index":
        postings: dict[str, dict[int, int]] = {}
        doc_lens = []
        for doc, text in enumerate(texts):
            terms = Counter(tokenize(text))
            doc_lens.append(sum(terms.values()))
            for term, tf in terms.items():
                postings.setdefault(term, {})[doc] = tf
        return cls(list(ids), doc_lens, postings, k1, b)

    def idf(self, term: str) -> float:
        n, df = len(self.ids), len(self.postings.get(term, ()))
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        """Top-k (chunk_id, score), best first; documents sharing no query term are never returned."""
        avg_len = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0
        scores: dict[int, float] = {}
        for term in set(tokenize(query)):
            idf = self.idf(term)
            for doc, tf in self.postings.get(term, {}).items():
                norm = self.k1 * (1 - self.b + self.b * self.doc_lens[doc] / avg_len)
                scores[doc] = scores.get(doc, 0.0) + idf * tf * (self.k1 + 1) / (tf + norm)
        best = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
        return [(self.ids[doc], score) for doc, score in best]

    def save(self, path: Path) -> None:
        data = {"k1": self.k1, "b": self.b, "ids": self.ids, "doc_lens": self.doc_lens,
                "postings": {term: [[doc, tf] for doc, tf in docs.items()] for term, docs in self.postings.items()}}
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        data = json.loads(path.read_text(encoding="utf-8"))
        postings = {term: {doc: tf for doc, tf in docs} for term, docs in data["postings"].items()}
        return cls(data["ids"], data["doc_lens"], postings, data["k1"], data["b"])
