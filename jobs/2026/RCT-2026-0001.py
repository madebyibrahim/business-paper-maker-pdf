"""RCT-2026-0001 — English-only receipt test."""
from config.business import *
from config.clients import ACME_CORP

DATE             = "2026-06-05"
RELATED_INVOICE  = "INV-2026-0001"

CLIENT = ACME_CORP

AMOUNT_RECEIVED   = 1395.50
PAYMENT_METHOD    = "Bank Transfer"
PAYMENT_REFERENCE = "Wire ref. BOB-2026-AX-44219, received 2026-06-05 at 14:32 UTC"
FOR_DESCRIPTION   = "Final balance on INV-2026-0001 (office network installation)."
BALANCE_REMAINING = 0.00

NOTES = [
    "Received with thanks. This receipt acknowledges full settlement of the referenced invoice.",
    "Please retain this receipt for your accounting records.",
]

EXCHANGE_RATE  = "Settled in USD; no FX conversion applied."
SHOW_SIGNATURE = True
BILINGUAL      = False
