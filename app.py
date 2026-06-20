#!/usr/bin/env python3
"""
app.py — launch the Paper Maker desktop GUI.

Usage:
    python app.py

This is a thin launcher. All GUI code lives under the gui/ package; the engine
(generate.py / new.py / ledger.py) and the LaTeX templates are untouched.
"""
import sys

from PySide6.QtWidgets import QApplication

from gui.app import MainWindow


def main() -> int:
    # Ensure the project root is importable when launched from anywhere.
    app = QApplication(sys.argv)
    app.setApplicationName("Paper Maker")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
