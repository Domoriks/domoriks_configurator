"""
Dialog windows for various configuration tasks.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QMessageBox, QFileDialog,
                             QLineEdit, QSpinBox, QFormLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QWidget, QListWidget, QSizePolicy)
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

        form = QFormLayout()
        self.name_edit = QLineEdit(self.module.name if self.module else "")
        self.name_edit.textChanged.connect(self._apply_changes)
        form.addRow("Module Name:", self.name_edit)

        self.node_spin = QSpinBox()
        self.node_spin.setRange(0, 65535)
        self.node_spin.setValue(getattr(self.module, 'node', 0) or 0)
        self.node_spin.valueChanged.connect(self._apply_changes)
        form.addRow("Node:", self.node_spin)
        root.addLayout(form)

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

        def _channel(value):
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                return value[1]
            return value

        items = list(outputs.items())
        try:
            items.sort(key=lambda kv: _safe_int(_channel(kv[1])))
        except Exception:
            items.sort(key=lambda kv: kv[0].lower())

        for row, (name, value) in enumerate(items):
            channel = _channel(value)
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
        self.module.name = self.name_edit.text()
        self.module.node = int(self.node_spin.value())
        outputs = self._get_outputs_from_table(silent=True)
        if outputs is not None:
            self.module.outputs = outputs
            self.module.num_outputs = len(outputs)
        self.saved.emit(self.module)

    def _get_outputs_from_table(self, silent=False):
        outputs = {}
        node = self.node_spin.value()
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
                outputs[name] = [node, channel]
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
        self.name_edit.setText(module.name if module else "")
        self.node_spin.setValue(getattr(module, 'node', 0) or 0)
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
        self.node_spin.setRange(0, 65535)
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
