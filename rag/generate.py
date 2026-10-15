"""Phase 3: answer a question from retrieved chunks only, citing a source for every claim.

The model sees numbered sources and cites them as [1], [2]: numbers are easier for it to get
right than legal citations. The code then rewrites each number into the source's citation
("[ITA 1947, s 14R(2)]"), so every citation in an answer is well-formed and points at a chunk the
model was actually shown. Numbers outside the source list are dropped and reported. An answer
with no valid citation is treated as a refusal: an uncited tax answer is worse than none.
"""

import re
from dataclasses import dataclass, field

from rag.llm import ChatModel, complete_with_fallback
from rag.retrieve import Retriever
from rag.schema import Chunk

REFUSAL = "I can't answer this from the Income Tax Act 1947 and the IRAS e-Tax guides I have."

SYSTEM_PROMPT = f"""You answer Singapore corporate income tax questions for tax associates at accounting firms.

Rules:
1. Use only the numbered sources in the user's message. Do not add facts from outside them, even ones you are sure of.
2. Cite the source of every statement with its number in square brackets, e.g. [2] or [1][3]. Cite only sources that say what you state.
3. If the sources don't answer the question, reply with exactly this sentence and nothing else: {REFUSAL}
4. If they answer only part of the question, answer that part and say which part they don't cover.
5. Give section numbers, amounts, dates, percentages and conditions exactly as the sources state them.
6. Start with a direct answer, then the conditions and exceptions that matter. Aim for under 200 words; a bullet list is fine. No headings."""

# [2], [1, 3], [1; 3], and the 【2†L5】 style some OpenAI-family models fall back to. One or two digits,
# so a bracketed year such as [2020] is left alone. Adjacent marks ([1][3], 【1†L2】【1†L7】) form one run
# and become one citation without repeats.
ONE_CITATION = r"\[(\d{1,2}(?:\s*[,;]\s*\d{1,2})*)\]|【(\d{1,2})[^】]*】"
ONE_CITATION_RE = re.compile(ONE_CITATION)
CITATION_RUN_RE = re.compile(rf"(?:{ONE_CITATION})(?:\s*(?:{ONE_CITATION}))*")
ODD_SPACES = str.maketrans({" ": " ", " ": " ", " ": " "})


@dataclass
class Answer:
    question: str
    text: str                     # the answer, citations rewritten as [ITA 1947, s 14R(2)]
    sources: list[Chunk]          # numbered sources the model was given (source n = sources[n - 1])
    cited: list[Chunk] = field(default_factory=list)   # sources the answer cites, in order of first use
    refused: bool = False
    model: str = ""               # model that answered; "" when none was called
    invalid_citations: list[int] = field(default_factory=list)   # cited numbers that weren't sources
    raw: str = ""                 # model output before rewriting, for debugging and evaluation


def format_source(n: int, chunk: Chunk) -> str:
    heading = f" ({chunk.heading})" if chunk.heading else ""
    return f"[{n}] {chunk.cite or chunk.doc_title}{heading}\n{chunk.text.strip()}"


def build_prompt(question: str, sources: list[Chunk]) -> str:
    listed = "\n\n".join(format_source(n, chunk) for n, chunk in enumerate(sources, start=1))
    return f"Sources:\n\n{listed}\n\nQuestion: {question.strip()}"


def render_citations(raw: str, sources: list[Chunk]) -> tuple[str, list[Chunk], list[int]]:
    """Rewrite [n] as [<citation>]. Returns (text, cited sources in order, invalid numbers)."""
    cited: list[Chunk] = []
    invalid: list[int] = []

    def rewrite(run: re.Match) -> str:
        numbers = [int(n) for one in ONE_CITATION_RE.finditer(run.group())
                   for n in re.findall(r"\d+", one.group(1) or one.group(2))]
        valid = [n for n in dict.fromkeys(numbers) if 1 <= n <= len(sources)]
        invalid.extend(n for n in numbers if n not in valid)
        for n in valid:
            if sources[n - 1] not in cited:
                cited.append(sources[n - 1])
        labels = list(dict.fromkeys(sources[n - 1].cite or sources[n - 1].doc_title for n in valid))
        if not labels:
            return ""
        before = run.string[run.start() - 1] if run.start() else " "
        return ("" if before.isspace() or before in "([" else " ") + f"[{'; '.join(labels)}]"

    text = CITATION_RUN_RE.sub(rewrite, raw.translate(ODD_SPACES))
    return re.sub(r" +([.,;:])", r"\1", text).strip(), cited, invalid


def answer(question: str, retriever: Retriever, models: list[ChatModel], config: str = "improved",
           k: int = 5) -> Answer:
    """Retrieve, generate, and check citations. The expanded (cross-referenced) chunks are extra sources."""
    result = retriever.search(question, config, k)
    sources = [hit.chunk for hit in result.hits] + result.expanded
    if not sources:
        return Answer(question, REFUSAL, sources, refused=True)
    raw, model = complete_with_fallback(models, SYSTEM_PROMPT, build_prompt(question, sources))
    text, cited, invalid = render_citations(raw, sources)
    if not cited:
        return Answer(question, REFUSAL, sources, refused=True, model=model, invalid_citations=invalid, raw=raw)
    return Answer(question, text, sources, cited, False, model, invalid, raw)
