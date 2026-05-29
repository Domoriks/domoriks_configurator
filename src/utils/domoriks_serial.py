"""Serial (RS-485) client for direct Modbus RTU communication with Domoriks devices."""

from __future__ import annotations

import struct
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import serial
import serial.tools.list_ports

from utils.domoriks_api import ApiError, RawExchange, _encode_modbus_rtu_frame, _crc16_modbus

_log = logging.getLogger(__name__)


# At 115200 baud, 1 char ≈ 0.087ms. Modbus RTU standard is 3.5 chars ≈ 0.3ms.
# Windows OS scheduler can't reliably do sub-ms, so use 3ms as practical minimum.
_INTER_BYTE_TIMEOUT_S = 0.003
_DEFAULT_BAUD = 115200
_READ_COILS = 0x01
_READ_HOLDING_REGISTERS = 0x03
_WRITE_SINGLE_REGISTER = 0x06
_WRITE_MULTIPLE_REGISTERS = 0x10


@dataclass
class SerialPortInfo:
    device: str
    description: str
    manufacturer: str
    hwid: str
    vid: Optional[int]
    pid: Optional[int]


def list_serial_ports() -> List[str]:
    """Return list of available COM port names."""
    return [p.device for p in list_serial_port_infos()]


def list_serial_port_infos() -> List[SerialPortInfo]:
    """Return detailed serial port entries for UI display and auto-selection."""
    infos: List[SerialPortInfo] = []
    for p in serial.tools.list_ports.comports():
        infos.append(
            SerialPortInfo(
                device=p.device,
                description=(getattr(p, "description", "") or ""),
                manufacturer=(getattr(p, "manufacturer", "") or ""),
                hwid=(getattr(p, "hwid", "") or ""),
                vid=getattr(p, "vid", None),
                pid=getattr(p, "pid", None),
            )
        )
    return infos


def find_stlink_vcp_port() -> Optional[str]:
    """Best-effort detection of an ST-Link virtual COM port."""
    st_vid = 0x0483  # STMicroelectronics
    stlink_vcp_pids = {0x374B, 0x374E, 0x3752, 0x3753, 0x3754}

    for p in list_serial_port_infos():
        desc = p.description.lower()
        manu = p.manufacturer.lower()
        hwid = p.hwid.lower()

        if "stlink" in desc or "st-link" in desc or "stlink" in hwid or "st-link" in hwid:
            return p.device
        if "virtual com" in desc and ("st" in desc or "stmicro" in desc):
            return p.device
        if p.vid == st_vid and (p.pid in stlink_vcp_pids):
            return p.device
        if "stmicroelectronics" in manu and "com" in p.device.lower():
            return p.device

    return None


