"""
Dialog windows for various configuration tasks.
"""

import json
import difflib
from html import escape

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QLineEdit,
    QSpinBox,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QWidget,
    QListWidget,
    QSizePolicy,
    QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal


class ModuleEditorWidget(QWidget):
    """Widget for editing a single module (right-side editor).

    Changes apply immediately to the module model.
    """

    saved = pyqtSignal(object)

    def __init__(self, module=None, all_modules=None, parent=None):
        super().__init__(parent)
        self.module = module
        self.all_modules = list(all_modules) if all_modules else []
        self._updating = False
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout()

        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Module:"))
        self.name_label = QLabel(self.module.name if self.module else "")
        self.name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.name_label)
        info_layout.addSpacing(20)
        info_layout.addWidget(QLabel("Node:"))
        self.node_label = QLabel(str(self.module.node) if self.module else "")
        self.node_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.node_label)
        info_layout.addStretch()
        root.addLayout(info_layout)

        root.addWidget(QLabel("Inputs:"))
        self.inputs_table = QTableWidget()
        self.inputs_table.setColumnCount(1)
        self.inputs_table.setHorizontalHeaderLabels(["Input Channel"])
        self.inputs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.inputs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._populate_inputs()
        self.inputs_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.inputs_table)

        root.addWidget(QLabel("Outputs:"))
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Name", "Channel"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSortingEnabled(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.populate_table()
        root.addWidget(self.table, 1)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setLayout(root)

    def _populate_inputs(self):
        num = self.module.num_inputs if self.module else 0
        self.inputs_table.setRowCount(num)
        for i in range(num):
            self.inputs_table.setItem(i, 0, QTableWidgetItem(f"Input {i + 1}"))

    def populate_table(self):
        self._updating = True
        outputs = self.module.outputs if self.module else {}
        self.table.setRowCount(len(outputs))

        def _safe_int(v, fallback=float('inf')):
            try:
                return int(v)
            except Exception:
                return fallback

        items = list(outputs.items())
        try:
            items.sort(key=lambda kv: _safe_int(kv[1]))
        except Exception:
            items.sort(key=lambda kv: kv[0].lower())

        for row, (name, channel) in enumerate(items):
            name_item = QTableWidgetItem(name)
            channel_item = QTableWidgetItem(str(channel))
            try:
                channel_item.setData(Qt.EditRole, int(channel))
            except Exception:
                pass
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, channel_item)
        self._updating = False

    def _on_table_item_changed(self, item):
        if not self._updating:
            self._apply_changes()

    def _apply_changes(self):
        if self._updating or not self.module:
            return
        outputs = self._get_outputs_from_table(silent=True)
        self.module.outputs = outputs
        self.module.num_outputs = len(outputs)
        self.saved.emit(self.module)

    def _get_outputs_from_table(self, silent=False):
        outputs = {}
        channels_seen = set()
        for row in range(self.table.rowCount()):
            try:
                name = self.table.item(row, 0).text()
                channel = int(self.table.item(row, 1).text())
                if not name:
                    if not silent:
                        QMessageBox.warning(self, "Invalid Data", f"Row {row + 1}: Name cannot be empty.")
                    return None
                if channel in channels_seen:
                    if not silent:
                        QMessageBox.warning(
                            self, "Duplicate Channel",
                            f"Row {row + 1}: Channel {channel} is already used by another output.\n"
                            f"Each output must have a unique channel number."
                        )
                    return None
                channels_seen.add(channel)
                outputs[name] = channel
            except (ValueError, AttributeError):
                if not silent:
                    QMessageBox.warning(
                        self, "Invalid Data",
                        f"Row {row + 1}: Ensure all fields are valid (integer for Channel)."
                    )
                return None
        return outputs

    def set_module(self, module):
        self._updating = True
        self.module = module
        self.name_label.setText(module.name if module else "")
        self.node_label.setText(str(module.node) if module else "")
        self._populate_inputs()
        self.populate_table()
        self._updating = False

