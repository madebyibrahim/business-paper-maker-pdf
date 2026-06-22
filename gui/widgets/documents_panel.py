"""Left sidebar: searchable, grouped list of all job documents.

Each entry shows the doc id plus the client name (pulled from the job on scan).
Selecting an entry asks the main window to load it.
"""
from __future__ import annotations

from gui import adapter, storage
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
    QWidget,
)


class DocumentsPanel(QWidget):
    """Lists every job under jobs/. Emits ``job_selected(path_str)``."""

    job_selected = Signal(str)
    new_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all: list[tuple[str, str, str]] = []  # (path, doc_id, subtitle)
        self.setMinimumWidth(220)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by id or client…")
        self.search.textChanged.connect(self._rebuild)

        self.filter = QComboBox()
        self.filter.addItems(["All", "Quotations", "Invoices", "Receipts"])
        self.filter.currentIndexChanged.connect(self._rebuild)

        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_select)

        title = QLabel("Documents")
        title.setStyleSheet("font-weight:bold; font-size:13px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(title)
        layout.addWidget(self.search)
        layout.addWidget(self.filter)
        layout.addWidget(self.list, 1)

    def refresh(self) -> None:
        """Re-scan jobs/ and rebuild the list."""
        self._all = []
        for p in storage.list_jobs():
            doc_id = p.stem
            prefix = doc_id.split("-", 1)[0]
            subtitle = ""
            try:
                m = adapter.load(p)
                subtitle = m.client.get("name", "")
            except Exception:  # noqa: BLE001 - a broken job shouldn't break the list
                subtitle = "(could not read)"
            self._all.append((str(p), doc_id, subtitle))
        self._rebuild()

    def _rebuild(self) -> None:
        needle = self.search.text().strip().lower()
        type_filter = self.filter.currentText()
        wanted_prefix = {"Quotations": "QUO", "Invoices": "INV",
                         "Receipts": "RCT"}.get(type_filter)

        self.list.clear()
        for path, doc_id, subtitle in self._all:
            if wanted_prefix and not doc_id.startswith(wanted_prefix):
                continue
            haystack = f"{doc_id} {subtitle}".lower()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem()
            label_main = doc_id
            label_sub = subtitle if subtitle else "(no client)"
            item.setText(f"{label_main}\n{label_sub}")
            item.setData(Qt.UserRole, path)
            self.list.addItem(item)

    def _on_select(self) -> None:
        items = self.list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        self.job_selected.emit(path)

    def select_path(self, path: str) -> None:
        """Programmatically select a row by path (after creating a new doc)."""
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) == path:
                self.list.setCurrentItem(it)
                return
