"""Ingest documents (PDF/MD/TXT) into a simple numpy vector store.

Save outputs to `data/vector_store/` as:
- `embeddings.npy` : float32 array shape (N, D)
- `metadata.json`  : list of {"id": int, "source": str, "chunk_index": int, "text": str}

Usage:
    python tools/ingest_pdfs_vectorstore.py --outdir data/vector_store --model all-MiniLM-L6-v2

This script uses `sentence-transformers` for embeddings. Install with:
    pip install sentence-transformers pypdf numpy
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable
import sys

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - helpful error message
    SentenceTransformer = None

# Ensure project root is on sys.path so `core` imports work when running this script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.vector_rag as vector_rag


def discover_documents(roots: Iterable[Path]) -> list[Path]:
    return vector_rag._discover_document_paths(list(roots))


def embed_chunks(chunks: list[str], model: SentenceTransformer) -> np.ndarray:
    if not chunks:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    embs = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
    return np.array(embs, dtype=np.float32)


def build_vector_store(roots: list[Path], model_name: str, outdir: Path) -> None:
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")

    model = SentenceTransformer(model_name)
    docs = discover_documents(roots)
    embeddings: list[np.ndarray] = []
    metadata: list[dict] = []
    idx = 0

    for doc_path in docs:
        try:
            text = vector_rag.load_document_text(doc_path)
        except Exception as exc:
            print(f"Skipping {doc_path}: {exc}")
            continue

        chunks = vector_rag.chunk_text(text)
        if not chunks:
            continue

        embs = embed_chunks(chunks, model)
        for i, chunk_text in enumerate(chunks):
            embeddings.append(embs[i])
            try:
                source = str(doc_path.relative_to(ROOT))
            except Exception:
                try:
                    source = str(doc_path.relative_to(Path.cwd()))
                except Exception:
                    source = str(doc_path)

            metadata.append({"id": idx, "source": source, "chunk_index": i, "text": chunk_text})
            idx += 1

    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    if embeddings:
        emb_array = np.stack(embeddings)
        np.save(outdir / "embeddings.npy", emb_array)
    else:
        np.save(outdir / "embeddings.npy", np.zeros((0, 1), dtype=np.float32))

    with (outdir / "metadata.json").open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, ensure_ascii=False, indent=2)

    print(f"Saved {len(metadata)} vectors to {outdir}")


def parse_roots(arg: str) -> list[Path]:
    if not arg:
        # default to graph_rag.DOCUMENT_ROOTS
        return list(vector_rag.DOCUMENT_ROOTS)
    return [Path(p.strip()) for p in arg.split(",") if p.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into a simple vector store")
    parser.add_argument("--roots", help="Comma-separated folders/files to ingest (default: graph_rag.DOCUMENT_ROOTS)")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="SentenceTransformer model name")
    parser.add_argument("--outdir", default="data/vector_store", help="Output directory for vectors and metadata")
    args = parser.parse_args()

    roots = parse_roots(args.roots)
    outdir = Path(args.outdir)

    build_vector_store(roots, args.model, outdir)


if __name__ == "__main__":
    main()
