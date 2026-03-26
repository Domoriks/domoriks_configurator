"""
EventAction data model representing a single event-action configuration.
"""

class EventAction:
    """Represents a single event action configuration."""
    
    ACTIONS = ["nop", "toggle", "on", "off"]
    ACTION_DISPLAY = {"nop": "None", "on": "On", "off": "Off", "toggle": "Toggle"}
    
    def __init__(self, name, action="nop", delay_action="nop", delay=0, 
                 brightness=100, node=0, output=0, reserved=0, extra_action_index=0):
        self.name = name
        self.action = action
        self.delay_action = delay_action
        self.delay = delay
        self.brightness = brightness
        self.node = node
        self.output = output
        self.reserved = reserved
        self.extra_action_index = extra_action_index
    
    def to_c_code(self):
        """Generate C code representation."""
        return (f"EventAction {self.name} = {{ {self.action}, {self.delay_action}, "
                f"{self.delay}, {self.brightness}, {self.node}, {self.output}, "
                f"{self.reserved}, {self.extra_action_index} }};")
    
    def get_light_point_name(self, light_points_dict):
        """Get light point name from node and output."""
        for name, (node, output) in light_points_dict.items():
            if node == self.node and output == self.output:
                return name
        return None
    
    def is_empty(self):
        """Check if this is an empty/default action."""
        return (self.action == "nop" and self.delay_action == "nop" and 
                self.extra_action_index == 0)
    
    def validate(self):
        """Validate the event action configuration."""
        errors = []
        
        if self.action not in self.ACTIONS:
            errors.append(f"Invalid action: {self.action}")
        
        if self.delay_action not in self.ACTIONS:
            errors.append(f"Invalid delay action: {self.delay_action}")
        
        if self.delay < 0:
            errors.append(f"Delay must be non-negative: {self.delay}")
        
        if not (0 <= self.brightness <= 100):
            errors.append(f"Brightness must be 0-100: {self.brightness}")
        
        if self.extra_action_index < 0:
            errors.append(f"Extra action index must be non-negative: {self.extra_action_index}")
        
        return errors
    
    def __repr__(self):
        return f"EventAction({self.name}, {self.action}, {self.delay_action})"
