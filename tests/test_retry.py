"""The reply retry (rag/generate.py reply_problem and answer_from_sources).

Network-free: a scripted chat model replays fixed replies and the retriever returns a fixed ranking, so each test sees
exactly which prompts the model was given.
"""
import pytest

from rag.generate import REFUSAL, answer, answer_from_sources, reply_problem
from rag.retrieve import Hit, RetrievalResult
from rag.schema import Chunk


def act(section: str, words: int = 10) -> Chunk:
    return Chunk(f"ITA:s{section}#1", "act", "Income Tax Act 1947", "ITA_1947.pdf", " ".join(["word"] * words),
                 heading=f"Section {section}", section=section, cite=f"ITA 1947, s {section}")


S37B = act("37B")


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
