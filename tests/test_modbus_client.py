"""The demo's hand-written Modbus/TCP client, against a tiny in-process server."""
import socket
import struct
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "demo"))
from modbus import ModbusClient, ModbusError  # noqa: E402


class FakePLC(threading.Thread):
    """Serves holding registers and coils from dicts; records raw requests."""

    def __init__(self):
        super().__init__(daemon=True)
        self.srv = socket.create_server(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.registers, self.coils, self.frames = {}, {}, []

    def run(self):
        conn, _ = self.srv.accept()
        with conn:
            while header := conn.recv(7):
                tid, _, length, unit = struct.unpack(">HHHB", header)
                pdu = conn.recv(length - 1)
                self.frames.append(header + pdu)
                fc = pdu[0]
                if fc == 6:
                    addr, val = struct.unpack(">Hh", pdu[1:5])
                    self.registers[addr] = val
                    reply = pdu
                elif fc == 3:
                    addr, n = struct.unpack(">HH", pdu[1:5])
                    vals = [self.registers.get(addr + i, 0) for i in range(n)]
                    reply = bytes([3, 2 * n]) + struct.pack(f">{n}h", *vals)
                elif fc == 5:
                    addr, val = struct.unpack(">HH", pdu[1:5])
                    self.coils[addr] = val == 0xFF00
                    reply = pdu
                elif fc == 1:
                    addr, n = struct.unpack(">HH", pdu[1:5])
                    bits = sum(1 << i for i in range(n) if self.coils.get(addr + i))
                    nbytes = (n + 7) // 8
                    reply = bytes([1, nbytes]) + bits.to_bytes(nbytes, "little")
                else:
                    reply = bytes([fc | 0x80, 1])  # illegal function
                conn.sendall(struct.pack(">HHHB", tid, 0, len(reply) + 1, unit) + reply)


def test_write_frame_is_twelve_bytes_with_no_credentials():
    plc = FakePLC(); plc.start()
    with ModbusClient("127.0.0.1", plc.port) as mb:
        mb.write_register(1024, 32767)
        assert mb.read_holding_registers(1024) == [32767]
    assert plc.frames[0] == bytes.fromhex("0001 0000 0006 01 06 0400 7fff")


def test_negative_values_and_coils():
    plc = FakePLC(); plc.start()
    with ModbusClient("127.0.0.1", plc.port) as mb:
        mb.write_register(5, -500)
        mb.write_coil(8, True)
        assert mb.read_holding_registers(5) == [-500]
        assert mb.read_coils(8, 2) == [True, False]


def test_exception_response_raises():
    plc = FakePLC(); plc.start()
    with ModbusClient("127.0.0.1", plc.port) as mb:
        try:
            mb._call(0x2B, b"")
        except ModbusError as exc:
            assert "exception code 1" in str(exc)
        else:
            raise AssertionError("expected ModbusError")
