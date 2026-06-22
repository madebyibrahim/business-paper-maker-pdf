"""Settings dialog — edit config/business.py and config/clients.py from the GUI.

Business identity and the reusable client records live in two plain Python
modules under config/. This dialog reads them by importing the modules (so
defaults and the current values are picked up exactly as the engine sees them)
and writes them back in the documented file format. The engine and CLI are
unaffected — they just read the same files.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from gui import storage

BUSINESS_PATH = storage.ROOT / "config" / "business.py"
CLIENTS_PATH = storage.ROOT / "config" / "clients.py"


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` so the file is never observed half-written.

    Writes a sibling temp file then ``os.replace`` (atomic on POSIX and on
    Windows for files on the same volume). On any failure the original file
    is left intact.
    """
    import os
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# (attr, label) pairs for the business file, in file order.
BUSINESS_FIELDS = [
    ("MY_NAME",    "Business name"),
    ("MY_PHONE",   "Phone"),
    ("MY_EMAIL",   "Email"),
    ("MY_ADDRESS", "Address"),
    ("MY_WEBSITE", "Website"),
    ("MY_TAGLINE", "Tagline"),
    ("LOGO_PATH",      "Logo path (relative)"),
    ("SIGNATURE_PATH", "Signature path (relative)"),
]


class SettingsDialog(QDialog):
    """Edit business identity, brand color, logo paths, and client records."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(720, 560)

        self._business_inputs: dict[str, QLineEdit] = {}
        self._brand_rgb = (30, 60, 114)

        # --- Business identity group ---
        biz_box = QGroupBox("Business identity")
        biz_form = QFormLayout(biz_box)
        for attr, label in BUSINESS_FIELDS:
            w = QLineEdit()
            self._business_inputs[attr] = w
            biz_form.addRow(label, w)

        # Brand color picker.
        self._color_button = QPushButton()
        self._color_button.setFixedHeight(28)
        self._color_button.clicked.connect(self._pick_color)
        biz_form.addRow("Brand color:", self._color_button)

        # --- Clients group ---
        # Five columns — all four client fields (name/phone/email/site) plus the
        # import key. Previously this had only 4 columns and hard-coded
        # "site": "" on save, which silently erased every client's address.
        self.clients_table = QTableWidget(0, 5)
        self.clients_table.setHorizontalHeaderLabels(["Key", "Name", "Phone", "Email", "Site / address"])
        # QHeaderView.Stretch / ResizeToContents must be read off the class, not
        # the instance, on this PySide6 build.
        header = self.clients_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.btn_add_client = QPushButton("+ Client")
        self.btn_del_client = QPushButton("− Remove")
        self.btn_add_client.clicked.connect(self._add_client_row)
        self.btn_del_client.clicked.connect(self._del_client_row)

        clients_box = QGroupBox("Reusable client records (config/clients.py)")
        clients_top = QHBoxLayout()
        clients_top.addStretch(1)
        clients_top.addWidget(self.btn_add_client)
        clients_top.addWidget(self.btn_del_client)
        clients_layout = QVBoxLayout(clients_box)
        clients_layout.addLayout(clients_top)
        clients_layout.addWidget(self.clients_table)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(biz_box)
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(clients_box)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        outer = QVBoxLayout(self)
        outer.addWidget(splitter)
        outer.addWidget(buttons)

        self._load_current()

    # --------------------------------------------------------------- loading

    def _load_current(self) -> None:
        business = self._import_module("config.business")
        for attr, _label in BUSINESS_FIELDS:
            val = getattr(business, attr, "")
            self._business_inputs[attr].setText(str(val))
        rgb = getattr(business, "BRAND_COLOR_RGB", (30, 60, 114))
        try:
            r, g, b = (int(x) for x in rgb)
        except (TypeError, ValueError):
            r, g, b = 30, 60, 114
        # Clamp to the valid 0..255 range so a hand-edited business.py with a
        # nonsensical tuple still gives the color button a paintable value.
        self._brand_rgb = (max(0, min(255, r)),
                           max(0, min(255, g)),
                           max(0, min(255, b)))
        self._update_color_button()

        clients = self._import_module("config.clients")
        # Any module-level dict whose keys are client fields counts as a client.
        client_keys = {"name", "phone", "email", "site"}
        for name in dir(clients):
            if name.startswith("_"):
                continue
            val = getattr(clients, name)
            if isinstance(val, dict) and client_keys & set(val.keys()):
                self._add_client_row(name, val)

    @staticmethod
    def _import_module(dotted: str):
        return importlib.import_module(dotted)

    # -------------------------------------------------------------- color UI

    def _pick_color(self) -> None:
        r, g, b = self._brand_rgb
        color = QColorDialog.getColor(QColor(r, g, b), self, "Brand color")
        if color.isValid():
            self._brand_rgb = (color.red(), color.green(), color.blue())
            self._update_color_button()

    def _update_color_button(self) -> None:
        r, g, b = self._brand_rgb
        self._color_button.setText(f"RGB {r}, {g}, {b}")
        self._color_button.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: white;"
            f" font-weight: bold;"
        )

    # ----------------------------------------------------------- clients rows

    def _add_client_row(self, key: str = "", data: dict | None = None) -> None:
        data = data or {"name": "", "phone": "", "email": "", "site": ""}
        r = self.clients_table.rowCount()
        self.clients_table.insertRow(r)
        self.clients_table.setItem(r, 0, QTableWidgetItem(str(key)))
        self.clients_table.setItem(r, 1, QTableWidgetItem(str(data.get("name", ""))))
        self.clients_table.setItem(r, 2, QTableWidgetItem(str(data.get("phone", ""))))
        self.clients_table.setItem(r, 3, QTableWidgetItem(str(data.get("email", ""))))
        self.clients_table.setItem(r, 4, QTableWidgetItem(str(data.get("site", ""))))

    def _del_client_row(self) -> None:
        rows = sorted({i.row() for i in self.clients_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.clients_table.removeRow(r)

    # ----------------------------------------------------------------- saving

    def _save(self) -> None:
        try:
            self._write_business()
            self._write_clients()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Could not save settings",
                                 f"{type(e).__name__}: {e}")
            return
        # Drop the cached config modules so the next job load picks up the new
        # business identity / clients instead of the stale in-memory copy.
        import sys as _sys
        _sys.modules.pop("config.business", None)
        _sys.modules.pop("config.clients", None)
        _sys.modules.pop("config", None)
        self.accept()

    def _write_business(self) -> None:
        val = {attr: w.text() for attr, w in self._business_inputs.items()}
        r, g, b = self._brand_rgb
        text = (
            "# ---- Required ----\n"
            f'MY_NAME    = {val["MY_NAME"]!r}\n'
            "\n"
            "# ---- Contact (any can be \"\" to omit) ----\n"
            f'MY_PHONE   = {val["MY_PHONE"]!r}\n'
            f'MY_EMAIL   = {val["MY_EMAIL"]!r}\n'
            f'MY_ADDRESS = {val["MY_ADDRESS"]!r}\n'
            f'MY_WEBSITE = {val["MY_WEBSITE"]!r}\n'
            "\n"
            '# ---- Tagline shown under your name in the header ("" to omit) ----\n'
            f'MY_TAGLINE = {val["MY_TAGLINE"]!r}\n'
            "\n"
            '# ---- Optional assets (relative to project root; "" to omit) ----\n'
            f'LOGO_PATH      = {val["LOGO_PATH"]!r}\n'
            f'SIGNATURE_PATH = {val["SIGNATURE_PATH"]!r}\n'
            "\n"
            "# ---- Brand color (single accent used across all documents) ----\n"
            f"BRAND_COLOR_RGB = ({r}, {g}, {b})\n"
        )
        _atomic_write(BUSINESS_PATH, text)

    def _write_clients(self) -> None:
        header = (
            "# Reusable client records.\n"
            "# Each dict can be imported into a job file with:\n"
            "#     from config.clients import SOME_KEY\n\n"
        )
        bodies = []
        for r in range(self.clients_table.rowCount()):
            key_item = self.clients_table.item(r, 0)
            key = key_item.text().strip() if key_item else ""
            if not key or not key.isidentifier():
                continue
            def cell(col: int) -> str:
                it = self.clients_table.item(r, col)
                return it.text() if it else ""
            name, phone, email, site = cell(1), cell(2), cell(3), cell(4)
            bodies.append(
                f"{key} = {{\n"
                f'    "name":  {name!r},\n'
                f'    "phone": {phone!r},\n'
                f'    "email": {email!r},\n'
                f'    "site":  {site!r},\n'
                "}\n"
            )
        _atomic_write(CLIENTS_PATH, header + "\n".join(bodies) + "\n")
