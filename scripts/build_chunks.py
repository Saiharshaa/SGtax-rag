"""Phase 1: PDFs in data/raw/ -> structured and naive chunks in data/processed/.

    python scripts/build_chunks.py

Writes:
    data/processed/text/<doc_id>.txt      normalised text (char spans refer to these files)
    data/processed/chunks_structured.jsonl
    data/processed/chunks_naive.jsonl
    data/processed/spans.json             gold-unit spans per document, for scoring naive chunks
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunk import act_chunks, guide_chunks, naive_chunks  # noqa: E402
from rag.parse_act import act_body_span, parse_act_text  # noqa: E402
from rag.parse_guide import parse_guide_text  # noqa: E402
from rag.pdf_text import extract_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

ACT = {"file": "ITA_1947.pdf", "doc_id": "ITA", "title": "Income Tax Act 1947", "short": "ITA 1947"}
GUIDES = [
    {"file": "etax_group_relief.pdf", "doc_id": "GR", "short": "e-Tax Guide: Group Relief System"},
    {"file": "etax_pre_commencement_expenses.pdf", "doc_id": "PC",
     "short": "e-Tax Guide: Expenses Incurred Prior to Commencement of Business"},
    {"file": "etax_date_of_commencement.pdf", "doc_id": "DC",
     "short": "e-Tax Guide: Date of Commencement of Business"},
    {"file": "etax_carry_back_relief.pdf", "doc_id": "CB", "short": "e-Tax Guide: Carry-back Relief System"},
    {"file": "etax_renovation_refurbishment.pdf", "doc_id": "RR",
     "short": "e-Tax Guide: Renovation or Refurbishment Works"},
]
GUIDE_MIN_FONT_SIZE = 10   # drops footnotes (6-9 pt) and title-page disclaimers (8 pt)


def build_act() -> tuple[list, list, dict]:
    text = extract_text(RAW / ACT["file"], merge_headings=True)
    _save_text(ACT["doc_id"], text)
    sections = parse_act_text(text)
    structured = act_chunks(sections, ACT["doc_id"], ACT["title"], ACT["short"], ACT["file"])
    naive = naive_chunks(text, ACT["doc_id"], ACT["title"], ACT["file"], span=act_body_span(text))
    spans = {s.number: [s.char_start, s.char_end] for s in sections}
    return structured, naive, spans


def build_guide(guide: dict) -> tuple[list, list, dict]:
    text = extract_text(RAW / guide["file"], min_font_size=GUIDE_MIN_FONT_SIZE)
    _save_text(guide["doc_id"], text)
    paragraphs = parse_guide_text(text)
    structured = guide_chunks(paragraphs, guide["doc_id"], guide["short"], guide["short"], guide["file"])
    body_start = paragraphs[0].char_start if paragraphs else 0
    naive = naive_chunks(text, guide["doc_id"], guide["short"], guide["file"], span=(body_start, len(text)))
    spans = {p.number: [p.char_start, p.char_end] for p in paragraphs}
    return structured, naive, spans


def _save_text(doc_id: str, text: str) -> None:
    (OUT / "text").mkdir(parents=True, exist_ok=True)
    (OUT / "text" / f"{doc_id}.txt").write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, chunks: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def main() -> None:
    structured, naive, spans = build_act()
    all_spans = {ACT["doc_id"]: spans}
    for guide in GUIDES:
        g_structured, g_naive, g_spans = build_guide(guide)
        structured += g_structured
        naive += g_naive
        all_spans[guide["doc_id"]] = g_spans

    _write_jsonl(OUT / "chunks_structured.jsonl", structured)
    _write_jsonl(OUT / "chunks_naive.jsonl", naive)
    (OUT / "spans.json").write_text(json.dumps(all_spans, indent=1), encoding="utf-8")
    print(f"structured chunks: {len(structured)}  naive chunks: {len(naive)}  -> {OUT}")


if __name__ == "__main__":
    main()
