"""Ledger viewer — runs the engine's ledger export and shows it in-app.

The engine (ledger.run) walks jobs/ and writes ledger_invoices.csv and
ledger_receipts.csv. Rather than duplicate that walk, we call run() and then
read the CSVs back into two searchable tables with a grand-total footer.
"""
from __future__ import annotations

import csv
from pathlib import Path

import ledger  # the engine
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from gui import storage


class _LedgerTab(QWidget):
    """One searchable table plus a total footer."""

    def __init__(self, csv_path: Path, money_col: str, parent=None):
        super().__init__(parent)
        self._csv_path = csv_path
        self._money_col = money_col
        self._rows: list[dict] = []
        self._headers: list[str] = []

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter…")
        self.search.textChanged.connect(self._rebuild)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.total_label = QLabel()

        self.export_btn = QPushButton("Export CSV…")
        self.export_btn.clicked.connect(self._export)

        bar = QHBoxLayout()
        bar.addWidget(self.search, 1)
        bar.addWidget(self.export_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.total_label)

    def load(self) -> None:
        self._rows, self._headers = [], []
        if self._csv_path.exists():
            with open(self._csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._headers = reader.fieldnames or []
                self._rows = list(reader)
        self._rebuild()

    def _rebuild(self) -> None:
        needle = self.search.text().strip().lower()
        rows = [r for r in self._rows
                if not needle or needle in " ".join(r.values()).lower()]
        self.table.setColumnCount(len(self._headers))
        self.table.setHorizontalHeaderLabels(self._headers)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, h in enumerate(self._headers):
                self.table.setItem(i, j, QTableWidgetItem(str(row.get(h, ""))))
        self.total_label.setText(self._total_text(rows))
        self.table.resizeColumnsToContents()

    def _total_text(self, rows: list[dict] = None) -> str:
        rows = rows if rows is not None else self._rows
        total = 0.0
        for r in rows:
            try:
                total += float(r.get(self._money_col, 0) or 0)
            except (TypeError, ValueError):
                pass
        return f"<b>{len(rows)}</b> rows &nbsp; · &nbsp; {self._money_col} total: <b>${total:,.2f}</b>"

    def _export(self) -> None:
        if not self._rows:
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", str(self._csv_path.name), "CSV (*.csv)")
        if not target:
            return
        with open(target, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self._headers)
            w.writeheader()
            w.writerows(self._rows)


class LedgerDialog(QDialog):
    """Runs ledger.run() then shows invoices + receipts in two tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ledger")
        self.resize(900, 560)

        self.status = QLabel("Click “Refresh” to (re)generate the ledger CSVs from jobs/.")

        self.inv_tab = _LedgerTab(storage.ROOT / "ledger_invoices.csv", "Total USD")
        self.rct_tab = _LedgerTab(storage.ROOT / "ledger_receipts.csv", "Amount Received USD")

        tabs = QTabWidget()
        tabs.addTab(self.inv_tab, "Invoices")
        tabs.addTab(self.rct_tab, "Receipts")

        self.refresh_btn = QPushButton("Refresh from jobs/")
        self.refresh_btn.clicked.connect(self._refresh)
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.refresh_btn)
        top_bar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addWidget(self.status)
        layout.addWidget(tabs, 1)

    def _refresh(self) -> None:
        try:
            ledger.run()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Could not generate ledger: {type(e).__name__}: {e}")
            return
        self.inv_tab.load()
        self.rct_tab.load()
        self.status.setText(
            f"Generated ledger. Invoices: {len(self.inv_tab._rows)}, "
            f"Receipts: {len(self.rct_tab._rows)}."
        )

    def showEvent(self, event):  # noqa: N802 - Qt signature
        super().showEvent(event)
        # Populate on first open without requiring a click.
        if not self.inv_tab._rows and not self.rct_tab._rows:
            self._refresh()
