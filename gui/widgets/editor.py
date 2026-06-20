"""The main editor form: loads a JobModel, edits every field by doc type,
shows live totals, and exposes Save / Generate / Open actions.

Live totals reuse generate.compute_items + compute_totals directly — the same
functions the engine uses to build the PDF — so the on-screen numbers always
match the rendered document.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
from typing import Any

import generate
from gui import adapter, latex_status, renderer, storage
from gui.models import DOC_FIELDS, JobModel, TYPE_LABELS
from gui.widgets.items_editor import ItemsEditor
from gui.widgets.pdf_view import PdfPreview
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)


class Editor(QWidget):
    """Right-hand pane: form on the left, PDF preview on the right."""

    save_requested = Signal()        # emitted after a successful save
    generate_done = Signal(str)      # emitted with the doc id after a successful render

    def __init__(self, latex: latex_status.LatexStatus, parent=None):
        super().__init__(parent)
        self._latex = latex
        self._model: JobModel | None = None
        self._guard = False
        self._dirty = False          # True when the form has unsaved edits
        self._widgets: dict[str, QWidget] = {}

        # ---- left: form ----
        self._form_host = QWidget()
        self._form_layout = QFormLayout(self._form_host)
        self._form_layout.setLabelAlignment(Qt.AlignRight)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(self._form_host)

        self._totals_label = QLabel("Open a document to begin.")
        self._totals_label.setStyleSheet("padding:8px; background:#f4f6fa; border-radius:4px;")

        # One persistent items editor for the life of the Editor. Parented to
        # self so it survives form rebuilds (see _build_form).
        self.items_editor = ItemsEditor(self)
        self.items_editor.changed.connect(self._on_live_change)

        self.btn_save = QPushButton("Save")
        self.btn_generate = QPushButton("Generate PDF")
        self.btn_generate.setStyleSheet("font-weight:bold;")
        self.btn_open = QPushButton("Open PDF")
        self.btn_reveal = QPushButton("Reveal in Explorer")
        for b in (self.btn_save, self.btn_generate, self.btn_open, self.btn_reveal):
            b.setEnabled(False)
        self.btn_save.clicked.connect(self.save)
        self.btn_generate.clicked.connect(self.generate)
        self.btn_open.clicked.connect(self._open_pdf)
        self.btn_reveal.clicked.connect(self._reveal)

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_generate)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_open)
        button_row.addWidget(self.btn_reveal)

        left = QVBoxLayout()
        left.addLayout(button_row)
        left.addWidget(self._totals_label)
        left.addWidget(form_scroll, 1)

        left_host = QWidget()
        left_host.setLayout(left)

        # ---- right: preview ----
        self.preview = PdfPreview()
        self.preview_label = QLabel("Preview")
        self.preview_label.setStyleSheet("padding:4px; color:#555;")
        right = QVBoxLayout()
        right.addWidget(self.preview_label)
        right.addWidget(self.preview, 1)
        right_host = QWidget()
        right_host.setLayout(right)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_host)
        splitter.addWidget(right_host)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([560, 520])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.addWidget(splitter)

        self.set_enabled(False)

    # ------------------------------------------------------------ public API

    def load_model(self, model: JobModel) -> None:
        self._guard = True
        self._model = model
        self._dirty = False
        self._build_form(model.doc_type)
        self._populate(model)
        self._guard = False
        self.set_enabled(True)
        self._update_save_state()
        self._refresh_preview()
        self._update_totals()

    def current_model(self) -> JobModel | None:
        if self._model is None:
            return None
        self._sync_model()
        return self._model

    def is_dirty(self) -> bool:
        """True if the current document has unsaved edits."""
        return self._model is not None and self._dirty

    def current_doc_id(self) -> str:
        return self._model.doc_id if self._model else ""

    def confirm_save_or_discard(self) -> bool:
        """If the current doc is dirty, ask the user what to do.

        Returns True if it's safe to proceed (saved or discarded),
        False if the user cancelled (caller should abort whatever it was doing).
        """
        if not self.is_dirty():
            return True
        doc = self.current_doc_id()
        choice = QMessageBox.question(
            self, "Unsaved changes",
            f"“{doc}” has unsaved changes. Save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if choice == QMessageBox.Save:
            return self.save()
        if choice == QMessageBox.Discard:
            return True
        return False  # Cancel

    def set_enabled(self, on: bool) -> None:
        for w in self._widgets.values():
            w.setEnabled(on)
        self.items_editor.setEnabled(on)
        for b in (self.btn_save, self.btn_generate):
            b.setEnabled(on)

    def refresh_latex(self, latex: latex_status.LatexStatus) -> None:
        self._latex = latex

    # --------------------------------------------------------------- actions

    def save(self) -> bool:
        if self._model is None:
            return False
        self._sync_model()
        try:
            adapter.save(self._model)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", f"{type(e).__name__}: {e}")
            return False
        self._dirty = False
        self._update_save_state()
        self.save_requested.emit()
        return True

    def generate(self) -> None:
        if self._model is None:
            return
        bilingual = bool(self._model.get("BILINGUAL", False))
        if not self._latex.can_compile(bilingual):
            need = "xelatex" if bilingual else "pdflatex"
            QMessageBox.warning(
                self, "Compiler missing",
                f"{need} is not installed on your system, so this document cannot be "
                f"compiled to PDF.\n\nInstall a TeX distribution (e.g. MiKTeX) and "
                f"restart the app."
            )
            return
        # Always save before rendering so the file on disk matches the form.
        if not self.save():
            return
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Generating…")
        self.repaint()
        try:
            result = renderer.render(self._model.path)
        finally:
            self.btn_generate.setText("Generate PDF")
            self.btn_generate.setEnabled(True)

        if result.ok:
            self._refresh_preview()
            self.btn_open.setEnabled(True)
            self.btn_reveal.setEnabled(True)
            self.generate_done.emit(self._model.doc_id)
            QMessageBox.information(self, "PDF generated",
                                    f"Saved to:\n{result.pdf_path}")
        elif result.is_tex_only:
            QMessageBox.warning(self, "Compiler missing",
                                "No LaTeX compiler found. The .tex source was written to:\n"
                                f"{result.pdf_path}")
        else:
            QMessageBox.critical(self, "PDF generation failed",
                                 result.log or "Compilation failed with no message.")

    def _open_pdf(self) -> None:
        if self._model is None:
            return
        pdf = storage.output_pdf_for(self._model.doc_id)
        if pdf.exists():
            self.preview._open_external()  # reuse the cross-platform opener
        else:
            QMessageBox.information(self, "No PDF yet",
                                    "Generate the PDF first.")

    def _reveal(self) -> None:
        if self._model is None:
            return
        pdf = storage.output_pdf_for(self._model.doc_id)
        target = pdf if pdf.exists() else pdf.parent
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", str(pdf)]) if pdf.exists() \
                else subprocess.Popen(["explorer", str(target)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(pdf)]) if pdf.exists() \
                else subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])

    # ----------------------------------------------------------- form building

    def _build_form(self, doc_type: str) -> None:
        # Detach the persistent items editor from any previous container before
        # clearing rows: removeRow deletes the row's widgets (and their children),
        # so anything still inside the old group box would be destroyed. Calling
        # setParent(None) first lifts it out of the doomed subtree.
        self.items_editor.setParent(None)

        # Clear previous rows.
        while self._form_layout.rowCount():
            self._form_layout.removeRow(0)
        self._widgets.clear()

        header = QLabel(f"{TYPE_LABELS[doc_type]}  ·  {self._model.doc_id if self._model else ''}")
        header.setStyleSheet("font-size:14px; font-weight:bold; padding:4px 0;")
        self._form_layout.addRow(header)

        # Client block.
        client_box = QGroupBox("Client")
        client_form = QFormLayout(client_box)
        self._client_widgets: dict[str, QLineEdit] = {}
        for key, label in [("name", "Name"), ("phone", "Phone"),
                           ("email", "Email"), ("site", "Site / address")]:
            w = QLineEdit()
            w.textChanged.connect(self._on_live_change)
            self._client_widgets[key] = w
            client_form.addRow(label, w)
        self._form_layout.addRow(client_box)

        # Doc-type fields.
        for key, kind, label in DOC_FIELDS[doc_type]:
            if kind == "items":
                # One persistent ItemsEditor, parented to ``self`` so it is never
                # garbage-collected when its container group box is removed on a
                # later rebuild (Qt would otherwise delete a widget owned by the
                # removed group box). We just re-add the same instance each time.
                box = QGroupBox(label)
                box_layout = QVBoxLayout(box)
                box_layout.addWidget(self.items_editor)
                self._form_layout.addRow(box)
                continue
            w = self._make_widget(kind)
            self._wire_widget(w, kind)
            self._widgets[key] = w
            self._form_layout.addRow(label, w)

    def _make_widget(self, kind: str) -> QWidget:
        if kind == "str":
            return QLineEdit()
        if kind == "text":
            edit = QPlainTextEdit()
            edit.setFixedHeight(80)
            return edit
        if kind == "date":
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setDate(QDate.currentDate())
            return de
        if kind == "pct":
            sp = QDoubleSpinBox()
            sp.setRange(0, 100)
            sp.setSuffix(" %")
            sp.setDecimals(2)
            sp.setSingleStep(0.5)
            return sp
        if kind == "money":
            sp = QDoubleSpinBox()
            sp.setRange(0, 1e9)
            sp.setDecimals(2)
            sp.setSingleStep(10.0)
            sp.setPrefix("$ ")
            return sp
        if kind == "bool":
            return QCheckBox()
        return QLineEdit()

    def _wire_widget(self, w: QWidget, kind: str) -> None:
        if kind == "str":
            w.textChanged.connect(self._on_live_change)
        elif kind == "text":
            w.textChanged.connect(self._on_live_change)
        elif kind == "date":
            w.dateChanged.connect(self._on_live_change)
        elif kind in ("pct", "money"):
            w.valueChanged.connect(self._on_live_change)
        elif kind == "bool":
            w.toggled.connect(self._on_live_change)

    # ------------------------------------------------------------- populate / sync

    def _populate(self, m: JobModel) -> None:
        for key, w in self._client_widgets.items():
            w.setText(m.client.get(key, ""))
        for key, kind, _label in DOC_FIELDS[m.doc_type]:
            if kind == "items":
                self.items_editor.set_items(m.get(key, []))
                continue
            self._set_widget_value(self._widgets[key], kind, m.get(key))

    def _set_widget_value(self, w: QWidget, kind: str, value: Any) -> None:
        if kind == "str":
            w.setText(str(value or ""))
        elif kind == "text":
            lines = value or []
            w.setPlainText("\n".join(str(x) for x in lines))
        elif kind == "date":
            d = self._parse_date(str(value or ""))
            if d is not None:
                w.setDate(QDate(d.year, d.month, d.day))
        elif kind in ("pct", "money"):
            try:
                w.setValue(float(value or 0))
            except (TypeError, ValueError):
                w.setValue(0.0)
        elif kind == "bool":
            w.setChecked(bool(value))

    def _sync_model(self) -> None:
        if self._model is None:
            return
        for key, w in self._client_widgets.items():
            self._model.client[key] = w.text()
        for key, kind, _label in DOC_FIELDS[self._model.doc_type]:
            if kind == "items":
                self._model.fields[key] = self.items_editor.get_items()
                continue
            self._model.fields[key] = self._widget_value(self._widgets[key], kind)

    @staticmethod
    def _widget_value(w: QWidget, kind: str) -> Any:
        if kind == "str":
            return w.text()
        if kind == "text":
            text = w.toPlainText()
            return [line for line in text.splitlines() if line.strip()] if text.strip() else []
        if kind == "date":
            return w.date().toString("yyyy-MM-dd")
        if kind in ("pct", "money"):
            return float(w.value())
        if kind == "bool":
            return bool(w.isChecked())
        return ""

    # ------------------------------------------------------------ live totals

    def _on_live_change(self, *_args) -> None:
        if self._guard:
            return
        # Any user edit marks the document dirty so load/close can prompt.
        self._dirty = True
        self._update_save_state()
        self._update_totals()

    def _update_save_state(self) -> None:
        """Reflect dirty state on the Save button (label + emphasis)."""
        if self._model is None:
            return
        if self._dirty:
            self.btn_save.setText("Save *")
            self.btn_save.setStyleSheet("font-weight:bold;")
        else:
            self.btn_save.setText("Save")
            self.btn_save.setStyleSheet("")

    def _update_totals(self) -> None:
        if self._model is None:
            return
        m = self._model
        lines = [f"<b>{TYPE_LABELS[m.doc_type]} {m.doc_id}</b>"]
        if m.doc_type in ("quotation", "invoice"):
            items = self.items_editor.get_items()
            rows, subtotal = generate.compute_items(items)
            discount = self._num_field("DISCOUNT_PCT", 0.0)
            tax = self._num_field("TAX_PCT", 0.0)
            deposit = self._num_field("DEPOSIT_PAID", 0.0) if m.doc_type == "invoice" else 0.0
            t = generate.compute_totals(subtotal, discount, tax, deposit)
            lines.append(
                f"Subtotal <b>${t['subtotal']}</b> &nbsp; · &nbsp; "
                f"Discount {t['discount_pct']}% (−${t['discount_amount']}) &nbsp; · &nbsp; "
                f"Tax {t['tax_pct']}% (+${t['tax_amount']})"
            )
            if m.doc_type == "invoice":
                lines.append(f"Deposit paid <b>−${t['deposit_paid']}</b>")
                lines.append(f"<span style='font-size:13px;'>AMOUNT DUE: "
                             f"<b>${t['amount_due']}</b></span>")
            else:
                lines.append(f"<span style='font-size:13px;'>TOTAL: "
                             f"<b>${t['grand_total']}</b></span>")
        elif m.doc_type == "receipt":
            amount = self._num_field("AMOUNT_RECEIVED", 0.0)
            balance = self._num_field("BALANCE_REMAINING", 0.0)
            words = generate.amount_in_words(amount)
            lines.append(f"Amount received <b>${generate.fmt_money(amount)}</b>")
            lines.append(f"In words: {words}")
            if balance:
                lines.append(f"Balance remaining: ${generate.fmt_money(balance)}")
        self._totals_label.setText("<br>".join(lines))

    def _num_field(self, key: str, default: float) -> float:
        w = self._widgets.get(key)
        if w is None:
            return default
        try:
            return float(w.value())
        except AttributeError:
            return default

    # ------------------------------------------------------------ misc helpers

    @staticmethod
    def _parse_date(s: str):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def _refresh_preview(self) -> None:
        if self._model is None:
            self.preview.clear()
            self.btn_open.setEnabled(False)
            self.btn_reveal.setEnabled(False)
            return
        pdf = storage.output_pdf_for(self._model.doc_id)
        self.preview.load(pdf)
        self.btn_open.setEnabled(pdf.exists())
        self.btn_reveal.setEnabled(pdf.exists())
