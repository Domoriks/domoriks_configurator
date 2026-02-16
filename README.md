# EventAction Configurator

A professional home automation event configuration tool with bidirectional C-code ↔ GUI conversion.

## Features

- **Bidirectional Conversion**: GUI ↔ C code
- **Multi-Device Support**: Configure multiple devices in one project
- **Config File Management**: Load/save light point configurations
- **User-Friendly Qt Interface**: Modern, intuitive design
- **Input Validation**: Prevents configuration errors
- **Undo/Redo Support**: Safe editing experience
- **Export/Import**: Share configurations easily

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python src/main.py
```

## Project Structure

```
event_action_config/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/
│   │   ├── main_window.py   # Main application window
│   │   ├── device_widget.py # Device configuration widget
│   │   └── dialogs.py       # Configuration dialogs
│   ├── models/
│   │   ├── event_action.py  # EventAction data model
│   │   ├── device.py        # Device model
│   │   └── project.py       # Project model
│   └── utils/
│       ├── parser.py        # C code parser
│       ├── generator.py     # C code generator
│       └── config.py        # Config file handler
├── config/
│   ├── default_config.json  # Default light points
│   └── example_project.json # Example project
├── tests/
│   └── test_parser.py       # Unit tests
└── docs/
    └── user_guide.md        # User documentation
```

## Usage

### Basic Workflow

1. **Create New Project**: File → New Project
2. **Add Devices**: Add device configurations
3. **Configure Events**: Set up button press actions
4. **Export C Code**: Generate firmware configuration
5. **Import C Code**: Parse existing firmware code

### Configuration Format

Light points configuration (JSON):
```json
{
  "light_points": {
    "l32_inkom": [64, 0],
    "l33_led_trap_beneden": [64, 1]
  }
}
```

## Bug Fixes from Original

1. Missing brightness field handling
2. No validation on numeric inputs
3. Inconsistent extraActionIndex handling
4. No error handling for invalid light points
5. GUI layout issues with large configurations
6. No support for loading existing configurations


