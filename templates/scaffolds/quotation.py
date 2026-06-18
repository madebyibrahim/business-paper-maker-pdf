"""{ID} — Quotation scaffold."""
from config.business import *
# from config.clients import SAMPLE_CLIENT  # uncomment to reuse a stored client

DATE        = "{TODAY}"
VALID_UNTIL = "{VALID_UNTIL}"

CLIENT = {{
    "name":  "",
    "phone": "",
    "email": "",
    "site":  "",
}}

PROJECT_TITLE = ""

# Items: tuples (description, qty, unit_price). Strings act as section subheaders.
ITEMS = [
    # "--- Materials ---",
    # ("Item Name", 1, 100.00),
]

DISCOUNT_PCT = 0
TAX_PCT      = 0

PAYMENT_METHODS = [
    f"Cash (Fresh USD) -- payable to {{MY_NAME}}.",
]

NOTES = [
    "This quotation is valid for 30 days.",
]

WATERMARK      = ""      # e.g. "DRAFT" or "" to omit
EXCHANGE_RATE  = ""      # e.g. "USD to LBP: 1 USD = 89,500 LBP"
SHOW_SIGNATURE = True
BILINGUAL      = False   # set True to render EN+AR via xelatex
