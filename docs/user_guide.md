# EventAction Configurator - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Workflow](#basic-workflow)
4. [Features](#features)
5. [Troubleshooting](#troubleshooting)

## Introduction

EventAction Configurator is a professional tool for configuring home automation systems. It provides a user-friendly interface for managing event-action mappings and supports bidirectional conversion between GUI configuration and C code.

## Getting Started

### Installation

1. Install Python 3.7 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python src/main.py
   ```

### First Launch

On first launch, the application will:
- Load default light point configurations
- Create a new project with one device
- Show the main configuration window

## Basic Workflow

### Creating a New Project

1. Click **File → New Project** (or Ctrl+N)
2. Give your project a name
3. Add devices as needed

### Adding Devices

1. Click **+ Add Device** button
2. Enter device details:
   - Name (e.g., "Living Room Controller")
   - Number of inputs (1-16)
   - Number of extra actions (0-50)
3. Click **Create**

### Configuring Input Actions

Each device has inputs with three press types:
- **Single Press**: Quick button press
- **Double Press**: Two quick presses
- **Long Press**: Hold button for extended period

For each input/press combination, configure:
1. **Action**: Primary action (toggle, on, off, etc.)
2. **Delay Action**: Action after delay expires
3. **Light Point**: Target light to control
4. **Delay**: Time in milliseconds before delay action
5. **Extra Action #**: Chain to another action (optional)

### Configuring Extra Actions

Extra actions provide additional automation sequences:
1. Go to **Extra Actions** tab
2. Configure actions that can be chained from inputs
3. Use **Clear** button to reset an action

### Managing Light Points

Light points define the physical lights in your home:

1. Click **Edit → Edit Light Points**
2. Add, edit, or remove light points
3. Each light point has:
   - **Name**: Descriptive identifier
   - **Node**: Controller node number
   - **Output**: Output channel number

#### Importing Light Points from C

If you have existing C code with light point definitions:
1. In Light Points Editor, click **Import from C**
2. Paste your C code containing light point arrays
3. Click **Import**

## Features

### Import from C Code

Convert existing C configurations to GUI:

1. Click **Code → Import from C Code** (Ctrl+I)
2. Paste your EventAction C code
3. Click **Validate** to check syntax
4. Click **Import** to add as new device

**Example C Code:**
```c
EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };
EventAction input1_doublePress = { toggle, nop, 0, 100, 64, 1, 0, 0 };
```

### Export to C Code

Generate C code from your configuration:

1. Click **Code → Export to C Code** (Ctrl+E)
2. Review generated code
3. **Copy to Clipboard** or **Save to File**

### Validation

Validate your configuration before deployment:

1. Click **Edit → Validate Configuration**
2. Review any errors or warnings
3. Fix issues and revalidate

Common validation checks:
- Valid action types
- Brightness values (0-100)
- Non-negative delays
- Valid extra action references

### Saving and Loading Projects

**Save Project:**
- **Ctrl+S**: Quick save
- **File → Save Project As**: Save with new name

**Open Project:**
- **Ctrl+O**: Open existing project
- Projects saved as JSON files

### Multiple Devices

Manage complex setups with multiple devices:

1. Use **Device → Add Device** (Ctrl+D) to add more
2. Each device has separate tab
3. Close device tabs with ❌ button
4. All devices export together

## Troubleshooting

### Common Issues

**Issue: Light point not appearing in dropdown**
- Solution: Check Light Points Editor (Edit → Edit Light Points)
- Verify light point is saved in configuration

**Issue: C code import fails**
- Solution: Validate C code syntax
- Ensure format matches: `EventAction name = { ... };`
- Check for 8 fields (7 commas) per action

**Issue: Extra action chain not working**
- Solution: Verify extra action index exists
- Check that target extra action is configured
- Extra actions numbered 1-20 (or your configured max)

**Issue: Changes not saved**
- Solution: Use Ctrl+S or File → Save Project
- Check for asterisk (*) in title bar indicating unsaved changes

### Advanced Tips

1. **Quick Toggle All Lights:**
   - Create extra action with multiple chained actions
   - Reference from input button

2. **Timed Sequences:**
   - Use delay actions for automated sequences
   - Chain multiple extra actions for complex timing

3. **Backup Configurations:**
   - Save projects as JSON files
   - Keep backups of working configurations

4. **Reusable Configurations:**
   - Export common patterns to C code
   - Import into new projects as templates

## Action Types Reference

| Action | Description |
|--------|-------------|
| nop | No operation (do nothing) |
| toggle | Switch light on/off |
| on | Turn light on |
| off | Turn light off |
| ondelayoff | Turn on, then off after delay |
| offdelayon | Turn off, then on after delay |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Project |
| Ctrl+O | Open Project |
| Ctrl+S | Save Project |
| Ctrl+Shift+S | Save Project As |
| Ctrl+D | Add Device |
| Ctrl+I | Import C Code |
| Ctrl+E | Export C Code |
| Ctrl+Q | Quit Application |

## Support

For issues or feature requests, please refer to the project README or contact support.
