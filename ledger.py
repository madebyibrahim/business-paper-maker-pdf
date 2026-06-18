#!/usr/bin/env python3
"""
ledger.py — export all invoices and receipts to CSV ledgers.
"""
import csv
from pathlib import Path
from generate import load_job, compute_items, compute_totals

ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"


def run():
    invoices, receipts = [], []
    for p in sorted(JOBS.rglob("*.py")):
        if p.name.startswith("INV-"):
            job = load_job(p)
            items, subtotal = compute_items(getattr(job, "ITEMS", []))
            totals = compute_totals(
                subtotal,
                getattr(job, "DISCOUNT_PCT", 0),
                getattr(job, "TAX_PCT", 0),
                getattr(job, "DEPOSIT_PAID", 0.0),
            )
            client = getattr(job, "CLIENT", {})
            invoices.append({
                "Date":             getattr(job, "DATE", ""),
                "Invoice ID":       p.stem,
                "Client":           client.get("name", ""),
                "Project":          getattr(job, "PROJECT_TITLE", ""),
                "Total USD":        totals["raw_grand_total"],
                "Deposit Paid USD": totals["raw_deposit"],
                "Amount Due USD":   totals["raw_amount_due"],
            })
        elif p.name.startswith("RCT-"):
            job = load_job(p)
            client = getattr(job, "CLIENT", {})
            receipts.append({
                "Date":                getattr(job, "DATE", ""),
                "Receipt ID":          p.stem,
                "Ref Invoice":         getattr(job, "RELATED_INVOICE", ""),
                "Client":              client.get("name", ""),
                "Payment Method":      getattr(job, "PAYMENT_METHOD", ""),
                "Amount Received USD": getattr(job, "AMOUNT_RECEIVED", 0.0),
            })

    if invoices:
        with open(ROOT / "ledger_invoices.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=invoices[0].keys())
            w.writeheader()
            w.writerows(invoices)
        print(f"✓ Created ledger_invoices.csv  ({len(invoices)} rows)")

    if receipts:
        with open(ROOT / "ledger_receipts.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=receipts[0].keys())
            w.writeheader()
            w.writerows(receipts)
        print(f"✓ Created ledger_receipts.csv  ({len(receipts)} rows)")


if __name__ == "__main__":
    if JOBS.exists():
        run()
