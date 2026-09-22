"""The generated TypeScript client has to *compile*, not merely contain the right words.

The tests in ``test_jsclient.py`` assert on substrings and on a balanced brace count.
Both passed while the emitter produced a file that ``tsc`` rejected outright:

* ``headers: {{ 'Content-Type': 'application/json' }}`` -- a doubled brace left over
  from a ``.format``-style string, which is a syntax error in TypeScript;
* a stray ``}`` before every method whose endpoint takes no parameters, closing the
  client class early and leaving the remaining methods at module scope;
* every optional parameter emitted as required, so a caller had to pass all seven
  arguments to a function with six defaults.

A brace count cannot see any of those -- the stray ``}`` and the doubled braces even
balance each other out. So this module runs the real compiler, and falls back to
structural assertions that would each have caught one of the three when it cannot.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence

import pytest

from qh import export_openapi, export_ts_client, mk_app


def sample_app():
    """An app with the three shapes that broke the emitter."""

    def gauge(
        source: str,
        *,
        fmt: str = "markdown",
        detectors: str | Sequence[str] | None = None,
        out: Optional[str] = None,
    ) -> str:
        """Many keyword-only defaults, and a PEP 604 union."""
        return source

    def listing() -> list:
        """No parameters at all -- this is what leaked a closing brace."""
        return []

    def add(x: int, y: int) -> int:
        """All-required, the shape the old tests covered."""
        return x + y

    return mk_app([gauge, listing, add])


@pytest.fixture(scope="module")
def ts_code() -> str:
    spec = export_openapi(sample_app(), include_python_metadata=True)
    return export_ts_client(spec, class_name="SampleClient")


def _tsc_available() -> bool:
    return shutil.which("npx") is not None


@pytest.mark.skipif(not _tsc_available(), reason="npx (for tsc) not available")
def test_generated_client_compiles_under_tsc(ts_code: str, tmp_path: Path) -> None:
    """The real gate: ``tsc --strict`` accepts the file."""
    src = tmp_path / "client.ts"
    src.write_text(ts_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [
                "npx",
                "-y",
                "-p",
                "typescript@5",
                "tsc",
                "--noEmit",
                "--strict",
                "--target",
                "es2020",
                "--lib",
                "es2020,dom",
                str(src),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as e:  # offline npx, no network
        pytest.skip(f"could not run tsc: {e}")
    if proc.returncode != 0 and "npm error" in (proc.stderr or ""):
        pytest.skip("npx could not fetch typescript (offline?)")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_doubled_braces(ts_code: str) -> None:
    """``{{`` is a Python formatting artefact and never valid here."""
    assert "{{" not in ts_code
    assert "}}" not in ts_code


def test_every_method_is_inside_the_class(ts_code: str) -> None:
    """All three methods must appear after ``export class`` and before its close.

    The zero-parameter endpoint used to emit a ``}`` ahead of itself, so everything
    from ``listing`` onwards landed outside the class.
    """
    start = ts_code.index("export class SampleClient")
    class_body = ts_code[start:]
    depth, end = 0, None
    for i, ch in enumerate(class_body):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    assert end is not None, "class never closes"
    body = class_body[:end]
    for name in ("async gauge(", "async listing(", "async add("):
        assert name in body, f"{name} escaped the class body"


def test_optional_parameters_are_optional_and_last(ts_code: str) -> None:
    """A parameter with a Python default must not be required on the client."""
    line = next(ln for ln in ts_code.splitlines() if "async gauge(" in ln)
    assert "source: string" in line
    assert "fmt?: string" in line
    assert "out?: string | null" in line
    # TypeScript rejects a required parameter after an optional one.
    args = line[line.index("(") + 1 : line.rindex(")")].split(", ")
    seen_optional = False
    for arg in args:
        optional = "?" in arg.split(":")[0]
        assert not (seen_optional and not optional), (
            f"required arg after optional: {arg}"
        )
        seen_optional = seen_optional or optional


def test_union_types_survive(ts_code: str) -> None:
    """``str | Sequence[str] | None`` must reach TypeScript intact."""
    assert "detectors?: string | string[] | null" in ts_code
    assert "out?: string | null" in ts_code


def test_docstring_cannot_close_the_jsdoc_comment() -> None:
    """A docstring containing ``*/`` must not terminate the comment early."""

    def tricky(x: str) -> str:
        """Matches /\\*(.*?)\\*/ in the source."""
        return x

    spec = export_openapi(mk_app([tricky]), include_python_metadata=True)
    code = export_ts_client(spec)
    # Slice the method's own JSDoc, not the class header's.
    start = code.rindex("/**", 0, code.index("async tricky"))
    header = code[start : code.index("async tricky")]
    assert header.count("*/") == 1, "the JSDoc block closes more than once"


def test_openapi_spec_is_json_serialisable() -> None:
    json.dumps(export_openapi(sample_app(), include_python_metadata=True))
