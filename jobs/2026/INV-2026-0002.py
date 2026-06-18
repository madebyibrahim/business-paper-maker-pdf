"""INV-2026-0002 — Bilingual EN+AR invoice test."""
from config.business import *
from config.clients import SAMPLE_CLIENT

DATE          = "2026-05-30"
DUE_DATE      = "2026-06-13"
RELATED_QUOTE = "QUO-2026-0002"

CLIENT = SAMPLE_CLIENT

PROJECT_TITLE = "Home Starlink & WiFi Installation / تركيب ستارلينك وواي فاي للمنزل"

ITEMS = [
    "--- Hardware / المعدات ---",
    ("Starlink Standard Kit / جهاز ستارلينك قياسي", 1, 380.00),
    ("UniFi Express Router / موجه واي فاي", 1, 149.00),
    ("Wall mount bracket / حامل تثبيت", 1, 35.00),
    "--- Cabling / الكابلات ---",
    ("Outdoor CAT6 per meter / كابل خارجي للمتر", 20, 2.00),
    ("RJ45 connectors / موصلات", 6, 1.50),
    "--- Labor / العمالة ---",
    ("Installation & configuration / التركيب والإعداد", 1, 120.00),
]

DISCOUNT_PCT = 5
TAX_PCT      = 11
DEPOSIT_PAID = 350.00

PAYMENT_METHODS = [
    f"Cash (Fresh USD) -- payable to {MY_NAME}. / نقدًا بالدولار.",
    "Bank transfer / تحويل بنكي على الطلب.",
    "OMT / Whish wallet / محفظة أوإم تي أو ويش.",
]

NOTES = [
    "Payment due within 14 days. / الدفع خلال 14 يومًا.",
    "Late payment may incur 1.5% monthly fee. / تأخير الدفع يخضع لرسم 1.5٪ شهريًا.",
]

WATERMARK      = ""
EXCHANGE_RATE  = "Indicative: 1 USD = 89,500 LBP / السعر الإرشادي."
SHOW_SIGNATURE = True
BILINGUAL      = True
