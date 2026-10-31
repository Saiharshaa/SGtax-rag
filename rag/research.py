"""Deep Tax Research: an opt-in answer mode that searches more than once before answering.

The default answer (rag.generate.answer) makes one search and one model call. Deep Tax Research first asks the
model which provisions the question needs and searches for each; merges those rankings with the question's own
(reciprocal rank fusion, the question's ranking counted twice) and cuts them to the usual 2,500 tokens; follows
the merged hits' references with the A* dependency expansion (rag/graph.py, as in `improved_astar`); asks the
model what the sources still miss, searches for that, and repeats the merge and the expansion. The answer step is
the usual one (rag.generate.answer_from_sources: same prompt, numbered sources, citation check and refusal) over
the same amount of context, so only the choice of sources changes.

Cost per question: two more chat calls (short, JSON) and up to five more searches, each one Gemini embedding call
(free tier: 1,000 a day) when the search is dense.

    result = research("Can a company carry back its loss and also transfer it under group relief?", retriever, models)
"""

import json
import re
from collections.abc import Callable

from rag.fusion import rrf
from rag.generate import CONTEXT_TOKENS, DENSE_UNAVAILABLE, Answer, answer, answer_from_sources, format_source
from rag.llm import ChatModel, complete_with_fallback
from rag.retrieve import CANDIDATES, CONFIGS, Retriever, within_budget
from rag.schema import Chunk

MAX_PLAN_QUERIES = 3     # searches planned from the question
MAX_GAP_QUERIES = 2      # searches for what the first sources miss
MAX_QUERY_CHARS = 200

PLANNER = "You plan searches of the Singapore Income Tax Act 1947 and the IRAS e-Tax guides. Reply with JSON only."
PLAN_PROMPT = """List up to 3 short search queries, each for one provision, condition, definition, exception or rule
that the answer to this tax question needs and that a search for the whole question might miss. Use a section number
when the question gives one. Do not answer the question.

Reply in JSON: {{"queries": ["...", "..."]}}. Reply {{"queries": []}} if a search for the question alone is enough.

Question: {question}"""
GAP_PROMPT = """These numbered sources were found for a Singapore income tax question. Name what a complete answer
still needs that the sources do not contain: up to 2 short search queries, each for one missing provision,
definition, condition or exception (for example a section that a source refers to but that is not among the
sources). Do not answer the question.

Reply in JSON: {{"missing": ["...", "..."]}}. Reply {{"missing": []}} if the sources cover the question.

Sources:

{sources}

Question: {question}"""


def parse_queries(raw: str, key: str, question: str, limit: int, seen: list[str]) -> list[str]:
    """The reply's list under `key`: distinct non-empty strings, not the question or an earlier query, at most
    `limit`. A reply that isn't JSON (or has stray text around it) gives what can be read, or nothing."""
    try:
        data = json.loads(raw)
    except ValueError:
        match = re.search(r"\{.*\}", raw, re.S)
        try:
            data = json.loads(match.group()) if match else {}
        except ValueError:
            data = {}
    items = data.get(key) if isinstance(data, dict) else None
    out, have = [], {q.lower() for q in [question, *seen]}
    for item in items if isinstance(items, list) else []:
        query = " ".join(item.split())[:MAX_QUERY_CHARS] if isinstance(item, str) else ""
        if query and query.lower() not in have:
            out.append(query)
            have.add(query.lower())
        if len(out) == limit:
            break
    return out


def merge(rankings: list[list[Chunk]], tokens: int) -> list[Chunk]:
    """The question's ranking (first, counted twice) fused with the others by RRF, ties in order of first
    appearance, cut to `tokens`. The question's ranking alone gives exactly the usual hits."""
    ids = [[chunk.chunk_id for chunk in ranking] for ranking in rankings]
    scores = rrf([ids[0], *ids])
    by_id = {chunk.chunk_id: chunk for ranking in rankings for chunk in ranking}
    first = {id_: i for i, id_ in enumerate(dict.fromkeys(id_ for ranking in ids for id_ in ranking))}
    order = sorted(scores, key=lambda id_: (-scores[id_], first[id_]))
    return within_budget([by_id[id_] for id_ in order], tokens)


def research(question: str, retriever: Retriever, models: list[ChatModel], config: str = "improved_astar",
             context_tokens: int = CONTEXT_TOKENS, retries: int = 0,
             expand: Callable[[list[Chunk]], list[Chunk]] | None = None) -> Answer:
    """Deep Tax Research with `config`'s ranking. `expand` defaults to the corpus's A* dependency expansion."""
    trace: list[str] = []

    def ranking(query: str) -> list[Chunk]:
        return [hit.chunk for hit in retriever.search(query, config, CANDIDATES).hits]

    def sources_for(rankings: list[list[Chunk]]) -> list[Chunk]:
        hits = merge(rankings, context_tokens)
        follow = expand or retriever.corpus(CONFIGS[config].corpus).dependency_graph().expand
        return hits + follow(hits)

    first = ranking(question)   # before any chat call: without dense search, research_best_available falls back cheaply
    raw, _ = complete_with_fallback(models, PLANNER, PLAN_PROMPT.format(question=question.strip()))
    queries = parse_queries(raw, "queries", question, MAX_PLAN_QUERIES, [])
    trace += [f"searched: {q}" for q in queries]
    rankings = [first] + [ranking(q) for q in queries]
    sources = sources_for(rankings)
    listed = "\n\n".join(format_source(n, chunk) for n, chunk in enumerate(sources, start=1))
    raw, _ = complete_with_fallback(models, PLANNER, GAP_PROMPT.format(sources=listed, question=question.strip()))
    missing = parse_queries(raw, "missing", question, MAX_GAP_QUERIES, queries)
    if missing:
        trace += [f"searched for what was missing: {q}" for q in missing]
        rankings += [ranking(q) for q in missing]
        sources = sources_for(rankings)
    result = answer_from_sources(question, sources, models, config, retries)
    result.trace = trace or ["searched for the question only"]
    return result


def research_best_available(question: str, retriever: Retriever, models: list[ChatModel],
                            config: str = "improved_astar", fallback: str = "improved_bm25",
                            context_tokens: int = CONTEXT_TOKENS, retries: int = 0) -> tuple[Answer, str | None]:
    """Deep Tax Research, or the plain `fallback` answer (BM25 only, one search) when dense search can't run."""
    try:
        return research(question, retriever, models, config, context_tokens, retries), None
    except DENSE_UNAVAILABLE as error:
        result = answer(question, retriever, models, fallback, context_tokens, retries)
        result.trace = ["dense search unavailable: answered from one BM25 search, without Deep Tax Research"]
        return result, str(error)
