# Alternative Editing Methods & Workflows

## Overview

Beyond the standard GUI interface, the EventAction Configurator supports multiple editing workflows to suit different preferences and use cases.

## 1. Direct JSON Editing

### Use Case
- Power users who prefer text editing
- Bulk modifications
- Version control friendly
- Quick regex-based changes

### Workflow
```bash
# 1. Save your project
File → Save Project → myproject.json

# 2. Edit with your favorite editor
vim myproject.json
# or
code myproject.json

# 3. Reload in GUI
File → Open Project → myproject.json
```

### Example JSON Structure
```json
{
  "name": "My Home",
  "devices": [{
    "name": "Living Room",
    "input_actions": {
      "input1_singlePress": {
        "action": "toggle",
        "delay_action": "nop",
        "delay": 0,
        "node": 64,
        "output": 7
      }
    }
  }]
}
```

### Advantages
- ✅ Fast bulk edits
- ✅ Copy/paste between projects
- ✅ Search/replace across all devices
- ✅ Version control integration

### Disadvantages
- ❌ No validation until reload
- ❌ Syntax errors can corrupt project
- ❌ Less visual

## 2. C Code Round-Trip

### Use Case
- Working with existing firmware
- Team collaboration
- Legacy system integration

### Workflow
```bash
# 1. Export from GUI
Code → Export to C Code → save to actions.c

# 2. Edit in IDE with syntax highlighting
vim actions.c  # Your C development environment

# 3. Re-import to GUI
Code → Import from C Code → paste/load actions.c

# 4. Make additional GUI changes

# 5. Export again
```

### Advantages
- ✅ Familiar C syntax
- ✅ IDE autocomplete
- ✅ Direct firmware integration
- ✅ Team can review C code

### Disadvantages
- ❌ Loses some GUI metadata
- ❌ Manual light point resolution

## 3. Hybrid Workflow (Recommended)

### Use Case
- Complex configurations
- Iterative development
- Best of both worlds

### Workflow
```bash
# 1. Design structure in GUI
- Create devices
- Configure light points
- Set up basic actions

# 2. Export to review
Code → Export to C Code

# 3. Bulk edits in C or JSON
- Use text editor for repetitive changes
- Copy/paste similar configurations

# 4. Re-import
Code → Import from C Code

# 5. Fine-tune in GUI
- Adjust delays
- Test configurations
- Validate

# 6. Save as project
File → Save Project
```

## 4. Template-Based Editing

### Use Case
- Standard configurations
- Multiple similar devices
- Rapid deployment

### Creating Templates
```bash
# 1. Configure one device perfectly in GUI
# 2. Export to C or save project
# 3. Use as template for similar devices
```

### Using Templates
```python
# Option A: Duplicate in JSON
{
  "devices": [
    { "name": "Room1", "input_actions": {...} },
    { "name": "Room2", "input_actions": {...} },  # Copy from Room1
    { "name": "Room3", "input_actions": {...} }   # Copy from Room1
  ]
}

# Option B: Import C code multiple times
# Import template → Rename device → Adjust specifics → Repeat
```

### Advantages
- ✅ Rapid deployment
- ✅ Consistency across devices
- ✅ Reduces errors

## 5. Script-Based Generation

### Use Case
- Very large installations
- Programmatic configurations
- Dynamic setups

### Example: Generate Configurations
```python
#!/usr/bin/env python3
import json

# Generate 10 identical devices
devices = []
for i in range(1, 11):
    device = {
        "name": f"Room_{i}",
        "num_inputs": 4,
        "input_actions": {
            "input1_singlePress": {
                "action": "toggle",
                "node": 64,
                "output": i-1,  # Unique output per room
                "delay": 0,
                "brightness": 100
            }
        }
    }
    devices.append(device)

project = {
    "name": "10 Room Setup",
    "devices": devices,
    "light_points": {...}
}

with open('generated_project.json', 'w') as f:
    json.dump(project, f, indent=2)

print("Generated! Load in GUI: File → Open Project")
```

### Advantages
- ✅ Unlimited scale
- ✅ Complex logic
- ✅ Automated generation

### Disadvantages
- ❌ Requires programming
- ❌ More complex

## 6. Command-Line Interface (Future)

### Planned Features
```bash
# Validate configuration
eventconfig validate myproject.json

# Export to C
eventconfig export myproject.json > output.c

# Import from C
eventconfig import input.c -o newproject.json

# List devices
eventconfig list myproject.json

# Add device
eventconfig add-device myproject.json "New Device"
```

## 7. Spreadsheet Editing (Future)

### Use Case
- Non-technical users
- Tabular view preference
- Easy copy/paste

### Workflow
```bash
# Export to CSV/Excel
File → Export → Spreadsheet

# Edit in Excel/Google Sheets
# Columns: Input, Press, Action, Light, Delay, Extra

# Re-import
File → Import → Spreadsheet
```

## 8. API/REST Interface (Future)

### Use Case
- Integration with other tools
- Web-based configuration
- Remote management

### Example
```python
import requests

# Get project
project = requests.get('http://localhost:8080/api/project/123')

# Update device
requests.put('http://localhost:8080/api/device/living-room', 
             json={'input1_singlePress': {...}})

# Export C code
c_code = requests.get('http://localhost:8080/api/export/c/123')
```

## Comparison Matrix

| Method | Ease | Speed | Validation | Best For |
|--------|------|-------|------------|----------|
| GUI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Beginners, visual users |
| JSON Edit | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Power users, bulk edits |
| C Round-Trip | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Firmware integration |
| Template | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Similar devices |
| Script Gen | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Large scale |
| CLI (future) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Automation |
| Spreadsheet (future) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Non-technical |
| API (future) | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Integration |

## Best Practices

### For Small Projects (1-3 devices)
- Use GUI exclusively
- Save as project file
- Export C code when ready

### For Medium Projects (4-10 devices)
- Start in GUI for structure
- Use templates for similar devices
- JSON editing for bulk changes
- Validate before export

### For Large Projects (10+ devices)
- Script-based generation recommended
- Template library
- Version control (Git)
- Automated testing

### For Team Environments
- C code as source of truth
- GUI for development
- Code review before deployment
- Hybrid workflow

## Troubleshooting

### JSON Edits Not Reflecting
- Ensure valid JSON syntax
- Reload project after editing
- Check validation errors

### C Code Import Fails
- Verify EventAction format
- Check field count (8 fields)
- Remove extra whitespace

### Merge Conflicts
- Use JSON diff tools
- Separate devices into files
- Maintain consistent formatting

## Future Vision

We're planning to support:
1. **Visual Programming**: Drag-and-drop action flows
2. **Live Hardware Testing**: Test configurations without redeployment  
3. **Cloud Collaboration**: Real-time multi-user editing
4. **Mobile Editing**: Configure from phone/tablet
5. **Voice Configuration**: "Add toggle light action to input 1"

## Contribute Your Workflow

Have a unique workflow? Share it with the community!
- Open GitHub issue
- Describe your method
- We'll add it here

---

**The beauty of open formats: Edit however you want!**
