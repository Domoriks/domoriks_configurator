# Quick Start Guide

## Installation (30 seconds)

```bash
# 1. Clone or download the project
cd event_action_config

# 2. Install dependencies
pip install PyQt5

# 3. Run the application
python src/main.py
```

## Your First Configuration (2 minutes)

### Step 1: Create a Device
1. Application starts with one device already created
2. Name it (e.g., "Living Room")

### Step 2: Configure an Input
1. Find "Input 1" → "Single Press" row
2. Set **Action** to "toggle"
3. Set **Light Point** to "l39_living"
4. Leave other fields as defaults

### Step 3: Test the Output
1. Click **Code → Export to C Code**
2. See generated code:
   ```c
   EventAction input1_singlePress = { toggle, nop, 0, 100, 64, 7, 0, 0 };
   ```
3. Copy to your firmware!

## Common Tasks

### Import Existing Configuration
```bash
# You have existing C code like:
# EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };
```

1. **Code → Import from C Code**
2. Paste your C code
3. Click **Import**
4. Edit in GUI!

### Add More Lights
1. **Edit → Edit Light Points**
2. Click **Add**
3. Enter: Name="bedroom", Node=65, Output=4
4. Click **Save**

### Save Your Work
1. **File → Save Project** (Ctrl+S)
2. Choose location
3. File saved as `.json`

### Create Multiple Devices
1. Click **+ Add Device**
2. Configure second device (e.g., "Kitchen")
3. All export together

## Tips

- **Use Extra Actions** for complex sequences
- **Validate** before deploying (Edit → Validate)
- **Save Often** with Ctrl+S
- **Explore Examples** in `config/example_project.json`

## Next Steps

Read the full [User Guide](user_guide.md) for advanced features!
