"""
Module configuration widget for editing event actions.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QComboBox, QSpinBox, QPushButton,
                             QLabel, QGroupBox, QTabWidget, QLineEdit, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from models.module import Module
from models.event_action import EventAction


class ModuleWidget(QWidget):
    """Widget for configuring a single module's actions."""

    module_modified = pyqtSignal()

    def __init__(self, module, parent=None):
        super().__init__(parent)
        self.module = module
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Module Name:"))
        self.name_edit = QLineEdit(self.module.name)
        self.name_edit.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)

        tabs = QTabWidget()
        input_widget = self.create_input_widget()
        tabs.addTab(input_widget, "Input Actions")
        extra_widget = self.create_extra_actions_widget()
        tabs.addTab(extra_widget, "Extra Actions")

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _sorted_light_point_names(self):
        def _name_key(n):
            try:
                return (0, int(n))
            except Exception:
                return (1, n.lower())

        def _safe_int(value, fallback=float('inf')):
            try:
                return int(value)
            except Exception:
                return fallback

        def _name_sort_key(n):
            node = self.module.outputs[n][0]
            output = self.module.outputs[n][1]
            return (_safe_int(node), _safe_int(output), _name_key(n))

        def _fallback_name_key(n):
            return _name_key(n)

        names = list(self.module.outputs.keys())
        try:
            names.sort(key=_name_sort_key)
        except Exception:
            names.sort(key=_fallback_name_key)
        return names

    def on_name_changed(self):
        self.module.name = self.name_edit.text()
        self.module_modified.emit()

    def create_input_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.input_table = QTableWidget()
        self.input_table.setColumnCount(7)
        self.input_table.setHorizontalHeaderLabels([
            "Input", "Press Type", "Action", "Delay Action",
            "Light Point", "Delay (ms)", "Extra Action #"
        ])

        num_rows = self.module.num_inputs * 3
        self.input_table.setRowCount(num_rows)

        row = 0
        for i in range(1, self.module.num_inputs + 1):
            for press in Module.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                action = self.module.input_actions[action_name]

                self.input_table.setItem(row, 0, QTableWidgetItem(str(i)))
                self.input_table.item(row, 0).setFlags(Qt.ItemIsEnabled)

                press_display = press.replace("Press", " Press")
                self.input_table.setItem(row, 1, QTableWidgetItem(press_display))
                self.input_table.item(row, 1).setFlags(Qt.ItemIsEnabled)

                action_combo = QComboBox()
                action_combo.addItems(EventAction.ACTIONS)
                action_combo.setCurrentText(action.action)
                action_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 2, action_combo)

                delay_combo = QComboBox()
                delay_combo.addItems(EventAction.ACTIONS)
                delay_combo.setCurrentText(action.delay_action)
                delay_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 3, delay_combo)

                light_combo = QComboBox()
                light_combo.addItem("(None)")
                light_combo.addItems(self._sorted_light_point_names())
                light_name = action.get_light_point_name(self.module.outputs)
                if light_name:
                    light_combo.setCurrentText(light_name)
                light_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 4, light_combo)

                delay_spin = QSpinBox()
                delay_spin.setRange(0, 3600000)
                delay_spin.setSingleStep(100)
                delay_spin.setValue(action.delay)
                delay_spin.valueChanged.connect(
                    lambda val, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 5, delay_spin)

                extra_spin = QSpinBox()
                extra_spin.setRange(0, self.module.num_extra_actions)
                extra_spin.setValue(action.extra_action_index)
                extra_spin.valueChanged.connect(
                    lambda val, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 6, extra_spin)

                row += 1

        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.input_table.horizontalHeader().setStretchLastSection(False)

        layout.addWidget(self.input_table)
        widget.setLayout(layout)
        return widget

    def create_extra_actions_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.extra_table = QTableWidget()
        self.extra_table.setColumnCount(7)
        self.extra_table.setHorizontalHeaderLabels([
            "#", "Action", "Delay Action", "Light Point",
            "Delay (ms)", "Extra Action #", "Clear"
        ])
        self.extra_table.setRowCount(self.module.num_extra_actions)

        for i in range(1, self.module.num_extra_actions + 1):
            row = i - 1
            action_name = f"extraAction{i}"
            action = self.module.extra_actions[action_name]

            self.extra_table.setItem(row, 0, QTableWidgetItem(str(i)))
            self.extra_table.item(row, 0).setFlags(Qt.ItemIsEnabled)

            action_combo = QComboBox()
            action_combo.addItems(EventAction.ACTIONS)
            action_combo.setCurrentText(action.action)
            action_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 1, action_combo)

            delay_combo = QComboBox()
            delay_combo.addItems(EventAction.ACTIONS)
            delay_combo.setCurrentText(action.delay_action)
            delay_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 2, delay_combo)

            light_combo = QComboBox()
            light_combo.addItem("(None)")
            light_combo.addItems(self._sorted_light_point_names())
            light_name = action.get_light_point_name(self.module.outputs)
            if light_name:
                light_combo.setCurrentText(light_name)
            light_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 3, light_combo)

            delay_spin = QSpinBox()
            delay_spin.setRange(0, 3600000)
            delay_spin.setSingleStep(100)
            delay_spin.setValue(action.delay)
            delay_spin.valueChanged.connect(
                lambda val, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 4, delay_spin)

            extra_spin = QSpinBox()
            extra_spin.setRange(0, self.module.num_extra_actions)
            extra_spin.setValue(action.extra_action_index)
            extra_spin.valueChanged.connect(
                lambda val, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 5, extra_spin)

            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, r=row: self.clear_extra_action(r))
            self.extra_table.setCellWidget(row, 6, clear_btn)

        self.extra_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        layout.addWidget(self.extra_table)
        widget.setLayout(layout)
        return widget

    def on_input_changed(self, row):
        input_num = (row // 3) + 1
        press_idx = row % 3
        press = Module.PRESS_TYPES[press_idx]
        action_name = f"input{input_num}_{press}"

        action_combo = self.input_table.cellWidget(row, 2)
        delay_combo = self.input_table.cellWidget(row, 3)
        light_combo = self.input_table.cellWidget(row, 4)
        delay_spin = self.input_table.cellWidget(row, 5)
        extra_spin = self.input_table.cellWidget(row, 6)

        action = self.module.input_actions[action_name]
        action.action = action_combo.currentText()
        action.delay_action = delay_combo.currentText()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()

        light_name = light_combo.currentText()
        if light_name != "(None)" and light_name in self.module.outputs:
            action.node, action.output = self.module.outputs[light_name]
        else:
            action.node, action.output = 0, 0

        self.module_modified.emit()

    def on_extra_changed(self, row):
        action_name = f"extraAction{row + 1}"

        action_combo = self.extra_table.cellWidget(row, 1)
        delay_combo = self.extra_table.cellWidget(row, 2)
        light_combo = self.extra_table.cellWidget(row, 3)
        delay_spin = self.extra_table.cellWidget(row, 4)
        extra_spin = self.extra_table.cellWidget(row, 5)

        action = self.module.extra_actions[action_name]
        action.action = action_combo.currentText()
        action.delay_action = delay_combo.currentText()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()

        light_name = light_combo.currentText()
        if light_name != "(None)" and light_name in self.module.outputs:
            action.node, action.output = self.module.outputs[light_name]
        else:
            action.node, action.output = 0, 0

        self.module_modified.emit()

    def clear_extra_action(self, row):
        action_name = f"extraAction{row + 1}"
        action = EventAction(action_name)
        self.module.extra_actions[action_name] = action

        self.extra_table.cellWidget(row, 1).setCurrentText("nop")
        self.extra_table.cellWidget(row, 2).setCurrentText("nop")
        self.extra_table.cellWidget(row, 3).setCurrentIndex(0)
        self.extra_table.cellWidget(row, 4).setValue(0)
        self.extra_table.cellWidget(row, 5).setValue(0)

        self.module_modified.emit()

    def update_outputs(self, outputs):
        self.module.outputs = outputs
        new_items = ["(None)"] + self._sorted_light_point_names()

        for row in range(self.input_table.rowCount()):
            combo = self.input_table.cellWidget(row, 4)
            if isinstance(combo, QComboBox):
                current_text = combo.currentText()
                combo.clear()
                combo.addItems(new_items)
                index = combo.findText(current_text)
                if index != -1:
                    combo.setCurrentIndex(index)
                else:
                    self.on_input_changed(row)

        for row in range(self.extra_table.rowCount()):
            combo = self.extra_table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                current_text = combo.currentText()
                combo.clear()
                combo.addItems(new_items)
                index = combo.findText(current_text)
                if index != -1:
                    combo.setCurrentIndex(index)
                else:
                    self.on_extra_changed(row)

    def rebuild_ui(self):
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
            # Remove the old layout so setup_ui can set a new one
            QWidget().setLayout(old_layout)
        self.setup_ui()
