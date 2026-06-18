#!/usr/bin/env python3
"""
new.py — scaffold a new Quotation / Invoice / Receipt job file.

Usage:
    python new.py quotation                # uses current year
    python new.py invoice --year 2026
    python new.py receipt
"""
import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT      = Path(__file__).parent
JOBS      = ROOT / "jobs"
SCAFFOLDS = ROOT / "templates" / "scaffolds"

TYPE_MAP = {
    "quotation": ("QUO", "quotation.py"),
    "invoice":   ("INV", "invoice.py"),
    "receipt":   ("RCT", "receipt.py"),
}

MAX_NUM = 9999


def next_number(year: int, prefix: str) -> int:
    year_dir = JOBS / str(year)
    pattern = re.compile(rf"^{prefix}-{year}-(\d{{4}})\.py$")
    existing = []
    if year_dir.exists():
        for f in year_dir.iterdir():
            m = pattern.match(f.name)
            if m:
                existing.append(int(m.group(1)))
    n = max(existing) + 1 if existing else 1
    if n > MAX_NUM:
        sys.exit(f"Number overflow: exceeded {MAX_NUM} for {prefix}-{year}.")
    return n


def scaffold(doc_type: str, year: int) -> Path:
    if doc_type not in TYPE_MAP:
        sys.exit(f"Unknown type '{doc_type}'. Use one of: {list(TYPE_MAP)}")

    prefix, scaffold_name = TYPE_MAP[doc_type]
    num = next_number(year, prefix)
    doc_id = f"{prefix}-{year}-{num:04d}"

    year_dir = JOBS / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    src = SCAFFOLDS / scaffold_name
    dst = year_dir / f"{doc_id}.py"

    today       = date.today().isoformat()
    valid_until = (date.today() + timedelta(days=30)).isoformat()
    due_date    = (date.today() + timedelta(days=14)).isoformat()

    content = src.read_text(encoding="utf-8").format(
        ID=doc_id,
        YEAR=year,
        TODAY=today,
        VALID_UNTIL=valid_until,
        DUE_DATE=due_date,
    )
    dst.write_text(content, encoding="utf-8")
    print(f"✓ Created {dst}")
    return dst


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("doc_type", choices=list(TYPE_MAP))
    p.add_argument("--year", type=int, default=date.today().year)
    args = p.parse_args()
    scaffold(args.doc_type, args.year)
