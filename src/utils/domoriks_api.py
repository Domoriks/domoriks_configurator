"""HTTP client helpers for Domoriks Home Assistant API."""

from __future__ import annotations

import json
import struct
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ApiError(RuntimeError):
    """Represents an API or transport failure with diagnostic details."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class RawExchange:
    request: Dict[str, Any]
    response: Dict[str, Any]


class DomoriksApiClient:
    """Thin synchronous client for HA /api/domoriks endpoints."""

    def __init__(self, base_url: str, token: str):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.byte_swap: Optional[bool] = None  # None = not yet detected

    def detect_range(self, start_slave: int, end_slave: int, timeout: float, progress_callback=None) -> Dict[str, Any]:
        """Detect slaves in range with progress callback.
        
        Pings each slave individually via raw endpoint for real per-slave progress.
        progress_callback(slave: int) called after each slave is tested.
        """
        reachable = []
        unreachable = []
        
        for slave in range(int(start_slave), int(end_slave) + 1):
            if self._ping_slave(slave, timeout):
                reachable.append(slave)
            else:
                unreachable.append(slave)
            
            if progress_callback:
                progress_callback(slave)
        
        return {"reachable": reachable, "unreachable": unreachable}
    
    def _ping_slave(self, slave: int, timeout: float) -> bool:
        """Send read_coils(0, 1) to check if slave responds."""
        try:
            payload = struct.pack(">HH", 0, 1)  # start=0, count=1
            frame = _encode_modbus_rtu_frame(int(slave), 0x01, payload)  # FC 0x01 = read coils
            exchange = self.raw(frame.hex(), timeout)
            
            response = exchange.response.get("response")
            if response is None:
                return False
            
            # Validate response format: {function, payload, ...}
            function = int(response.get("function", 0))
            # Exception response has MSB set
            if function & 0x80:
                return False
            
            # Check function matches
            if function != 0x01:
                return False
            
            return True
        except Exception:
            return False

    def raw(self, frame_hex: str, timeout: float) -> RawExchange:
        payload = {
            "frame": frame_hex,
            "timeout": float(timeout),
        }
        response = self._post_json("/api/domoriks/raw", payload)
        return RawExchange(request=payload, response=response)

    def read_holding_registers(self, slave: int, start: int, count: int, timeout: float) -> RawExchange:
        payload = struct.pack(">HH", int(start), int(count))
        frame = _encode_modbus_rtu_frame(int(slave), 0x03, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during read holding registers", {
                "request_json": exchange.request,
                "response_json": exchange.response,
                "exception_code": response.get("exception_code"),
            })

        if function != 0x03:
            raise ApiError("Unexpected Modbus function in read response", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        payload_hex = response.get("payload", "")
        data = bytes.fromhex(payload_hex)
        if not data:
            raise ApiError("Empty read payload", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        byte_count = data[0]
        reg_data = data[1 : 1 + byte_count]
        if len(reg_data) != byte_count or byte_count % 2 != 0:
            raise ApiError("Invalid read payload length", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        registers: List[int] = []
        for i in range(0, len(reg_data), 2):
            registers.append(struct.unpack(">H", reg_data[i : i + 2])[0])

        # Apply byte-swap correction for old firmware that sends [lo, hi]
        if self.byte_swap:
            registers = [((r & 0xFF) << 8) | ((r >> 8) & 0xFF) for r in registers]

        exchange.response["decoded_registers"] = registers
        return exchange

    def write_multiple_registers(self, slave: int, start: int, registers: List[int], timeout: float) -> RawExchange:
        reg_count = len(registers)
        if reg_count <= 0:
            raise ApiError("At least one register is required for write")

        encoded = b"".join(struct.pack(">H", int(v) & 0xFFFF) for v in registers)
        payload = struct.pack(">HHB", int(start), reg_count, len(encoded)) + encoded
        frame = _encode_modbus_rtu_frame(int(slave), 0x10, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during write multiple registers", {
                "request_json": exchange.request,
                "response_json": exchange.response,
                "exception_code": response.get("exception_code"),
            })

        if function != 0x10:
            raise ApiError("Unexpected Modbus function in write response", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        return exchange

    def write_single_register(self, slave: int, address: int, value: int, timeout: float) -> RawExchange:
        payload = struct.pack(">HH", int(address) & 0xFFFF, int(value) & 0xFFFF)
        frame = _encode_modbus_rtu_frame(int(slave), 0x06, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during write single register", {
                "request_json": exchange.request,
                "response_json": exchange.response,
                "exception_code": response.get("exception_code"),
            })

        if function != 0x06:
            raise ApiError("Unexpected Modbus function in write single register response", {
                "request_json": exchange.request,
                "response_json": exchange.response,
            })

        return exchange

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            raise ApiError("Base URL is not configured")
        if not self.token:
            raise ApiError("API token is not configured")

        url = self.base_url + path
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise ApiError(
                f"HTTP error {exc.code} from Domoriks API",
                {
                    "url": url,
                    "http_status": exc.code,
                    "http_body": body,
                    "request_json": payload,
                },
            ) from exc
        except urllib.error.URLError as exc:
            raise ApiError(
                "Failed to connect to Domoriks API",
                {
                    "url": url,
                    "request_json": payload,
                    "reason": str(exc.reason),
                },
            ) from exc
        except json.JSONDecodeError as exc:
            raise ApiError(
                "Invalid JSON response from Domoriks API",
                {
                    "url": url,
                    "request_json": payload,
                },
            ) from exc


def _encode_modbus_rtu_frame(slave: int, function: int, payload: bytes) -> bytes:
    base = bytes([slave & 0xFF, function & 0xFF]) + payload
    crc = _crc16_modbus(base)
    return base + struct.pack("<H", crc)


def _crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF
