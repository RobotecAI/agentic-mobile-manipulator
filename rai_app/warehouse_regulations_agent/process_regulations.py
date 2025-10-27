# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Developed by Robotec.ai sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence

# Summarization constants
SUPPORTED_CONTENT_FILES = ["content.md", "text.txt"]


def extract_regulation_number(regulation_name):
    """
    Extract the numerical part from regulation directory name.
    e.g., '1910.23' -> 23, '1910.132AppA' -> 132
    """
    # Match pattern like 1910.XXX where XXX is the regulation number
    match = re.match(r"1910\.(\d+)", regulation_name)
    if match:
        return int(match.group(1))
    return None


def is_in_ranges(number, ranges):
    """
    Check if a number falls within any of the specified ranges.
    ranges: list of tuples (start, end) inclusive
    """
    for start, end in ranges:
        if start <= number <= end:
            return True
    return False


def copy_regulation(source_path, dest_path):
    """
    Copy a regulation directory from source to destination.
    """
    try:
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(source_path, dest_path)
        print(f"✓ Copied: {source_path.name}")
        return True
    except Exception as e:
        print(f"✗ Failed to copy {source_path.name}: {e}")
        return False


def filter_regulations(
    source_dir,
    dest_dir="processed_regulations",
    ranges=None,
    summarize=False,
    llm=None,
    chain_type="stuff",
    chunk_size=3500,
    chunk_overlap=300,
    short_threshold=1200,
    overwrite_summaries=False,
    verbose=False,
):
    """
    Filter and copy regulations based on number ranges, optionally with summarization.

    Args:
        source_dir: Directory containing scraped regulations
        dest_dir: Directory to copy filtered regulations to
        ranges: List of tuples (start, end) for regulation number ranges
        summarize: Whether to summarize regulations after copying
        llm: Language model for summarization
        chain_type: Summarization chain type ('stuff', 'map_reduce', 'refine')
        chunk_size: Character chunk size for splitting
        chunk_overlap: Character overlap between chunks
        short_threshold: If text shorter than this, keep as-is
        overwrite_summaries: Whether to regenerate existing summaries
        verbose: Verbose logging
    """
    if ranges is None:
        ranges = [(1, 40), (66, 68), (132, 140), (155, 165), 176, 212, 335]

    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist")
        return False

    # Create destination directory
    dest_path.mkdir(exist_ok=True)

    # Also copy manifest.json if it exists
    manifest_source = source_path / "manifest.json"
    manifest_dest = dest_path / "manifest.json"

    copied_count = 0
    skipped_count = 0
    summarized_count = 0

    print(f"Filtering regulations from '{source_dir}' to '{dest_dir}'")
    print(f"Target ranges: {ranges}")
    if summarize:
        print(f"Summarization enabled with chain type: {chain_type}")
    print("-" * 50)

    # Get all regulation directories
    regulation_dirs = [
        d for d in source_path.iterdir() if d.is_dir() and d.name.startswith("1910.")
    ]

    # Sort by regulation number for cleaner output
    regulation_dirs.sort(key=lambda x: extract_regulation_number(x.name) or 0)

    for reg_dir in regulation_dirs:
        reg_number = extract_regulation_number(reg_dir.name)

        if reg_number is None:
            print(f"? Skipping {reg_dir.name} (couldn't parse number)")
            skipped_count += 1
            continue

        if is_in_ranges(reg_number, ranges):
            dest_reg_path = dest_path / reg_dir.name

            # Summarize if requested
            if summarize and llm is not None:
                if summarize_regulation(
                    reg_dir,
                    dest_path,
                    llm,
                    chain_type,
                    chunk_size,
                    chunk_overlap,
                    short_threshold,
                    overwrite_summaries,
                    verbose,
                ):
                    summarized_count += 1
                else:
                    skipped_count += 1
            else:
                if copy_regulation(reg_dir, dest_reg_path):
                    copied_count += 1
                else:
                    skipped_count += 1

        else:
            print(
                f"- Skipping {reg_dir.name} (number {reg_number} not in target ranges)"
            )
            skipped_count += 1

    # Copy manifest if it exists
    if manifest_source.exists():
        try:
            shutil.copy2(manifest_source, manifest_dest)
            print("✓ Copied: manifest.json")
        except Exception as e:
            print(f"✗ Failed to copy manifest.json: {e}")

    print("-" * 50)
    print("Summary:")
    print(f"  Copied: {copied_count} regulations")
    print(f"  Skipped: {skipped_count} regulations")
    if summarize:
        print(f"  Summarized: {summarized_count} regulations")
    print(f"  Destination: {dest_path.absolute()}")

    return True


