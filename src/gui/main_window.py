"""
Main application window for EventAction Configurator.
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QPushButton, QMessageBox, QFileDialog,
                             QMenuBar, QMenu, QAction, QLabel, QStatusBar, QDialog,
                             QToolBar)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from models.project import Project
from models.device import Device
from gui.device_widget import DeviceWidget
from gui.dialogs import (CCodeImportDialog, CCodeExportDialog, 
                        NewDeviceDialog, LightPointsEditorDialog)
from utils.parser import CCodeParser
from utils.config import ConfigManager


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EventAction Configurator")
        self.setGeometry(100, 100, 1200, 800)
        
        self.project = Project()
        self.config_manager = ConfigManager("../config")
        self.current_file = None
        
        # Load default light points
        self.project.set_light_points(self.config_manager.load_light_points())
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # Add a default device
        self.add_device()
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Project name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Project:"))
        self.project_label = QLabel(self.project.name)
        self.project_label.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(self.project_label)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # Tab widget for devices
        self.device_tabs = QTabWidget()
        self.device_tabs.setTabsClosable(True)
        self.device_tabs.tabCloseRequested.connect(self.close_device_tab)
        layout.addWidget(self.device_tabs)
        
        # Add device button
        add_device_btn = QPushButton("+ Add Device")
        add_device_btn.clicked.connect(self.add_device)
        layout.addWidget(add_device_btn)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Project", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save Project As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        light_points_action = QAction("Edit Light Points...", self)
        light_points_action.triggered.connect(self.edit_light_points)
        edit_menu.addAction(light_points_action)
        
        validate_action = QAction("Validate Configuration", self)
        validate_action.triggered.connect(self.validate_project)
        edit_menu.addAction(validate_action)
        
        # Device menu
        device_menu = menubar.addMenu("Device")
        
        add_device_action = QAction("Add Device", self)
        add_device_action.setShortcut("Ctrl+D")
        add_device_action.triggered.connect(self.add_device)
        device_menu.addAction(add_device_action)
        
        remove_device_action = QAction("Remove Current Device", self)
        remove_device_action.triggered.connect(self.remove_current_device)
        device_menu.addAction(remove_device_action)
        
        # Code menu
        code_menu = menubar.addMenu("Code")
        
        import_action = QAction("Import from C Code...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_c_code)
        code_menu.addAction(import_action)
        
        export_action = QAction("Export to C Code...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_c_code)
        code_menu.addAction(export_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Setup toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Add common actions
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.new_project)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.open_project)
        toolbar.addWidget(open_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_project)
        toolbar.addWidget(save_btn)
        
        toolbar.addSeparator()
        
        import_btn = QPushButton("Import C")
        import_btn.clicked.connect(self.import_c_code)
        toolbar.addWidget(import_btn)
        
        export_btn = QPushButton("Export C")
        export_btn.clicked.connect(self.export_c_code)
        toolbar.addWidget(export_btn)
        
        toolbar.addSeparator()
        
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate_project)
        toolbar.addWidget(validate_btn)
    
    def setup_statusbar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")
    
    def new_project(self):
        """Create a new project."""
        if self.project.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before creating a new project?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_project()
            elif reply == QMessageBox.Cancel:
                return
        
        self.project = Project("New Project")
        self.project.set_light_points(self.config_manager.load_light_points())
        self.current_file = None
        self.project_label.setText(self.project.name)
        
        # Clear all device tabs
        self.device_tabs.clear()
        
        # Add default device
        self.add_device()
        
        self.statusBar().showMessage("New project created")
    
    def open_project(self):
        """Open an existing project."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                self.project = Project.load_from_file(filepath)
                self.current_file = filepath
                self.project_label.setText(self.project.name)
                
                # Clear and reload device tabs
                self.device_tabs.clear()
                for device in self.project.devices:
                    self.add_device_tab(device)
                
                self.statusBar().showMessage(f"Opened: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
    
    def save_project(self):
        """Save the current project."""
        if self.current_file:
            try:
                self.project.save_to_file(self.current_file)
                self.statusBar().showMessage(f"Saved: {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
        else:
            self.save_project_as()
    
    def save_project_as(self):
        """Save the project to a new file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                self.project.save_to_file(filepath)
                self.current_file = filepath
                self.statusBar().showMessage(f"Saved: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
    
    def add_device(self):
        """Add a new device to the project."""
        dialog = NewDeviceDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_device_config()
            device = Device(
                name=config["name"],
                num_inputs=config["num_inputs"],
                num_extra_actions=config["num_extra_actions"]
            )
            self.project.add_device(device)
            self.add_device_tab(device)
            self.statusBar().showMessage(f"Added device: {device.name}")
    
    def add_device_tab(self, device):
        """Add a device tab to the UI."""
        widget = DeviceWidget(device, self.project.light_points)
        widget.device_modified.connect(self.on_device_modified)
        self.device_tabs.addTab(widget, device.name)
        self.device_tabs.setCurrentWidget(widget)
    
    def close_device_tab(self, index):
        """Close a device tab."""
        widget = self.device_tabs.widget(index)
        device_name = widget.device.name
        
        reply = QMessageBox.question(
            self, "Remove Device",
            f"Are you sure you want to remove device '{device_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.project.remove_device(device_name)
            self.device_tabs.removeTab(index)
            self.statusBar().showMessage(f"Removed device: {device_name}")
    
    def remove_current_device(self):
        """Remove the currently selected device."""
        current_index = self.device_tabs.currentIndex()
        if current_index >= 0:
            self.close_device_tab(current_index)
    
    def edit_light_points(self):
        """Edit light points configuration."""
        dialog = LightPointsEditorDialog(self.project.light_points, self)
        if dialog.exec_() == QDialog.Accepted:
            self.project.set_light_points(dialog.get_light_points())
            
            # Update all device widgets
            for i in range(self.device_tabs.count()):
                widget = self.device_tabs.widget(i)
                widget.update_light_points(self.project.light_points)
            
            self.statusBar().showMessage("Light points updated")
    
    def validate_project(self):
        """Validate the project configuration."""
        errors = self.project.validate()
        
        if errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "Found validation errors:\n\n" + "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self, "Validation Successful",
                "Project configuration is valid!"
            )
    
    def import_c_code(self):
        """Import configuration from C code."""
        dialog = CCodeImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            c_code = dialog.get_c_code()
            
            try:
                device = CCodeParser.parse_to_device(c_code, "Imported Device")
                self.project.add_device(device)
                self.add_device_tab(device)
                self.statusBar().showMessage(f"Imported device: {device.name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {e}")
    
    def export_c_code(self):
        """Export configuration to C code."""
        c_code = self.project.to_c_code()
        dialog = CCodeExportDialog(c_code, self)
        dialog.exec_()
    
    def on_device_modified(self):
        """Handle device modification."""
        self.project.modified = True
        if not self.windowTitle().endswith("*"):
            self.setWindowTitle(self.windowTitle() + "*")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About EventAction Configurator",
            "<h3>EventAction Configurator</h3>"
            "<p>A professional home automation event configuration tool.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Bidirectional C code ↔ GUI conversion</li>"
            "<li>Multi-device support</li>"
            "<li>Configurable light points</li>"
            "<li>Input validation</li>"
            "</ul>"
            "<p>Version 1.0</p>"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.project.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_project()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
