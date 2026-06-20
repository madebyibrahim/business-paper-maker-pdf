"""GUI-safe wrapper around generate.render().

generate.render() is the one process-oriented entry point in the engine: it
prints status to stdout and calls sys.exit(1) on a compile failure. Both of
those would kill a GUI event loop, so this module captures stdout and catches
SystemExit, returning a structured Result the UI can render as a friendly
message instead of crashing.

No engine logic is duplicated — render() does all the real work.
"""
from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass
from pathlib import Path

import generate


@dataclass
class RenderResult:
    ok: bool
    pdf_path: str          # the produced PDF (or .tex if no compiler)
    is_tex_only: bool      # True when the compiler was missing
    log: str               # captured stdout from generate.render()


def render(job_path: str | Path) -> RenderResult:
    """Run the full engine pipeline on a job file, never raising to the caller.

    Catches SystemExit (raised by generate.render on compile failure) and any
    other exception, folding them into a RenderResult so the GUI can show a
    clean message. Returns the path generate.render produced (PDF on success,
    .tex when no compiler) plus the captured text.
    """
    buf = io.StringIO()
    try:
        # generate.render() both prints and returns the output path.
        with contextlib.redirect_stdout(buf):
            out = generate.render(Path(job_path))
    except SystemExit as e:
        # The engine calls sys.exit(1) after printing the log excerpt.
        return RenderResult(ok=False, pdf_path="", is_tex_only=False,
                            log=buf.getvalue() or f"Exit code {e.code}")
    except Exception as e:  # noqa: BLE001 - any engine error is a UI message
        return RenderResult(ok=False, pdf_path="", is_tex_only=False,
                            log=buf.getvalue() + f"\n{type(e).__name__}: {e}")

    out = Path(out)
    return RenderResult(
        ok=out.suffix == ".pdf",
        pdf_path=str(out),
        is_tex_only=out.suffix == ".tex",
        log=buf.getvalue(),
    )
