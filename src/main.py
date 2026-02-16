#!/usr/bin/env python3
"""
EventAction Configurator - Main Entry Point

A professional home automation event configuration tool with bidirectional
C-code ↔ GUI conversion.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Get the absolute path to the icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'domoriks.png')
    app.setWindowIcon(QIcon(icon_path))

    app.setApplicationName("Domoriks Actions Configurator")
    app.setOrganizationName("Domoriks")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
