"""Deep Tax Research (rag/research.py) and the validation retry (rag/generate.py answer_from_sources).

Network-free: a scripted chat model replays fixed replies, the retriever returns a fixed ranking per query, and the
A* expansion is injected, so each test sees exactly which searches ran and which sources the answer was given.
"""
import json

import pytest

from rag.generate import REFUSAL, answer, answer_from_sources, build_prompt, reply_problem
from rag.research import merge, parse_queries, research, research_best_available
from rag.retrieve import Hit, IncompleteIndex, RetrievalResult
from rag.schema import Chunk


def act(section: str, words: int = 10) -> Chunk:
    return Chunk(f"ITA:s{section}#1", "act", "Income Tax Act 1947", "ITA_1947.pdf", " ".join(["word"] * words),
                 heading=f"Section {section}", section=section, cite=f"ITA 1947, s {section}")


S37B, S37C, S37D, S37E, S14R = act("37B"), act("37C"), act("37D"), act("37E"), act("14R", 5)


class RankingRetriever:
    """A fixed ranking per query; records (query, config, k, budget) for every search."""

    def __init__(self, rankings: dict[str, list[Chunk]]):
        self.rankings, self.calls = rankings, []

    def search(self, query, config, k=5, budget=None):
        self.calls.append((query, config, k, budget))
        return RetrievalResult(query, [Hit(chunk, 1.0) for chunk in self.rankings.get(query, [])])


class ScriptedChat:
    """Replies in order; records (system, user) for every call."""

    def __init__(self, *replies: str, name: str = "fake:model"):
        self.replies, self.name, self.prompts = list(replies), name, []
        self.last_finish_reason = None

    def complete(self, system, user):
        self.prompts.append((system, user))
        reply = self.replies[len(self.prompts) - 1]
        self.last_finish_reason = "length" if reply == "" else "stop"
        return reply


def plan(*queries):
    return json.dumps({"queries": list(queries)})


def gaps(*queries):
    return json.dumps({"missing": list(queries)})


def follows(deps: dict[str, list[Chunk]]):
    """An A* stand-in: each hit's listed dependencies that aren't already in the evidence."""
    def expand(hits):
        have, out = {c.chunk_id for c in hits}, []
        for chunk in hits:
            for dep in deps.get(chunk.chunk_id, []):
                if dep.chunk_id not in have:
                    out.append(dep)
                    have.add(dep.chunk_id)
        return out
    return expand


# -------------------------------------------------------------------------------------------- merging the searches
def test_the_question_alone_gives_the_usual_hits_within_the_budget():
    assert merge([[S37B, S37C, S37D]], 25) == [S37B, S37C]


def test_a_chunk_found_by_two_searches_rises_and_a_sub_query_adds_after_the_questions_hits():
    assert merge([[S37B, S37C, S37D], [S37E, S37D]], 100) == [S37D, S37B, S37C, S37E]


def test_queries_are_read_from_json_with_stray_text_and_cleaned():
    raw = 'Here you go: {"queries": [" s 37B ", "S 37B", "", 3, "Q?", "loss transfer", "x", "y"]}'
    assert parse_queries(raw, "queries", "Q?", 3, []) == ["s 37B", "loss transfer", "x"]
    assert parse_queries("not json", "queries", "Q?", 3, []) == []
    assert parse_queries(gaps("s 37B", "s 37E"), "missing", "Q?", 2, ["s 37B"]) == ["s 37E"]


# -------------------------------------------------------------------------------------------- Deep Tax Research
def test_research_searches_the_plan_and_the_gaps_and_answers_once_from_the_final_sources():
    retriever = RankingRetriever({"Q?": [S37B, S37C], "group relief": [S37D], "carry-back": [S37E]})
    chat = ScriptedChat(plan("group relief", "Q?"), gaps("carry-back"), "Yes [1], subject to [4] [5].")
    result = research("Q?", retriever, [chat], context_tokens=30, expand=follows({"ITA:s37D#1": [S14R]}))
    assert [call[0] for call in retriever.calls] == ["Q?", "group relief", "carry-back"]
    assert all(call[2] == 50 and call[3] is None for call in retriever.calls)   # rankings, cut to the budget here
    assert result.sources == [S37B, S37C, S37D, S14R]    # S37E doesn't fit the 30 tokens; S14R is what S37D refers to
    assert result.invalid_citations == [5] and result.cited == [S37B, S14R]
    assert chat.prompts[2][1] == build_prompt("Q?", result.sources)
    assert "[1] ITA 1947, s 37B" in chat.prompts[1][1]   # the gap check sees the numbered sources
    assert result.trace == ["searched: group relief", "searched for what was missing: carry-back"]
    assert not result.refused and result.config == "improved_astar"


