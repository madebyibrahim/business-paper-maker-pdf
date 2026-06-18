# Business Paper Maker PDF

Generate professional **Quotations**, **Invoices**, and **Receipts** as PDF from
small Python "job" files. Six document variants are supported — English-only or
bilingual **English + Arabic** for each type:

| Type        | English-only          | Bilingual (EN + AR)          |
|-------------|-----------------------|------------------------------|
| Quotation   | `quotation.tex.j2`    | `quotation_bilingual.tex.j2` |
| Invoice     | `invoice.tex.j2`      | `invoice_bilingual.tex.j2`   |
| Receipt     | `receipt.tex.j2`      | `receipt_bilingual.tex.j2`   |

Each document gets a sequential, year-scoped ID (`QUO-2026-0001`, `INV-2026-0007`,
`RCT-2026-0012`, …) so your paperwork stays organized and never collides.

---

## How it works

```
config/business.py   ── your identity (name, phone, brand color)   ── once
config/clients.py    ── reusable client records                      ── once
        │
        ▼
new.py      ─▶  jobs/2026/QUO-2026-0001.py   (scaffold, you fill in client + ITEMS)
        │
        ▼
generate.py ─▶  output/QUO-2026-0001.pdf     (rendered PDF)
        │
        ▼
ledger.py   ─▶  ledger_invoices.csv, ledger_receipts.csv   (export all jobs)
```

You describe each document as a tiny Python file (the "job") listing the client,
the line items, and a few totals flags. The generator compiles it to LaTeX and
then to a PDF. There is no database, no server, no GUI — just plain files you can
version-control and back up with `git`.

---

## Quick start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install LaTeX (one-time)

The generator shells out to a LaTeX compiler, so you need a TeX distribution.

**Debian/Ubuntu:**
```bash
sudo apt-get install -y texlive-latex-base texlive-latex-recommended \
    texlive-latex-extra texlive-xetex texlive-fonts-recommended \
    texlive-lang-arabic fonts-hosny-amiri
```

