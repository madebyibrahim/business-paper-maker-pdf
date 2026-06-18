"""{ID} — Receipt scaffold."""
from config.business import *

DATE             = "{TODAY}"
RELATED_INVOICE  = ""

CLIENT = {{
    "name":  "",
    "phone": "",
    "email": "",
    "site":  "",
}}

AMOUNT_RECEIVED   = 0.00
PAYMENT_METHOD    = "Cash (Fresh USD)"
PAYMENT_REFERENCE = ""    # e.g. wire ref, OMT receipt #, cheque #
FOR_DESCRIPTION   = ""    # e.g. "Final payment for INV-2026-0001"
BALANCE_REMAINING = 0.00  # 0 means fully paid

NOTES = [
    "Received with thanks.",
]

EXCHANGE_RATE  = ""
SHOW_SIGNATURE = True
BILINGUAL      = False
