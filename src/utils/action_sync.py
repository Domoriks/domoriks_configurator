"""Action register mapping and sync helpers for Domoriks devices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

from models.event_action import EventAction
from utils.domoriks_api import ApiError, DomoriksApiClient

ACTION_REG_BASE = 0x0300
EXTRA_ACTION_REG_BASE = 0x0500
REGS_PER_ACTION = 7
ACTION_TYPES_PER_INPUT = 5

PRESS_TO_ACTION_TYPE = {
    "singlePress": 1,
    "doublePress": 2,
    "longPress": 3,
    "switchOn": 4,
    "switchOff": 5,
}


class UploadError(RuntimeError):
    """Represents a failed action upload with full diagnostics."""

    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details


@dataclass
class ActionStep:
    index: int
    name: str
    action_type: int
    start_address: int
    action: EventAction


def read_module_actions(client: DomoriksApiClient, module, timeout: float) -> Dict[str, EventAction]:
    result: Dict[str, EventAction] = {}

    for i in range(1, int(module.num_inputs) + 1):
        for press in ["singlePress", "doublePress", "longPress", "switchOn", "switchOff"]:
            name = f"input{i}_{press}"
            if name not in module.input_actions:
                continue

            action_type = PRESS_TO_ACTION_TYPE[press]
            start = ACTION_REG_BASE + ((i - 1) * ACTION_TYPES_PER_INPUT + (action_type - 1)) * REGS_PER_ACTION
            exchange = client.read_holding_registers(module.node, start, REGS_PER_ACTION, timeout)
            regs = exchange.response.get("decoded_registers", [])

            # Auto-detect firmware byte order on first read
            if client.byte_swap is None and len(regs) >= 1:
                _detect_byte_order(client, regs[0], i - 1, action_type)
                # Re-read with correct byte swap applied
                exchange = client.read_holding_registers(module.node, start, REGS_PER_ACTION, timeout)
                regs = exchange.response.get("decoded_registers", [])

            result[name] = _registers_to_action(name, regs)

    for i in range(1, int(module.num_extra_actions) + 1):
        name = f"extraAction{i}"
        if name not in module.extra_actions:
            continue

        start = EXTRA_ACTION_REG_BASE + (i - 1) * REGS_PER_ACTION
        exchange = client.read_holding_registers(module.node, start, REGS_PER_ACTION, timeout)
        regs = exchange.response.get("decoded_registers", [])
        result[name] = _registers_to_action(name, regs)

    return result


def upload_module_actions(client: DomoriksApiClient, module, timeout: float) -> None:
    steps = _ordered_steps(module)
    if not steps:
        return

    for i, step in enumerate(steps, start=1):
        save_flag = 1 if i == len(steps) else 0
        regs = _action_to_registers(step.action, step.index, step.action_type, save_flag)
        try:
            client.write_multiple_registers(module.node, 0, regs, timeout)
        except ApiError as exc:
            details = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "device_id": module.node,
                "action_index": i,
                "action_name": step.name,
                "timeout": timeout,
                "register_payload": regs,
            }
            details.update(exc.details)
            raise UploadError("Action upload failed", details) from exc


def diff_module_actions(module, device_actions: Dict[str, EventAction]) -> List[ActionStep]:
    """Return ordered steps whose local action differs from device state."""
    changed: List[ActionStep] = []
    for step in _ordered_steps(module):
        remote = device_actions.get(step.name)
        if remote is None or _action_to_dict(remote) != _action_to_dict(step.action):
            changed.append(step)
    return changed


def upload_changed_actions(client: DomoriksApiClient, module, changed_steps: List[ActionStep], timeout: float) -> None:
    if not changed_steps:
        return

    for i, step in enumerate(changed_steps, start=1):
        save_flag = 1 if i == len(changed_steps) else 0
        regs = _action_to_registers(step.action, step.index, step.action_type, save_flag)
        try:
            client.write_multiple_registers(module.node, 0, regs, timeout)
        except ApiError as exc:
            details = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "device_id": module.node,
                "action_index": i,
                "action_name": step.name,
                "timeout": timeout,
                "register_payload": regs,
            }
            details.update(exc.details)
            raise UploadError("Action upload failed", details) from exc


def apply_actions_to_module(module, actions: Dict[str, EventAction]) -> None:
    for name, action in actions.items():
        if name in module.input_actions:
            module.input_actions[name] = action
        elif name in module.extra_actions:
            module.extra_actions[name] = action


def build_actions_snapshot(module, actions_override: Dict[str, EventAction] | None = None) -> Dict[str, Any]:
    override = actions_override or {}
    actions_list: List[Dict[str, Any]] = []

    for step in _ordered_steps(module):
        action = override.get(step.name, step.action)
        actions_list.append({
            "name": step.name,
            "kind": "extra" if step.action_type == 6 else "input",
            "action_type": step.action_type,
            "action": action.action,
            "delay_action": action.delay_action,
            "delay": int(action.delay),
            "brightness": int(action.brightness),
            "node": int(action.node),
            "output": int(action.output),
            "send": int(action.send),
            "extra_action_index": int(action.extra_action_index),
        })

    return {
        "module": {
            "name": module.name,
            "node": int(module.node),
        },
        "actions": actions_list,
    }


def _ordered_steps(module) -> List[ActionStep]:
    steps: List[ActionStep] = []

    for i in range(1, int(module.num_inputs) + 1):
        for press in ["singlePress", "doublePress", "longPress", "switchOn", "switchOff"]:
            name = f"input{i}_{press}"
            if name not in module.input_actions:
                continue
            action_type = PRESS_TO_ACTION_TYPE[press]
            start_address = ACTION_REG_BASE + ((i - 1) * ACTION_TYPES_PER_INPUT + (action_type - 1)) * REGS_PER_ACTION
            steps.append(ActionStep(index=i - 1, name=name, action_type=action_type, start_address=start_address, action=module.input_actions[name]))

    for i in range(1, int(module.num_extra_actions) + 1):
        name = f"extraAction{i}"
        if name not in module.extra_actions:
            continue
        start_address = EXTRA_ACTION_REG_BASE + (i - 1) * REGS_PER_ACTION
        steps.append(ActionStep(index=i - 1, name=name, action_type=6, start_address=start_address, action=module.extra_actions[name]))

    return steps


def _action_to_registers(action: EventAction, index: int, action_type: int, save_flag: int) -> List[int]:
    action_code = EventAction.ACTIONS.index(action.action) if action.action in EventAction.ACTIONS else 0
    delay_action_code = EventAction.ACTIONS.index(action.delay_action) if action.delay_action in EventAction.ACTIONS else 0
    delay_value = int(action.delay) & 0xFFFFFFFF

    return [
        ((index & 0xFF) << 8) | (action_type & 0xFF),
        ((action_code & 0xFF) << 8) | (delay_action_code & 0xFF),
        (delay_value >> 16) & 0xFFFF,
        delay_value & 0xFFFF,
        ((int(action.brightness) & 0xFF) << 8) | (int(action.node) & 0xFF),
        ((int(action.output) & 0xFF) << 8) | (int(action.send) & 0xFF),
        ((int(action.extra_action_index) & 0xFF) << 8) | (save_flag & 0xFF),
    ]


def _registers_to_action(name: str, registers: List[int]) -> EventAction:
    if len(registers) < 7:
        raise ApiError("Read action payload too short", {"decoded_registers": registers})

    action_code = (registers[1] >> 8) & 0xFF
    delay_action_code = registers[1] & 0xFF
    delay_value = ((registers[2] & 0xFFFF) << 16) | (registers[3] & 0xFFFF)
    brightness = (registers[4] >> 8) & 0xFF
    node = registers[4] & 0xFF
    output = (registers[5] >> 8) & 0xFF
    send = registers[5] & 0xFF
    extra = (registers[6] >> 8) & 0xFF

    action = EventAction(name)
    action.action = EventAction.ACTIONS[action_code] if action_code < len(EventAction.ACTIONS) else "nop"
    action.delay_action = EventAction.ACTIONS[delay_action_code] if delay_action_code < len(EventAction.ACTIONS) else "nop"
    action.delay = int(delay_value)
    action.brightness = int(brightness)
    action.node = int(node)
    action.output = int(output)
    action.send = int(send)
    action.extra_action_index = int(extra)
    return action


def _action_to_dict(action: EventAction) -> Dict[str, Any]:
    return {
        "action": action.action,
        "delay_action": action.delay_action,
        "delay": int(action.delay),
        "brightness": int(action.brightness),
        "node": int(action.node),
        "output": int(action.output),
        "send": int(action.send),
        "extra_action_index": int(action.extra_action_index),
    }


def _detect_byte_order(client: DomoriksApiClient, reg0: int, expected_index: int, expected_action_type: int) -> None:
    """Auto-detect firmware byte order by checking register[0] plausibility.

    Register[0] should be (input_index << 8) | action_type.
    If the bytes are swapped, it would be (action_type << 8) | input_index.
    """
    hi = (reg0 >> 8) & 0xFF
    lo = reg0 & 0xFF

    # Standard Modbus (new firmware): hi=input_index, lo=action_type
    if hi == expected_index and lo == expected_action_type:
        client.byte_swap = False
        return

    # Swapped (old firmware): hi=action_type, lo=input_index
    if hi == expected_action_type and lo == expected_index:
        client.byte_swap = True
        return

    # Cannot determine — assume new firmware (standard Modbus)
    client.byte_swap = False