**macOS (Homebrew):** `brew install --cask mactex`
**Windows:** install [MiKTeX](https://miktex.org/) and ensure it's on your `PATH`.

> English-only documents use **`pdflatex`**; bilingual (Arabic) documents use
> **`xelatex`**. `generate.py` picks the right engine automatically based on the
> `BILINGUAL = True/False` flag in each job.

### 3. Set your business identity (once)

Edit `config/business.py`:

```python
MY_NAME    = "Your Name or Company"     # printed at the top of every document
MY_PHONE   = "+961 1 234 567"
MY_EMAIL   = "you@example.com"
MY_ADDRESS = "Beirut, Lebanon"
MY_TAGLINE = "Satellite & Wireless Network Solutions"
BRAND_COLOR_RGB = (30, 60, 114)        # the single accent color used everywhere
LOGO_PATH      = ""                    # optional, relative to project root
SIGNATURE_PATH = ""                    # optional
```

### 4. Create, fill in, and render a document

```bash
# (a) scaffold a new quotation — picks the next free number for the year
python new.py quotation                       # -> jobs/2026/QUO-2026-0001.py

# (b) open the generated file and fill in the client + ITEMS
$EDITOR jobs/2026/QUO-2026-0001.py

# (c) render to PDF
python generate.py jobs/2026/QUO-2026-0001.py  # -> output/QUO-2026-0001.pdf
```

The same three steps apply to invoices and receipts — just swap the type:

```bash
python new.py invoice
python new.py receipt
```

---

## The three commands

### `new.py <type> [--year YYYY]`

Scaffolds a new empty job file with the next sequential ID.

| Argument  | Choices                | Default        |
|-----------|------------------------|----------------|
| `type`    | `quotation`, `invoice`, `receipt` | —      |
| `--year`  | (any year, e.g. `2026`) | current year  |

```bash
python new.py quotation            # current year
python new.py invoice --year 2026
```

It reads `templates/scaffolds/*.py`, fills in the ID and dates, and writes
`jobs/<year>/<PREFIX>-<year>-<NNNN>.py`. Max 9999 per series per year.

### `generate.py <path-to-job.py>`

Renders one job file to `output/<ID>.pdf`.

```bash
python generate.py jobs/2026/QUO-2026-0001.py
```

It loads the job, builds the totals, escapes all user text for LaTeX, picks the
engine (`pdflatex` vs `xelatex`), runs two compilation passes (for cross-refs and
the "Page X of Y" footer), and copies the final PDF to `output/`. If the LaTeX
compiler isn't installed, it leaves the `.tex` source in `output/.build/` and
prints a warning instead of failing. On a compile error it prints the relevant
excerpt from the log.

### `ledger.py`

Exports **every** invoice and receipt under `jobs/` to two CSV files:

```bash
python ledger.py
# -> ledger_invoices.csv   (Date, Invoice ID, Client, Project, Total, Deposit, Due)
# -> ledger_receipts.csv   (Date, Receipt ID, Ref Invoice, Client, Method, Amount)
```

Handy for accounting, tax, or importing into a spreadsheet.

---

## Anatomy of a job file

A job is just a Python module of plain variables. Example (`jobs/2026/QUO-2026-0001.py`):

```python
"""QUO-2026-0001 — quotation."""
from config.business import *
from config.clients import ACME_CORP

DATE        = "2026-05-27"
VALID_UNTIL = "2026-06-26"
CLIENT      = ACME_CORP
PROJECT_TITLE = "Office Network & Satellite Internet Installation"

# Each item is a (description, qty, unit_price) tuple.
# A plain string becomes a colored section-subheader row.
ITEMS = [
    "--- Hardware ---",
    ("UniFi U6-LR access points", 4, 179.00),
    ("Outdoor-rated CAT6 cable (per meter)", 80, 2.50),
    "--- Labor ---",
    ("Installation and configuration", 1, 350.00),
]

DISCOUNT_PCT = 5
TAX_PCT      = 11

PAYMENT_METHODS = [f"Cash (Fresh USD) -- payable to {MY_NAME}."]
NOTES = ["This quotation is valid for 30 days."]
BILINGUAL = False        # True -> render EN+AR via xelatex
```

### Variables by document type

| Field            | Quotation | Invoice | Receipt |
|------------------|:---------:|:-------:|:-------:|
| `DATE`           | ✓ | ✓ | ✓ |
| `CLIENT`         | ✓ | ✓ | ✓ |
| `ITEMS`          | ✓ | ✓ |   |
| `PROJECT_TITLE`  | ✓ | ✓ |   |
| `VALID_UNTIL`    | ✓ |   |   |
| `DUE_DATE`       |   | ✓ |   |
| `RELATED_QUOTE`  |   | ✓ |   |
| `DEPOSIT_PAID`   |   | ✓ |   |
| `DISCOUNT_PCT`   | ✓ | ✓ |   |
| `TAX_PCT`        | ✓ | ✓ |   |
| `PAYMENT_METHODS`| ✓ | ✓ |   |
| `AMOUNT_RECEIVED`|   |   | ✓ |
| `PAYMENT_METHOD` |   |   | ✓ |
| `PAYMENT_REFERENCE` |   |   | ✓ |
| `RELATED_INVOICE`|   |   | ✓ |
| `BALANCE_REMAINING` |   |   | ✓ |
| `NOTES`          | ✓ | ✓ | ✓ |
| `EXCHANGE_RATE`  | ✓ | ✓ | ✓ |
| `WATERMARK`      | ✓ | ✓ |   |
| `SHOW_SIGNATURE` | ✓ | ✓ | ✓ |
| `BILINGUAL`      | ✓ | ✓ | ✓ |

---

## Key features

- **Bilingual Arabic + English, automatic**: any run of Arabic characters in your
  input is auto-wrapped in `\textarabic{}` so polyglossia picks the right font and
  text direction. Just set `BILINGUAL = True` and mix the two languages anywhere.
- **Subheader rows**: a bare string inside `ITEMS` (e.g. `"--- Labor ---"`)
  becomes a colored section divider inside the table.
- **Standardized totals block**: right-aligned, fixed-width, with a highlighted
  AMOUNT-DUE / TOTAL box.
- **Strict layout**: all table columns use paragraph-style wrapping (`p{}`) so
  long descriptions wrap instead of overflowing the page.
- **One brand color** drives all six templates — change `BRAND_COLOR_RGB` once.
- **Amounts in words**: receipts spell out the received amount ("One thousand
  three hundred ninety-five US Dollars and 50 Cents only.") via `num2words`.
- **Robust LaTeX escaping**: every user-supplied string is escaped, so ampersands,
  `%`, `_`, `$`, etc. in your descriptions never break compilation.
- **Reproducible IDs**: filenames follow `PREFIX-YYYY-NNNN`, locked to the year.

---

## Repository layout

```
paper_maker/
├── config/
│   ├── business.py        # your identity + brand color  (EDIT THIS)
│   └── clients.py         # reusable client records       (EDIT THIS)
├── templates/
│   ├── scaffolds/         # skeletons used by new.py
│   ├── *.tex.j2           # one Jinja template per document variant
│   └── _*.tex.j2          # shared partials (preamble, totals blocks)
├── jobs/
│   └── <YYYY>/            # one file per document, grouped by year
├── output/                # generated PDFs (+ a hidden .build/ for .tex/.log)
├── preview/               # rendered PNG previews of the sample jobs
├── new.py                 # scaffold a new job
├── generate.py            # render one job to PDF
├── ledger.py              # export all jobs to CSV
└── requirements.txt
```

`jobs/` and `output/` contain your real business data once you start using it.
You may want to keep them out of any public copy.

---

## Sample documents

The repo ships with three pairs of demo jobs under `jobs/2026/` (English-only and
bilingual for each type), all using obviously-fake placeholder data. Their
rendered previews live in `preview/`. Use them as copy-paste starting points, then
delete them once you have your own.

---

## Credits

This project was developed with the assistance of an AI coding assistant (code
generation, refactoring, and review). The design, requirements, and all business
decisions are the author's; the assistant was used as a productivity tool.