class DomoriksSerialClient:
    """Synchronous serial Modbus RTU client matching DomoriksApiClient interface."""

    def __init__(self, port: str, baudrate: int = _DEFAULT_BAUD):
        self.port = port
        self.baudrate = baudrate
        self.byte_swap: Optional[bool] = None

    def detect_range(self, start_slave: int, end_slave: int, timeout: float) -> Dict[str, Any]:
        """Scan slave range using read_coils. timeout is per-slave in seconds."""
        reachable: List[int] = []
        unreachable: List[int] = []
        scan_start = int(start_slave)
        scan_end = int(end_slave)
        for slave in range(scan_start, scan_end + 1):
            if self._ping_slave(slave, timeout):
                reachable.append(slave)
            else:
                unreachable.append(slave)
        return {"reachable": reachable, "unreachable": unreachable}

    def raw(self, frame_hex: str, timeout: float) -> RawExchange:
        """Send raw RTU frame and return response."""
        frame = bytes.fromhex(frame_hex)
        response_bytes = self._transact(frame, timeout)

        request_info = {"frame": frame_hex}

        if response_bytes is None:
            return RawExchange(
                request=request_info,
                response={"response": None},
            )

        # Parse response: slave(1) + function(1) + payload(N) + crc(2)
        if len(response_bytes) < 4:
            return RawExchange(
                request=request_info,
                response={"response": None},
            )

        slave = response_bytes[0]
        function = response_bytes[1]
        payload = response_bytes[2:-2]

        return RawExchange(
            request=request_info,
            response={
                "response": {
                    "slave": slave,
                    "function": function,
                    "payload": payload.hex(),
                    "exception_code": payload[0] if (function & 0x80) and payload else None,
                }
            },
        )

    def read_holding_registers(self, slave: int, start: int, count: int, timeout: float) -> RawExchange:
        payload = struct.pack(">HH", int(start), int(count))
        frame = _encode_modbus_rtu_frame(int(slave), _READ_HOLDING_REGISTERS, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received (serial)", {
                "port": self.port,
                "request_frame": frame.hex(),
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during read holding registers", {
                "port": self.port,
                "exception_code": response.get("exception_code"),
            })

        if function != _READ_HOLDING_REGISTERS:
            raise ApiError("Unexpected Modbus function in read response", {
                "port": self.port,
                "response": response,
            })

        payload_hex = response.get("payload", "")
        data = bytes.fromhex(payload_hex)
        if not data:
            raise ApiError("Empty read payload", {"port": self.port})

        byte_count = data[0]
        reg_data = data[1: 1 + byte_count]
        if len(reg_data) != byte_count or byte_count % 2 != 0:
            raise ApiError("Invalid read payload length", {
                "port": self.port,
                "byte_count": byte_count,
                "actual_len": len(reg_data),
            })

        registers: List[int] = []
        for i in range(0, len(reg_data), 2):
            registers.append(struct.unpack(">H", reg_data[i: i + 2])[0])

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
        frame = _encode_modbus_rtu_frame(int(slave), _WRITE_MULTIPLE_REGISTERS, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received (serial)", {
                "port": self.port,
                "request_frame": frame.hex(),
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during write multiple registers", {
                "port": self.port,
                "exception_code": response.get("exception_code"),
            })

        if function != _WRITE_MULTIPLE_REGISTERS:
            raise ApiError("Unexpected Modbus function in write response", {
                "port": self.port,
                "response": response,
            })

        return exchange

    def write_single_register(self, slave: int, address: int, value: int, timeout: float) -> RawExchange:
        payload = struct.pack(">HH", int(address) & 0xFFFF, int(value) & 0xFFFF)
        frame = _encode_modbus_rtu_frame(int(slave), _WRITE_SINGLE_REGISTER, payload)
        exchange = self.raw(frame.hex(), timeout)

        response = exchange.response.get("response")
        if response is None:
            raise ApiError("No Modbus response received (serial)", {
                "port": self.port,
                "request_frame": frame.hex(),
            })

        function = int(response.get("function", 0))
        if function & 0x80:
            raise ApiError("Modbus exception during write single register", {
                "port": self.port,
                "exception_code": response.get("exception_code"),
            })

        if function != _WRITE_SINGLE_REGISTER:
            raise ApiError("Unexpected Modbus function in write single response", {
                "port": self.port,
                "response": response,
            })

        return exchange

    def _ping_slave(self, slave: int, timeout: float) -> bool:
        """Send read_coils(0, 1) to check if slave responds."""
        payload = struct.pack(">HH", 0, 1)
        frame = _encode_modbus_rtu_frame(slave, _READ_COILS, payload)
        _log.debug("PING slave %d: start", slave)
        response = self._transact(frame, timeout)
        if response is None:
            _log.debug("PING slave %d: no response (timeout)", slave)
            return False
        _log.debug("PING slave %d: RX %s (%d bytes)", slave, response.hex(), len(response))
        # Valid response: at least slave + function + 1 data byte + 2 CRC
        if len(response) < 5:
            _log.debug("PING slave %d: response too short (%d bytes)", slave, len(response))
            return False
        # Check CRC
        crc_calc = _crc16_modbus(response[:-2])
        crc_recv = struct.unpack("<H", response[-2:])[0]
        if crc_calc != crc_recv:
            _log.debug("PING slave %d: CRC mismatch (calc=0x%04X recv=0x%04X)", slave, crc_calc, crc_recv)
            return False
        # Check it's not an exception for our slave
        if response[0] != slave:
            _log.debug("PING slave %d: wrong slave in response (%d)", slave, response[0])
            return False
        _log.debug("PING slave %d: OK", slave)
        return True

    def _transact(self, frame: bytes, timeout: float) -> Optional[bytes]:
        """Open port, send frame, wait for response, close port."""
        try:
            _log.debug("Opening %s @ %d baud", self.port, self.baudrate)
            with serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                inter_byte_timeout=_INTER_BYTE_TIMEOUT_S,
            ) as ser:
                _log.debug("Opened %s", self.port)
                # Flush any stale data
                ser.reset_input_buffer()

                # Small delay after open to let RS-485 adapter settle
                time.sleep(0.005)

                _log.debug("TX [%s] %s (%d bytes)", self.port, frame.hex(), len(frame))
                ser.write(frame)
                ser.flush()

                # Read response using inter_byte_timeout for frame detection
                response = ser.read(1)  # Wait for first byte up to `timeout`
                if not response:
                    _log.debug("RX [%s] no response (timeout=%.3fs)", self.port, timeout)
                    return None

                # Read remaining bytes until inter-byte silence
                remaining = ser.read(256)
                response += remaining

                _log.debug("RX [%s] %s (%d bytes)", self.port, response.hex(), len(response))
                return response if len(response) >= 4 else None

        except serial.SerialException as exc:
            available_ports = list_serial_ports()
            _log.error("Serial error on %s: %s", self.port, exc)
            raise ApiError(
                f"Serial communication error on {self.port}",
                {
                    "port": self.port,
                    "reason": str(exc),
                    "available_ports": available_ports,
                },
            ) from exc
