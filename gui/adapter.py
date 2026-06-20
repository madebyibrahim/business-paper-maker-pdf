"""Bridge between a job ``.py`` file on disk and a :class:`JobModel` in memory.

Reading reuses generate.load_job(), which imports the job module (pulling
``from config.business import *`` automatically) and exposes every field as a
module attribute. Writing produces source that matches templates/scaffolds/*.py
verbatim in shape, so the CLI keeps working and the files stay diff-friendly.

Trade-off (called out in the plan): if you hand-write Python expressions in a
job file (e.g. an f-string ``f"... {MY_NAME}."``), load_job evaluates them and
the adapter writes the *result* back as a plain literal on save. The rendered
PDF is identical; only the source loses the expression. That is the right call
for a simplification tool — the GUI owns plain-text fields, not arbitrary code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import generate  # the engine; load_job lives there
from gui.models import (
    DOC_FIELDS, JobModel, empty_client,
)


# ---------------------------------------------------------------------------
# Reading: job module -> JobModel
# ---------------------------------------------------------------------------

def load(path: str | Path) -> JobModel:
    """Import a job file and copy its attributes into a JobModel."""
    path = Path(path)
    job = generate.load_job(path)  # also ensures ROOT is on sys.path

    prefix, year, num, doc_type = _parse_stem(path.stem)

    # CLIENT is a dict with the four known keys; pad any missing ones.
    raw_client = getattr(job, "CLIENT", {})
    client = empty_client()
    for k in client:
        client[k] = str(raw_client.get(k, "")) if raw_client else ""

    # Copy every field the editor knows about for this doc type, with defaults.
    fields: dict[str, Any] = {}
    for key, kind, _label in DOC_FIELDS[doc_type]:
        fields[key] = _coerce_in(getattr(job, key, _default_for(kind)), kind)

    return JobModel(
        path=str(path),
        doc_type=doc_type,
        doc_id=path.stem,
        client=client,
        fields=fields,
    )


# ---------------------------------------------------------------------------
# Writing: JobModel -> job .py (scaffold-shaped source)
# ---------------------------------------------------------------------------

def save(model: JobModel, path: str | Path | None = None) -> Path:
    """Serialize the model to a job file in the scaffold format. Returns the path."""
    path = Path(path or model.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_source(model), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _parse_stem(stem: str):
    from gui.storage import parse_id
    prefix, year, num, doc_type = parse_id(stem)
    return prefix, year, num, doc_type


def _default_for(kind: str) -> Any:
    if kind in ("items",):
        return []
    if kind == "bool":
        return False
    if kind == "pct":
        return 0
    if kind == "money":
        return 0.0
    return ""


def _coerce_in(value: Any, kind: str) -> Any:
    """Normalize a loaded attribute into something the editor widgets expect."""
    if kind == "items":
        return [_normalize_item(value) if not isinstance(value, str) else value
                for value in (value or [])]
    return value


def _normalize_item(value: Any) -> Any:
    """A line item should be a 3-tuple (desc, qty, unit). Coerce numeric parts."""
    if isinstance(value, (tuple, list)) and len(value) == 3:
        desc, qty, unit = value
        return (str(desc), _to_number(qty), _to_number(unit))
    return value


def _to_number(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _py_literal(value: Any) -> str:
    """Render a Python value as source for a top-level assignment.

    repr() handles strings, ints, floats, bools, tuples, lists and dicts, and
    produces valid Python for all of them — including correct quoting/escaping
    for strings (so a value containing a quote or backslash stays valid).
    """
    return repr(value)


def _render_source(model: JobModel) -> str:
    """Produce the full job file text, matching the scaffold conventions."""
    type_label = {"quotation": "Quotation", "invoice": "Invoice",
                  "receipt": "Receipt"}[model.doc_type]
    lines: list[str] = []
    lines.append(f'"""{model.doc_id} — {type_label}."""')
    lines.append("from config.business import *")
    lines.append("")

    # Header doc-specific fields first (date, validity/due, related ids), then
    # CLIENT, then PROJECT_TITLE / money / items, then the common tail.
    order = [k for k, _kind, _lbl in DOC_FIELDS[model.doc_type]]

    # 1. Top date / validity block (everything before CLIENT in the scaffold).
    client_block_keys = {"quotation": ["DATE", "VALID_UNTIL"],
                         "invoice":   ["DATE", "DUE_DATE", "RELATED_QUOTE"],
                         "receipt":   ["DATE", "RELATED_INVOICE"]}[model.doc_type]
    for k in client_block_keys:
        lines.append(_assignment(k, model.get(k)))
    lines.append("")

    # 2. CLIENT dict, four keys, aligned like the scaffolds.
    c = model.client
    lines.append("CLIENT = {")
    lines.append(f'    "name":  {_py_literal(c["name"])},')
    lines.append(f'    "phone": {_py_literal(c["phone"])},')
    lines.append(f'    "email": {_py_literal(c["email"])},')
    lines.append(f'    "site":  {_py_literal(c["site"])},')
    lines.append("}")
    lines.append("")

    # 3. Remaining fields in scaffold order, skipping the ones already emitted.
    emitted = set(client_block_keys) | {"CLIENT"}
    for key in order:
        if key in emitted:
            continue
        lines.append(_assignment(key, model.get(key, _default_for_kind(key))))
    lines.append("")
    return "\n".join(lines)


def _default_for_kind(key: str) -> Any:
    for _k, kind, _lbl in [f for fields in DOC_FIELDS.values() for f in fields]:
        if _k == key:
            return _default_for(kind)
    return ""


def _assignment(key: str, value: Any) -> str:
    """One ``KEY = <literal>`` line, with light formatting per kind."""
    if key == "ITEMS":
        return _assignment_items(value)
    if key in ("PAYMENT_METHODS", "NOTES"):
        return _assignment_list(key, value)
    return f"{key} = {_py_literal(value)}"


def _assignment_items(items: list) -> str:
    if not items:
        return "ITEMS = [\n" "    # (\"Item Name\", 1, 100.00),\n" "]"
    body = []
    for it in items:
        if isinstance(it, str):
            body.append(f"    {_py_literal(it)},")
        else:
            desc, qty, unit = it
            # qty reads naturally as an int; unit price keeps money style (599.00).
            body.append(f"    ({_py_literal(desc)}, {_fmt_qty(qty)}, {_fmt_money(unit)}),")
    return "ITEMS = [\n" + "\n".join(body) + "\n]"


def _assignment_list(key: str, values) -> str:
    values = list(values or [])
    # An empty list serializes as a clean empty list (not a placeholder [""]),
    # so round-tripping a doc with no notes doesn't grow a spurious empty entry.
    if not values:
        return f"{key} = []"
    body = "\n".join(f"    {_py_literal(str(v))}," for v in values)
    return f"{key} = [\n{body}\n]"


def _fmt_qty(x) -> str:
    """Quantities render as int when whole (1 not 1.0), else as-is."""
    f = float(x)
    if f.is_integer():
        return str(int(f))
    return repr(f)


def _fmt_money(x) -> str:
    """Unit prices keep two decimals (599.00) to match scaffold style."""
    return f"{float(x):.2f}"
