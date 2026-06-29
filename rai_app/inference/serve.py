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

"""Inference dispatcher — the single entry point that turns the SSOT config
(``config.toml`` / ``[endpoints.*]``) into running model servers.

It reads each endpoint, routes it to the right backend, and builds the launch
command:

    backend = "gpu" | "cpu"  → llama.cpp   (inference/llama.cpp/build/bin/llama-server)
    backend = "npu"          → FastFlowLM  (`flm serve`)
    backend = "openai"       → remote API, skipped (nothing to serve locally)

Because every port / weight path / model tag lives in one file, the dispatcher
is also the source for the health checks (`--health`) and weight downloads
(`--download`), so smoke_test.sh and download_models.sh no longer hardcode them.

Usage:
    python -m rai_app.inference.serve               # tmux grid of all local endpoints
    python -m rai_app.inference.serve --only NAME   # run ONE endpoint in the foreground
    python -m rai_app.inference.serve --print       # print resolved commands and exit
    python -m rai_app.inference.serve --health      # print health-check URLs and exit
    python -m rai_app.inference.serve --download    # fetch weights for all local endpoints

Stdlib-only on purpose: the dispatcher must run under the bare pixi/conda env
(so the launched C++ servers inherit the Vulkan/XRT runtime), and must not drag
in the agent stack (langchain, etc.).
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib

# backends whose endpoints `pixi run inference` actually launches.
LOCAL_BACKENDS = {"gpu", "cpu", "npu"}
LLAMA_BACKENDS = {"gpu", "cpu"}

TMUX_SESSION = "llm-servers"

# Extra llama.cpp flags implied by an endpoint's `type`. The embedding/reranker
# context flags mirror the values the demo has always served with.
LLAMA_TYPE_ARGS: dict[str, list[str]] = {
    "llm": [],
    "vlm": [],  # --mmproj is added separately (it needs a path from the endpoint)
    "embedding": [
        "--embedding",
        "--pooling",
        "last",
        "-c",
        "4096",
        "-b",
        "2048",
        "-ub",
        "2048",
    ],
    "reranker": [
        "--embedding",
        "--pooling",
        "rank",
        "-c",
        "4096",
        "-b",
        "2048",
        "-ub",
        "2048",
    ],
}


def demo_root(config_path: str) -> str:
    """Root used to expand ``${DEMO_ROOT}``. Falls back to the config's directory
    so the dispatcher works even outside an activated pixi shell (e.g. --print)."""
    return os.environ.get("DEMO_ROOT") or str(Path(config_path).resolve().parent)


def _expand(value: str, root: str) -> str:
    return os.path.expanduser(os.path.expandvars(value.replace("${DEMO_ROOT}", root)))


def load_endpoints(config_path: str) -> dict[str, dict]:
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)
    endpoints = raw.get("endpoints")
    if not endpoints:
        raise SystemExit(f"{config_path}: no [endpoints.*] tables found")
    return endpoints


def is_served_locally(ep: dict) -> bool:
    """An endpoint is launched here only if it runs on a local backend AND has no
    explicit base_url. An explicit base_url means it already lives elsewhere
    (remote API, or a separate container) — this host just talks to it."""
    return ep.get("backend") in LOCAL_BACKENDS and not ep.get("base_url")


def local_endpoints(endpoints: dict[str, dict]) -> list[tuple[str, dict]]:
    """Endpoints this host should serve."""
    return [(name, ep) for name, ep in endpoints.items() if is_served_locally(ep)]


def llama_server_bin(root: str) -> str:
    return os.path.join(root, "inference", "llama.cpp", "build", "bin", "llama-server")


def flm_bin(root: str) -> str | None:
    """The repo-built fork binary, or None if it hasn't been built. We deliberately
    do NOT fall back to a `flm` on PATH: the global /usr/local/bin flm is the upstream
    release with no GBNF grammar support, and BOTH report the same `flm version`, so a
    PATH fallback would silently serve the wrong binary. Local or nothing."""
    repo_flm = os.path.join(root, "inference", "FastFlowLM", "src", "build", "flm")
    return repo_flm if os.path.exists(repo_flm) else None


def build_command(name: str, ep: dict, root: str) -> list[str]:
    """Resolve a single endpoint into its launch argv. Raises ValueError on a
    misconfigured endpoint (missing weights, unknown backend, ...)."""
    backend = ep.get("backend")
    etype = ep.get("type")
    host = ep.get("host", "localhost")
    port = ep.get("port")
    extra = list(ep.get("extra_args", []))

    if port is None:
        raise ValueError(f"endpoint '{name}': missing 'port'")
    if etype not in LLAMA_TYPE_ARGS:
        raise ValueError(
            f"endpoint '{name}': unknown type '{etype}' "
            f"(expected one of {sorted(LLAMA_TYPE_ARGS)})"
        )

    if backend in LLAMA_BACKENDS:
        model_path = ep.get("model_path")
        if not model_path:
            raise ValueError(
                f"endpoint '{name}': backend '{backend}' needs 'model_path'"
            )
        cmd = [llama_server_bin(root), "-m", _expand(model_path, root)]
        if etype == "vlm":
            mmproj = ep.get("mmproj_path")
            if not mmproj:
                raise ValueError(
                    f"endpoint '{name}': a vlm on '{backend}' needs 'mmproj_path'"
                )
            cmd += ["--mmproj", _expand(mmproj, root)]
        cmd += LLAMA_TYPE_ARGS[etype]
        if backend == "cpu":
            cmd += ["-ngl", "0"]  # force CPU even on the Vulkan build
        cmd += ["--host", str(host), "--port", str(port)]
        cmd += extra
        return cmd

    if backend == "npu":
        flm_model = ep.get("flm_model")
        if not flm_model:
            raise ValueError(
                f"endpoint '{name}': backend 'npu' needs 'flm_model' (FastFlowLM tag)"
            )
        flm = flm_bin(root)
        if not flm:
            raise ValueError(
                f"endpoint '{name}': FastFlowLM not built at "
                f"inference/FastFlowLM/src/build/flm — run 'pixi run build-fastflowlm'"
            )
        return [
            flm,
            "serve",
            flm_model,
            "--host",
            str(host),
            "--port",
            str(port),
            *extra,
        ]

    raise ValueError(f"endpoint '{name}': backend '{backend}' is not launchable here")


def health_url(ep: dict) -> str:
    host = ep.get("host", "localhost")
    return f"http://{host}:{ep['port']}/health"


# ─── Modes ──────────────────────────────────────────────────────────────────


def cmd_print(endpoints: dict[str, dict], root: str) -> int:
    serveable = local_endpoints(endpoints)
    remote = [n for n, e in endpoints.items() if not is_served_locally(e)]
    print(f"# DEMO_ROOT = {root}")
    for name, ep in serveable:
        backend = ep.get("backend")
        try:
            cmd = build_command(name, ep, root)
            rendered = shlex.join(cmd)
        except ValueError as exc:
            rendered = f"!! {exc}"
        print(
            f"\n[{name}]  type={ep.get('type')}  backend={backend}  port={ep.get('port')}"
        )
        print(f"  {rendered}")
    if remote:
        print(f"\n# remote (not served locally): {', '.join(remote)}")
    return 0


def cmd_health(endpoints: dict[str, dict]) -> int:
    for _name, ep in local_endpoints(endpoints):
        print(health_url(ep))
    return 0


def cmd_download(endpoints: dict[str, dict], root: str) -> int:
    rc = 0
    for name, ep in local_endpoints(endpoints):
        backend = ep.get("backend")
        if backend == "npu":
            tag = ep.get("flm_model")
            flm = flm_bin(root)
            if not flm:
                print(
                    f"[skip] {name}: FastFlowLM ('flm') not installed — run 'pixi run build-fastflowlm' on an NPU host"
                )
                continue
            print(f"[flm pull] {name}: {tag}")
            rc |= subprocess.call([flm, "pull", tag])
            continue
        # llama.cpp backends: fetch the gguf(s) named in the SSOT.
        targets = [(ep.get("model_url"), ep.get("model_path"))]
        if ep.get("type") == "vlm":
            targets.append((ep.get("mmproj_url"), ep.get("mmproj_path")))
        for url, dest in targets:
            if not url or not dest:
                continue
            dest = _expand(dest, root)
            if os.path.exists(dest):
                print(f"[skip] {name}: {os.path.basename(dest)} already exists")
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            print(f"[download] {name}: {os.path.basename(dest)}")
            rc |= subprocess.call(
                ["wget", "-q", "--show-progress", "-c", "-O", dest, url]
            )
    return rc


def cmd_only(endpoints: dict[str, dict], root: str, name: str) -> int:
    if name not in endpoints:
        raise SystemExit(f"unknown endpoint '{name}'. Known: {sorted(endpoints)}")
    ep = endpoints[name]
    if not is_served_locally(ep):
        raise SystemExit(
            f"endpoint '{name}' (backend={ep.get('backend')}) is not served locally"
        )
    cmd = build_command(name, ep, root)
    print(f"[{name}] exec: {shlex.join(cmd)}", file=sys.stderr)
    os.execvp(cmd[0], cmd)  # replace this process with the server


def cmd_grid(endpoints: dict[str, dict], root: str) -> int:
    serveable = local_endpoints(endpoints)
    if not serveable:
        raise SystemExit("no local endpoints to serve (all remote?)")
    # Validate every endpoint up front so a typo fails fast, not pane-by-pane.
    for name, ep in serveable:
        build_command(name, ep, root)
    if not shutil.which("tmux"):
        raise SystemExit(
            "tmux is required for `pixi run inference` (use --only NAME without it)"
        )

    if (
        subprocess.call(
            ["tmux", "has-session", "-t", TMUX_SESSION],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0
    ):
        print(f"Session '{TMUX_SESSION}' already exists. Attaching...")
        return subprocess.call(["tmux", "attach-session", "-t", TMUX_SESSION])

    # Re-enter pixi per pane so each server gets the activated runtime, then run
    # this same dispatcher in --only mode (which execs the server in-place).
    def pane_cmd(name: str) -> str:
        return f"pixi run inference --only {shlex.quote(name)}"

    first, *rest = serveable
    subprocess.check_call(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            TMUX_SESSION,
            "-n",
            "inference",
            "-x",
            "220",
            "-y",
            "50",
        ]
    )
    subprocess.check_call(
        [
            "tmux",
            "send-keys",
            "-t",
            f"{TMUX_SESSION}:inference",
            pane_cmd(first[0]),
            "Enter",
        ]
    )
    for name, _ep in rest:
        subprocess.check_call(
            ["tmux", "split-window", "-t", f"{TMUX_SESSION}:inference"]
        )
        subprocess.check_call(
            ["tmux", "select-layout", "-t", f"{TMUX_SESSION}:inference", "tiled"]
        )
        subprocess.check_call(
            [
                "tmux",
                "send-keys",
                "-t",
                f"{TMUX_SESSION}:inference",
                pane_cmd(name),
                "Enter",
            ]
        )
    subprocess.check_call(
        ["tmux", "select-layout", "-t", f"{TMUX_SESSION}:inference", "tiled"]
    )
    return subprocess.call(["tmux", "attach-session", "-t", TMUX_SESSION])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("INFERENCE_CONFIG", "config.toml"),
        help="path to the SSOT config (default: config.toml)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--only", metavar="NAME", help="run a single endpoint in the foreground"
    )
    mode.add_argument(
        "--print",
        dest="do_print",
        action="store_true",
        help="print resolved commands and exit",
    )
    mode.add_argument(
        "--health", action="store_true", help="print health-check URLs and exit"
    )
    mode.add_argument(
        "--download", action="store_true", help="download weights for local endpoints"
    )
    args = parser.parse_args(argv)

    endpoints = load_endpoints(args.config)
    root = demo_root(args.config)

    if args.do_print:
        return cmd_print(endpoints, root)
    if args.health:
        return cmd_health(endpoints)
    if args.download:
        return cmd_download(endpoints, root)
    if args.only:
        return cmd_only(endpoints, root, args.only)
    return cmd_grid(endpoints, root)


if __name__ == "__main__":
    raise SystemExit(main())