def test_with_nothing_planned_or_missing_the_sources_are_improved_astar_s():
    retriever = RankingRetriever({"Q?": [S37B, S37C]})
    chat = ScriptedChat(plan(), gaps(), "Yes [1].")
    result = research("Q?", retriever, [chat], expand=follows({"ITA:s37B#1": [S37D]}))
    assert result.sources == [S37B, S37C, S37D] and result.trace == ["searched for the question only"]


def test_an_unreadable_plan_costs_no_search_and_still_answers():
    retriever = RankingRetriever({"Q?": [S37B]})
    chat = ScriptedChat("I think you should search for group relief.", "{}", "Yes [1].")
    result = research("Q?", retriever, [chat], expand=follows({}))
    assert [call[0] for call in retriever.calls] == ["Q?"] and not result.refused


class DenseDown(RankingRetriever):
    def search(self, query, config, k=5, budget=None):
        if config == "improved_astar":
            raise IncompleteIndex("the dense index for 'structured' has 1700 of 3577 chunks")
        return super().search(query, config, k, budget)


def test_without_dense_search_it_falls_back_to_the_plain_bm25_answer_before_any_planning_call():
    retriever = DenseDown({"Q?": [S37B]})
    chat = ScriptedChat("Yes [1].")
    result, reason = research_best_available("Q?", retriever, [chat])
    assert result.config == "improved_bm25" and "1700 of 3577" in reason and not result.refused
    assert len(chat.prompts) == 1 and result.trace[0].startswith("dense search unavailable")


# -------------------------------------------------------------------------------------------- the validation retry
@pytest.mark.parametrize("raw, cited, invalid, reason, expected", [
    (REFUSAL, [], [], "stop", ""),
    ("", [], [], "length", "ran out of its output limit"),
    ("Half [1]", [S37B], [], "length", "ran out of its output limit"),
    ("Section 37B allows it.", [], [], "stop", "did not cite the sources by number"),
    ("Yes [1][7].", [S37B], [7], "stop", "don't exist (7). Cite only [1] to [2]."),
    ("Yes [1].", [S37B], [], "stop", ""),
], ids=["own-refusal", "empty-at-cap", "cut-off", "uncited", "invalid-number", "fine"])
def test_reply_problem_names_what_to_fix_and_accepts_the_models_own_refusal(raw, cited, invalid, reason, expected):
    note = reply_problem(raw, cited, invalid, 2, reason)
    assert (expected in note) if expected else note == ""


def test_an_uncited_reply_is_sent_back_once_with_the_note_and_the_reply():
    chat = ScriptedChat("Section 37B allows it.", "Section 37B allows it [1].")
    result = answer_from_sources("Q?", [S37B], [chat], "improved", retries=1)
    assert not result.refused and result.attempts == 2
    assert "did not cite" in chat.prompts[1][1] and "<previous_reply>\nSection 37B allows it.\n</previous_reply>" in chat.prompts[1][1]


def test_an_empty_reply_at_the_cap_is_retried_without_quoting_it():
    chat = ScriptedChat("", "Yes [1].")
    result = answer_from_sources("Q?", [S37B], [chat], retries=2)
    assert result.attempts == 2 and "ran out of its output limit" in chat.prompts[1][1]
    assert "<previous_reply>" not in chat.prompts[1][1]


def test_retries_stop_at_the_limit_and_an_unusable_last_reply_is_a_refusal():
    chat = ScriptedChat("no cites", "still none", "none again")
    result = answer_from_sources("Q?", [S37B], [chat], retries=2)
    assert len(chat.prompts) == 3 and result.refused and result.raw == "none again" and result.attempts == 3


def test_without_retries_answer_behaves_as_before():
    chat = ScriptedChat("Yes, always deductible.")
    result = answer("Q?", RankingRetriever({"Q?": [S37B]}), [chat])
    assert result.refused and result.text == REFUSAL and len(chat.prompts) == 1 and result.attempts == 1
