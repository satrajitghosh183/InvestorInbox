"""
GUI Components for Email Enrichment App
"""

try:
    import tkinter as tk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

__all__ = ['GUI_AVAILABLE']

if GUI_AVAILABLE:
    from .main_window import MainWindow
    from .setup_window import SetupWindow
    __all__.extend(['MainWindow', 'SetupWindow'])