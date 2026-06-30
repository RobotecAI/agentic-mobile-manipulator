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

"""Backend-aware structured output.

npu (FastFlowLM) has no response_format/function-calling: constrain output with a
top-level GBNF ``grammar`` field and parse the JSON. Other backends use
``with_structured_output``. ``vlm_structured`` returns a Runnable matching its
interface (``.invoke`` → schema, or the include_raw dict).
"""

from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# JSON-schema → GBNF converter from the llama.cpp submodule (stdlib-only).
_CONVERTER = (
    Path(__file__).resolve().parents[2]
    / "inference"
    / "llama.cpp"
    / "examples"
    / "json_schema_to_grammar.py"
)


@lru_cache(maxsize=1)
def _converter_module():
    if not _CONVERTER.exists():
        raise FileNotFoundError(
            f"GBNF converter not found at {_CONVERTER}; check out the llama.cpp "
            "submodule (`pixi run -e inference submodules`)."
        )
    spec = importlib.util.spec_from_file_location(
        "_flm_json_schema_to_grammar", _CONVERTER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=64)
def _schema_to_gbnf(schema_json: str) -> str:
    mod = _converter_module()
    converter = mod.SchemaConverter(
        prop_order={}, allow_fetch=False, dotall=False, raw_pattern=False
    )
    schema = converter.resolve_refs(json.loads(schema_json), "schema")
    converter.visit(schema, "")  # "" → start rule named 'root'
    return converter.format_grammar()


def _flm_structured(model: Runnable, schema: type[T], include_raw: bool) -> Runnable:
    gbnf = _schema_to_gbnf(json.dumps(schema.model_json_schema()))
    bound = model.bind(extra_body={"grammar": gbnf, "grammar_root": "root"})

    def parse(message):
        text = getattr(message, "content", None)
        text = text if isinstance(text, str) else str(message)
        if not include_raw:
            return schema.model_validate_json(text)
        # Match with_structured_output(include_raw=True)'s shape.
        try:
            return {
                "raw": message,
                "parsed": schema.model_validate_json(text),
                "parsing_error": None,
            }
        except ValidationError as exc:
            return {"raw": message, "parsed": None, "parsing_error": exc}

    return bound | RunnableLambda(parse)


def vlm_structured(
    model: Runnable,
    schema: type[T],
    backend: str | None,
    *,
    include_raw: bool = False,
) -> Runnable:
    """Constrain ``model``'s output to ``schema``. ``npu`` uses GBNF grammar;
    other backends use ``with_structured_output``."""
    if backend == "npu":
        return _flm_structured(model, schema, include_raw)
    return model.with_structured_output(schema, include_raw=include_raw)


def demo() -> None:
    """Self-check: schema → GBNF produces a 'root' rule. Needs no server."""

    class _Box(BaseModel):
        damaged: bool

    g = _schema_to_gbnf(json.dumps(_Box.model_json_schema()))
    assert "root ::=" in g, g
    print("ok:\n" + g)


if __name__ == "__main__":
    demo()
