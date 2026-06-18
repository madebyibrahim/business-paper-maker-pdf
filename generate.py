#!/usr/bin/env python3
"""
generate.py — render a Quotation / Invoice / Receipt PDF from a Python job file.

Usage:
    python generate.py jobs/2026/QUO-2026-0001.py
"""
from __future__ import annotations
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    sys.exit("Missing dependency. Run:  pip install -r requirements.txt")

try:
    from num2words import num2words
    HAVE_NUM2WORDS = True
except ImportError:
    HAVE_NUM2WORDS = False

ROOT      = Path(__file__).parent
TEMPLATES = ROOT / "templates"
OUTPUT    = ROOT / "output"
BUILD     = OUTPUT / ".build"

ID_RE = re.compile(r"^(QUO|INV|RCT)-(\d{4})-(\d{4})$")

DOC_TYPES = {
    "QUO": "quotation",
    "INV": "invoice",
    "RCT": "receipt",
}

# ---------------------------------------------------------------------------
# Job loading & parsing
# ---------------------------------------------------------------------------

def load_job(path: Path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        sys.exit(f"Cannot load job file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_id(stem: str):
    m = ID_RE.match(stem)
    if not m:
        sys.exit(f"Filename '{stem}' does not match pattern PREFIX-YYYY-NNNN.")
    prefix, year, num = m.groups()
    return prefix, year, num, DOC_TYPES[prefix]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_date(d_str: str) -> str:
    if not d_str:
        return ""
    try:
        return datetime.strptime(d_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return d_str


def fmt_money(x: float) -> str:
    return f"{x:,.2f}"


def fmt_qty(q) -> str:
    if isinstance(q, float) and q.is_integer():
        return str(int(q))
    return str(q)


def compute_items(raw_items):
    rows = []
    subtotal = 0.0
    row_idx = 1
    for item in raw_items:
        if isinstance(item, str):
            rows.append({
                "is_subheader": True,
                "desc": item.strip("- ").strip(),
            })
        else:
            desc, qty, unit = item
            line = round(qty * unit, 2)
            subtotal += line
            rows.append({
                "is_subheader": False,
                "n":      f"{row_idx:02d}",
                "desc":   desc,
                "qty":    fmt_qty(qty),
                "unit":   fmt_money(unit),
                "total":  fmt_money(line),
                "alt":    (row_idx % 2 == 0),
            })
            row_idx += 1
    return rows, round(subtotal, 2)


def compute_totals(subtotal, discount_pct=0, tax_pct=0, deposit_paid=0.0):
    discount_amount = round(subtotal * discount_pct / 100, 2) if discount_pct else 0.0
    after_discount  = round(subtotal - discount_amount, 2)
    tax_amount      = round(after_discount * tax_pct / 100, 2) if tax_pct else 0.0
    grand_total     = round(after_discount + tax_amount, 2)
    amount_due      = round(grand_total - (deposit_paid or 0), 2)

    return {
        "subtotal":         fmt_money(subtotal),
        "discount_pct":     discount_pct or 0,
        "discount_amount":  fmt_money(discount_amount),
        "tax_pct":          tax_pct or 0,
        "tax_amount":       fmt_money(tax_amount),
        "grand_total":      fmt_money(grand_total),
        "deposit_paid":     fmt_money(deposit_paid) if deposit_paid else 0,
        "amount_due":       fmt_money(amount_due),
        "raw_grand_total":  grand_total,
        "raw_deposit":      deposit_paid or 0.0,
        "raw_amount_due":   amount_due,
    }


def amount_in_words(amount: float) -> str:
    if not HAVE_NUM2WORDS:
        return f"USD {fmt_money(amount)} only."
    whole = int(amount)
    cents = round((amount - whole) * 100)
    words = num2words(whole).replace("-", " ").capitalize()
    out = f"{words} US Dollars"
    if cents:
        out += f" and {num2words(cents)} Cents"
    return out + " only."


# ---------------------------------------------------------------------------
# LaTeX escaping + bilingual Arabic wrapping
# ---------------------------------------------------------------------------

def tex_escape(s):
    if s is None:
        return ""
    s = str(s)
    repl = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for k, v in repl:
        s = s.replace(k, v)
    return s


# Unicode ranges that contain Arabic letters & presentation forms.
ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u0870-\u089F\u08A0-\u08FF"
    r"\uFB50-\uFDFF\uFE70-\uFEFF]"
)
# Walk one "token" at a time: a LaTeX macro, an escaped char, or a single char.
TOKEN_RE = re.compile(r"\\[a-zA-Z]+(?:\{\})?|\\.|.", re.DOTALL)


def is_latex_letter_macro(tok: str) -> bool:
    return len(tok) >= 2 and tok[0] == "\\" and tok[1].isascii() and tok[1].isalpha()


def wrap_arabic_runs(s: str) -> str:
    r"""
    In bilingual mode, automatically wrap Arabic character runs with
    \textarabic{...} so polyglossia renders them with the Arabic font/direction.

    Anchors that decide which mode we're in:
      - A *Latin anchor* is an ASCII letter or a LaTeX command (\textbf, \&, ...).
      - An *Arabic anchor* is any Arabic-range character.
    Non-anchor tokens (spaces, digits, punctuation) follow the current mode.
    """
    if not s or not ARABIC_RE.search(s):
        return s

    out, buf = [], []
    mode = "latin"

    def flush():
        if not buf:
            return
        seg = "".join(buf)
        if mode == "arabic":
            out.append(r"\textarabic{" + seg + "}")
        else:
            out.append(seg)
        buf.clear()

    for tok in TOKEN_RE.findall(s):
        is_latin_anchor  = is_latex_letter_macro(tok) or (len(tok) == 1 and tok.isascii() and tok.isalpha())
        is_arabic_anchor = bool(ARABIC_RE.search(tok))
        if is_latin_anchor and mode == "arabic":
            flush()
            mode = "latin"
        elif is_arabic_anchor and mode == "latin":
            flush()
            mode = "arabic"
        buf.append(tok)
    flush()
    return "".join(out)


# ---------------------------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------------------------

def make_env(bilingual: bool = False) -> Environment:
    def finalize(v):
        if isinstance(v, str):
            v = tex_escape(v)
            if bilingual:
                v = wrap_arabic_runs(v)
        return v

    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        block_start_string="((*",    block_end_string="*))",
        variable_start_string="<<",  variable_end_string=">>",
        comment_start_string="((#",  comment_end_string="#))",
        trim_blocks=True, lstrip_blocks=True,
        autoescape=False, undefined=StrictUndefined,
        finalize=finalize,
    )


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def build_quotation_ctx(job, doc_id, business):
    items, subtotal = compute_items(getattr(job, "ITEMS", []))
    totals = compute_totals(
        subtotal,
        discount_pct=getattr(job, "DISCOUNT_PCT", 0),
        tax_pct=getattr(job, "TAX_PCT", 0),
    )
    return {
        "doc": {
            "id":              doc_id,
            "date":            fmt_date(job.DATE),
            "valid_until":     fmt_date(job.VALID_UNTIL),
            "project_title":   getattr(job, "PROJECT_TITLE", ""),
            "payment_methods": getattr(job, "PAYMENT_METHODS", []),
            "notes":           getattr(job, "NOTES", []),
            "watermark":       getattr(job, "WATERMARK", ""),
            "exchange_rate":   getattr(job, "EXCHANGE_RATE", ""),
            "show_signature":  getattr(job, "SHOW_SIGNATURE", True),
        },
        "client": job.CLIENT, "items": items, "totals": totals, **business,
    }


def build_invoice_ctx(job, doc_id, business):
    items, subtotal = compute_items(getattr(job, "ITEMS", []))
    totals = compute_totals(
        subtotal,
        discount_pct=getattr(job, "DISCOUNT_PCT", 0),
        tax_pct=getattr(job, "TAX_PCT", 0),
        deposit_paid=getattr(job, "DEPOSIT_PAID", 0.0),
    )
    return {
        "doc": {
            "id":              doc_id,
            "date":            fmt_date(job.DATE),
            "due_date":        fmt_date(job.DUE_DATE),
            "related_quote":   getattr(job, "RELATED_QUOTE", ""),
            "project_title":   getattr(job, "PROJECT_TITLE", ""),
            "payment_methods": getattr(job, "PAYMENT_METHODS", []),
            "notes":           getattr(job, "NOTES", []),
            "watermark":       getattr(job, "WATERMARK", ""),
            "exchange_rate":   getattr(job, "EXCHANGE_RATE", ""),
            "show_signature":  getattr(job, "SHOW_SIGNATURE", True),
        },
        "client": job.CLIENT, "items": items, "totals": totals, **business,
    }


def build_receipt_ctx(job, doc_id, business):
    amount  = float(job.AMOUNT_RECEIVED)
    balance = float(getattr(job, "BALANCE_REMAINING", 0) or 0)
    return {
        "doc": {
            "id":                doc_id,
            "date":              fmt_date(job.DATE),
            "related_invoice":   getattr(job, "RELATED_INVOICE", ""),
            "amount_received":   fmt_money(amount),
            "amount_words":      amount_in_words(amount),
            "payment_method":    job.PAYMENT_METHOD,
            "payment_reference": getattr(job, "PAYMENT_REFERENCE", ""),
            "for_description":   getattr(job, "FOR_DESCRIPTION", ""),
            "balance_remaining": fmt_money(balance) if balance else 0,
            "notes":             getattr(job, "NOTES", []),
            "exchange_rate":     getattr(job, "EXCHANGE_RATE", ""),
            "show_signature":    getattr(job, "SHOW_SIGNATURE", True),
        },
        "client": job.CLIENT, **business,
    }


CTX_BUILDERS = {
    "quotation": build_quotation_ctx,
    "invoice":   build_invoice_ctx,
    "receipt":   build_receipt_ctx,
}


def build_business_ctx(job):
    rgb = getattr(job, "BRAND_COLOR_RGB", (30, 60, 114))
    return {
        "business": {
            "name":           job.MY_NAME,
            "phone":          getattr(job, "MY_PHONE", ""),
            "email":          getattr(job, "MY_EMAIL", ""),
            "address":        getattr(job, "MY_ADDRESS", ""),
            "website":        getattr(job, "MY_WEBSITE", ""),
            "tagline":        getattr(job, "MY_TAGLINE", ""),
            "logo_path":      getattr(job, "LOGO_PATH", ""),
            "signature_path": getattr(job, "SIGNATURE_PATH", ""),
        },
        "brand": {"r": rgb[0], "g": rgb[1], "b": rgb[2]},
    }


# ---------------------------------------------------------------------------
# Engine / template selection
# ---------------------------------------------------------------------------

def pick_engine_and_template(doc_type: str, job):
    bilingual = bool(getattr(job, "BILINGUAL", False))
    if bilingual:
        return f"{doc_type}_bilingual.tex.j2", "xelatex", True
    return f"{doc_type}.tex.j2", "pdflatex", False


# ---------------------------------------------------------------------------
# Rendering pipeline
# ---------------------------------------------------------------------------

def render(job_path: Path) -> Path:
    prefix, year, num, doc_type = parse_id(job_path.stem)
    doc_id = job_path.stem

    job = load_job(job_path)

    business_ctx = build_business_ctx(job)
    ctx          = CTX_BUILDERS[doc_type](job, doc_id, business_ctx)

    template_name, compiler, bilingual = pick_engine_and_template(doc_type, job)
    env  = make_env(bilingual=bilingual)
    tmpl = env.get_template(template_name)

    tex_source = tmpl.render(**ctx)

    BUILD.mkdir(parents=True, exist_ok=True)
    tex_path = BUILD / f"{doc_id}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")

    if not shutil.which(compiler):
        print(f"[warn] {compiler} not installed. TeX source kept at {tex_path}")
        return tex_path

    last_result = None
    for _ in range(2):  # two passes for lastpage/cross-refs
        last_result = subprocess.run(
            [compiler, "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory", str(BUILD), str(tex_path)],
            capture_output=True, text=True,
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pdf_src = BUILD / f"{doc_id}.pdf"
    pdf_dst = OUTPUT / f"{doc_id}.pdf"

    if pdf_src.exists():
        shutil.copy2(pdf_src, pdf_dst)
        print(f"✓ Generated {pdf_dst}")
        return pdf_dst

    # Failure: show useful error excerpt
    print(f"✗ Compilation FAILED for {doc_id}. Last 40 lines of {compiler} log:")
    log_path = BUILD / f"{doc_id}.log"
    if log_path.exists():
        log = log_path.read_text(encoding="utf-8", errors="replace")
        lines = log.splitlines()
        # find lines with "!" (error markers)
        err_starts = [i for i, ln in enumerate(lines) if ln.startswith("!")]
        if err_starts:
            i = err_starts[0]
            print("\n".join(lines[max(0, i-2): i+20]))
        else:
            print("\n".join(lines[-40:]))
    elif last_result is not None:
        print((last_result.stdout or "")[-2000:])
        print((last_result.stderr or "")[-2000:])
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python generate.py <jobs/YYYY/PREFIX-YYYY-NNNN.py>")
    render(Path(sys.argv[1]))
