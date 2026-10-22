"""Phase 2: chunks in data/processed/ -> retrieval indexes in index/.

    python scripts/build_index.py              # BM25 + Gemini dense index for both corpora
    python scripts/build_index.py --bm25-only  # no API key needed
    python scripts/build_index.py --corpus structured

Writes:
    index/<corpus>/chunks.jsonl   chunks served at query time (copied, so index/ is self-contained)
    index/<corpus>/bm25.json
    index/chroma/                 one Chroma collection per corpus

The dense build resumes: after a quota error, rerun it and only the missing chunks are embedded.
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.bm25 import BM25Index  # noqa: E402
from rag.dense import DenseIndex  # noqa: E402
from rag.embed import GeminiEmbedder, MissingApiKey, QuotaExhausted  # noqa: E402
from rag.schema import load_chunks, save_chunks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED, INDEX = ROOT / "data" / "processed", ROOT / "index"
CORPORA = ("structured", "naive")


def build_bm25(name: str, chunks: list, index_dir: Path) -> None:
    folder = index_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    save_chunks(folder / "chunks.jsonl", chunks)
    BM25Index.build([c.chunk_id for c in chunks], [c.embed_text() for c in chunks]).save(folder / "bm25.json")
    print(f"{name}: BM25 over {len(chunks)} chunks -> {folder}")


def build_dense(name: str, chunks: list, embedder, index_dir: Path) -> None:
    started = time.monotonic()
    index = DenseIndex.open(index_dir / "chroma", name, embedder.name)
    embedded = index.build(chunks, embedder, lambda done, total: print(f"  {name}: {done}/{total}", flush=True))
    print(f"{name}: {embedded} chunks embedded with {embedder.name}, {len(chunks) - embedded} already current "
          f"({time.monotonic() - started:.0f} s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=CORPORA, help="build one corpus only")
    parser.add_argument("--bm25-only", action="store_true", help="skip the dense index (no API key needed)")
    parser.add_argument("--index-dir", type=Path, default=INDEX, help="where to write the index (default: index/)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    names = [args.corpus] if args.corpus else CORPORA
    corpora = {name: load_chunks(PROCESSED / f"chunks_{name}.jsonl") for name in names}
    for name, chunks in corpora.items():
        build_bm25(name, chunks, args.index_dir)
    if args.bm25_only:
        return
    try:
        embedder = GeminiEmbedder()
    except MissingApiKey as error:
        sys.exit(f"{error}\nBM25 indexes are built; rerun with --bm25-only to skip the dense index.")
    try:
        for name, chunks in corpora.items():
            build_dense(name, chunks, embedder, args.index_dir)
    except QuotaExhausted as error:
        sys.exit(f"{error}\nEverything embedded so far is saved; the next run continues from there.")


if __name__ == "__main__":
    main()
