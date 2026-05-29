"""
Main application window for Domoriks Configurator.
"""
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QPushButton, QMessageBox, QFileDialog,
                             QAction, QLabel, QDialog, QToolBar, QListWidget,
                             QStackedWidget, QSizePolicy, QLineEdit,
                             QProgressDialog, QInputDialog, QComboBox)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

from models.project import Project
from models.module import Module
from gui.module_widget import ModuleWidget
from gui.dialogs import (
    ApiSettingsDialog,
    BusDetectDialog,
    CCodeImportDialog,
    CCodeExportDialog,
    DetectResultsDialog,
    ErrorDetailsDialog,
    JsonSideBySideDiffDialog,
    ModuleDialog,
    ModuleEditorWidget,
)
from utils.parser import CCodeParser
from utils.domoriks_api import ApiError, DomoriksApiClient
from utils.domoriks_serial import DomoriksSerialClient, find_stlink_vcp_port, list_serial_ports
from utils.action_sync import (
    UploadError,
    apply_actions_to_module,
    build_actions_snapshot,
    diff_module_actions,
    read_module_actions,
    upload_changed_actions,
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class _DetectWorker(QThread):
    """Run bus detection in a background thread (serial)."""
    finished = pyqtSignal(object)  # dict result or Exception
    progress = pyqtSignal(int)  # current slave being scanned

    def __init__(self, client, start_slave, end_slave, timeout):
        super().__init__()
        self._client = client
        self._start = start_slave
        self._end = end_slave
        self._timeout = timeout
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            reachable = []
            unreachable = []
            for slave in range(self._start, self._end + 1):
                if self._cancelled:
                    break
                if self._client._ping_slave(slave, self._timeout):
                    reachable.append(slave)
                else:
                    unreachable.append(slave)
                    # If opening the COM port timed out, remaining pings will fail too.
                    if getattr(self._client, "_last_open_timeout_error", False):
                        remaining_start = slave + 1
                        if remaining_start <= self._end:
                            unreachable.extend(range(remaining_start, self._end + 1))
                        self.progress.emit(self._end)
                        break
                self.progress.emit(slave)
            self.finished.emit({"reachable": reachable, "unreachable": unreachable})
        except Exception as e:
            self.finished.emit(e)


class _ApiDetectWorker(QThread):
    """Run bus detection in a background thread (API)."""
    finished = pyqtSignal(object)  # dict result or Exception
    progress = pyqtSignal(int)  # current slave being scanned (simulated per-position)

    def __init__(self, client, start_slave, end_slave, timeout):
        super().__init__()
        self._client = client
        self._start = start_slave
        self._end = end_slave
        self._timeout = timeout
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            def progress_cb(slave):
                if not self._cancelled:
                    self.progress.emit(slave)

            result = self._client.detect_range(self._start, self._end, self._timeout, progress_callback=progress_cb)
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.finished.emit(e)


class _ProgressUpdater:
    """Thread-safe progress callback that emits Qt signals."""
    def __init__(self, signal):
        self.signal = signal
    
    def __call__(self, current, total):
        """Callback(current, total) format for action read/write progress."""
        self.signal.emit(current, total)


class _TaskWorker(QThread):
    """Run an arbitrary callable in a background thread with optional progress."""
    finished = pyqtSignal(object)  # result or Exception
    progress = pyqtSignal(int, int)  # (current, total) for action-level progress

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)
    
    def get_progress_callback(self):
        """Return a callback for pass to read/write functions."""
        return _ProgressUpdater(self.progress)


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

        # Main stacked area: Devices overview (index 0), Actions (index 1), Device ID (index 2)
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
        api_btn = QPushButton("Connection Settings")
        api_btn.clicked.connect(self.configure_api_settings)
        action_btn_row.addWidget(api_btn)

        detect_btn = QPushButton("Detect Bus")
        detect_btn.clicked.connect(self.detect_bus)
        action_btn_row.addWidget(detect_btn)

        load_btn = QPushButton("Download from Device")
        load_btn.clicked.connect(self.load_device_config)
        action_btn_row.addWidget(load_btn)

        upload_btn = QPushButton("Upload to Device")
        upload_btn.clicked.connect(self.upload_device_config)
        action_btn_row.addWidget(upload_btn)

        action_btn_row.addStretch()
        actions_layout.addLayout(action_btn_row)

        actions_page.setLayout(actions_layout)
        self.main_stack.addWidget(actions_page)

        # --- Device ID page ---
        device_id_page = QWidget()
        device_id_layout = QVBoxLayout()

        device_id_layout.addWidget(QLabel("Vendor-specific method: write holding register 0x0031 (range 1-247)."))

        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("Detected Device:"))
        self.device_id_detected_combo = QComboBox()
        self.device_id_detected_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        select_row.addWidget(self.device_id_detected_combo)
        detect_btn = QPushButton("Detect")
        detect_btn.clicked.connect(self.detect_bus_for_device_id)
        select_row.addWidget(detect_btn)
        device_id_layout.addLayout(select_row)

        self.device_id_status_label = QLabel("Run Detect to list reachable devices.")
        device_id_layout.addWidget(self.device_id_status_label)

        id_btn_row = QHBoxLayout()
        set_id_btn = QPushButton("Set Device ID")
        set_id_btn.clicked.connect(self.set_device_id)
        id_btn_row.addWidget(set_id_btn)
        id_btn_row.addStretch()
        device_id_layout.addLayout(id_btn_row)
        device_id_layout.addStretch()

        device_id_page.setLayout(device_id_layout)
        self.main_stack.addWidget(device_id_page)
        self._device_id_reachable = []

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
        ie_menu.addSeparator()
        self._add_action(ie_menu, "Connection Settings...", self.configure_api_settings)
        self._add_action(ie_menu, "Detect Bus...", self.detect_bus)
        self._add_action(ie_menu, "Set Device ID...", self.set_device_id)
        self._add_action(ie_menu, "Download from Device...", self.load_device_config)
        self._add_action(ie_menu, "Upload to Device...", self.upload_device_config)

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

        device_id_action = QAction("Device ID", self)
        device_id_action.setCheckable(True)
        device_id_action.triggered.connect(self.switch_to_device_id)
        toolbar.addAction(device_id_action)
        self._device_id_toolbar_action = device_id_action

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
            if hasattr(self, '_device_id_toolbar_action'):
                self._device_id_toolbar_action.setChecked(False)
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
            if hasattr(self, '_device_id_toolbar_action'):
                self._device_id_toolbar_action.setChecked(False)
        except Exception:
            pass
        self._update_toolbar_state()

    def switch_to_device_id(self):
        """Show the device-id update page."""
        try:
            self.main_stack.setCurrentIndex(2)
        except Exception:
            pass
        try:
            if hasattr(self, '_modules_toolbar_action'):
                self._modules_toolbar_action.setChecked(False)
            if hasattr(self, '_actions_toolbar_action'):
                self._actions_toolbar_action.setChecked(False)
            if hasattr(self, '_device_id_toolbar_action'):
                self._device_id_toolbar_action.setChecked(True)
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

    def _set_detected_device_ids(self, reachable_ids):
        if not hasattr(self, 'device_id_detected_combo'):
            return
        combo = self.device_id_detected_combo
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for slave in reachable_ids:
            combo.addItem(f"Device {slave}", int(slave))
        if combo.count() > 0:
            idx = combo.findData(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def detect_bus_for_device_id(self):
        dialog = BusDetectDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            client = self._get_api_client()
            values = dialog.get_values()
        except Exception as e:
            QMessageBox.critical(self, "Detect Error", f"Failed to detect bus: {e}")
            return

        start_slave = values["start_slave"]
        end_slave = values["end_slave"]
        timeout = values["timeout"]

        def apply_detect_result(result):
            reachable = sorted(int(v) for v in result.get("reachable", []))
            self._device_id_reachable = list(reachable)
            self._set_detected_device_ids(reachable)
            if reachable:
                self.device_id_status_label.setText(f"Reachable IDs: {', '.join(str(v) for v in reachable)}")
            else:
                self.device_id_status_label.setText("No reachable devices in selected range.")

        # Use threaded detection for serial (iterates per-slave), blocking for API.
        if hasattr(client, '_ping_slave'):
            total = end_slave - start_slave + 1
            progress = QProgressDialog(
                f"Scanning slaves {start_slave}\u2013{end_slave}...",
                "Cancel", 0, total, self
            )
            progress.setWindowTitle("Detecting Bus")
            progress.setMinimumDuration(0)
            progress.setValue(0)

            self._detect_worker = _DetectWorker(client, start_slave, end_slave, timeout)
            self._detect_progress = progress

            def on_progress(slave):
                done = slave - start_slave + 1
                progress.setValue(done)
                progress.setLabelText(f"Scanned slave {slave} ({done}/{total})")

            def on_finished(result):
                try:
                    progress.canceled.disconnect(on_cancelled)
                except Exception:
                    pass
                progress.close()
                self._detect_worker.deleteLater()
                self._close_client(client)
                self._detect_worker = None
                self._detect_progress = None
                if self._detect_cancelled:
                    return
                if isinstance(result, Exception):
                    QMessageBox.critical(self, "Detect Error", f"Failed to detect bus: {result}")
                    return
                apply_detect_result(result)

            def on_cancelled():
                self._detect_cancelled = True
                if self._detect_worker is not None:
                    self._detect_worker.cancel()
                progress.close()

            self._detect_cancelled = False
            self._detect_worker.progress.connect(on_progress)
            self._detect_worker.finished.connect(on_finished)
            progress.canceled.connect(on_cancelled)
            self._detect_worker.start()
        else:
            try:
                result = client.detect_range(start_slave, end_slave, timeout)
                apply_detect_result(result)
            except Exception as e:
                QMessageBox.critical(self, "Detect Error", f"Failed to detect bus: {e}")
            finally:
                self._close_client(client)

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
                self.project.save_to_file(
                    self.current_file,
                    preserve_existing_token=self.project.api_token_session_only,
                )
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
                self.project.save_to_file(
                    filepath,
                    preserve_existing_token=self.project.api_token_session_only,
                )
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

    def _get_api_client(self):
        if self.project.connection_mode == "serial":
            serial_port = self.project.serial_port
            available_ports = list_serial_ports()

            # Handle stale saved COM ports (e.g., adapter re-enumerated after reinstall).
            if serial_port and serial_port not in available_ports:
                fallback_port = find_stlink_vcp_port()
                if fallback_port and fallback_port in available_ports:
                    serial_port = fallback_port
                    self.project.serial_port = fallback_port
                else:
                    ports_text = ", ".join(available_ports) if available_ports else "none"
                    raise ValueError(
                        f"Configured serial port '{self.project.serial_port}' is not available. "
                        f"Available ports: {ports_text}"
                    )

            if not serial_port:
                serial_port = find_stlink_vcp_port()
                if serial_port:
                    self.project.serial_port = serial_port
            if not serial_port:
                raise ValueError("Serial port not configured and no ST-Link VCP found")

            return DomoriksSerialClient(serial_port)
        else:
            if not self.project.api_base_url:
                raise ValueError("API base URL not configured")
            if not self.project.api_token:
                raise ValueError("API token not configured")
            return DomoriksApiClient(self.project.api_base_url, self.project.api_token)

    def _close_client(self, client):
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass

    def configure_api_settings(self):
        dialog = ApiSettingsDialog(
            base_url=self.project.api_base_url,
            token=self.project.api_token,
            token_session_only=self.project.api_token_session_only,
            connection_mode=self.project.connection_mode,
            serial_port=self.project.serial_port,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            self.project.connection_mode = settings["connection_mode"]
            self.project.api_base_url = settings["base_url"]
            if settings["token"]:
                self.project.api_token = settings["token"]
            elif not settings["token_session_only"]:
                self.project.api_token = ""
            self.project.api_token_session_only = settings["token_session_only"]
            self.project.serial_port = settings["serial_port"]
            self.on_module_modified()
            self.statusBar().showMessage("Connection settings updated")

    def detect_bus(self):
        dialog = BusDetectDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            client = self._get_api_client()
            values = dialog.get_values()
        except Exception as e:
            QMessageBox.critical(self, "Detect Error", f"Failed to detect bus: {e}")
            return

        start_slave = values["start_slave"]
        end_slave = values["end_slave"]
        timeout = values["timeout"]

        # Use threaded detection for both serial and API to show consistent progress.
        total = end_slave - start_slave + 1
        progress = QProgressDialog(
            f"Scanning slaves {start_slave}–{end_slave}...",
            "Cancel", 0, total, self
        )
        progress.setWindowTitle("Detecting Bus")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        if hasattr(client, '_ping_slave'):
            self._detect_worker = _DetectWorker(client, start_slave, end_slave, timeout)
        else:
            self._detect_worker = _ApiDetectWorker(client, start_slave, end_slave, timeout)

        self._detect_progress = progress

        def on_progress(slave):
            done = slave - start_slave + 1
            progress.setValue(done)
            progress.setLabelText(f"Scanned slave {slave} ({done}/{total})")

        def on_finished(result):
            # Prevent programmatic close from invoking cancel handler.
            try:
                progress.canceled.disconnect(on_cancelled)
            except Exception:
                pass
            progress.close()
            self._detect_worker.deleteLater()
            self._close_client(client)
            self._detect_worker = None
            self._detect_progress = None
            if self._detect_cancelled:
                return
            if isinstance(result, Exception):
                QMessageBox.critical(self, "Detect Error", f"Failed to detect bus: {result}")
                return
            self._show_detect_results(result)

        def on_cancelled():
            self._detect_cancelled = True
            if self._detect_worker is not None:
                self._detect_worker.cancel()
            progress.close()

        self._detect_cancelled = False
        self._detect_worker.progress.connect(on_progress)
        self._detect_worker.finished.connect(on_finished)
        progress.canceled.connect(on_cancelled)
        self._detect_worker.start()

    def _show_detect_results(self, result):
        reachable = result.get("reachable", [])
        unreachable = result.get("unreachable", [])
        project_nodes = [module.node for module in self.project.modules]
        results_dialog = DetectResultsDialog(reachable, unreachable, project_nodes, self)
        results_dialog.add_requested.connect(self._add_detected_device)
        results_dialog.delete_requested.connect(self._delete_detected_device)
        results_dialog.exec_()

    def set_device_id(self):
        if not hasattr(self, 'device_id_detected_combo'):
            QMessageBox.information(self, "No Device", "Device selector is not available.")
            return

        current_id = self.device_id_detected_combo.currentData()
        if current_id is None:
            QMessageBox.information(self, "No Device", "No detected device selected. Run Detect first.")
            return

        current_id = int(current_id)
        new_id, ok = QInputDialog.getInt(
            self,
            "Set Device ID",
            f"New Device ID for device {current_id} (1-247):",
            current_id,
            1,
            247,
            1,
        )
        if not ok:
            return
        if new_id == current_id:
            return

        if int(new_id) in set(int(v) for v in self._device_id_reachable):
            QMessageBox.warning(
                self,
                "ID Already In Use",
                f"Device ID {new_id} already responds on the bus.",
            )
            return

        try:
            client = self._get_api_client()
        except Exception as e:
            QMessageBox.critical(self, "Set Device ID Error", f"Failed to connect: {e}")
            return

        try:
            # Vendor-specific method: holding register 0x0031 updates Modbus ID.
            if hasattr(client, "write_single_register"):
                client.write_single_register(current_id, 0x0031, int(new_id), timeout=2.0)
            else:
                client.write_multiple_registers(current_id, 0x0031, [int(new_id)], timeout=2.0)
        except Exception as e:
            QMessageBox.critical(self, "Set Device ID Error", f"Failed to set device ID: {e}")
            return
        finally:
            self._close_client(client)

        # Keep detected list in sync after successful ID change.
        self._device_id_reachable = [int(new_id) if int(v) == int(current_id) else int(v) for v in self._device_id_reachable]
        self._device_id_reachable = sorted(set(self._device_id_reachable))
        self._set_detected_device_ids(self._device_id_reachable)
        idx = self.device_id_detected_combo.findData(int(new_id))
        if idx >= 0:
            self.device_id_detected_combo.setCurrentIndex(idx)
        if self._device_id_reachable:
            self.device_id_status_label.setText(f"Reachable IDs: {', '.join(str(v) for v in self._device_id_reachable)}")

        self.statusBar().showMessage(f"Updated device ID on bus: {current_id} -> {new_id}")
        QMessageBox.information(
            self,
            "Device ID Updated",
            f"Device ID changed from {current_id} to {new_id}.\nUse the new ID for future commands.",
        )

    def _add_detected_device(self, slave):
        if any(module.node == slave for module in self.project.modules):
            QMessageBox.information(self, "Already in Project", f"Device {slave} already exists in project.")
            return

        dialog = ModuleDialog(parent=self)
        dialog.name_edit.setText(f"Device {slave}")
        dialog.inputs_spin.setValue(4)
        dialog.extras_spin.setValue(20)
        dialog.outputs_spin.setValue(0)
        dialog.node_spin.setValue(slave)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_module_config()
            module = Module(
                name=config["name"],
                num_inputs=config["num_inputs"],
                num_extra_actions=config["num_extra_actions"],
                num_outputs=config.get("num_outputs", 0),
                node=config.get("node", slave),
            )
            self.project.add_module(module)
            if module.num_inputs > 0:
                self.add_module_tab(module)
            self.refresh_module_list()
            self.on_module_modified()
            self.statusBar().showMessage(f"Added detected device: {module.name}")

    def _delete_detected_device(self, slave):
        module = next((m for m in self.project.modules if int(m.node) == int(slave)), None)
        if not module:
            QMessageBox.information(self, "Not In Project", f"Device {slave} is not in the project.")
            return

        reply = QMessageBox.question(
            self,
            "Delete From Project",
            f"Remove module '{module.name}' (node {slave}) from project?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        idx = self.find_module_tab_index(module)
        if idx != -1:
            self.module_tabs.removeTab(idx)

        try:
            self.project.modules.remove(module)
        except ValueError:
            pass

        self.on_module_modified()
        self.refresh_module_list()
        self.statusBar().showMessage(f"Removed detected device from project: {module.name}")

    def _current_selected_module(self):
        current = self.module_tabs.currentWidget()
        if current and hasattr(current, "module"):
            return current.module
        item = self.modules_list.currentItem()
        if item:
            return next((m for m in self.project.modules if m.name == item.text()), None)
        return None

    def load_device_config(self):
        module = self._current_selected_module()
        if not module:
            QMessageBox.information(self, "No Module", "No module selected.")
            return

        try:
            client = self._get_api_client()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load device config: {e}")
            return

        total_actions = int(module.num_inputs) * 5 + int(module.num_extra_actions)
        progress = QProgressDialog(
            "Reading device actions...",
            None, 0, total_actions, self
        )
        progress.setWindowTitle("Download from Device")
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def do_read():
            progress_callback = worker.get_progress_callback()
            return read_module_actions(client, module, timeout=2.0, progress_callback=progress_callback)

        worker = _TaskWorker(do_read)

        def on_progress(current, total):
            progress.setMaximum(total)
            progress.setValue(current)
            progress.setLabelText(f"Read {current} of {total} actions...")

        def on_finished(result):
            progress.close()
            worker.deleteLater()
            self._close_client(client)
            if isinstance(result, Exception):
                QMessageBox.critical(self, "Load Error", f"Failed to load device config: {result}")
                return
            self._show_download_diff(module, result)

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()

    def _show_download_diff(self, module, device_actions):
        remote_snapshot = build_actions_snapshot(module, device_actions)
        local_snapshot = build_actions_snapshot(module)

        diff_dialog = JsonSideBySideDiffDialog(
            "Local project JSON",
            "Device JSON",
            local_snapshot,
            remote_snapshot,
            self,
        )
        if diff_dialog.exec_() == QDialog.Accepted:
            final_actions = diff_dialog.device_actions or device_actions
            apply_actions_to_module(module, final_actions)
            self.on_module_modified()
            self.statusBar().showMessage(f"Loaded device config for {module.name}")

    def upload_device_config(self):
        module = self._current_selected_module()
        if not module:
            QMessageBox.information(self, "No Module", "No module selected.")
            return

        try:
            client = self._get_api_client()
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to upload device config: {e}")
            return

        progress = QProgressDialog("Reading device actions...", None, 0, 0, self)
        progress.setWindowTitle("Upload to Device")
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def do_read():
            return read_module_actions(client, module, timeout=2.0)

        worker = _TaskWorker(do_read)

        def on_finished(result):
            progress.close()
            worker.deleteLater()
            self._close_client(client)
            if isinstance(result, Exception):
                QMessageBox.critical(self, "Upload Error", f"Failed to upload device config: {result}")
                return
            self._show_upload_diff(module, result)

        worker.finished.connect(on_finished)
        worker.start()

    def _show_upload_diff(self, module, device_actions):
        changed_steps = diff_module_actions(module, device_actions)
        if not changed_steps:
            QMessageBox.information(self, "No Changes", f"No action differences for {module.name}.")
            return

        local_snapshot = build_actions_snapshot(module)
        remote_snapshot = build_actions_snapshot(module, device_actions)

        diff_dialog = JsonSideBySideDiffDialog(
            "Device JSON",
            "Local project JSON",
            remote_snapshot,
            local_snapshot,
            self,
        )
        if diff_dialog.exec_() != QDialog.Accepted:
            return

        final_actions = diff_dialog.device_actions or device_actions
        final_changed = diff_module_actions(module, final_actions)
        if not final_changed:
            QMessageBox.information(self, "No Changes", f"No action differences for {module.name}.")
            return

        # Upload in background thread with per-action progress
        progress = QProgressDialog(
            "Uploading actions...",
            None, 0, len(final_changed), self
        )
        progress.setWindowTitle("Upload to Device")
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def do_upload():
            c = self._get_api_client()
            try:
                progress_callback = worker.get_progress_callback()
                upload_changed_actions(c, module, final_changed, timeout=2.0, progress_callback=progress_callback)
                return len(final_changed)
            finally:
                self._close_client(c)

        worker = _TaskWorker(do_upload)

        def on_progress(current, total):
            progress.setMaximum(total)
            progress.setValue(current)
            progress.setLabelText(f"Uploaded {current} of {total} actions...")

        def on_upload_finished(result):
            progress.close()
            worker.deleteLater()
            if isinstance(result, Exception):
                if isinstance(result, UploadError):
                    self._show_upload_failure(result)
                else:
                    QMessageBox.critical(self, "Upload Error", f"Failed to upload device config: {result}")
                return
            self.statusBar().showMessage(f"Uploaded {result} changed actions to {module.name}")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_upload_finished)
        worker.start()

    def _show_upload_failure(self, error):
        details = error.details if hasattr(error, "details") else {"error": str(error)}
        try:
            import json

            details_text = json.dumps(details, indent=2, sort_keys=True, default=str)
        except Exception:
            details_text = "\n".join(f"{key}: {value}" for key, value in details.items())
        dialog = ErrorDetailsDialog(
            "Upload Failed",
            "Upload stopped. Power-cycle or restart the failed device, then retry.",
            details_text,
            self,
        )
        dialog.exec_()

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
            "<p>Version 0.2.1</p>"
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
