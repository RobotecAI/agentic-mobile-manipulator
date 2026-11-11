#!/usr/bin/env python3
"""Copy the licence files of every conda package installed by pixi into one directory.

A conda package carries its licence texts in ``info/licenses/``, which the installer
keeps in the package cache (``~/.cache/rattler``), not in the environment. The Docker
images are published, so this copies them next to the environments where they cannot
be lost to a cache cleanup:

    third_party_licenses/conda/<name>-<version>-<build>/...   licence files per package
    third_party_licenses/conda/PACKAGES.tsv                   index: environment, package,
                                                              version, build, licence, the URL
                                                              it was installed from, where its
                                                              licence files are, and the recipe
                                                              repository + commit it was built
                                                              from (its source)

Some packages ship no ``info/licenses``: split outputs whose parent package carries the
files, packages that install their licence into the environment itself (e.g.
``share/licenses/``, recorded in the index), and RoboStack's ``ros-jazzy-*`` builds,
which declare their licence only by name (also recorded in the index).

Run it after every step that installs or updates a pixi environment (``pixi run
collect-licenses``). It regenerates the directory from scratch, and fails if an
installed package's cache entry is gone, because its licence files could not be copied.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path


# Licence-looking files a package installs into the environment itself.
_LICENCE_PATH = re.compile(r"(^|/)(licen[cs]e|copying|notice|copyright)[^/]*$|(^|/)share/licenses/", re.I)


def rattler_cache_pkgs() -> Path:
    cache = os.environ.get("RATTLER_CACHE_DIR") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "rattler", "cache"
    )
    return Path(cache) / "pkgs"


def recipe_of(extracted: Path, package_url: str) -> tuple[str, str]:
    """The recipe repository and commit a package was built from.

    conda-forge records them in ``info/about.json`` (``extra.remote_url``/``extra.sha``);
    that is the feedstock, which for split packages is not ``<name>-feedstock`` (e.g.
    libgcc comes from ctng-compilers-feedstock). RoboStack packages record neither; their
    recipes are generated in the channel's repository (e.g. RoboStack/ros-jazzy).
    """
    try:
        extra = json.loads((extracted / "info" / "about.json").read_text()).get("extra") or {}
    except (OSError, ValueError):
        extra = {}
    if extra.get("remote_url"):
        return extra["remote_url"], extra.get("sha") or ""
    channel = re.search(r"/robostack-([a-z]+)/", package_url)
    if channel:
        return f"https://github.com/RoboStack/ros-{channel.group(1)}", ""
    return "", ""


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--envs", type=Path, default=root / ".pixi" / "envs")
    parser.add_argument("--out", type=Path, default=root / "third_party_licenses" / "conda")
    args = parser.parse_args()

    envs = sorted(p for p in args.envs.iterdir() if (p / "conda-meta").is_dir()) if args.envs.is_dir() else []
    if not envs:
        print(f"error: no pixi environments under {args.envs}", file=sys.stderr)
        return 1

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    licence_dirs: dict[str, str] = {}
    recipes: dict[str, tuple[str, str]] = {}
    rows, lost, without_files = [], [], []
    for env in envs:
        for record_path in sorted((env / "conda-meta").glob("*.json")):
            record = json.loads(record_path.read_text())
            if not {"name", "version", "build"} <= record.keys():
                continue
            package = f"{record['name']}-{record['version']}-{record['build']}"
            if package not in licence_dirs:
                extracted = Path(record.get("extracted_package_dir") or rattler_cache_pkgs() / package)
                recipes[package] = recipe_of(extracted, record.get("url") or "")
                if not extracted.is_dir():
                    lost.append(f"{env.name}: {package} ({extracted})")
                    licence_dirs[package] = ""
                elif (extracted / "info" / "licenses").is_dir():
                    shutil.copytree(extracted / "info" / "licenses", args.out / package)
                    licence_dirs[package] = package
                else:
                    in_env = [f for f in record.get("files", []) if _LICENCE_PATH.search(f)]
                    if in_env:
                        more = f" (+{len(in_env) - 1} more)" if len(in_env) > 1 else ""
                        licence_dirs[package] = f"in environment: {in_env[0]}{more}"
                    else:
                        without_files.append(package)
                        licence_dirs[package] = "none (licence declared by name only)"
            rows.append(
                (env.name, record["name"], record["version"], record["build"],
                 record.get("license") or "", record.get("url") or "", licence_dirs[package],
                 *recipes[package])
            )

    with open(args.out / "PACKAGES.tsv", "w") as index:
        index.write("environment\tpackage\tversion\tbuild\tlicense\tpackage_url\tlicense_files"
                    "\trecipe\trecipe_commit\n")
        for row in rows:
            index.write("\t".join(row) + "\n")

    copied = sum(1 for d in licence_dirs.values() if d and not d.startswith(("in environment", "none")))
    in_env = sum(1 for d in licence_dirs.values() if d.startswith("in environment"))
    print(f"{len(rows)} installed packages in {len(envs)} environment(s), {len(licence_dirs)} distinct: "
          f"licence files copied for {copied} into {args.out}; {in_env} install them into the environment; "
          f"{len(without_files)} declare their licence by name only (see PACKAGES.tsv)")
    if lost:
        print("error: package cache entries are missing, so their licence files cannot be copied:\n  "
              + "\n  ".join(lost), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