def parse_ranges(range_string):
    """
    Parse range string like "1-40,66-68,132-140,155-165" into list of tuples.
    """
    ranges = []
    for part in range_string.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ranges.append((int(start.strip()), int(end.strip())))
        else:
            # Single number
            num = int(part.strip())
            ranges.append((num, num))
    return ranges


# Summarization functions
def build_llm(model: str = "gpt-4o", temperature: float = 0.1) -> Any:
    """Instantiate an OpenAI LLM/Chat model."""
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)
    except ImportError:
        print(
            "Error: langchain_openai is required for summarization. Install with: pip install langchain-openai"
        )
        return None


def select_content_file(reg_dir: Path, priority: Sequence[str]) -> Optional[Path]:
    """Select the first available content file based on priority."""
    for name in priority:
        p = reg_dir / name
        if p.exists():
            return p
    return None


def make_documents(
    text: str, reg_dir: str, chunk_size: int, chunk_overlap: int
) -> List[Any]:
    """Split text into documents for summarization."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
        docs = splitter.create_documents([text])
        # annotate metadata
        for i, d in enumerate(docs):
            d.metadata["reg_dir"] = reg_dir
            d.metadata["chunk_index"] = i
        return docs
    except ImportError:
        print(
            "Error: langchain and langchain_text_splitters are required for summarization."
        )
        return []


def summarize_text(
    docs: List[Any],
    llm: Any,
    chain_type: str,
    max_retries: int = 2,
    verbose: bool = False,
) -> str:
    """Summarize text using LangChain summarization chain."""
    if not docs:
        return ""

    try:
        from langchain.chains.summarize import load_summarize_chain

        chain = load_summarize_chain(llm, chain_type=chain_type)
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                result = chain.invoke({"input_documents": docs})
                # Newer LangChain returns dict with 'output_text' or string
                if isinstance(result, dict):
                    return result.get("output_text") or result.get("text") or ""
                if isinstance(result, str):
                    return result
                return str(result)
            except Exception as e:
                last_err = e
                if verbose:
                    print(f"  Attempt {attempt} failed: {e}")
                time.sleep(1.5 * attempt)
        raise RuntimeError(
            f"Summarization failed after {max_retries} attempts: {last_err}"
        )
    except ImportError:
        print("Error: langchain is required for summarization.")
        return ""


def maybe_short_circuit(text: str, short_threshold: int) -> Optional[str]:
    """Return text as-is if it's already short enough."""
    if len(text) <= short_threshold:
        return text.strip()
    return None


