"""
Dialog windows for various configuration tasks.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QMessageBox, QFileDialog,
                             QLineEdit, QSpinBox, QFormLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt

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


class NewDeviceDialog(QDialog):
    """Dialog for creating a new device."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Device")
        self.setMinimumWidth(300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout()
        
        # Device name
        self.name_edit = QLineEdit("New Device")
        layout.addRow("Device Name:", self.name_edit)
        
        # Number of inputs
        self.inputs_spin = QSpinBox()
        self.inputs_spin.setRange(1, 16)
        self.inputs_spin.setValue(4)
        layout.addRow("Number of Inputs:", self.inputs_spin)
        
        # Number of extra actions
        self.extras_spin = QSpinBox()
        self.extras_spin.setRange(0, 50)
        self.extras_spin.setValue(20)
        layout.addRow("Extra Actions:", self.extras_spin)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def get_device_config(self):
        """Get the device configuration."""
        return {
            "name": self.name_edit.text(),
            "num_inputs": self.inputs_spin.value(),
            "num_extra_actions": self.extras_spin.value()
        }


class LightPointsEditorDialog(QDialog):
    """Dialog for editing light points configuration."""
    
    def __init__(self, light_points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Light Points")
        self.setMinimumSize(600, 400)
        self.light_points = light_points.copy()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        label = QLabel("Edit light point configurations:")
        layout.addWidget(label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Node", "Output"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        self.populate_table()
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_light_point)
        button_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_btn)
        
        button_layout.addStretch()
        
        import_btn = QPushButton("Import from C...")
        import_btn.clicked.connect(self.import_from_c)
        button_layout.addWidget(import_btn)

        export_btn = QPushButton("Export to C...")
        export_btn.clicked.connect(self.export_to_c)
        button_layout.addWidget(export_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def populate_table(self):
        """Populate table with light points."""
        self.table.setRowCount(len(self.light_points))
        
        for row, (name, (node, output)) in enumerate(sorted(self.light_points.items())):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(node)))
            self.table.setItem(row, 2, QTableWidgetItem(str(output)))
    
    def add_light_point(self):
        """Add a new light point."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"new_light_{row}"))
        self.table.setItem(row, 1, QTableWidgetItem("64"))
        self.table.setItem(row, 2, QTableWidgetItem("0"))
    
    def remove_selected(self):
        """Remove selected light points."""
        selected = self.table.selectedIndexes()
        if selected:
            rows = sorted(set(index.row() for index in selected), reverse=True)
            for row in rows:
                self.table.removeRow(row)
    
    def import_from_c(self):
        """Import light points from C code."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Import Light Points from C")
        layout = QVBoxLayout()
        
        label = QLabel("Paste C code with light point definitions:")
        layout.addWidget(label)
        
        text_edit = QTextEdit()
        layout.addWidget(text_edit)
        
        button_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(import_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        def do_import():
            from utils.config import ConfigManager
            config_mgr = ConfigManager()
            imported = config_mgr.import_light_points_from_c(text_edit.toPlainText())
            if imported:
                self.light_points.update(imported)
                self.populate_table()
                dialog.accept()
                QMessageBox.information(
                    self, "Success",
                    f"Imported {len(imported)} light points"
                )
            else:
                QMessageBox.warning(
                    self, "No Data",
                    "No light point definitions found in C code"
                )
        
        import_btn.clicked.connect(do_import)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
    
    def _get_light_points_from_table(self):
        """Parse the table and return light points dictionary, or None on error."""
        light_points = {}
        for row in range(self.table.rowCount()):
            try:
                name = self.table.item(row, 0).text()
                node = int(self.table.item(row, 1).text())
                output = int(self.table.item(row, 2).text())

                if not name:
                    QMessageBox.warning(self, "Invalid Data", f"Row {row + 1}: Name cannot be empty.")
                    return None

                light_points[name] = [node, output]
            except (ValueError, AttributeError):
                QMessageBox.warning(
                    self, "Invalid Data",
                    f"Row {row + 1}: Ensure all fields are valid (integers for Node/Output)."
                )
                return None
        return light_points

    def export_to_c(self):
        """Export current light points to C code."""
        light_points = self._get_light_points_from_table()
        if light_points is None:
            return  # Error message shown in helper

        from utils.config import ConfigManager
        config_mgr = ConfigManager()
        c_code = config_mgr.export_light_points_to_c(light_points)

        dialog = CCodeExportDialog(c_code, self)
        dialog.exec_()

    def save_changes(self):
        """Save changes to light points."""
        new_light_points = self._get_light_points_from_table()
        if new_light_points is not None:
            self.light_points = new_light_points
            self.accept()
    
    def get_light_points(self):
        """Get the edited light points."""
        return self.light_points
