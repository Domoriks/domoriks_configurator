"""
Configuration file handler for light points and settings.
"""

import json
import os

class ConfigManager:
    """Manage configuration files for light points and settings."""
    
    DEFAULT_LIGHT_POINTS = {
        "l32_inkom": [64, 0],
        "l33_led_trap_beneden": [64, 1],
        "l34_traphal_beneden": [64, 2],
        "l35_wc_beneden": [64, 3],
        "l36_keuken": [64, 4],
        "l37_keuken_led": [64, 5],
        "l38_keuken_eiland": [64, 6],
        "l39_living": [64, 7],
        "l40_tv_meubel": [64, 8],
        "l41_buiten_achter": [64, 9],
        "l42_slaapkamer_straat": [64, 10],
        "l43_slaapkamer_achter": [64, 11],
        "l44_badkamer": [64, 12],
        "l45_badkamer_spiegel": [64, 13],
        "l46_wc_boven": [64, 14],
        "l47_hal_boven": [64, 15],
        "l48_zolder3": [65, 0],
        "l49_zolder2": [65, 1],
        "l50_zolder1": [65, 2],
        "l51_led_trap_boven": [65, 3],
    }
    
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def get_default_config_path(self):
        """Get path to default config file."""
        return os.path.join(self.config_dir, "default_config.json")
    
    def load_light_points(self, filepath=None):
        """Load light points from config file.
        
        Args:
            filepath: Path to config file (uses default if None)
            
        Returns:
            Dictionary of light points
        """
        if filepath is None:
            filepath = self.get_default_config_path()
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data.get("light_points", self.DEFAULT_LIGHT_POINTS)
        except FileNotFoundError:
            # Return default if file doesn't exist
            return self.DEFAULT_LIGHT_POINTS.copy()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def save_light_points(self, light_points, filepath=None):
        """Save light points to config file.
        
        Args:
            light_points: Dictionary of light points
            filepath: Path to config file (uses default if None)
        """
        if filepath is None:
            filepath = self.get_default_config_path()
        
        data = {"light_points": light_points}
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def validate_light_points(self, light_points):
        """Validate light points configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not isinstance(light_points, dict):
            errors.append("Light points must be a dictionary")
            return errors
        
        for name, value in light_points.items():
            if not isinstance(name, str):
                errors.append(f"Light point name must be string: {name}")
            
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                errors.append(f"Light point '{name}' must have [node, output] format")
                continue
            
            node, output = value
            if not isinstance(node, int) or not isinstance(output, int):
                errors.append(f"Light point '{name}' node and output must be integers")
            
            if node < 0 or output < 0:
                errors.append(f"Light point '{name}' node and output must be non-negative")
        
        return errors
    
    def import_light_points_from_c(self, c_code):
        """Extract light points definitions from C code.
        
        Looks for patterns like:
        const LightPoint light_points[] = {
            {"l32_inkom", 64, 0},
            ...
        };
        """
        import re
        
        light_points = {}
        
        # Pattern to match light point definitions
        pattern = r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\s*\}'
        
        for match in re.finditer(pattern, c_code):
            name, node, output = match.groups()
            light_points[name] = [int(node), int(output)]
        
        return light_points
    
    def export_light_points_to_c(self, light_points):
        """Export light points to C array format."""
        lines = [
            "const LightPoint light_points[] = {"
        ]
        
        for name, (node, output) in sorted(light_points.items()):
            lines.append(f'    {{"{name}", {node}, {output}}},')
        
        lines.append("};")
        
        return "\n".join(lines)
