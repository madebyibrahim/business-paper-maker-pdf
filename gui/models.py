"""Form-friendly data model for a job file.

A :class:`JobModel` mirrors the module-level variables a job ``.py`` exposes
(see templates/scaffolds/*.py and the field table in README.md). It is a plain
data container — no Qt, no I/O — so the adapter and the editor widgets can both
depend on it without a circular dependency on PySide6.

Three document types share most fields; type-specific ones live in
:attr:`JobModel.fields` keyed by the names the engine reads via ``getattr``
(DATE, VALID_UNTIL, DUE_DATE, ITEMS, AMOUNT_RECEIVED, ...). Keeping everything
in one flat dict keeps serialization to the scaffold format trivial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Document type -> human label + ID prefix (must stay in sync with generate.DOC_TYPES
# and new.TYPE_MAP).
DOC_TYPES = ("quotation", "invoice", "receipt")
TYPE_LABELS = {
    "quotation": "Quotation",
    "invoice":   "Invoice",
    "receipt":   "Receipt",
}
TYPE_PREFIXES = {
    "quotation": "QUO",
    "invoice":   "INV",
    "receipt":   "RCT",
}
PREFIX_TO_TYPE = {v: k for k, v in TYPE_PREFIXES.items()}


# A client dict has exactly these keys (config/clients.py + every scaffold).
CLIENT_KEYS = ("name", "phone", "email", "site")


def empty_client() -> dict[str, str]:
    return {k: "" for k in CLIENT_KEYS}


# Per-type ordered field definitions for the editor. Each entry is
# (key, kind, label). ``kind`` drives which widget renders it:
#   str   -> single-line text
#   text  -> multi-line text (notes, payment methods)
#   date  -> YYYY-MM-DD date edit
#   pct   -> percentage spin (DISCOUNT_PCT / TAX_PCT)
#   money -> decimal money field
#   bool  -> checkbox
#   items -> the line-items table (handled by the items editor)
DOC_FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "quotation": [
        ("DATE",            "date",  "Date"),
        ("VALID_UNTIL",     "date",  "Valid until"),
        ("PROJECT_TITLE",   "str",   "Project title"),
        ("ITEMS",           "items", "Items"),
        ("DISCOUNT_PCT",    "pct",   "Discount %"),
        ("TAX_PCT",         "pct",   "Tax %"),
        ("PAYMENT_METHODS", "text",  "Payment methods (one per line)"),
        ("NOTES",           "text",  "Notes (one per line)"),
        ("WATERMARK",       "str",   "Watermark (blank to omit)"),
        ("EXCHANGE_RATE",   "str",   "Exchange rate note"),
        ("SHOW_SIGNATURE",  "bool",  "Show signature line"),
        ("BILINGUAL",       "bool",  "Bilingual (English + Arabic)"),
    ],
    "invoice": [
        ("DATE",            "date",  "Date"),
        ("DUE_DATE",        "date",  "Due date"),
        ("RELATED_QUOTE",   "str",   "Related quote ID"),
        ("PROJECT_TITLE",   "str",   "Project title"),
        ("ITEMS",           "items", "Items"),
        ("DISCOUNT_PCT",    "pct",   "Discount %"),
        ("TAX_PCT",         "pct",   "Tax %"),
        ("DEPOSIT_PAID",    "money", "Deposit paid"),
        ("PAYMENT_METHODS", "text",  "Payment methods (one per line)"),
        ("NOTES",           "text",  "Notes (one per line)"),
        ("WATERMARK",       "str",   "Watermark (blank to omit)"),
        ("EXCHANGE_RATE",   "str",   "Exchange rate note"),
        ("SHOW_SIGNATURE",  "bool",  "Show signature line"),
        ("BILINGUAL",       "bool",  "Bilingual (English + Arabic)"),
    ],
    "receipt": [
        ("DATE",             "date",  "Date"),
        ("RELATED_INVOICE",  "str",   "Related invoice ID"),
        ("AMOUNT_RECEIVED",  "money", "Amount received"),
        ("PAYMENT_METHOD",   "str",   "Payment method"),
        ("PAYMENT_REFERENCE","str",   "Payment reference"),
        ("FOR_DESCRIPTION",  "str",   "For / description"),
        ("BALANCE_REMAINING","money", "Balance remaining"),
        ("NOTES",            "text",  "Notes (one per line)"),
        ("EXCHANGE_RATE",    "str",   "Exchange rate note"),
        ("SHOW_SIGNATURE",   "bool",  "Show signature line"),
        ("BILINGUAL",        "bool",  "Bilingual (English + Arabic)"),
    ],
}


@dataclass
class JobModel:
    """A single editable business document, in memory."""

    path: str                       # jobs/<year>/<ID>.py, "" if not yet saved
    doc_type: str                   # "quotation" | "invoice" | "receipt"
    doc_id: str                     # e.g. "QUO-2026-0001"
    client: dict[str, str] = field(default_factory=empty_client)
    fields: dict[str, Any] = field(default_factory=dict)  # all other variables

    def get(self, key: str, default: Any = "") -> Any:
        return self.fields.get(key, default)
