"""Editor for the heterogeneous ITEMS list.

A job's ITEMS mixes two row kinds (compute_items in generate.py knows both):
  * line items:   (description, qty, unit_price)  -> a priced table row
  * subheaders:   "--- Labor ---"                 -> a coloured section divider

This widget renders them in a QTableWidget where the first column is a kind
toggle. The widget emits ``changed`` whenever anything is edited so the parent
editor can recompute totals live.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

COL_KIND, COL_DESC, COL_QTY, COL_UNIT, COL_TOTAL = range(5)
KIND_ITEM = "Item"
KIND_HEADER = "Section header"


def _money(x: float) -> str:
    return f"{x:,.2f}"


class ItemsEditor(QWidget):
    """Table editor for ITEMS. Emits ``changed`` on any edit."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._guard = False  # suppress signals while rebuilding programmatically

        self.table = QTableWidget(0, COL_TOTAL + 1, self)
        self.table.setHorizontalHeaderLabels(["Type", "Description", "Qty", "Unit price", "Line total"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_KIND, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_QTY, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_UNIT, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_TOTAL, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self._on_item_changed)

        # Toolbar: add item / add header / remove / move up / move down.
        bar = QHBoxLayout()
        self.btn_add_item = QPushButton("+ Item")
        self.btn_add_header = QPushButton("+ Section header")
        self.btn_remove = QPushButton("− Remove")
        self.btn_up = QPushButton("▲ Up")
        self.btn_down = QPushButton("▼ Down")
        for b in (self.btn_add_item, self.btn_add_header, self.btn_remove, self.btn_up, self.btn_down):
            bar.addWidget(b)
        bar.addStretch(1)

        self.btn_add_item.clicked.connect(lambda: self._add_row(KIND_ITEM))
        self.btn_add_header.clicked.connect(lambda: self._add_row(KIND_HEADER))
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_up.clicked.connect(lambda: self._move_selected(-1))
        self.btn_down.clicked.connect(lambda: self._move_selected(1))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        layout.addLayout(bar)

    # ------------------------------------------------------------------ API

    def set_items(self, items: list[Any]) -> None:
        """Replace the whole table from a job's ITEMS list."""
        self._guard = True
        self.table.setRowCount(0)
        for it in items or []:
            if isinstance(it, str):
                self._append_row(KIND_HEADER, desc=it.strip("- ").strip())
            else:
                desc, qty, unit = it
                self._append_row(KIND_ITEM, desc=str(desc), qty=float(qty), unit=float(unit))
        self._guard = False
        self._recompute_totals()

    def get_items(self) -> list[Any]:
        """Return the current list in job-file form (tuples + header strings)."""
        out: list[Any] = []
        for r in range(self.table.rowCount()):
            kind = self._kind_at(r)
            desc = self.table.item(r, COL_DESC).text() if self.table.item(r, COL_DESC) else ""
            if kind == KIND_HEADER:
                out.append(f"--- {desc} ---" if desc else "---")
            else:
                qty = self._num_at(r, COL_QTY, 0.0)
                unit = self._num_at(r, COL_UNIT, 0.0)
                out.append((desc, qty, unit))
        return out

    # -------------------------------------------------------------- internals

    def _append_row(self, kind: str, desc: str = "", qty: float = 0.0,
                    unit: float = 0.0, at: int | None = None) -> None:
        # ``at=None`` appends at the end; an explicit index inserts there. The
        # move-up/down logic relies on positional insertion — without it, moved
        # rows always land at the bottom.
        r = self.table.rowCount() if at is None else at
        self.table.insertRow(r)

        combo = QComboBox()
        combo.addItems([KIND_ITEM, KIND_HEADER])
        combo.setCurrentText(kind)
        combo.currentTextChanged.connect(lambda *_: self._on_kind_changed(r))
        self.table.setCellWidget(r, COL_KIND, combo)

        self.table.setItem(r, COL_DESC, QTableWidgetItem(desc))
        self.table.setItem(r, COL_QTY, QTableWidgetItem("" if kind == KIND_HEADER else self._fmt_num(qty)))
        self.table.setItem(r, COL_UNIT, QTableWidgetItem("" if kind == KIND_HEADER else self._fmt_num(unit)))
        total_item = QTableWidgetItem("")
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(r, COL_TOTAL, total_item)
        self._apply_row_kind(r)

    def _add_row(self, kind: str) -> None:
        self._guard = True
        self._append_row(kind)
        self._guard = False
        self.changed.emit()

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        self._guard = True
        for r in rows:
            self.table.removeRow(r)
        self._guard = False
        self._recompute_totals()
        self.changed.emit()

    def _move_selected(self, delta: int) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            return
        # Move the (assumed contiguous) selected block as a unit.
        first, last = rows[0], rows[-1]
        target = first + delta
        if target < 0 or last + delta >= self.table.rowCount():
            return
        self._guard = True
        # Snapshot the block, remove it, then reinsert at the target position.
        snapshot = [self._row_values(r) for r in range(first, last + 1)]
        for r in range(last, first - 1, -1):
            self.table.removeRow(r)
        for i, vals in enumerate(snapshot):
            self._insert_row_at(target + i, vals)
        self._guard = False
        # Reselect the moved block at its new location.
        for r in range(target, target + len(snapshot)):
            self.table.selectRow(r)
        self._recompute_totals()
        self.changed.emit()

    def _row_values(self, r: int) -> tuple[str, str, str, str]:
        kind = self._kind_at(r)
        desc = self.table.item(r, COL_DESC).text() if self.table.item(r, COL_DESC) else ""
        qty = self.table.item(r, COL_QTY).text() if self.table.item(r, COL_QTY) else ""
        unit = self.table.item(r, COL_UNIT).text() if self.table.item(r, COL_UNIT) else ""
        return kind, desc, qty, unit

    def _insert_row_at(self, r: int, vals: tuple[str, str, str, str]) -> None:
        kind, desc, qty, unit = vals
        self._append_row(kind, desc=desc,
                         qty=self._parse_num(qty), unit=self._parse_num(unit), at=r)

    def _on_kind_changed(self, r: int) -> None:
        if self._guard:
            return
        self._guard = True
        self._apply_row_kind(r)
        self._guard = False
        self._recompute_totals()
        self.changed.emit()

    def _apply_row_kind(self, r: int) -> None:
        kind = self._kind_at(r)
        is_header = kind == KIND_HEADER
        for col in (COL_QTY, COL_UNIT):
            it = self.table.item(r, col)
            if it is not None:
                flags = it.flags()
                if is_header:
                    it.setFlags(flags & ~Qt.ItemIsEditable)
                    it.setText("")
                else:
                    it.setFlags(flags | Qt.ItemIsEditable)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._guard:
            return
        if item.column() in (COL_QTY, COL_UNIT):
            self._recompute_totals()
        self.changed.emit()

    def _recompute_totals(self) -> None:
        for r in range(self.table.rowCount()):
            total_item = self.table.item(r, COL_TOTAL)
            if total_item is None:
                continue
            if self._kind_at(r) == KIND_HEADER:
                total_item.setText("")
            else:
                qty = self._num_at(r, COL_QTY, 0.0)
                unit = self._num_at(r, COL_UNIT, 0.0)
                total_item.setText(_money(qty * unit))

    # --- tiny helpers ---

    def _kind_at(self, r: int) -> str:
        w = self.table.cellWidget(r, COL_KIND)
        return w.currentText() if w else KIND_ITEM

    def _num_at(self, r: int, col: int, default: float) -> float:
        it = self.table.item(r, col)
        return self._parse_num(it.text()) if it and it.text() else default

    @staticmethod
    def _parse_num(s: str) -> float:
        try:
            return float(s)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fmt_num(x: float) -> str:
        return str(int(x)) if float(x).is_integer() else str(x)