def summarize_regulation(
    reg_dir: Path,
    dest_root: Path,
    llm: Any,
    chain_type: str = "stuff",
    chunk_size: int = 3500,
    chunk_overlap: int = 300,
    short_threshold: int = 1200,
    overwrite: bool = False,
    verbose: bool = False,
) -> bool:
    """Summarize a single regulation directory."""
    if llm is None:
        return False

    content_path = select_content_file(reg_dir, SUPPORTED_CONTENT_FILES)
    if not content_path:
        if verbose:
            print(f"  Skip {reg_dir.name}: no content file")
        return False

    try:
        raw_text = content_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  Error reading {content_path}: {e}")
        return False

    out_dir = dest_root / reg_dir.name

    # Determine which original content files exist so we mirror their names.
    source_files = [
        fname for fname in SUPPORTED_CONTENT_FILES if (reg_dir / fname).exists()
    ]
    if not source_files:
        if verbose:
            print(f"  Skip {reg_dir.name}: no supported content files present")
        return False

    # Skip if ALL destination counterparts already exist and not overwriting.
    if not overwrite and all((out_dir / f).exists() for f in source_files):
        if verbose:
            print(
                f"  Skip {reg_dir.name}: all summary files already exist (use --overwrite-summaries)"
            )
        return True

    # Check if text is short enough to keep as-is
    short_text = maybe_short_circuit(raw_text, short_threshold)
    if short_text is not None:
        summary = short_text
        if verbose:
            print(f"  Using original text for {reg_dir.name} (short enough)")
    else:
        if verbose:
            print(f"  Summarizing {reg_dir.name}...")
        docs = make_documents(raw_text, reg_dir.name, chunk_size, chunk_overlap)
        if not docs:
            return False
        summary = summarize_text(docs, llm, chain_type=chain_type, verbose=verbose)
        if not summary:
            print(f"  Failed to summarize {reg_dir.name}")
            return False

    # Write summary files
    written_files = []
    for fname in source_files:
        out_path = out_dir / fname
        os.makedirs(out_dir, exist_ok=True)
        if fname == "content.md":
            # Markdown version with header
            md_body = f"# Summary of {reg_dir.name}\n\n" + summary.strip() + "\n"
            out_path.write_text(md_body, encoding="utf-8")
        elif fname == "text.txt":
            txt_body = summary.strip() + "\n"
            out_path.write_text(txt_body, encoding="utf-8")
        else:
            # Fallback
            out_path.write_text(summary.strip() + "\n", encoding="utf-8")
        written_files.append(fname)

    # Copy & augment meta.json if present
    meta_src = reg_dir / "meta.json"
    meta_dest = out_dir / "meta.json"
    meta_data = {}
    if meta_src.exists():
        try:
            meta_data = json.loads(meta_src.read_text(encoding="utf-8"))
        except Exception:
            meta_data = {}

    meta_data["summary_files"] = written_files
    if len(written_files) == 1:
        meta_data["summary_file"] = written_files[0]
    meta_data["summary_model"] = getattr(llm, "model", "unknown")
    meta_data["summary_chain_type"] = chain_type
    meta_data["summary_chars_each"] = {
        f: (out_dir / f).stat().st_size for f in written_files if (out_dir / f).exists()
    }
    meta_data["original_chars"] = len(raw_text)
    meta_dest.write_text(
        json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if verbose:
        print(f"  ✓ Summarized: {reg_dir.name}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Filter and copy OSHA regulations based on number ranges, with optional summarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 process_regulations.py
  python3 process_regulations.py --ranges "1-40,66-68,132-140,155-165, 176, 212, 335"
  python3 process_regulations.py --source regulations --dest my_filtered_regs
  python3 process_regulations.py --ranges "1-10,20-30" --dest essential_regs
  python3 process_regulations.py --summarize --chain stuff --model gpt-4o
        """,
    )

    parser.add_argument(
        "--source",
        "-s",
        default="regulations",
        help="Source directory containing scraped regulations (default: regulations)",
    )

    parser.add_argument(
        "--dest",
        "-d",
        default="processed_regulations",
        help="Destination directory for processed regulations (default: processed_regulations)",
    )

    parser.add_argument(
        "--ranges",
        "-r",
        default="1-40,66-68,132-140,155-165",
        help="Comma-separated ranges of regulation numbers (default: 1-40,66-68,132-140,155-165,176,212,335)",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available regulations without copying",
    )

    # Summarization arguments
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Enable summarization of regulations after copying",
    )

    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o",
        help="Language model for summarization (default: gpt-4o)",
    )

    parser.add_argument(
        "--chain",
        choices=["stuff", "map_reduce", "refine"],
        default="stuff",
        help="Summarization chain type (default: stuff)",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=3500,
        help="Character chunk size for splitting (default: 3500)",
    )

    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=300,
        help="Character overlap between chunks (default: 300)",
    )

    parser.add_argument(
        "--short-threshold",
        type=int,
        default=1200,
        help="If source text shorter than this, keep as-is (default: 1200)",
    )

    parser.add_argument(
        "--overwrite-summaries",
        action="store_true",
        help="Regenerate existing summaries",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.list:
        # List available regulations
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"Error: Source directory '{args.source}' does not exist")
            return 1

        regulation_dirs = [
            d
            for d in source_path.iterdir()
            if d.is_dir() and d.name.startswith("1910.")
        ]
        regulation_dirs.sort(key=lambda x: extract_regulation_number(x.name) or 0)

        print(f"Available regulations in '{args.source}':")
        print("-" * 50)
        for reg_dir in regulation_dirs:
            reg_number = extract_regulation_number(reg_dir.name)
            if reg_number is not None:
                print(f"1910.{reg_number:3d} - {reg_dir.name}")
            else:
                print(f"     ? - {reg_dir.name}")
        print(f"\nTotal: {len(regulation_dirs)} regulations")
        return 0

    try:
        ranges = parse_ranges(args.ranges)

        # Initialize LLM if summarization is requested
        llm = None
        if args.summarize:
            llm = build_llm(model=args.model)
            if llm is None:
                print("Error: Failed to initialize language model for summarization")
                return 1

        success = filter_regulations(
            source_dir=args.source,
            dest_dir=args.dest,
            ranges=ranges,
            summarize=args.summarize,
            llm=llm,
            chain_type=args.chain,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            short_threshold=args.short_threshold,
            overwrite_summaries=args.overwrite_summaries,
            verbose=args.verbose,
        )
        return 0 if success else 1
    except ValueError as e:
        print(f"Error parsing ranges: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
