"""'New document' dialog — picks type + year and scaffolds the job file.

Delegates the actual file creation to new.scaffold() so numbering and the
scaffold format have exactly one home (the CLI and the GUI stay in sync).
"""
from __future__ import annotations

from datetime import date

from new import scaffold  # the engine's scaffolder
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QMessageBox,
    QSpinBox,
)

from gui.models import TYPE_LABELS


class NewDocDialog(QDialog):
    """Returns the path of the newly created job file via ``get_path()``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New document")
        self._created_path: str | None = None

        self.type_combo = QComboBox()
        self.type_combo.addItems([TYPE_LABELS[t] for t in ("quotation", "invoice", "receipt")])

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 9999)
        self.year_spin.setValue(date.today().year)

        form = QFormLayout(self)
        form.addRow("Type:", self.type_combo)
        form.addRow("Year:", self.year_spin)

        hint = QLabel("The next sequential ID for this type/year is assigned automatically.")
        hint.setWordWrap(True)
        form.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        label_to_type = {v: k for k, v in TYPE_LABELS.items()}
        doc_type = label_to_type[self.type_combo.currentText()]
        year = self.year_spin.value()
        try:
            path = scaffold(doc_type, year)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Could not create document",
                                 f"{type(e).__name__}: {e}")
            return
        self._created_path = str(path)
        self.accept()

    def get_path(self) -> str | None:
        return self._created_path
