"""
Module configuration widget for editing event actions.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QComboBox, QSpinBox, QPushButton,
                             QLabel, QGroupBox, QTabWidget, QLineEdit, QHeaderView,
                             QStyledItemDelegate, QStyleOptionViewItem)
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QPalette
from models.module import Module
from models.event_action import EventAction


class _OutputComboDelegate(QStyledItemDelegate):
    """Delegate that renders ' - nodeX' suffix in grey."""

    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole) or ""
        sep = " - "
        if sep in text and text != "(None)":
            parts = text.split(sep, 1)
            name_part = parts[0]
            suffix = sep + parts[1]

            # Draw selection/hover background
            self.initStyleOption(option, index)
            style = option.widget.style() if option.widget else None
            if style:
                style.drawPrimitive(style.PE_PanelItemViewItem, option, painter, option.widget)

            painter.save()
            rect = option.rect
            # Draw name part in normal color
            if option.state & 0x00004:  # QStyle.State_Selected
                painter.setPen(option.palette.color(QPalette.HighlightedText))
            else:
                painter.setPen(option.palette.color(QPalette.Text))
            name_rect = QRect(rect)
            name_rect.setLeft(rect.left() + 4)
            painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, name_part)

            # Draw suffix in grey
            fm = painter.fontMetrics()
            name_width = fm.horizontalAdvance(name_part)
            painter.setPen(QColor(150, 150, 150))
            suffix_rect = QRect(rect)
            suffix_rect.setLeft(rect.left() + 4 + name_width)
            painter.drawText(suffix_rect, Qt.AlignLeft | Qt.AlignVCenter, suffix)
            painter.restore()
        else:
            super().paint(painter, option, index)


class ModuleWidget(QWidget):
    """Widget for configuring a single module's actions."""

    module_modified = pyqtSignal()

    def __init__(self, module, all_modules=None, parent=None):
        super().__init__(parent)
        self.module = module
        self.all_modules = list(all_modules) if all_modules else []
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

    def _all_outputs(self):
        """Build combined outputs dict from all modules."""
        combined = {}
        combined.update(self.module.outputs)
        for m in self.all_modules:
            if m is not self.module:
                combined.update(m.outputs)
        return combined

    def _make_action_combo(self, current_value):
        combo = QComboBox()
        for a in EventAction.ACTIONS:
            combo.addItem(EventAction.ACTION_DISPLAY.get(a, a), a)
        idx = combo.findData(current_value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        return combo

    def _sorted_output_display_items(self):
        """Return list of (display_text, name, node, output) for all outputs across modules.

        Display text is 'name - nodeX' so user can see which module owns the output.
        """
        items = []
        seen = set()
        sources = [self.module] + [m for m in self.all_modules if m is not self.module]
        for m in sources:
            node = m.node
            for name, output_nr in m.outputs.items():
                key = (name, node, output_nr)
                if key not in seen:
                    seen.add(key)
                    display = f"{name} - node{node}"
                    items.append((display, name, node, output_nr))

        def _safe_int(v, fallback=float('inf')):
            try:
                return int(v)
            except Exception:
                return fallback

        items.sort(key=lambda t: (_safe_int(t[2]), _safe_int(t[3]), t[1].lower()))
        return items

    def _make_light_combo(self, current_node=0, current_output=0):
        """Create a light point combo populated with all outputs, with grey node suffix."""
        combo = QComboBox()
        delegate = _OutputComboDelegate(combo)
        combo.setItemDelegate(delegate)
        combo.addItem("(None)", None)
        items = self._sorted_output_display_items()
        selected_idx = 0
        for i, (display, name, node, output) in enumerate(items):
            combo.addItem(display, (node, output))
            if node == current_node and output == current_output and current_node != 0:
                selected_idx = i + 1  # +1 for (None)
        combo.setCurrentIndex(selected_idx)
        return combo

    def _resolve_combo_output(self, combo):
        """Get (node, output) from combo's current item data."""
        data = combo.currentData()
        if data is not None:
            return data
        return (0, 0)

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

                action_combo = self._make_action_combo(action.action)
                action_combo.currentIndexChanged.connect(
                    lambda idx, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 2, action_combo)

                delay_combo = self._make_action_combo(action.delay_action)
                delay_combo.currentIndexChanged.connect(
                    lambda idx, r=row: self.on_input_changed(r))
                self.input_table.setCellWidget(row, 3, delay_combo)

                light_combo = self._make_light_combo(action.node, action.output)
                light_combo.currentIndexChanged.connect(
                    lambda idx, r=row: self.on_input_changed(r))
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

            action_combo = self._make_action_combo(action.action)
            action_combo.currentIndexChanged.connect(
                lambda idx, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 1, action_combo)

            delay_combo = self._make_action_combo(action.delay_action)
            delay_combo.currentIndexChanged.connect(
                lambda idx, r=row: self.on_extra_changed(r))
            self.extra_table.setCellWidget(row, 2, delay_combo)

            light_combo = self._make_light_combo(action.node, action.output)
            light_combo.currentIndexChanged.connect(
                lambda idx, r=row: self.on_extra_changed(r))
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
        action.action = action_combo.currentData()
        action.delay_action = delay_combo.currentData()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()

        action.node, action.output = self._resolve_combo_output(light_combo)

        self.module_modified.emit()

    def on_extra_changed(self, row):
        action_name = f"extraAction{row + 1}"

        action_combo = self.extra_table.cellWidget(row, 1)
        delay_combo = self.extra_table.cellWidget(row, 2)
        light_combo = self.extra_table.cellWidget(row, 3)
        delay_spin = self.extra_table.cellWidget(row, 4)
        extra_spin = self.extra_table.cellWidget(row, 5)

        action = self.module.extra_actions[action_name]
        action.action = action_combo.currentData()
        action.delay_action = delay_combo.currentData()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()

        action.node, action.output = self._resolve_combo_output(light_combo)

        self.module_modified.emit()

    def clear_extra_action(self, row):
        action_name = f"extraAction{row + 1}"
        action = EventAction(action_name)
        self.module.extra_actions[action_name] = action

        self.extra_table.cellWidget(row, 1).setCurrentIndex(0)
        self.extra_table.cellWidget(row, 2).setCurrentIndex(0)
        self.extra_table.cellWidget(row, 3).setCurrentIndex(0)
        self.extra_table.cellWidget(row, 4).setValue(0)
        self.extra_table.cellWidget(row, 5).setValue(0)

        self.module_modified.emit()

    def update_outputs(self, outputs):
        self.module.outputs = outputs
        items = self._sorted_output_display_items()

        for row in range(self.input_table.rowCount()):
            combo = self.input_table.cellWidget(row, 4)
            if isinstance(combo, QComboBox):
                old_data = combo.currentData()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("(None)", None)
                selected = 0
                for i, (display, name, node, output) in enumerate(items):
                    combo.addItem(display, (node, output))
                    if old_data and old_data == (node, output):
                        selected = i + 1
                combo.setCurrentIndex(selected)
                combo.blockSignals(False)
                if selected == 0 and old_data:
                    self.on_input_changed(row)

        for row in range(self.extra_table.rowCount()):
            combo = self.extra_table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                old_data = combo.currentData()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("(None)", None)
                selected = 0
                for i, (display, name, node, output) in enumerate(items):
                    combo.addItem(display, (node, output))
                    if old_data and old_data == (node, output):
                        selected = i + 1
                combo.setCurrentIndex(selected)
                combo.blockSignals(False)
                if selected == 0 and old_data:
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
