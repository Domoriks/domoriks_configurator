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
            client.write_multiple_registers(module.node, step.start_address, regs, timeout)
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
            client.write_multiple_registers(module.node, step.start_address, regs, timeout)
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

    # Erased flash commonly returns 0xFF fields (with reg0 still containing index/type).
    # Treat that as an empty/default action instead of surfacing invalid values.
    if _is_erased_action_payload(registers):
        return EventAction(
            name,
            action="nop",
            delay_action="nop",
            delay=0,
            brightness=100,
            node=0,
            output=0,
            send=0,
            extra_action_index=0,
        )

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
    action.delay = 0 if delay_value == 0xFFFFFFFF else int(delay_value)
    action.brightness = int(brightness) if 0 <= int(brightness) <= 100 else 100
    action.node = 0 if int(node) == 0xFF else int(node)
    action.output = 0 if int(output) == 0xFF else int(output)
    action.send = int(send) if int(send) in (0, 1, 2, 3) else 0
    action.extra_action_index = 0 if int(extra) == 0xFF else int(extra)
    return action


def _is_erased_action_payload(registers: List[int]) -> bool:
    """True when register payload matches an erased flash action slot."""
    if len(registers) < 7:
        return False

    # reg0 is index/type and is generated dynamically by firmware, so ignore it.
    return (
        registers[1] == 0xFFFF
        and registers[2] == 0xFFFF
        and registers[3] == 0xFFFF
        and registers[4] == 0xFFFF
        and registers[5] in (0xFFFF, 0xFF00)
        and registers[6] in (0xFFFF, 0xFF00)
    )


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


