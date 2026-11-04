"""Query the index from the command line and show where each hit came from.

    python scripts/search.py "Can a company deduct expenses incurred before it started business?"
    python scripts/search.py "conditions for group relief under s 37B" --config structured_bm25_boost -k 10

Configs that need no API key: naive_bm25, structured_bm25, structured_bm25_boost.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.embed import MissingApiKey, QuotaExhausted  # noqa: E402
from rag.retrieve import CONFIGS, Hit, IncompleteIndex, Retriever  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def describe(hit: Hit) -> str:
    chunk = hit.chunk
    label = chunk.cite or f"{chunk.doc_title}, chars {chunk.char_start}-{chunk.char_end}"
    sources = [f"{name} #{rank}" for name, rank in (("bm25", hit.bm25_rank), ("dense", hit.dense_rank)) if rank]
    if hit.boosted:
        sources.append("section boost")
    preview = " ".join(chunk.text.split())[:150]
    return f"{label}   [{', '.join(sources)}]\n      {chunk.heading + ': ' if chunk.heading else ''}{preview}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query")
    parser.add_argument("--config", default="improved", choices=sorted(CONFIGS))
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    try:
        result = Retriever(ROOT / "index").search(args.query, args.config, args.k)
    except (MissingApiKey, QuotaExhausted, IncompleteIndex) as error:
        offline = ", ".join(name for name, cfg in CONFIGS.items() if not cfg.dense)
        sys.exit(f"{error}\nConfigs that need no API key: {offline}")
    if result.query_sections:
        print(f"sections named in the query: {', '.join(result.query_sections)}")
    for rank, hit in enumerate(result.hits, start=1):
        print(f"{rank:>2}. {hit.score:.4f}  {describe(hit)}")
    label = "added" if CONFIGS[args.config].expand_astar else "cited"   # A* also adds definitions and split pieces
    for chunk in result.expanded:
        print(f"    + {label}: {chunk.cite} {chunk.heading}")


if __name__ == "__main__":
    main()