class CCodeImportDialog(QDialog):
    """Dialog for importing C code."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import C Code")
        self.setMinimumSize(700, 500)
        self.c_code = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        label = QLabel("Paste your EventAction C code below:")
        layout.addWidget(label)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };\n"
            "EventAction input1_doublePress = { toggle, nop, 0, 100, 64, 1, 0, 0 };"
        )
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load from File...")
        load_btn.clicked.connect(self.load_from_file)
        button_layout.addWidget(load_btn)
        
        button_layout.addStretch()
        
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate_code)
        button_layout.addWidget(validate_btn)
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.accept)
        button_layout.addWidget(import_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_from_file(self):
        """Load C code from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open C File", "", "C Files (*.c *.h);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    self.text_edit.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
    
    def validate_code(self):
        """Validate the C code."""
        from utils.parser import CCodeParser
        
        code = self.text_edit.toPlainText()
        errors = CCodeParser.validate_c_code(code)
        
        if errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "Found validation errors:\n\n" + "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self, "Validation Successful",
                "C code is valid and ready to import!"
            )
    
    def get_c_code(self):
        """Get the entered C code."""
        return self.text_edit.toPlainText()


class CCodeExportDialog(QDialog):
    """Dialog for exporting C code."""
    
    def __init__(self, c_code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export C Code")
        self.setMinimumSize(700, 500)
        self.c_code = c_code
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        label = QLabel("Generated C code:")
        layout.addWidget(label)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.c_code)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        save_btn = QPushButton("Save to File...")
        save_btn.clicked.connect(self.save_to_file)
        button_layout.addWidget(save_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def copy_to_clipboard(self):
        """Copy C code to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.c_code)
        QMessageBox.information(self, "Success", "C code copied to clipboard!")
    
    def save_to_file(self):
        """Save C code to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save C File", "", "C Files (*.c *.h);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(self.c_code)
                QMessageBox.information(self, "Success", "C code saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")


class ModuleDialog(QDialog):
    """Dialog for creating or editing a module."""
    
    def __init__(self, module=None, parent=None):
        super().__init__(parent)
        self._module = module
        self._editing = module is not None
        self.setWindowTitle("Edit Module" if self._editing else "New Module")
        self.setMinimumWidth(300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit(self._module.name if self._module else "New Module")
        layout.addRow("Module Name:", self.name_edit)
        
        self.inputs_spin = QSpinBox()
        self.inputs_spin.setRange(0, 16)
        self.inputs_spin.setValue(self._module.num_inputs if self._module else 4)
        layout.addRow("Number of Inputs:", self.inputs_spin)
        
        self.extras_spin = QSpinBox()
        self.extras_spin.setRange(0, 50)
        self.extras_spin.setValue(self._module.num_extra_actions if self._module else 20)
        layout.addRow("Extra Actions:", self.extras_spin)

        self.outputs_spin = QSpinBox()
        self.outputs_spin.setRange(0, 16)
        self.outputs_spin.setValue(self._module.num_outputs if self._module else 0)
        layout.addRow("Number of Outputs:", self.outputs_spin)
        
        self.node_spin = QSpinBox()
        self.node_spin.setRange(0, 255)
        self.node_spin.setValue(self._module.node if self._module else 64)
        layout.addRow("Node:", self.node_spin)
        
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Save" if self._editing else "Create")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def get_module_config(self):
        """Get the module configuration."""
        return {
            "name": self.name_edit.text(),
            "num_inputs": self.inputs_spin.value(),
            "num_extra_actions": self.extras_spin.value(),
            "num_outputs": self.outputs_spin.value(),
            "node": self.node_spin.value()
        }


class ApiSettingsDialog(QDialog):
    """Dialog for API base URL and token settings."""

    def __init__(self, base_url="", token="", token_session_only=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Settings")
        self.setMinimumWidth(520)
        self._token_session_only = bool(token_session_only)
        self.setup_ui(base_url, token)

    def setup_ui(self, base_url, token):
        layout = QFormLayout()

        self.base_url_edit = QLineEdit(base_url or "")
        self.base_url_edit.setPlaceholderText("http://homeassistant.local:8123")
        layout.addRow("Base URL:", self.base_url_edit)

        self.token_edit = QLineEdit(token or "")
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.token_edit.setPlaceholderText("Long-lived access token")
        layout.addRow("API Token:", self.token_edit)

        self.session_only_check = QCheckBox("Session only: do not overwrite token in saved JSON")
        self.session_only_check.setChecked(self._token_session_only)
        layout.addRow("", self.session_only_check)

        button_layout = QHBoxLayout()
        self.clean_button = QPushButton("Clean Token")
        self.clean_button.clicked.connect(self._clean_token)
        button_layout.addWidget(self.clean_button)

        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        root = QVBoxLayout()
        root.addLayout(layout)
        root.addLayout(button_layout)
        self.setLayout(root)

    def _clean_token(self):
        self.token_edit.clear()

    def get_settings(self):
        return {
            "base_url": self.base_url_edit.text().strip(),
            "token": self.token_edit.text().strip(),
            "token_session_only": self.session_only_check.isChecked(),
        }


class BusDetectDialog(QDialog):
    """Collect detect range and timeout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detect Bus")
        self.setMinimumWidth(360)
        layout = QFormLayout()

        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 255)
        self.start_spin.setValue(0)
        layout.addRow("Start slave:", self.start_spin)

        self.end_spin = QSpinBox()
        self.end_spin.setRange(0, 255)
        self.end_spin.setValue(255)
        layout.addRow("End slave:", self.end_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 30000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" ms")
        layout.addRow("Timeout:", self.timeout_spin)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Detect")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        root = QVBoxLayout()
        root.addLayout(layout)
        root.addLayout(button_layout)
        self.setLayout(root)

    def get_values(self):
        return {
            "start_slave": self.start_spin.value(),
            "end_slave": self.end_spin.value(),
            "timeout": self.timeout_spin.value() / 1000.0,
        }


class JsonSideBySideDiffDialog(QDialog):
    """Show side-by-side colored JSON diff with accept/deny and byte-order toggle."""

    def __init__(self, left_title, right_title, left_json, right_json, parent=None,
                 refresh_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Review Device Config")
        self.setMinimumSize(1200, 700)
        self._left_title = left_title
        self._right_title = right_title
        self._refresh_callback = refresh_callback
        self.device_actions = None

        self.left_view = QTextEdit()
        self.left_view.setReadOnly(True)

        self.right_view = QTextEdit()
        self.right_view.setReadOnly(True)

        self._update_diff(left_json, right_json)

        splitter = QSplitter()
        splitter.addWidget(self.left_view)
        splitter.addWidget(self.right_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        button_layout = QHBoxLayout()
        deny_btn = QPushButton("Deny")
        deny_btn.clicked.connect(self.reject)
        button_layout.addWidget(deny_btn)

        if refresh_callback:
            button_layout.addStretch()
            button_layout.addWidget(QLabel("Byte Order:"))
            self.byte_order_combo = QComboBox()
            self.byte_order_combo.addItems(["Auto Detect", "Standard (new FW)", "Swapped (old FW)"])
            self.byte_order_combo.setToolTip("Change byte order and re-read device registers")
            self.byte_order_combo.currentIndexChanged.connect(self._on_byte_order_changed)
            button_layout.addWidget(self.byte_order_combo)

        button_layout.addStretch()
        accept_btn = QPushButton("Accept")
        accept_btn.clicked.connect(self.accept)
        button_layout.addWidget(accept_btn)

        root = QVBoxLayout()
        root.addWidget(splitter)
        root.addLayout(button_layout)
        self.setLayout(root)

    def _update_diff(self, left_json, right_json):
        left_html, right_html = _json_side_by_side_html(
            left_json, right_json, self._left_title, self._right_title
        )
        self.left_view.setHtml(left_html)
        self.right_view.setHtml(right_html)

    def _on_byte_order_changed(self, index):
        if not self._refresh_callback:
            return
        byte_swap_map = {0: None, 1: False, 2: True}
        byte_swap = byte_swap_map[index]
        try:
            left_json, right_json, actions = self._refresh_callback(byte_swap)
            self.device_actions = actions
            self._update_diff(left_json, right_json)
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to re-read device: {e}")


class ErrorDetailsDialog(QDialog):
    """Show detailed error message with copy support."""

    def __init__(self, title, message, details_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(820, 520)
        self._details_text = details_text

        root = QVBoxLayout()
        root.addWidget(QLabel(message))

        self.details_edit = QTextEdit()
        self.details_edit.setReadOnly(True)
        self.details_edit.setPlainText(details_text)
        root.addWidget(self.details_edit, 1)

        button_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy Details")
        copy_btn.clicked.connect(self.copy_details)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        root.addLayout(button_layout)

        self.setLayout(root)

    def copy_details(self):
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(self._details_text)


class DetectResultsDialog(QDialog):
    """Show bus detect results and allow adding missing devices."""

    add_requested = pyqtSignal(int)

    def __init__(self, reachable, unreachable, project_nodes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bus Detect Results")
        self.setMinimumSize(760, 520)
        self._project_nodes = set(int(v) for v in (project_nodes or []))

        root = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Slave", "Status", "In Project", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        rows = []
        for slave in reachable:
            rows.append((int(slave), True))
        for slave in unreachable:
            rows.append((int(slave), False))
        rows.sort(key=lambda item: item[0])
        self.table.setRowCount(len(rows))

        for row, (slave, is_reachable) in enumerate(rows):
            in_project = slave in self._project_nodes
            self.table.setItem(row, 0, QTableWidgetItem(str(slave)))
            self.table.setItem(row, 1, QTableWidgetItem("Reachable" if is_reachable else "Not responding"))
            self.table.setItem(row, 2, QTableWidgetItem("Yes" if in_project else "No"))
            action_btn = QPushButton("Add device" if not in_project else "In project")
            action_btn.setEnabled(not in_project and is_reachable)
            action_btn.clicked.connect(lambda checked=False, s=slave: self.add_requested.emit(s))
            self.table.setCellWidget(row, 3, action_btn)

        root.addWidget(self.table)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)
        self.setLayout(root)


def _json_diff_html(value, highlight="none", title="JSON"):
    text = json.dumps(value, indent=2)
    lines = []
    for raw_line in text.splitlines():
        safe = escape(raw_line)
        if highlight == "removed":
            safe = f'<span style="background:#3a1515;color:#ffb3b3;">{safe}</span>'
        elif highlight == "added":
            safe = f'<span style="background:#153a15;color:#bfffc0;">{safe}</span>'
        lines.append(safe)
    body = "<br>".join(lines)
    return (
        f"<html><body style='font-family:monospace; white-space:pre; background:#111; color:#eee;'>"
        f"<h3 style='color:#ddd;'>{escape(title)}</h3><pre>{body}</pre></body></html>"
    )


def _json_side_by_side_html(left_value, right_value, left_title, right_title):
    left_text = json.dumps(left_value, indent=2).splitlines()
    right_text = json.dumps(right_value, indent=2).splitlines()

    matcher = difflib.SequenceMatcher(None, left_text, right_text)
    left_lines = []
    right_lines = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for left_line, right_line in zip(left_text[i1:i2], right_text[j1:j2]):
                left_lines.append(_line_html(left_line))
                right_lines.append(_line_html(right_line))
        elif tag == "replace":
            left_chunk = left_text[i1:i2]
            right_chunk = right_text[j1:j2]
            max_len = max(len(left_chunk), len(right_chunk))
            for idx in range(max_len):
                if idx < len(left_chunk):
                    left_lines.append(_line_html(left_chunk[idx], "removed"))
                else:
                    left_lines.append(_line_html("", "removed"))
                if idx < len(right_chunk):
                    right_lines.append(_line_html(right_chunk[idx], "added"))
                else:
                    right_lines.append(_line_html("", "added"))
        elif tag == "delete":
            for left_line in left_text[i1:i2]:
                left_lines.append(_line_html(left_line, "removed"))
        elif tag == "insert":
            for right_line in right_text[j1:j2]:
                right_lines.append(_line_html(right_line, "added"))

    max_len = max(len(left_lines), len(right_lines))
    while len(left_lines) < max_len:
        left_lines.append(_line_html(""))
    while len(right_lines) < max_len:
        right_lines.append(_line_html(""))

    left_body = "<br>".join(left_lines)
    right_body = "<br>".join(right_lines)
    return (
        f"<html><body style='font-family:monospace; white-space:pre; background:#111; color:#eee;'>"
        f"<h3 style='color:#ddd;'>{escape(left_title)}</h3><pre>{left_body}</pre></body></html>",
        f"<html><body style='font-family:monospace; white-space:pre; background:#111; color:#eee;'>"
        f"<h3 style='color:#ddd;'>{escape(right_title)}</h3><pre>{right_body}</pre></body></html>"
    )


def _line_html(line, state="equal"):
    safe = escape(line)
    if state == "removed":
        return f'<span style="background:#3a1515;color:#ffb3b3;">{safe}</span>'
    if state == "added":
        return f'<span style="background:#153a15;color:#bfffc0;">{safe}</span>'
    return safe
