"""Paper Maker GUI — a PySide6 desktop front-end for the file-based paper maker.

This package is a thin layer over the existing engine (generate.py / new.py /
ledger.py). It never re-implements pricing, formatting, escaping or rendering;
it calls the pure functions from generate.py directly and wraps the one
process-oriented entry point (generate.render) in a GUI-safe adapter.
"""
