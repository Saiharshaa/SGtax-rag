import pytest

from rag.generate import REFUSAL, SYSTEM_PROMPT, answer, build_prompt, render_citations
from rag.retrieve import Hit, RetrievalResult
from rag.schema import Chunk

S14R2 = Chunk("ITA:s14R(2)#1", "act", "Income Tax Act 1947", "ITA_1947.pdf",
              "A previous expense is any outgoing incurred before the first dollar of income.",
              heading="Deduction for expenses incurred before first dollar of income", section="14R",
              subsection="2", cite="ITA 1947, s 14R(2)")
PC42 = Chunk("PC:p4.2#1", "guide", "e-Tax Guide: Pre-commencement Expenses", "pc.pdf",
             "Under section 14R, a person is deemed to have commenced business on the deemed date.",
             heading="Background", para="4.2", cite="e-Tax Guide: Pre-commencement Expenses, para 4.2")
S14X = Chunk("ITA:s14X#1", "act", "Income Tax Act 1947", "ITA_1947.pdf", "Attribution of expenses.",
             heading="Attribution of deductible expenses", section="14X", cite="ITA 1947, s 14X")


class FakeRetriever:
    def __init__(self, hits: list[Chunk], expanded: list[Chunk] = ()):
        self.hits, self.expanded, self.calls = hits, list(expanded), []

    def search(self, query, config, k):
        self.calls.append((query, config, k))
        return RetrievalResult(query, [Hit(chunk, 1.0) for chunk in self.hits], self.expanded)


class FakeChat:
    def __init__(self, reply: str, name: str = "fake:model"):
        self.reply, self.name, self.prompts = reply, name, []

    def complete(self, system, user):
        self.prompts.append((system, user))
        return self.reply


def test_prompt_numbers_sources_with_citation_heading_and_text():
    prompt = build_prompt("  Can I deduct it? ", [S14R2, PC42])
    assert prompt.startswith("Sources:\n\n[1] ITA 1947, s 14R(2) (Deduction for expenses incurred before first")
    assert "\n[2] e-Tax Guide: Pre-commencement Expenses, para 4.2 (Background)\nUnder section 14R" in prompt
    assert prompt.endswith("Question: Can I deduct it?")


def test_system_prompt_states_the_exact_refusal():
    assert REFUSAL in SYSTEM_PROMPT


def test_numbers_become_citations():
    text, cited, invalid = render_citations("Yes, before the first dollar [1]. See the guide [2].", [S14R2, PC42])
    assert text == "Yes, before the first dollar [ITA 1947, s 14R(2)]. See the guide " \
                   "[e-Tax Guide: Pre-commencement Expenses, para 4.2]."
    assert cited == [S14R2, PC42] and invalid == []


@pytest.mark.parametrize("raw", ["Deductible [1, 2].", "Deductible [1; 2].", "Deductible [1][2].",
                                 "Deductible [1] [2][1]."])
def test_adjacent_sources_merge_into_one_citation(raw):
    text, cited, _ = render_citations(raw, [S14R2, PC42])
    assert cited == [S14R2, PC42]
    assert text == "Deductible [ITA 1947, s 14R(2); e-Tax Guide: Pre-commencement Expenses, para 4.2]."


def test_citation_glued_to_a_word_gets_a_space():
    assert render_citations("**deductible**[1]", [S14R2])[0] == "**deductible** [ITA 1947, s 14R(2)]"


def test_openai_style_citation_marks_are_understood():
    text, cited, invalid = render_citations("Deductible 【1†L3-L5】【1†L9-L12】.", [S14R2])
    assert (text, cited, invalid) == ("Deductible [ITA 1947, s 14R(2)].", [S14R2], [])


def test_citations_to_missing_sources_are_dropped_and_reported():
    text, cited, invalid = render_citations("Deductible [1]. Also [7].", [S14R2])
    assert text == "Deductible [ITA 1947, s 14R(2)]. Also."
    assert invalid == [7]


def test_other_brackets_are_left_alone():
    raw = "Amended [Act 33 of 2022 wef 26/04/2024] from [2020] onwards [1]."
    assert render_citations(raw, [S14R2])[0] == \
        "Amended [Act 33 of 2022 wef 26/04/2024] from [2020] onwards [ITA 1947, s 14R(2)]."


def test_narrow_spaces_from_the_model_are_normalised():
    assert render_citations("Income Tax Act 1947 [1].", [S14R2])[0] == \
        "Income Tax Act 1947 [ITA 1947, s 14R(2)]."


def test_answer_cites_and_reports_the_model():
    chat = FakeChat("Yes, previous expenses are deductible [1], per the guide [2].")
    retriever = FakeRetriever([S14R2, PC42], expanded=[S14X])
    result = answer("Pre-commencement expenses?", retriever, [chat], config="structured_bm25", k=2)
    assert retriever.calls == [("Pre-commencement expenses?", "structured_bm25", 2)]
    assert result.sources == [S14R2, PC42, S14X]
    assert "[3] ITA 1947, s 14X" in chat.prompts[0][1]
    assert result.cited == [S14R2, PC42]
    assert not result.refused and result.model == "fake:model"


def test_model_refusal():
    result = answer("What is the GST rate?", FakeRetriever([S14R2]), [FakeChat(REFUSAL)])
    assert result.refused and result.text == REFUSAL and result.cited == []


def test_uncited_answer_is_refused_but_kept_for_debugging():
    result = answer("Pre-commencement expenses?", FakeRetriever([S14R2]), [FakeChat("Yes, always deductible.")])
    assert result.refused and result.text == REFUSAL
    assert result.raw == "Yes, always deductible."


def test_nothing_retrieved_means_no_model_call():
    chat = FakeChat("should not be called")
    result = answer("anything", FakeRetriever([]), [chat])
    assert result.refused and chat.prompts == [] and result.model == ""
