# Domoriks Configurator

**Version 0.2.1**

A professional home automation event configuration tool with bidirectional C-code ↔ GUI conversion.

## Features

- **Bidirectional Conversion**: GUI ↔ C code
- **Multi-Module Support**: Configure multiple modules in one project
- **Config File Management**: Load/save light point configurations
- **User-Friendly Qt Interface**: Modern Fusion-styled design
- **Input Validation**: Prevents configuration errors
- **Import/Export**: Import/export C code and module JSON per module or for all modules
- **C Code Parsing**: Parse and validate C code for EventAction declarations
- **Cross-Module Output References**: Action combos show outputs from all modules
- **Project Name in Title Bar**: Editable project name reflected in the window title

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python src/main.py
```

## Building

Build a standalone executable using PyInstaller.

### Windows

```bat
build.bat
```

Runs `PyInstaller --onefile --windowed` to produce `dist/Domoriks Configurator.exe`.

### Linux / macOS

```bash
chmod +x build.sh
./build.sh
```

Runs the same PyInstaller command with Linux/macOS path separators (`:` instead of `;` for `--add-data`). Output is `dist/Domoriks Configurator`.

### Setup (Linux / macOS)

`setup.sh` is a helper that checks Python 3, installs dependencies from `requirements.txt`, runs the test suite, and makes `src/main.py` executable. Run it once before building:

```bash
chmod +x setup.sh
./setup.sh
```

## Project Structure

```
app/
├── build.bat                # Build script (Windows)
├── build.sh                 # Build script (Linux / macOS)
├── setup.sh                 # Setup helper (Linux / macOS)
├── requirements.txt         # Python dependencies
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/
│   │   ├── main_window.py   # Main application window
│   │   ├── module_widget.py  # Module action configuration widget
│   │   └── dialogs.py       # Configuration dialogs
│   ├── models/
│   │   ├── event_action.py  # EventAction data model
│   │   ├── module.py        # Module model
│   │   └── project.py       # Project model
│   └── utils/
│       ├── parser.py        # C code parser
│       └── config.py        # Config file handler
├── config/
│   ├── default_config.json  # Default light points
│   └── example_project.json # Example project
├── tests/
│   └── test_parser.py       # Unit tests
└── README.md
```

## Usage

### Basic Workflow

1. **Create New Project**: File → New Project
2. **Add Modules**: Add module configurations (name, node, inputs, outputs)
3. **Configure Actions**: Set up button press actions (short, long, double press)
4. **Export C Code**: Generate firmware configuration via Import/Export menu
5. **Import C Code**: Parse existing firmware code via Import/Export menu

### Configuration Format

Project file (JSON):
```json
{
  "name": "My Project",
  "modules": [
    {
      "node": 64,
      "name": "Living Switch",
      "num_inputs": 4,
      "num_extra_actions": 20,
      "num_outputs": 16,
      "input_actions": {
        "input1_singlePress": {
          "action": "toggle",
          "delay_action": "nop",
          "delay": 0,
          "brightness": 100,
          "node": 64,
          "output": 0,
          "extra_action_index": 0
        }
      },
      "extra_actions": { },
      "outputs": {
        "Inkom": 0,
        "Led trap": 1
      }
    }
  ]
}
```


## Changelog

### v0.2.1
- Bug fixes related to outputs view
- Delay is in seconds not millis

### v0.2.0
- Renamed "Device" to "Module" throughout the application
- Unified add/edit module dialog
- Auto-apply changes in module editor (no save/revert buttons)
- Cross-module output references in action combos
- Import/Export menu for C code and module JSON
- Editable project name shown in title bar
- Friendly action display names (None, On, Off, Toggle)
- Modules with 0 inputs excluded from actions view
- Double-click module to edit instead of opening actions

### v0.1.0
- Initial release with multi-device support
- C code parser and generator
- Project save/load


