"""The main application window.

Layout (matches the approved mockup):
  +------+--------------+--------------------+
  | side | documents     |  editor + preview |
  | bar  |  (left)       |     (right)       |
  +------+--------------+--------------------+

The leftmost narrow column is the navigation (Documents / Settings / Ledger
plus the live LaTeX status). Next is the documents list; the wide right pane is
the editor with its PDF preview.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QStackedWidget, QVBoxLayout, QWidget,
)

from gui import adapter, latex_status, storage
from gui.widgets.documents_panel import DocumentsPanel
from gui.widgets.editor import Editor
from gui.widgets.ledger_dialog import LedgerDialog
from gui.widgets.new_doc_dialog import NewDocDialog
from gui.widgets.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paper Maker")
        self.resize(1280, 820)
        self.setMinimumSize(960, 600)

        self._latex = latex_status.detect()

        # --- side nav ---
        self.nav_documents = QPushButton("Documents")
        self.nav_settings = QPushButton("Settings")
        self.nav_ledger = QPushButton("Ledger")
        self.nav_new = QPushButton("+ New")
        self.nav_new.setStyleSheet("font-weight:bold;")
        for b in (self.nav_documents, self.nav_settings, self.nav_ledger, self.nav_new):
            b.setCheckable(True)
            b.setMinimumWidth(120)
            b.clicked.connect(self._on_nav_clicked)
        self.nav_documents.setChecked(True)

        self.latex_label = QLabel(self._latex.message())
        self.latex_label.setWordWrap(True)
        self.latex_label.setStyleSheet("color:#555; padding:6px; font-size:11px;")

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(6, 6, 6, 6)
        nav_layout.addWidget(self.nav_new)
        nav_layout.addSpacing(8)
        nav_layout.addWidget(self.nav_documents)
        nav_layout.addWidget(self.nav_settings)
        nav_layout.addWidget(self.nav_ledger)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.latex_label)
        nav_host = QWidget()
        nav_host.setLayout(nav_layout)
        nav_host.setFixedWidth(150)

        # --- main area: documents list + editor/preview ---
        self.documents = DocumentsPanel()
        self.documents.job_selected.connect(self._load_job)

        self.editor = Editor(self._latex)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(nav_host)
        splitter.addWidget(self.documents)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([150, 280, 850])

        central = QWidget()
        central.setLayout(QHBoxLayout(central))
        central.layout().setContentsMargins(0, 0, 0, 0)
        central.layout().addWidget(splitter)
        self.setCentralWidget(central)

        # Wire nav.
        self.nav_documents.clicked.connect(lambda: self._set_nav("documents"))
        self.nav_settings.clicked.connect(self._open_settings)
        self.nav_ledger.clicked.connect(self._open_ledger)
        self.nav_new.clicked.connect(self._open_new_doc)

        # Initial load.
        self.documents.refresh()

    # ----------------------------------------------------------- navigation

    def _on_nav_clicked(self) -> None:
        # Keep "Documents" as the active nav unless a dialog takes over.
        pass

    def _set_nav(self, which: str) -> None:
        self.nav_documents.setChecked(which == "documents")

    # ------------------------------------------------------------- actions

    def _load_job(self, path: str) -> None:
        # Re-selecting the already-loaded doc is a no-op — and most importantly
        # it must NOT trigger an unsaved-changes prompt, because that's exactly
        # what happens after the user cancelled a switch and we re-selected the
        # current row programmatically.
        if self.editor.current_path() == path:
            return
        # If the current doc has unsaved edits, let the user save / discard /
        # cancel before we throw it away by loading a different one.
        if not self.editor.confirm_save_or_discard():
            # User cancelled — re-select the currently-loaded doc in the list so
            # the selection matches what's actually shown.
            current = self.editor.current_path()
            if current:
                self.documents.select_path(current)
            return
        try:
            model = adapter.load(path)
        except SystemExit:
            QMessageBox.critical(self, "Cannot open document",
                                 f"The engine rejected this file:\n{path}")
            return
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Cannot open document",
                                 f"{type(e).__name__}: {e}")
            return
        self._set_nav("documents")
        self.editor.load_model(model)

    def closeEvent(self, event):  # noqa: N802 - Qt signature
        # Prompt for unsaved edits before the window closes. If the user cancels,
        # ignore the event so the app stays open.
        if self.editor.confirm_save_or_discard():
            event.accept()
        else:
            event.ignore()

    def _open_new_doc(self) -> None:
        dlg = NewDocDialog(self)
        if dlg.exec() == NewDocDialog.Accepted and dlg.get_path():
            self.documents.refresh()
            self.documents.select_path(dlg.get_path())

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        dlg.exec()
        # Re-detect compilers (cheap) and reload the document list since a
        # business identity / client change may update subtitles.
        self._latex = latex_status.detect()
        self.latex_label.setText(self._latex.message())
        self.editor.refresh_latex(self._latex)
        self.documents.refresh()

    def _open_ledger(self) -> None:
        dlg = LedgerDialog(self)
        dlg.exec()
        self._set_nav("documents")
