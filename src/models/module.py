"""
Module model representing a single module with multiple inputs and extra actions.
"""

from models.event_action import EventAction


class Module:
    """Represents a module with inputs, outputs and extra actions."""

    PRESS_TYPES = ["singlePress", "doublePress", "longPress"]

    def __init__(self, name, num_inputs=4, num_extra_actions=20, num_outputs=0, node=0):
        self.name = name
        self.num_inputs = num_inputs
        self.num_extra_actions = num_extra_actions
        self.num_outputs = num_outputs
        self.node = node

        self.input_actions = {}
        for i in range(1, num_inputs + 1):
            for press in self.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                self.input_actions[action_name] = EventAction(action_name)

        self.extra_actions = {}
        for i in range(1, num_extra_actions + 1):
            action_name = f"extraAction{i}"
            self.extra_actions[action_name] = EventAction(action_name)

        self.outputs = {}
        for i in range(1, num_outputs + 1):
            output_name = f"Output {i}"
            self.outputs[output_name] = i - 1

    def set_action(self, action_name, event_action):
        if action_name in self.input_actions:
            self.input_actions[action_name] = event_action
        elif action_name in self.extra_actions:
            self.extra_actions[action_name] = event_action

    def get_all_actions(self):
        all_actions = {}
        all_actions.update(self.input_actions)
        all_actions.update(self.extra_actions)
        return all_actions

    def to_c_code(self):
        lines = [f"// Module: {self.name}"]
        for i in range(1, self.num_inputs + 1):
            for press in self.PRESS_TYPES:
                action_name = f"input{i}_{press}"
                action = self.input_actions[action_name]
                if not action.is_empty():
                    lines.append(action.to_c_code())
        for i in range(1, self.num_extra_actions + 1):
            action_name = f"extraAction{i}"
            action = self.extra_actions[action_name]
            if not action.is_empty():
                lines.append(action.to_c_code())
        return "\n".join(lines)

    def validate(self):
        errors = []
        for action_name, action in self.get_all_actions().items():
            action_errors = action.validate()
            if action_errors:
                errors.extend([f"{action_name}: {err}" for err in action_errors])
        return errors

    def to_dict(self):
        return {
            "node": self.node,
            "name": self.name,
            "num_inputs": self.num_inputs,
            "num_extra_actions": self.num_extra_actions,
            "num_outputs": self.num_outputs,
            "input_actions": {
                name: action.to_dict()
                for name, action in self.input_actions.items()
            },
            "extra_actions": {
                name: action.to_dict()
                for name, action in self.extra_actions.items()
            },
            "outputs": dict(self.outputs)
        }

    @classmethod
    def from_dict(cls, data):
        module = cls(
            name=data.get("name", "Unnamed Module"),
            num_inputs=data.get("num_inputs", 4),
            num_extra_actions=data.get("num_extra_actions", 20),
            num_outputs=data.get("num_outputs", 0),
            node=data.get("node", data.get("id", 0)),
        )
        for name, action_data in data.get("input_actions", {}).items():
            module.input_actions[name] = EventAction.from_dict(name, action_data)
        for name, action_data in data.get("extra_actions", {}).items():
            module.extra_actions[name] = EventAction.from_dict(name, action_data)

        json_outputs = data.get("outputs", {})
        if json_outputs:
            module.outputs = {}
        for name, out_data in json_outputs.items():
            try:
                # Support legacy [node, output_nr] arrays as well as plain ints
                if isinstance(out_data, (int, float)):
                    module.outputs[name] = int(out_data)
                else:
                    module.outputs[name] = int(out_data[1])
            except Exception:
                module.outputs[name] = 0

        if not module.node:
            nodes = []
            for act in list(module.input_actions.values()) + list(module.extra_actions.values()):
                if act.node and act.node not in (0, 255):
                    nodes.append(act.node)
            if nodes:
                from collections import Counter
                module.node = int(Counter(nodes).most_common(1)[0][0])

        return module

    def __repr__(self):
        return f"Module({self.name}, node={self.node}, inputs={self.num_inputs}, extras={self.num_extra_actions}, outputs={self.num_outputs})"

    def update_from_dict(self, cfg):
        self.name = cfg.get("name", self.name)
        self.node = int(cfg.get("node", self.node))

        new_num_inputs = int(cfg.get("num_inputs", self.num_inputs))
        if new_num_inputs != self.num_inputs:
            new_input_actions = {}
            for i in range(1, new_num_inputs + 1):
                for press in self.PRESS_TYPES:
                    action_name = f"input{i}_{press}"
                    if action_name in self.input_actions:
                        new_input_actions[action_name] = self.input_actions[action_name]
                    else:
                        new_input_actions[action_name] = EventAction(action_name)
            self.input_actions = new_input_actions
            self.num_inputs = new_num_inputs

        new_num_extras = int(cfg.get("num_extra_actions", self.num_extra_actions))
        if new_num_extras != self.num_extra_actions:
            new_extra_actions = {}
            for i in range(1, new_num_extras + 1):
                action_name = f"extraAction{i}"
                if action_name in self.extra_actions:
                    new_extra_actions[action_name] = self.extra_actions[action_name]
                else:
                    new_extra_actions[action_name] = EventAction(action_name)
            self.extra_actions = new_extra_actions
            self.num_extra_actions = new_num_extras

        new_num_outputs = int(cfg.get("num_outputs", self.num_outputs))
        if new_num_outputs != self.num_outputs or "outputs" in cfg:
            if "outputs" in cfg:
                self.outputs = cfg["outputs"]
            else:
                # Resize outputs: keep existing up to new count, add new ones if growing
                old_items = list(self.outputs.items())
                new_outputs = {}
                for i in range(min(new_num_outputs, len(old_items))):
                    new_outputs[old_items[i][0]] = old_items[i][1]
                for i in range(len(old_items), new_num_outputs):
                    new_outputs[f"Output {i + 1}"] = i
                self.outputs = new_outputs
            self.num_outputs = new_num_outputs
