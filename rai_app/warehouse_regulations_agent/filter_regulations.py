"""
Filter and copy OSHA regulations based on specified number ranges.
This script copies only the regulations that fall within the specified ranges.
"""

import argparse
import re
import shutil
from pathlib import Path


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
    source_dir="output", dest_dir="filtered_regulations", ranges=None
):
    """
    Filter and copy regulations based on number ranges.

    Args:
        source_dir: Directory containing scraped regulations
        dest_dir: Directory to copy filtered regulations to
        ranges: List of tuples (start, end) for regulation number ranges
    """
    if ranges is None:
        ranges = [(1, 40), (66, 68), (132, 140), (155, 165)]

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

    print(f"Filtering regulations from '{source_dir}' to '{dest_dir}'")
    print(f"Target ranges: {ranges}")
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


def main():
    parser = argparse.ArgumentParser(
        description="Filter and copy OSHA regulations based on number ranges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 filter_regulations.py
  python3 filter_regulations.py --ranges "1-40,66-68,132-140,155-165, 176, 212, 335"
  python3 filter_regulations.py --source output --dest my_filtered_regs
  python3 filter_regulations.py --ranges "1-10,20-30" --dest essential_regs
        """,
    )

    parser.add_argument(
        "--source",
        "-s",
        default="output",
        help="Source directory containing scraped regulations (default: output)",
    )

    parser.add_argument(
        "--dest",
        "-d",
        default="filtered_regulations",
        help="Destination directory for filtered regulations (default: filtered_regulations)",
    )

    parser.add_argument(
        "--ranges",
        "-r",
        default="1-40,66-68,132-140,155-165",
        help="Comma-separated ranges of regulation numbers (default: 1-40,66-68,132-140,155-165)",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available regulations without copying",
    )

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
        success = filter_regulations(args.source, args.dest, ranges)
        return 0 if success else 1
    except ValueError as e:
        print(f"Error parsing ranges: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
