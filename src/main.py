#!/usr/bin/env python3
"""
Domoriks Configurator - Main Entry Point

A professional home automation event configuration tool with bidirectional
C-code ↔ GUI conversion.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller onefile.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set icon
    icon_path = resource_path("domoriks.ico")
    app.setWindowIcon(QIcon(icon_path))

    app.setApplicationName("Domoriks Configurator")
    app.setOrganizationName("Domoriks")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
