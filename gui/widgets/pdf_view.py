"""In-app PDF preview pane, with a graceful fallback.

Uses PySide6's built-in QtPdfWidgets.QPdfView + QtPdf.QPdfDocument when
available (they are, on this install). If for any reason the module is missing
on another machine, we fall back to a placeholder that offers "Open in system
viewer" so the user is never stuck.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QPushButton, QVBoxLayout, QWidget,
)

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    HAVE_QTPDF = True
except ImportError:  # pragma: no cover - environment-dependent
    HAVE_QTPDF = False


class PdfPreview(QWidget):
    """Shows a PDF inside the app, or a fallback panel if QtPdf is absent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAVE_QTPDF:
            self._document = QPdfDocument(self)
            self._view = QPdfView(self)
            self._view.setDocument(self._document)
            self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            layout.addWidget(self._view)
        else:
            self._view = None
            hint = QLabel(
                "In-app PDF rendering is unavailable on this machine.\n"
                "You can still generate PDFs and open them in your system viewer."
            )
            hint.setAlignment(Qt.AlignCenter)
            layout.addWidget(hint)

        self._current_path: str | None = None
        self._fallback_button = QPushButton("Open in system viewer")
        self._fallback_button.clicked.connect(self._open_external)
        self._fallback_button.setEnabled(False)
        layout.addWidget(self._fallback_button)

    def load(self, path: str | Path) -> None:
        """Load a PDF file. Non-existent or empty path clears the view."""
        path = str(path) if path else ""
        self._current_path = path if path and Path(path).exists() else None

        if HAVE_QTPDF:
            if self._current_path:
                # QPdfDocument.load accepts a filename string (not a QUrl) in PySide6.
                self._document.load(self._current_path)
            else:
                # Reload an empty document to blank the view.
                self._document = QPdfDocument(self)
                self._view.setDocument(self._document)

        self._fallback_button.setEnabled(self._current_path is not None)

    def clear(self) -> None:
        self.load("")

    def _open_external(self) -> None:
        if not self._current_path:
            return
        # os.startfile is Windows-only; the engine targets Windows/Mac/Linux,
        # so cover the others too.
        if sys.platform == "win32":
            os.startfile(self._current_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{self._current_path}"')
        else:
            os.system(f'xdg-open "{self._current_path}"')
