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
    python -m rai_app.inference.serve --check       # send a real request to each running endpoint
    python -m rai_app.inference.serve --download    # fetch weights for all local endpoints

Stdlib-only on purpose: the dispatcher must run under the bare pixi/conda env
(so the launched C++ servers inherit the Vulkan/XRT runtime), and must not drag
in the agent stack (langchain, etc.).
"""

import argparse
import concurrent.futures
import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import tomllib

# backends whose endpoints `pixi run inference` actually launches.
LOCAL_BACKENDS = {"gpu", "cpu", "npu"}
LLAMA_BACKENDS = {"gpu", "cpu"}

TMUX_SESSION = "agentic-mobile-manipulator-llm-servers"

# 1x1 PNG (red) as a data URI — enough to exercise the multimodal path in --check
# without shipping an image file. The check only asserts a non-empty reply.
_TEST_IMAGE_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

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
        # flm's --host wants a numeric IP: "localhost" fails with
        # "Invalid argument [system:22]". llama.cpp accepts "localhost", so the
        # SSOT keeps it; only flm needs the translation. Clients still reach it
        # via localhost (resolves to 127.0.0.1).
        flm_host = "127.0.0.1" if str(host) == "localhost" else str(host)
        return [
            flm,
            "serve",
            flm_model,
            "--host",
            flm_host,
            "--port",
            str(port),
            *extra,
        ]

    raise ValueError(f"endpoint '{name}': backend '{backend}' is not launchable here")


def health_url(ep: dict) -> str:
    host = ep.get("host", "localhost")
    # flm (npu/FastFlowLM) has no /health route — its liveness signal is /v1/models.
    # llama.cpp serves /health.
    path = "/v1/models" if ep.get("backend") == "npu" else "/health"
    return f"http://{host}:{ep['port']}{path}"


def _api_root(ep: dict) -> str:
    return f"http://{ep.get('host', 'localhost')}:{ep['port']}"


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    """POST JSON and return the parsed JSON response (raises on HTTP/transport error)."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check_endpoint(name: str, ep: dict) -> tuple[bool, str]:
    """Send one type-appropriate inference request and validate a real response.
    Returns (ok, detail). First request may trigger a model load, so timeouts are
    generous."""
    etype = ep.get("type")
    model = ep.get("model", "")
    root = _api_root(ep)
    try:
        if etype == "embedding":
            r = _post_json(
                f"{root}/v1/embeddings", {"model": model, "input": "hello world"}, 90
            )
            vec = r["data"][0]["embedding"]
            return (len(vec) > 0, f"dim={len(vec)}")

        if etype == "reranker":
            r = _post_json(
                f"{root}/v1/reranking",
                {"model": model, "query": "a cat", "documents": ["a cat", "a car"]},
                90,
            )
            results = r.get("results", [])
            return (
                len(results) > 0 and "relevance_score" in results[0],
                f"{len(results)} scored",
            )

        if etype in ("llm", "vlm"):
            content: object = "Reply with the single word: pong."
            if etype == "vlm":
                content = [
                    {"type": "text", "text": "Reply with the single word: pong."},
                    {"type": "image_url", "image_url": {"url": _TEST_IMAGE_DATA_URI}},
                ]
            r = _post_json(
                f"{root}/v1/chat/completions",
                {
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 256,  # reasoning models (gpt-oss) spend tokens on
                    # reasoning_content first; 16 left content empty
                },
                300,  # a cold 20B load can be slow
            )
            msg = r["choices"][0]["message"]
            # A reasoning model may put its output in reasoning_content and leave
            # content empty on a tight budget — either proves it's generating.
            text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            if not text:
                return (False, "empty completion")
            # NPU endpoints additionally exercise the fork's GBNF grammar support.
            if ep.get("backend") == "npu":
                g = _post_json(
                    f"{root}/v1/chat/completions",
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": "yes or no?"}],
                        "max_tokens": 8,
                        "grammar": 'root ::= "yes" | "no"',
                    },
                    120,
                )
                gtext = (g["choices"][0]["message"]["content"] or "").strip()
                ok = gtext in ("yes", "no")
                return (ok, f"chat ok; grammar={'ok' if ok else f'BAD({gtext!r})'}")
            return (True, f"reply={text[:24]!r}")

        return (False, f"unknown type {etype!r}")
    except (urllib.error.URLError, TimeoutError) as exc:
        return (False, f"unreachable ({getattr(exc, 'reason', exc)})")
    except (KeyError, IndexError, ValueError) as exc:
        return (False, f"bad response ({exc})")


