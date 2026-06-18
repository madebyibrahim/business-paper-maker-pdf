"""QUO-2026-0002 — Bilingual EN+AR quotation test."""
from config.business import *
from config.clients import SAMPLE_CLIENT

DATE        = "2026-05-27"
VALID_UNTIL = "2026-06-26"

CLIENT = SAMPLE_CLIENT

PROJECT_TITLE = "Home Starlink & WiFi Installation / تركيب ستارلينك وواي فاي للمنزل"

ITEMS = [
    "--- Hardware / المعدات ---",
    ("Starlink Standard Kit / جهاز ستارلينك قياسي", 1, 380.00),
    ("UniFi Express Router / موجه واي فاي", 1, 149.00),
    ("Wall mount bracket / حامل تثبيت على الحائط", 1, 35.00),
    "--- Cabling / الكابلات ---",
    ("Outdoor CAT6 cable per meter / كابل خارجي للمتر", 20, 2.00),
    ("RJ45 connectors / موصلات", 6, 1.50),
    "--- Labor / العمالة ---",
    ("Installation and configuration / التركيب والإعداد", 1, 120.00),
]

DISCOUNT_PCT = 5
TAX_PCT      = 11

PAYMENT_METHODS = [
    f"Cash (Fresh USD) -- payable to {MY_NAME}. / نقدًا بالدولار الطازج.",
    "50% deposit, balance on completion. / 50٪ دفعة مقدمة والباقي عند الإنجاز.",
]

NOTES = [
    "Quotation valid for 30 days. / العرض صالح لمدة 30 يومًا.",
    "Warranty: 1 year hardware, 90 days labor. / الضمان: سنة على المعدات، 90 يومًا على التركيب.",
]

WATERMARK      = ""
EXCHANGE_RATE  = "Indicative: 1 USD = 89,500 LBP / السعر الإرشادي."
SHOW_SIGNATURE = True
BILINGUAL      = True
