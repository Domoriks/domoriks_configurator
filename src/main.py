#!/usr/bin/env python3
"""
EventAction Configurator - Main Entry Point

A professional home automation event configuration tool with bidirectional
C-code ↔ GUI conversion.
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
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
