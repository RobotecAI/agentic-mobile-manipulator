#!/usr/bin/env python3
"""
Build vector database script extracted from the original rag.py logic.
This script contains the specific vector database building functions that were previously in rag.py.

Usage:
    python3 build_rag_vector_db.py --source summarized_regulations --output regulations_db --strategy per_regulation
"""

import argparse
from pathlib import Path
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

SUPPORTED_CONTENT_FILES = ["text.txt", "content.md"]  # prefer plain text first


def gather_local_regulations(
    source_dir: str = "filtered_regulations",
) -> List[Document]:
    """Collect candidate regulation documents from a directory structure.

    Parameters
    ----------
    source_dir : str, optional
        Directory containing regulation subdirectories. Defaults to
        ``"filtered_regulations"``.

    Returns
    -------
    list[Document]
        One document per regulation directory.

    Raises
    ------
    FileNotFoundError
        If ``source_dir`` does not exist.
    """
    base = Path(source_dir)
    if not base.exists():
        raise FileNotFoundError(
            f"Source directory not found: {source_dir} (try running from test_warehouse_regulations dir)"
        )
    docs: List[Document] = []
    for item in sorted(base.iterdir()):
        if not item.is_dir() or not item.name.startswith("1910."):
            continue
        content_path: Optional[Path] = None
        for fname in SUPPORTED_CONTENT_FILES:
            candidate = item / fname
            if candidate.exists():
                content_path = candidate
                break
        if not content_path:
            continue
        try:
            text = content_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"WARN: failed reading {content_path}: {e}")
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={"reg_dir": item.name, "source_file": content_path.name},
            )
        )
    return docs


def split_documents(
    base_docs: List[Document],
    strategy: str = "per_regulation",
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """Split documents according to the requested strategy.

    Parameters
    ----------
    base_docs : list[Document]
        Source documents to split.
    strategy : str, optional
        Splitting strategy. Supported values are ``"per_regulation"``,
        ``"recursive"``, and ``"markdown_headers"``. Defaults to
        ``"per_regulation"``.
    chunk_size : int, optional
        Chunk size passed to text splitters. Defaults to ``1000``.
    chunk_overlap : int, optional
        Chunk overlap for recursive splitting. Defaults to ``200``.

    Returns
    -------
    list[Document]
        Resulting list of documents after splitting.

    Raises
    ------
    ValueError
        If ``strategy`` is not recognized.
    """
    if strategy == "per_regulation":
        return base_docs
    if strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        return splitter.split_documents(base_docs)
    if strategy == "markdown_headers":
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
        )
        out: List[Document] = []
        for d in base_docs:
            parts = header_splitter.split_text(d.page_content)
            # propagate metadata
            for p in parts:
                p.metadata.update(d.metadata)
            out.extend(parts)
        # (Optional) re-chunk very small parts using recursive splitter for consistency
        normalized: List[Document] = []
        tmp_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        for p in out:
            if len(p.page_content) < chunk_size // 3:
                normalized.extend(tmp_splitter.split_documents([p]))
            else:
                normalized.append(p)
        return normalized
    raise ValueError(f"Unknown split strategy: {strategy}")


def build_local_index(
    source_dir: str = "filtered_regulations",
    strategy: str = "per_regulation",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    embedding_model: str = "mxbai-embed-large",
) -> FAISS:
    """Construct a FAISS vector store from local regulation documents.

    Parameters
    ----------
    source_dir : str, optional
        Directory containing regulation documents. Defaults to
        ``"filtered_regulations"``.
    strategy : str, optional
        Document splitting strategy. Defaults to ``"per_regulation"``.
    chunk_size : int, optional
        Chunk size for recursive splitting. Defaults to ``1000``.
    chunk_overlap : int, optional
        Chunk overlap for recursive splitting. Defaults to ``200``.
    embedding_model : str, optional
        Ollama embedding model name. Defaults to ``"mxbai-embed-large"``.

    Returns
    -------
    FAISS
        In-memory FAISS vector store populated with embeddings.
    """
    print(
        f"Loading regulation documents from '{source_dir}' using '{strategy}' strategy ..."
    )
    base_docs = gather_local_regulations(source_dir)
    print(f"Loaded {len(base_docs)} base regulation documents.")

    docs = split_documents(
        base_docs, strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    print(
        f"Prepared {len(docs)} chunks (avg chars: {sum(len(d.page_content) for d in docs) // max(1, len(docs))})."
    )

    # Initialize embeddings
    embeddings = OllamaEmbeddings(model=embedding_model)

    # Build FAISS vector store
    vector_store = FAISS.from_documents(docs, embedding=embeddings)
    print("Initialized FAISS index (dimension inferred from first batch).")

    return vector_store


def save_vector_store(vector_store: FAISS, output_path: str):
    """Persist a FAISS vector store to disk.

    Parameters
    ----------
    vector_store : FAISS
        Vector store to serialize.
    output_path : str
        Destination directory for the serialized data.
    """
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(output_dir))
    print(f"Saved FAISS vector store to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS vector database from regulation documents using original rag.py logic"
    )
    parser.add_argument(
        "--source",
        "-s",
        default="processed_regulations",
        help="Source directory containing regulation folders (default: processed_regulations)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="regulations_db",
        help="Output directory for FAISS vector database (default: regulations_db)",
    )
    parser.add_argument(
        "--strategy",
        choices=["per_regulation", "recursive", "markdown_headers"],
        default="per_regulation",
        help="Document splitting strategy (default: per_regulation)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size for text splitting (default: 1000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Chunk overlap for text splitting (default: 200)",
    )
    parser.add_argument(
        "--embedding-model",
        default="mxbai-embed-large",
        help="Ollama embedding model to use (default: mxbai-embed-large)",
    )
    parser.add_argument(
        "--test-query", help="Optional test query to run after building the database"
    )

    args = parser.parse_args()

    # Build the vector store
    vector_store = build_local_index(
        source_dir=args.source,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_model=args.embedding_model,
    )

    # Save to disk
    save_vector_store(vector_store, args.output)

    # Optional test query
    if args.test_query:
        print(f"\nRunning test query: '{args.test_query}'")
        results = vector_store.similarity_search(args.test_query, k=3)
        for i, result in enumerate(results, 1):
            print(
                f"[{i}] {result.metadata.get('reg_dir', 'unknown')} ({len(result.page_content)} chars)"
            )
            print(
                f"    {result.page_content[:200]}..."
                if len(result.page_content) > 200
                else f"    {result.page_content}"
            )
            print()

    print("Vector database build completed successfully!")


if __name__ == "__main__":
    main()
