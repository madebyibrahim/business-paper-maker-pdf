"""QUO-2026-0001 — English-only quotation test."""
from config.business import *
from config.clients import ACME_CORP

DATE        = "2026-05-27"
VALID_UNTIL = "2026-06-26"

CLIENT = ACME_CORP

PROJECT_TITLE = "Office Network & Satellite Internet Installation"

ITEMS = [
    "--- Hardware ---",
    ("Starlink Standard Kit (Generation 3) including dish, router, and 15m cable", 1, 599.00),
    ("Ubiquiti UniFi Dream Machine Pro (UDM-Pro) rack-mounted gateway", 1, 379.00),
    ("UniFi 24-port PoE switch (USW-24-PoE) for office distribution", 1, 459.00),
    ("UniFi U6-LR access points for full-building Wi-Fi 6 coverage", 4, 179.00),
    "--- Cabling & Accessories ---",
    ("Outdoor-rated CAT6 shielded cable (per meter, installed)", 80, 2.50),
    ("RJ45 shielded keystones and faceplates", 12, 4.50),
    ("Cable trunking and conduit (white PVC, 25mm)", 30, 1.80),
    "--- Labor ---",
    ("Site survey, mounting, configuration and customer hand-over (2 technicians, 1 day)", 1, 350.00),
]

DISCOUNT_PCT = 5
TAX_PCT      = 11

PAYMENT_METHODS = [
    "50% deposit on order confirmation; balance on completion.",
    f"Cash (Fresh USD) -- payable to {MY_NAME}.",
    "Bank transfer on request (details on the invoice).",
]

NOTES = [
    "This quotation is valid for 30 days from the date above.",
    "Prices include delivery within Greater Beirut. Outside areas: extra freight at cost.",
    "Warranty: 1 year on hardware (manufacturer); 90 days on installation labor.",
]

WATERMARK      = ""
EXCHANGE_RATE  = ""
SHOW_SIGNATURE = True
BILINGUAL      = False
