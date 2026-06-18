"""{ID} — Invoice scaffold."""
from config.business import *

DATE          = "{TODAY}"
DUE_DATE      = "{DUE_DATE}"
RELATED_QUOTE = ""

CLIENT = {{
    "name":  "",
    "phone": "",
    "email": "",
    "site":  "",
}}

PROJECT_TITLE = ""

ITEMS = [
    # ("Item Name", 1, 100.00),
]

DISCOUNT_PCT = 0
TAX_PCT      = 0
DEPOSIT_PAID = 0.00

PAYMENT_METHODS = [
    f"Cash (Fresh USD) -- payable to {{MY_NAME}}.",
]

NOTES = [
    "Payment due within 14 days of invoice date.",
]

WATERMARK      = ""
EXCHANGE_RATE  = ""
SHOW_SIGNATURE = True
BILINGUAL      = False
