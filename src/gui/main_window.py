"""
Main application window for Domoriks Configurator.
"""
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QPushButton, QMessageBox, QFileDialog,
                             QAction, QLabel, QDialog, QToolBar, QListWidget,
                             QStackedWidget, QSizePolicy, QLineEdit)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

from models.project import Project
from models.module import Module
from gui.module_widget import ModuleWidget
from gui.dialogs import (CCodeImportDialog, CCodeExportDialog,
                        ModuleDialog, ModuleEditorWidget)
from utils.parser import CCodeParser


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path("domoriks.ico")))
        self.setGeometry(100, 100, 1200, 800)
        
        self.project = Project()
        self.current_file = None
        self._update_title()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        
        QTimer.singleShot(0, self.show_welcome_dialog)

    def show_welcome_dialog(self):
        """Show a welcome dialog to ask user for action."""
        reply = QMessageBox.question(self, 'Welcome',
            "Do you want to open an existing project?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.open_project()
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Project name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Project:"))
        self.project_name_edit = QLineEdit(self.project.name)
        self.project_name_edit.setStyleSheet("font-weight: bold;")
        self.project_name_edit.textChanged.connect(self._on_project_name_changed)
        name_layout.addWidget(self.project_name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)

        # Main stacked area: Devices overview (index 0) and Actions view (index 1)
        self.main_stack = QStackedWidget()

        # --- Devices overview page ---
        devices_page = QWidget()
        devices_layout = QHBoxLayout()

        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Modules"))
        self.modules_list = QListWidget()
        self.modules_list.itemDoubleClicked.connect(self._on_module_double_clicked)
        self.modules_list.currentItemChanged.connect(self._on_modules_selection_changed)
        left_col.addWidget(self.modules_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_module)
        btn_row.addWidget(add_btn)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_selected_module)
        btn_row.addWidget(edit_btn)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_selected_module)
        btn_row.addWidget(remove_btn)
        left_col.addLayout(btn_row)

        devices_layout.addLayout(left_col, 1)

        right_col = QVBoxLayout()
        # Inline module editor replaces the placeholder label/button
        self.module_editor = ModuleEditorWidget(None, self.project.modules, self)
        self.module_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.module_editor.saved.connect(self._on_module_saved)
        # Give the editor the vertical stretch so it fills the right column
        right_col.addWidget(self.module_editor, 1)
        devices_layout.addLayout(right_col, 2)

        devices_page.setLayout(devices_layout)
        self.main_stack.addWidget(devices_page)

        # --- Actions page (current main UI) ---
        actions_page = QWidget()
        actions_layout = QVBoxLayout()

        self.module_tabs = QTabWidget()
        actions_layout.addWidget(self.module_tabs)

        action_btn_row = QHBoxLayout()
        action_btn_row.addStretch()
        actions_layout.addLayout(action_btn_row)

        actions_page.setLayout(actions_layout)
        self.main_stack.addWidget(actions_page)

        layout.addWidget(self.main_stack)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Start on modules overview
        self.switch_to_modules()
    
    def _add_action(self, menu, label, slot, shortcut=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        self._new_action = self._add_action(file_menu, "New Project", self.new_project, "Ctrl+N")
        self._open_action = self._add_action(file_menu, "Open Project...", self.open_project, "Ctrl+O")
        self._save_action = self._add_action(file_menu, "Save Project", self.save_project, "Ctrl+S")
        self._add_action(file_menu, "Save Project As...", self.save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        self._validate_action = self._add_action(file_menu, "Validate Configuration", self.validate_project)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit", self.close, "Ctrl+Q")

        ie_menu = menubar.addMenu("Import/Export")
        self._add_action(ie_menu, "Export All Actions", self.export_c_code)
        self._add_action(ie_menu, "Import All Actions", self.import_c_code)
        ie_menu.addSeparator()
        self._export_selected_c_action = self._add_action(ie_menu, "Export Module Actions", self.export_selected_module_c)
        self._import_selected_c_action = self._add_action(ie_menu, "Import Module Actions", self.import_selected_module_c)
        ie_menu.addSeparator()
        self._add_action(ie_menu, "Import Module (JSON)", self.import_module_json)
        self._add_action(ie_menu, "Export Module (JSON)", self.export_module_json)

        help_menu = menubar.addMenu("Help")
        self._add_action(help_menu, "About", self.show_about)
    
    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(2)  # Qt.ToolButtonTextOnly
        self.addToolBar(toolbar)

        modules_action = QAction("Modules", self)
        modules_action.setCheckable(True)
        modules_action.triggered.connect(self.switch_to_modules)
        toolbar.addAction(modules_action)
        modules_action.setChecked(True)
        self._modules_toolbar_action = modules_action

        actions_action = QAction("Actions", self)
        actions_action.setCheckable(True)
        actions_action.triggered.connect(self.switch_to_actions)
        toolbar.addAction(actions_action)
        self._actions_toolbar_action = actions_action

        self._update_toolbar_state()
    
    def setup_statusbar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    def _update_toolbar_state(self):
        """Enable/disable menu actions based on current view."""
        if not hasattr(self, '_export_selected_c_action'):
            return
        in_actions = self.main_stack.currentIndex() == 1
        self._export_selected_c_action.setEnabled(in_actions)
        self._import_selected_c_action.setEnabled(in_actions)
    
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
        self.current_file = None
        self.project_name_edit.setText(self.project.name)
        self._update_title()
        
        # Clear all module tabs
        self.module_tabs.clear()
        self.refresh_module_list()
        if hasattr(self, 'module_editor'):
            self.module_editor.set_module(None)
        
        self.statusBar().showMessage("New project created")

    # --- Devices / Actions view helpers ---------------------------------
    def switch_to_modules(self):
        """Show the modules overview page."""
        try:
            self.main_stack.setCurrentIndex(0)
        except Exception:
            pass
        # Reflect toolbar state
        try:
            if hasattr(self, '_modules_toolbar_action'):
                self._modules_toolbar_action.setChecked(True)
            if hasattr(self, '_actions_toolbar_action'):
                self._actions_toolbar_action.setChecked(False)
        except Exception:
            pass
        self.refresh_module_list()
        self._update_toolbar_state()
        # Select first module if present and populate inline editor
        try:
            if self.modules_list.count() > 0:
                self.modules_list.setCurrentRow(0)
            else:
                if hasattr(self, 'module_editor'):
                    self.module_editor.set_module(None)
        except Exception:
            pass

    def switch_to_actions(self):
        """Show the actions (device tabs) page."""
        try:
            self.main_stack.setCurrentIndex(1)
        except Exception:
            pass
        # Reflect toolbar state
        try:
            if hasattr(self, '_modules_toolbar_action'):
                self._modules_toolbar_action.setChecked(False)
            if hasattr(self, '_actions_toolbar_action'):
                self._actions_toolbar_action.setChecked(True)
        except Exception:
            pass
        self._update_toolbar_state()

    def refresh_module_list(self):
        """Refresh the modules list widget from project data."""
        try:
            current_name = None
            if self.modules_list.currentItem():
                current_name = self.modules_list.currentItem().text()
            self.modules_list.clear()
            for m in self.project.modules:
                self.modules_list.addItem(m.name)
            # Restore previous selection or default to first
            restored = False
            if current_name:
                for i in range(self.modules_list.count()):
                    if self.modules_list.item(i).text() == current_name:
                        self.modules_list.setCurrentRow(i)
                        restored = True
                        break
            if not restored and self.modules_list.count() > 0:
                self.modules_list.setCurrentRow(0)
            # Keep inline editor's module list reference up-to-date
            try:
                if hasattr(self, 'module_editor'):
                    self.module_editor.all_modules = list(self.project.modules)
            except Exception:
                pass
        except Exception:
            pass

    def _on_module_double_clicked(self, item):
        self.edit_selected_module()

    def _on_modules_selection_changed(self, current, previous):
        """Handle selection change in modules list."""
        if not current:
            if hasattr(self, 'module_editor'):
                self.module_editor.set_module(None)
            return

        name = current.text()
        module = next((m for m in self.project.modules if m.name == name), None)
        if hasattr(self, 'module_editor'):
            self.module_editor.set_module(module)

    def _on_module_saved(self, module):
        """Handler called when inline editor emits saved signal."""
        try:
            # Update all open module tabs (outputs from any module may appear in combos)
            for i in range(self.module_tabs.count()):
                tab_widget = self.module_tabs.widget(i)
                if not hasattr(tab_widget, 'module'):
                    continue
                tab_widget.all_modules = list(self.project.modules)
                if tab_widget.module is module:
                    self.module_tabs.setTabText(i, module.name)
                    try:
                        tab_widget.name_edit.blockSignals(True)
                        tab_widget.name_edit.setText(module.name)
                        tab_widget.name_edit.blockSignals(False)
                    except Exception:
                        pass
                tab_widget.update_outputs(tab_widget.module.outputs)
            # Refresh list and mark project modified
            self.refresh_module_list()
            self.on_module_modified()
            self.statusBar().showMessage(f"Saved module: {module.name}")
        except Exception:
            pass

    def open_actions_for_selected(self):
        """Open the actions view for the currently selected module in the list."""
        item = self.modules_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Module", "No module selected.")
            return
        name = item.text()
        module = next((m for m in self.project.modules if m.name == name), None)
        if not module:
            QMessageBox.warning(self, "Not Found", "Selected module not found in project.")
            return

        idx = self.find_module_tab_index(module)
        if idx == -1:
            if module.num_inputs > 0:
                self.add_module_tab(module)
                idx = self.find_module_tab_index(module)
            else:
                QMessageBox.information(self, "No Actions", "Selected module has no inputs/actions to edit.")
                return

        self.switch_to_actions()
        if idx != -1:
            self.module_tabs.setCurrentIndex(idx)

    def find_module_tab_index(self, module):
        for i in range(self.module_tabs.count()):
            widget = self.module_tabs.widget(i)
            if hasattr(widget, 'module') and widget.module is module:
                return i
        return -1

    def edit_selected_module(self):
        item = self.modules_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Module", "No module selected.")
            return
        module = next((m for m in self.project.modules if m.name == item.text()), None)
        if not module:
            QMessageBox.warning(self, "Not Found", "Module not found.")
            return
        dialog = ModuleDialog(module=module, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_module_config()
            old_inputs = module.num_inputs
            old_extras = module.num_extra_actions
            module.update_from_dict(config)

            idx = self.find_module_tab_index(module)
            if module.num_inputs == 0:
                # Remove action tab if inputs set to zero
                if idx != -1:
                    self.module_tabs.removeTab(idx)
            elif idx != -1:
                # Update existing action tab
                tab_widget = self.module_tabs.widget(idx)
                tab_widget.all_modules = list(self.project.modules)
                self.module_tabs.setTabText(idx, module.name)
                tab_widget.name_edit.blockSignals(True)
                tab_widget.name_edit.setText(module.name)
                tab_widget.name_edit.blockSignals(False)
                if module.num_inputs != old_inputs or module.num_extra_actions != old_extras:
                    tab_widget.rebuild_ui()
                else:
                    tab_widget.update_outputs(module.outputs)
            elif old_inputs == 0 and module.num_inputs > 0:
                # Inputs changed from 0 to >0, add new tab
                self.add_module_tab(module)

            # Refresh combos on all other open tabs
            for i in range(self.module_tabs.count()):
                tw = self.module_tabs.widget(i)
                if hasattr(tw, 'module') and tw.module is not module:
                    tw.all_modules = list(self.project.modules)
                    tw.update_outputs(tw.module.outputs)

            # Update inline editor
            if hasattr(self, 'module_editor'):
                self.module_editor.set_module(module)

            self.on_module_modified()
            self.refresh_module_list()
            self.statusBar().showMessage(f"Updated module: {module.name}")

    def remove_selected_module(self):
        item = self.modules_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Module", "No module selected.")
            return
        module = next((m for m in self.project.modules if m.name == item.text()), None)
        if not module:
            QMessageBox.warning(self, "Not Found", "Module not found.")
            return
        reply = QMessageBox.question(self, "Remove Module",
                                     f"Are you sure you want to remove module '{module.name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            idx = self.find_module_tab_index(module)
            if idx != -1:
                self.module_tabs.removeTab(idx)
            try:
                self.project.modules.remove(module)
            except ValueError:
                pass
            self.project.modified = True
            self.refresh_module_list()
            self.statusBar().showMessage(f"Removed module: {module.name}")
    
    def open_project(self):
        """Open an existing project."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                self.project = Project.load_from_file(filepath)
                self.current_file = filepath
                self.project_name_edit.setText(self.project.name)
                self._update_title()
                
                # Clear and reload module tabs (only modules with inputs)
                self.module_tabs.clear()
                for module in self.project.modules:
                    if module.num_inputs > 0:
                        self.add_module_tab(module)
                # Refresh list view
                self.refresh_module_list()
                
                self.statusBar().showMessage(f"Opened: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
    
    def save_project(self):
        """Save the current project."""
        if self.current_file:
            try:
                self.project.save_to_file(self.current_file)
                self._mark_saved()
                self.statusBar().showMessage(f"Saved: {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
        else:
            self.save_project_as()
    
    def save_project_as(self):
        """Save the project to a new file."""
        suggested = self.project.name.replace(" ", "_") + ".json" if self.project.name else ""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", suggested, "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                self.project.save_to_file(filepath)
                self.current_file = filepath
                self._mark_saved()
                self.statusBar().showMessage(f"Saved: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
    
    def add_module(self):
        """Add a new module to the project."""
        dialog = ModuleDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_module_config()
            module = Module(
                name=config["name"],
                num_inputs=config["num_inputs"],
                num_extra_actions=config["num_extra_actions"],
                num_outputs=config.get("num_outputs", 0),
                node=config.get("node", 0),
            )
            self.project.add_module(module)
            if module.num_inputs > 0:
                self.add_module_tab(module)
            # Keep module list in sync and select the new module
            self.refresh_module_list()
            for i in range(self.modules_list.count()):
                if self.modules_list.item(i).text() == module.name:
                    self.modules_list.setCurrentRow(i)
                    break
            self.statusBar().showMessage(f"Added module: {module.name}")
    
    def add_module_tab(self, module):
        """Add a module tab to the UI."""
        widget = ModuleWidget(module, all_modules=self.project.modules)
        widget.module_modified.connect(self.on_module_modified)
        self.module_tabs.addTab(widget, module.name)
        self.module_tabs.setCurrentWidget(widget)
        # Keep the modules list up to date
        try:
            self.refresh_module_list()
        except Exception:
            pass
    
    def close_module_tab(self, index):
        """Close a module tab."""
        widget = self.module_tabs.widget(index)
        module = widget.module

        reply = QMessageBox.question(
            self, "Remove Module",
            f"Are you sure you want to remove module '{module.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.project.modules.remove(module)
            except ValueError:
                pass
            self.project.modified = True
            self.module_tabs.removeTab(index)
            try:
                self.refresh_module_list()
            except Exception:
                pass
            self.statusBar().showMessage(f"Removed module: {module.name}")
    
    def remove_current_module(self):
        """Remove the currently selected module."""
        current_index = self.module_tabs.currentIndex()
        if current_index >= 0:
            self.close_module_tab(current_index)
    
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
                module = CCodeParser.parse_to_module(c_code, "Imported Module")
                self.project.add_module(module)
                if module.num_inputs > 0:
                    self.add_module_tab(module)
                self.refresh_module_list()
                self.statusBar().showMessage(f"Imported module: {module.name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {e}")
    
    def export_c_code(self):
        """Export configuration to C code."""
        c_code = self.project.to_c_code()
        dialog = CCodeExportDialog(c_code, self)
        dialog.exec_()

    def export_selected_module_c(self):
        """Export the currently selected module's actions to C code."""
        current = self.module_tabs.currentWidget()
        if not current or not hasattr(current, 'module'):
            QMessageBox.information(self, "No Module", "No module tab is selected.")
            return
        c_code = current.module.to_c_code()
        dialog = CCodeExportDialog(c_code, self)
        dialog.exec_()

    def import_selected_module_c(self):
        """Import actions from C code into the currently selected module."""
        current = self.module_tabs.currentWidget()
        if not current or not hasattr(current, 'module'):
            QMessageBox.information(self, "No Module", "No module tab is selected.")
            return
        dialog = CCodeImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            c_code = dialog.get_c_code()
            try:
                actions = CCodeParser.parse_c_code(c_code)
                module = current.module
                for name, action in actions.items():
                    module.set_action(name, action)
                current.rebuild_ui()
                self.on_module_modified()
                self.statusBar().showMessage(f"Imported {len(actions)} actions into {module.name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {e}")

    def import_module_json(self):
        """Import a single module from a JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Module from JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                import json
                with open(filepath, 'r') as f:
                    data = json.load(f)
                module = Module.from_dict(data)
                self.project.add_module(module)
                if module.num_inputs > 0:
                    self.add_module_tab(module)
                self.refresh_module_list()
                self.statusBar().showMessage(f"Imported module: {module.name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import module: {e}")

    def export_module_json(self):
        """Export the selected module to a JSON file."""
        # Try actions tab first, then modules list
        module = None
        current = self.module_tabs.currentWidget()
        if current and hasattr(current, 'module'):
            module = current.module
        else:
            item = self.modules_list.currentItem()
            if item:
                module = next((m for m in self.project.modules if m.name == item.text()), None)
        if not module:
            QMessageBox.information(self, "No Module", "No module selected.")
            return
        suggested = module.name.replace(" ", "_") + ".json"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Module to JSON", suggested, "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            try:
                import json
                with open(filepath, 'w') as f:
                    json.dump(module.to_dict(), f, indent=2)
                self.statusBar().showMessage(f"Exported module: {module.name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export module: {e}")
    
    def _update_title(self):
        name = self.project.name or "Untitled"
        title = f"Domoriks Configurator - {name}"
        if self.project.modified:
            title += "*"
        self.setWindowTitle(title)

    def _mark_saved(self):
        self.project.modified = False
        self._update_title()

    def _on_project_name_changed(self, text):
        self.project.name = text
        self.on_module_modified()

    def on_module_modified(self):
        """Handle module modification."""
        self.project.modified = True
        self._update_title()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Domoriks Configurator",
            "<h3>Domoriks Configurator</h3>"
            "<p>A professional home automation event configuration tool.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Bidirectional C code ↔ GUI conversion</li>"
            "<li>Multi-device support</li>"
            "<li>Configurable light points</li>"
            "<li>Input validation</li>"
            "</ul>"
            "<p>Version 0.2.0</p>"
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
