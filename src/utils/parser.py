"""
C code parser for EventAction declarations.
"""

import re
from models.event_action import EventAction
from models.device import Device

class CCodeParser:
    """Parse C code containing EventAction declarations."""
    
    @staticmethod
    def parse_c_code(c_code):
        """Parse C code and extract EventAction declarations.
        
        Args:
            c_code: String containing C code
            
        Returns:
            Dictionary of EventAction objects keyed by name
        """
        actions = {}
        
        # Pattern to match EventAction declarations
        pattern = r'EventAction\s+(\w+)\s*=\s*\{\s*(\w+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\};'
        
        for match in re.finditer(pattern, c_code):
            name, action, delay_action, delay, brightness, node, output, reserved, extra_action_index = match.groups()
            
            event_action = EventAction(
                name=name,
                action=action,
                delay_action=delay_action,
                delay=int(delay),
                brightness=int(brightness),
                node=int(node),
                output=int(output),
                reserved=int(reserved),
                extra_action_index=int(extra_action_index)
            )
            
            actions[name] = event_action
        
        return actions
    
    @staticmethod
    def parse_to_device(c_code, device_name="Imported Device"):
        """Parse C code and create a Device object.
        
        Args:
            c_code: String containing C code
            device_name: Name for the created device
            
        Returns:
            Device object populated with parsed actions
        """
        actions = CCodeParser.parse_c_code(c_code)
        
        # Determine number of inputs and extra actions
        max_input = 0
        max_extra = 0
        
        for name in actions.keys():
            if name.startswith("input"):
                # Extract input number from name like "input3_singlePress"
                parts = name.split("_")
                if len(parts) >= 2 and parts[0].startswith("input"):
                    try:
                        input_num = int(parts[0].replace("input", ""))
                        max_input = max(max_input, input_num)
                    except ValueError:
                        pass
            elif name.startswith("extraAction"):
                # Extract extra action number
                try:
                    extra_num = int(name.replace("extraAction", ""))
                    max_extra = max(max_extra, extra_num)
                except ValueError:
                    pass
        
        # Create device with appropriate sizes
        device = Device(
            name=device_name,
            num_inputs=max(max_input, 4),
            num_extra_actions=max(max_extra, 20)
        )
        
        # Populate device with parsed actions
        for name, action in actions.items():
            device.set_action(name, action)
        
        return device
    
    @staticmethod
    def validate_c_code(c_code):
        """Validate C code format.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check for common syntax issues
        lines = c_code.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line or line.startswith('//'):
                continue
            
            if 'EventAction' in line:
                if not line.endswith(';'):
                    errors.append(f"Line {i}: Missing semicolon")
                
                if line.count('{') != line.count('}'):
                    errors.append(f"Line {i}: Mismatched braces")
                
                # Count commas (should be 7 for 8 fields)
                if line.count(',') != 7:
                    errors.append(f"Line {i}: Expected 8 fields (7 commas)")
        
        return errors
