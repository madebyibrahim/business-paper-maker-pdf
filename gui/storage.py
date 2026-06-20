"""Filesystem access for the GUI — listing jobs and computing the next ID.

This reuses new.next_number() verbatim for ID assignment so the GUI and the CLI
can never disagree about numbering. Scanning lives here (rather than calling
into the engine) because the engine has no list function — generate.py only
loads one job at a time.
"""
from __future__ import annotations

import re
from pathlib import Path

# Project layout is fixed and derived from generate.py / new.py conventions.
ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "jobs"
OUTPUT_DIR = ROOT / "output"

# Mirrors generate.ID_RE — the filename is load-bearing.
ID_RE = re.compile(r"^(QUO|INV|RCT)-(\d{4})-(\d{4})$")


def list_jobs() -> list[Path]:
    """All job files under jobs/, sorted newest-year-first then by ID.

    Files that don't match the ID pattern (stray scripts, __init__.py) are
    ignored, matching what generate.parse_id would accept.
    """
    if not JOBS_DIR.exists():
        return []
    found = [p for p in JOBS_DIR.rglob("*.py") if ID_RE.match(p.stem)]
    # Sort by (year desc, prefix, number desc) so the most recent docs land on top.
    def sort_key(p: Path):
        prefix, year, num, _ = _parse(p.stem)
        return (-int(year), prefix, -int(num))
    return sorted(found, key=sort_key)


def output_pdf_for(doc_id: str) -> Path:
    """Where the engine writes the finished PDF for a given doc id."""
    return OUTPUT_DIR / f"{doc_id}.pdf"


def _parse(stem: str):
    m = ID_RE.match(stem)
    prefix, year, num = m.group(1), m.group(2), m.group(3)
    type_map = {"QUO": "quotation", "INV": "invoice", "RCT": "receipt"}
    return prefix, year, num, type_map[prefix]


def parse_id(stem: str):
    """Public wrapper kept here so the GUI never imports generate just to parse."""
    return _parse(stem)


def next_doc_id(doc_type: str, year: int) -> str:
    """Compute the next sequential doc id for a type+year.

    Delegates to new.next_number() so the numbering logic has exactly one home.
    """
    from new import next_number, TYPE_MAP  # local import; new.py is a sibling script
    prefix = TYPE_MAP[doc_type][0]
    num = next_number(year, prefix)
    return f"{prefix}-{year}-{num:04d}"
