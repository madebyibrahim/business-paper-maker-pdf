"""Detect whether the LaTeX compilers needed by the engine are installed.

The engine (generate.pick_engine_and_template) chooses pdflatex for
English-only documents and xelatex for bilingual (Arabic) ones. We surface that
choice to the UI so the user knows, before clicking Generate, whether a given
document will actually compile.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class LatexStatus:
    pdflatex: bool     # needed for English-only docs
    xelatex: bool      # needed for bilingual (Arabic) docs

    @property
    def any_compiler(self) -> bool:
        return self.pdflatex or self.xelatex

    def can_compile(self, bilingual: bool) -> bool:
        """Whether the required compiler for the given document is present."""
        return self.xelatex if bilingual else self.pdflatex

    def message(self) -> str:
        """Short, UI-ready summary line, e.g. 'pdflatex: yes | xelatex: no'."""
        def yn(p): return "yes" if p else "no"
        return f"pdflatex: {yn(self.pdflatex)}   |   xelatex: {yn(self.xelatex)}"


def detect() -> LatexStatus:
    return LatexStatus(
        pdflatex=bool(shutil.which("pdflatex")),
        xelatex=bool(shutil.which("xelatex")),
    )