def framework(ep: dict) -> str:
    """Serving framework implied by an endpoint's backend (from the SSOT)."""
    backend = ep.get("backend")
    if backend in LLAMA_BACKENDS:
        return "llama.cpp"
    if backend == "npu":
        return "FastFlowLM"
    return backend or "?"


def cmd_check(endpoints: dict[str, dict]) -> int:
    serveable = local_endpoints(endpoints)
    if not serveable:
        print("no local endpoints to check (all remote?)")
        return 0
    failed = 0
    print("=== Inference functional check ===")
    for name, ep in serveable:
        ok, detail = check_endpoint(name, ep)
        mark = "PASS" if ok else "FAIL"
        via = f"{framework(ep)}/{ep.get('backend')}"
        print(
            f"  [{mark}] {name:<12} type={ep.get('type'):<9} {via:<15} "
            f":{ep.get('port')}  {detail}"
        )
        failed += not ok
    print(f"  {len(serveable) - failed} passed, {failed} failed")
    return 1 if failed else 0


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
    # Collect every fetch up front, then run them concurrently so total
    # throughput saturates the link instead of trickling one file at a time.
    # Output streams live (bars from parallel jobs interleave — that's the cost
    # of seeing progress while saturating the link).
    jobs: list[tuple[str, list[str]]] = []  # (label, argv)
    for name, ep in local_endpoints(endpoints):
        if ep.get("backend") == "npu":
            tag = ep.get("flm_model")
            flm = flm_bin(root)
            if not flm:
                print(
                    f"[skip] {name}: FastFlowLM ('flm') not installed — run 'pixi run build-fastflowlm' on an NPU host"
                )
                continue
            jobs.append((f"{name}: {tag}", [flm, "pull", tag]))
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
            jobs.append(
                (
                    f"{name}: {os.path.basename(dest)}",
                    ["wget", "-q", "--show-progress", "-c", "-O", dest, url],
                )
            )

    if not jobs:
        return 0

    def fetch(job: tuple[str, list[str]]) -> tuple[str, int]:
        label, argv = job
        print(f"[download] {label}", flush=True)
        return label, subprocess.call(argv)  # inherit stdout/stderr -> live progress

    rc = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for label, code in [f.result() for f in [pool.submit(fetch, j) for j in jobs]]:
            print(
                f"[done] {label}" if code == 0 else f"[FAIL] {label} (exit {code})",
                file=sys.stderr,
            )
            rc |= 1 if code else 0
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


def _attach(session: str) -> int:
    # Leave the grid detached when nested in tmux or when a caller (demo.sh)
    # only wants it started, not attached.
    if os.environ.get("TMUX") or os.environ.get("AMM_NO_ATTACH"):
        return 0
    return subprocess.call(["tmux", "attach-session", "-t", session])


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
        print(f"Session '{TMUX_SESSION}' already exists.")
        return _attach(TMUX_SESSION)

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
    return _attach(TMUX_SESSION)


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
    mode.add_argument(
        "--check",
        action="store_true",
        help="send a real inference request to each running local endpoint and validate it",
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
    if args.check:
        return cmd_check(endpoints)
    if args.only:
        return cmd_only(endpoints, root, args.only)
    return cmd_grid(endpoints, root)


if __name__ == "__main__":
    raise SystemExit(main())
