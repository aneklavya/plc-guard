"""A minimal Modbus/TCP client written from the protocol, standard library only.

It exists to make one point visible: a Modbus request is a few bytes with a
function code, an address and a value. There is no login, no key and no
signature, so anyone who can reach TCP port 502 can read and write the PLC.

Frame layout (all big-endian):
  MBAP header: transaction id (2) | protocol id = 0 (2) | length (2) | unit id (1)
  PDU:         function code (1) | data (...)
"""
from __future__ import annotations

import socket
import struct

READ_COILS = 0x01
READ_HOLDING_REGISTERS = 0x03
WRITE_SINGLE_COIL = 0x05
WRITE_SINGLE_REGISTER = 0x06


class ModbusError(RuntimeError):
    pass


class ModbusClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 502, unit: int = 1,
                 timeout: float = 3.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.unit = unit
        self.tid = 0

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _call(self, function: int, data: bytes) -> bytes:
        self.tid = (self.tid + 1) & 0xFFFF
        pdu = bytes([function]) + data
        frame = struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu
        self.sock.sendall(frame)
        header = self._recv(7)
        tid, _proto, length, _unit = struct.unpack(">HHHB", header)
        body = self._recv(length - 1)
        if body[0] == function | 0x80:
            raise ModbusError(f"exception code {body[1]} for function {function}")
        return body[1:]

    def _recv(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ModbusError("connection closed")
            buf += chunk
        return buf

    # -- the four functions the demo needs ------------------------------------

    def read_holding_registers(self, address: int, count: int = 1) -> list[int]:
        data = self._call(READ_HOLDING_REGISTERS, struct.pack(">HH", address, count))
        return list(struct.unpack(f">{count}h", data[1:1 + 2 * count]))

    def write_register(self, address: int, value: int) -> None:
        self._call(WRITE_SINGLE_REGISTER, struct.pack(">Hh", address, value))

    def read_coils(self, address: int, count: int = 1) -> list[bool]:
        data = self._call(READ_COILS, struct.pack(">HH", address, count))
        bits = int.from_bytes(data[1:], "little")
        return [bool(bits >> i & 1) for i in range(count)]

    def write_coil(self, address: int, value: bool) -> None:
        self._call(WRITE_SINGLE_COIL, struct.pack(">HH", address, 0xFF00 if value else 0))
