"""RCT-2026-0002 — Bilingual EN+AR receipt test."""
from config.business import *
from config.clients import SAMPLE_CLIENT

DATE             = "2026-06-05"
RELATED_INVOICE  = "INV-2026-0002"

CLIENT = SAMPLE_CLIENT

AMOUNT_RECEIVED   = 350.00
PAYMENT_METHOD    = "Cash (Fresh USD) / نقدًا بالدولار الطازج"
PAYMENT_REFERENCE = ""
FOR_DESCRIPTION   = "50% deposit on INV-2026-0002 / دفعة مقدمة 50٪ على الفاتورة."
BALANCE_REMAINING = 369.16

NOTES = [
    "Received with thanks. / تم الاستلام مع الشكر.",
    "Balance due upon project completion. / الرصيد المتبقي يُسدّد عند الإنجاز.",
]

EXCHANGE_RATE  = "Settled in USD / تمت التسوية بالدولار."
SHOW_SIGNATURE = True
BILINGUAL      = True
