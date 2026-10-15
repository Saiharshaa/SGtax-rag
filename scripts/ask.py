"""Ask a question and get a cited answer from the Act and e-Tax guides.

    python scripts/ask.py "Can a company deduct expenses incurred before it started business?"
    python scripts/ask.py "..." --config structured_bm25_boost --sources

Needs GROQ_API_KEY or GEMINI_API_KEY; configs with dense retrieval also need GEMINI_API_KEY.
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.embed import MissingApiKey  # noqa: E402
from rag.generate import answer  # noqa: E402
from rag.llm import LLMUnavailable, default_models  # noqa: E402
from rag.retrieve import CONFIGS, Retriever  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--config", default="improved", choices=sorted(CONFIGS))
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--sources", action="store_true", help="also list every source the model was given")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    started = time.monotonic()
    try:
        result = answer(args.question, Retriever(ROOT / "index"), default_models(), args.config, args.k)
    except (MissingApiKey, LLMUnavailable) as error:
        sys.exit(str(error))
    print(result.text)
    print(f"\n({result.model or 'no model called'}, {time.monotonic() - started:.1f} s)")
    if result.invalid_citations:
        print(f"dropped citations to sources that don't exist: {result.invalid_citations}")
    print("\nCited:" if result.cited else "")
    for chunk in result.cited:
        print(f"  {chunk.cite}  {chunk.heading}")
    if args.sources:
        print("\nSources given to the model:")
        for n, chunk in enumerate(result.sources, start=1):
            print(f"  [{n}] {chunk.cite}  {chunk.heading}")


if __name__ == "__main__":
    main()
