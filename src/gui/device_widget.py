"""
Device configuration widget for editing event actions.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QComboBox, QSpinBox, QPushButton,
                             QLabel, QGroupBox, QTabWidget, QLineEdit, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from models.device import Device
from models.event_action import EventAction

class DeviceWidget(QWidget):
    """Widget for configuring a single device."""
    
    device_modified = pyqtSignal()
    
    def __init__(self, device, light_points, parent=None):
        super().__init__(parent)
        self.device = device
        self.light_points = light_points
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        
        # Device name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Device Name:"))
        self.name_edit = QLineEdit(self.device.name)
        self.name_edit.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # Tab widget for inputs and extra actions
        tabs = QTabWidget()
        
        # Input actions tab
        input_widget = self.create_input_widget()
        tabs.addTab(input_widget, "Input Actions")
        
        # Extra actions tab
        extra_widget = self.create_extra_actions_widget()
        tabs.addTab(extra_widget, "Extra Actions")
        
        layout.addWidget(tabs)
        
        self.setLayout(layout)
    
    def on_name_changed(self):
        """Handle device name change."""
        self.device.name = self.name_edit.text()
        self.device_modified.emit()
    
    def create_input_widget(self):
        """Create widget for input actions."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Create table for input actions
        self.input_table = QTableWidget()
        self.input_table.setColumnCount(7)
        self.input_table.setHorizontalHeaderLabels([
            "Input", "Press Type", "Action", "Delay Action", 
            "Light Point", "Delay (ms)", "Extra Action #"
        ])
        
        # Calculate rows (num_inputs * 3 press types)
        num_rows = self.device.num_inputs * 3
        self.input_table.setRowCount(num_rows)
        
        # Populate table
        row = 0
        for i in range(1, self.device.num_inputs + 1):
            for press in Device.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                action = self.device.input_actions[action_name]
                
                # Input number (read-only)
                self.input_table.setItem(row, 0, QTableWidgetItem(str(i)))
                self.input_table.item(row, 0).setFlags(Qt.ItemIsEnabled)
                
                # Press type (read-only)
                press_display = press.replace("Press", " Press")
                self.input_table.setItem(row, 1, QTableWidgetItem(press_display))
                self.input_table.item(row, 1).setFlags(Qt.ItemIsEnabled)
                
                # Action combo
                action_combo = QComboBox()
                action_combo.addItems(EventAction.ACTIONS)
                action_combo.setCurrentText(action.action)
                action_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r)
                )
                self.input_table.setCellWidget(row, 2, action_combo)
                
                # Delay action combo
                delay_combo = QComboBox()
                delay_combo.addItems(EventAction.ACTIONS)
                delay_combo.setCurrentText(action.delay_action)
                delay_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r)
                )
                self.input_table.setCellWidget(row, 3, delay_combo)
                
                # Light point combo
                light_combo = QComboBox()
                light_combo.addItem("(None)")
                light_combo.addItems(sorted(self.light_points.keys()))
                light_name = action.get_light_point_name(self.light_points)
                if light_name:
                    light_combo.setCurrentText(light_name)
                light_combo.currentTextChanged.connect(
                    lambda text, r=row: self.on_input_changed(r)
                )
                self.input_table.setCellWidget(row, 4, light_combo)
                
                # Delay spinbox
                delay_spin = QSpinBox()
                delay_spin.setRange(0, 3600000)  # Up to 1 hour
                delay_spin.setSingleStep(100)
                delay_spin.setValue(action.delay)
                delay_spin.valueChanged.connect(
                    lambda val, r=row: self.on_input_changed(r)
                )
                self.input_table.setCellWidget(row, 5, delay_spin)
                
                # Extra action index
                extra_spin = QSpinBox()
                extra_spin.setRange(0, self.device.num_extra_actions)
                extra_spin.setValue(action.extra_action_index)
                extra_spin.valueChanged.connect(
                    lambda val, r=row: self.on_input_changed(r)
                )
                self.input_table.setCellWidget(row, 6, extra_spin)
                
                row += 1
        
        # Resize columns to content
        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.input_table.horizontalHeader().setStretchLastSection(False)
        
        layout.addWidget(self.input_table)
        widget.setLayout(layout)
        return widget
    
    def create_extra_actions_widget(self):
        """Create widget for extra actions."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Create table for extra actions
        self.extra_table = QTableWidget()
        self.extra_table.setColumnCount(7)
        self.extra_table.setHorizontalHeaderLabels([
            "#", "Action", "Delay Action", "Light Point", 
            "Delay (ms)", "Extra Action #", "Clear"
        ])
        
        self.extra_table.setRowCount(self.device.num_extra_actions)
        
        # Populate table
        for i in range(1, self.device.num_extra_actions + 1):
            row = i - 1
            action_name = f"extraAction{i}"
            action = self.device.extra_actions[action_name]
            
            # Action number (read-only)
            self.extra_table.setItem(row, 0, QTableWidgetItem(str(i)))
            self.extra_table.item(row, 0).setFlags(Qt.ItemIsEnabled)
            
            # Action combo
            action_combo = QComboBox()
            action_combo.addItems(EventAction.ACTIONS)
            action_combo.setCurrentText(action.action)
            action_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r)
            )
            self.extra_table.setCellWidget(row, 1, action_combo)
            
            # Delay action combo
            delay_combo = QComboBox()
            delay_combo.addItems(EventAction.ACTIONS)
            delay_combo.setCurrentText(action.delay_action)
            delay_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r)
            )
            self.extra_table.setCellWidget(row, 2, delay_combo)
            
            # Light point combo
            light_combo = QComboBox()
            light_combo.addItem("(None)")
            light_combo.addItems(sorted(self.light_points.keys()))
            light_name = action.get_light_point_name(self.light_points)
            if light_name:
                light_combo.setCurrentText(light_name)
            light_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_extra_changed(r)
            )
            self.extra_table.setCellWidget(row, 3, light_combo)
            
            # Delay spinbox
            delay_spin = QSpinBox()
            delay_spin.setRange(0, 3600000)
            delay_spin.setSingleStep(100)
            delay_spin.setValue(action.delay)
            delay_spin.valueChanged.connect(
                lambda val, r=row: self.on_extra_changed(r)
            )
            self.extra_table.setCellWidget(row, 4, delay_spin)
            
            # Extra action index
            extra_spin = QSpinBox()
            extra_spin.setRange(0, self.device.num_extra_actions)
            extra_spin.setValue(action.extra_action_index)
            extra_spin.valueChanged.connect(
                lambda val, r=row: self.on_extra_changed(r)
            )
            self.extra_table.setCellWidget(row, 5, extra_spin)
            
            # Clear button
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, r=row: self.clear_extra_action(r))
            self.extra_table.setCellWidget(row, 6, clear_btn)
        
        # Resize columns
        self.extra_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(self.extra_table)
        widget.setLayout(layout)
        return widget
    
    def on_input_changed(self, row):
        """Handle input action change."""
        # Calculate input number and press type
        input_num = (row // 3) + 1
        press_idx = row % 3
        press = Device.PRESS_TYPES[press_idx]
        action_name = f"input{input_num}_{press}"
        
        # Get values from table
        action_combo = self.input_table.cellWidget(row, 2)
        delay_combo = self.input_table.cellWidget(row, 3)
        light_combo = self.input_table.cellWidget(row, 4)
        delay_spin = self.input_table.cellWidget(row, 5)
        extra_spin = self.input_table.cellWidget(row, 6)
        
        # Update action
        action = self.device.input_actions[action_name]
        action.action = action_combo.currentText()
        action.delay_action = delay_combo.currentText()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()
        
        # Update light point
        light_name = light_combo.currentText()
        if light_name != "(None)" and light_name in self.light_points:
            action.node, action.output = self.light_points[light_name]
        else:
            action.node, action.output = 0, 0
        
        self.device_modified.emit()
    
    def on_extra_changed(self, row):
        """Handle extra action change."""
        action_name = f"extraAction{row + 1}"
        
        # Get values from table
        action_combo = self.extra_table.cellWidget(row, 1)
        delay_combo = self.extra_table.cellWidget(row, 2)
        light_combo = self.extra_table.cellWidget(row, 3)
        delay_spin = self.extra_table.cellWidget(row, 4)
        extra_spin = self.extra_table.cellWidget(row, 5)
        
        # Update action
        action = self.device.extra_actions[action_name]
        action.action = action_combo.currentText()
        action.delay_action = delay_combo.currentText()
        action.delay = delay_spin.value()
        action.extra_action_index = extra_spin.value()
        
        # Update light point
        light_name = light_combo.currentText()
        if light_name != "(None)" and light_name in self.light_points:
            action.node, action.output = self.light_points[light_name]
        else:
            action.node, action.output = 0, 0
        
        self.device_modified.emit()
    
    def clear_extra_action(self, row):
        """Clear an extra action."""
        action_name = f"extraAction{row + 1}"
        
        # Reset to defaults
        action = EventAction(action_name)
        self.device.extra_actions[action_name] = action
        
        # Update widgets
        self.extra_table.cellWidget(row, 1).setCurrentText("nop")
        self.extra_table.cellWidget(row, 2).setCurrentText("nop")
        self.extra_table.cellWidget(row, 3).setCurrentIndex(0)
        self.extra_table.cellWidget(row, 4).setValue(0)
        self.extra_table.cellWidget(row, 5).setValue(0)
        
        self.device_modified.emit()
    
    def update_light_points(self, light_points):
        """Update light points configuration."""
        self.light_points = light_points
        # TODO: Refresh combo boxes
