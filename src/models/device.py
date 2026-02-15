"""
Device model representing a single device with multiple inputs and extra actions.
"""

from models.event_action import EventAction

class Device:
    """Represents a device with inputs and extra actions."""
    
    PRESS_TYPES = ["singlePress", "doublePress", "longPress"]
    
    def __init__(self, name, num_inputs=4, num_extra_actions=20):
        self.name = name
        self.num_inputs = num_inputs
        self.num_extra_actions = num_extra_actions
        
        # Initialize input event actions
        self.input_actions = {}
        for i in range(1, num_inputs + 1):
            for press in self.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                self.input_actions[action_name] = EventAction(action_name)
        
        # Initialize extra actions
        self.extra_actions = {}
        for i in range(1, num_extra_actions + 1):
            action_name = f"extraAction{i}"
            self.extra_actions[action_name] = EventAction(action_name)
    
    def get_action(self, action_name):
        """Get an event action by name."""
        if action_name in self.input_actions:
            return self.input_actions[action_name]
        elif action_name in self.extra_actions:
            return self.extra_actions[action_name]
        return None
    
    def set_action(self, action_name, event_action):
        """Set an event action."""
        if action_name in self.input_actions:
            self.input_actions[action_name] = event_action
        elif action_name in self.extra_actions:
            self.extra_actions[action_name] = event_action
    
    def get_all_actions(self):
        """Get all event actions (inputs + extras)."""
        all_actions = {}
        all_actions.update(self.input_actions)
        all_actions.update(self.extra_actions)
        return all_actions
    
    def to_c_code(self):
        """Generate C code for all device actions."""
        lines = [f"// Device: {self.name}"]
        
        # Input actions
        for i in range(1, self.num_inputs + 1):
            for press in self.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                action = self.input_actions[action_name]
                if not action.is_empty():
                    lines.append(action.to_c_code())
        
        # Extra actions (only non-empty ones)
        for i in range(1, self.num_extra_actions + 1):
            action_name = f"extraAction{i}"
            action = self.extra_actions[action_name]
            if not action.is_empty():
                lines.append(action.to_c_code())
        
        return "\n".join(lines)
    
    def validate(self):
        """Validate all event actions in this device."""
        errors = []
        
        for action_name, action in self.get_all_actions().items():
            action_errors = action.validate()
            if action_errors:
                errors.extend([f"{action_name}: {err}" for err in action_errors])
        
        return errors
    
    def to_dict(self):
        """Convert device to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "num_inputs": self.num_inputs,
            "num_extra_actions": self.num_extra_actions,
            "input_actions": {
                name: {
                    "action": action.action,
                    "delay_action": action.delay_action,
                    "delay": action.delay,
                    "brightness": action.brightness,
                    "node": action.node,
                    "output": action.output,
                    "extra_action_index": action.extra_action_index
                }
                for name, action in self.input_actions.items()
            },
            "extra_actions": {
                name: {
                    "action": action.action,
                    "delay_action": action.delay_action,
                    "delay": action.delay,
                    "brightness": action.brightness,
                    "node": action.node,
                    "output": action.output,
                    "extra_action_index": action.extra_action_index
                }
                for name, action in self.extra_actions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create device from dictionary."""
        device = cls(
            name=data["name"],
            num_inputs=data.get("num_inputs", 4),
            num_extra_actions=data.get("num_extra_actions", 20)
        )
        
        # Load input actions
        for name, action_data in data.get("input_actions", {}).items():
            action = EventAction(
                name=name,
                action=action_data.get("action", "nop"),
                delay_action=action_data.get("delay_action", "nop"),
                delay=action_data.get("delay", 0),
                brightness=action_data.get("brightness", 100),
                node=action_data.get("node", 0),
                output=action_data.get("output", 0),
                extra_action_index=action_data.get("extra_action_index", 0)
            )
            device.input_actions[name] = action
        
        # Load extra actions
        for name, action_data in data.get("extra_actions", {}).items():
            action = EventAction(
                name=name,
                action=action_data.get("action", "nop"),
                delay_action=action_data.get("delay_action", "nop"),
                delay=action_data.get("delay", 0),
                brightness=action_data.get("brightness", 100),
                node=action_data.get("node", 0),
                output=action_data.get("output", 0),
                extra_action_index=action_data.get("extra_action_index", 0)
            )
            device.extra_actions[name] = action
        
        return device
    
    def __repr__(self):
        return f"Device({self.name}, inputs={self.num_inputs}, extras={self.num_extra_actions})"
