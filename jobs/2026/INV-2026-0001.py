"""INV-2026-0001 — English-only invoice test."""
from config.business import *
from config.clients import ACME_CORP

DATE          = "2026-05-30"
DUE_DATE      = "2026-06-13"
RELATED_QUOTE = "QUO-2026-0001"

CLIENT = ACME_CORP

PROJECT_TITLE = "Office Network & Satellite Internet Installation"

ITEMS = [
    "--- Hardware Delivered ---",
    ("Starlink Standard Kit (Generation 3) including dish, router, and 15m cable", 1, 599.00),
    ("Ubiquiti UniFi Dream Machine Pro (UDM-Pro)", 1, 379.00),
    ("UniFi 24-port PoE switch (USW-24-PoE)", 1, 459.00),
    ("UniFi U6-LR access points", 4, 179.00),
    "--- Cabling & Accessories ---",
    ("Outdoor-rated CAT6 shielded cable (meters installed)", 80, 2.50),
    ("RJ45 shielded keystones and faceplates", 12, 4.50),
    ("Cable trunking and conduit (25mm PVC)", 30, 1.80),
    "--- Labor ---",
    ("Site survey, mounting, configuration, and customer hand-over", 1, 350.00),
]

DISCOUNT_PCT = 5
TAX_PCT      = 11
DEPOSIT_PAID = 1200.00

PAYMENT_METHODS = [
    f"Cash (Fresh USD) -- payable to {MY_NAME}.",
    "Bank transfer: Bank of Beirut, IBAN LB00 0000 0000 0000 0000 0000 0000.",
    "OMT / Whish wallet on request.",
]

NOTES = [
    "Payment due within 14 days of invoice date.",
    "Late payments may be subject to a 1.5% monthly service fee.",
    "Hardware warranty starts on the installation date.",
]

WATERMARK      = ""
EXCHANGE_RATE  = "Indicative rate: 1 USD = 89,500 LBP."
SHOW_SIGNATURE = True
BILINGUAL      = False
