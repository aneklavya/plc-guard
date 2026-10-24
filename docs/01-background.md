# 1. Background

## What a PLC is

A **Programmable Logic Controller (PLC)** is a ruggedised industrial computer
that controls a physical process: pumps in a water plant, conveyors in a
factory, burners in a boiler. It runs one program in an endless loop called
the **scan cycle**:

1. Read every input (sensors, switches) into memory.
2. Run the program once, top to bottom.
3. Write every output (motors, valves, alarms).
4. Repeat, typically every 10 to 100 ms.

Because the program runs forever and drives real equipment, a bug is not a
crash on a screen. It can be an overflowing tank, a motor that starts while
someone is working on it, or a boiler that keeps firing above its safe
pressure.

## IEC 61131-3 and Structured Text

**IEC 61131-3** is the international standard for PLC programming languages.
It defines five; PLCGuard works on **Structured Text (ST)**, the textual one,
which looks like Pascal:

```pascal
PROGRAM PumpStation
  VAR
    hmi_start      AT %QX1.0 : BOOL;   (* command bit from the operator screen *)
    low_level_sw   AT %IX0.0 : BOOL;   (* physical sensor *)
    pump_run       AT %QX0.0 : BOOL;   (* physical output *)
  END_VAR

  pump_run := hmi_start AND NOT low_level_sw;
END_PROGRAM
```

Things to know when reading ST:

- `:=` is assignment, `=` is comparison.
- A **POU** (Program Organisation Unit) is a `PROGRAM`, `FUNCTION_BLOCK` or
  `FUNCTION`.
- Variables are declared in `VAR ... END_VAR` blocks. `VAR CONSTANT` makes
  them read-only.
- `AT %...` binds a variable to a physical or memory **location**.

## Locations: where the danger comes from

The `AT` address says where a variable lives, and that tells you who can
change it. PLCGuard follows OpenPLC's conventions:

| Address | Meaning | Who can write it | Trust |
|---|---|---|---|
| `%IX0.0` | digital input (switch, sensor) | the physical world | trusted sensor |
| `%IW0` | analog input (level, pressure) | the physical world | trusted sensor |
| `%QX0.0` | digital output (motor, valve) | the program | actuator |
| `%QX1.x` | used here as HMI command bits | operator screen | operator command |
| `%QW0` | analog output (setpoint) | the program | actuator |
| `%MW`, `%MD`, `%ML` | memory words = **Modbus holding registers** | **anyone on the network** | **untrusted** |

That last row is the key security idea of the whole project.

## Modbus and why the network is untrusted

**Modbus/TCP** is the most common industrial network protocol. It was
designed in 1979 for closed serial links and has **no authentication and no
encryption**. Anyone who can reach the PLC on TCP port 502 can read and write
its holding registers (`%MW...`). Tools like `mbpoll` or a ten-line Python
script with `pymodbus` can do it.

So if a PLC program takes a value from `%MW10` and uses it as a motor speed,
a tank setpoint or a safety limit without checking it, then anyone on the
plant network controls that motor, tank or limit. Real incidents show this
matters: Stuxnet (2010) manipulated PLC logic to destroy centrifuges, and the
2021 Oldsmar water-plant intrusion changed a chemical dosing setpoint
remotely.

## HMI

An **HMI (Human-Machine Interface)** is the operator's touchscreen. It talks
to the PLC over the same network (often Modbus), so HMI inputs are also
network inputs. A value typed on the HMI must be range-checked by the PLC,
because the PLC cannot tell the HMI apart from an attacker.

## OpenPLC

**OpenPLC** is an open-source PLC runtime that runs on Linux, a Raspberry Pi
or in Docker. It executes ST programs and exposes them over Modbus/TCP. Its
compiler, **MatIEC**, translates ST into C. PLCGuard uses OpenPLC's address
conventions now, and will use MatIEC in Stage 3 (to check that a repaired
program still compiles) and the runtime in Stage 5 (for a live attack demo).

## The 8 vulnerability classes

PLCGuard detects eight classes. Each is mapped to the closest **CWE** (Common
Weakness Enumeration, MITRE's catalogue of software weakness types).

### INPUT_VALIDATION (CWE-20)
A network-writable value reaches an output without a range check.
```pascal
speed_sp AT %MW0 : INT;
motor_speed AT %QW0 : INT;
motor_speed := speed_sp;                    (* vulnerable: any value goes *)
motor_speed := LIMIT(0, speed_sp, 1500);    (* fixed: clamped *)
```

### MISSING_INTERLOCK (CWE-693)
An actuator can be switched on without checking safety conditions. An
**interlock** is a condition that must be true before equipment may run
(e-stop released, tank not empty, motor not overloaded).
```pascal
pump_run := run_latch;                                          (* vulnerable *)
pump_run := run_latch AND NOT low_level_sw AND NOT motor_overload;  (* fixed *)
```

### HARDCODED_CREDENTIAL (CWE-798)
A password or PIN is written into the logic.
```pascal
IF key_switch OR hmi_pin = 4711 THEN maint_mode := TRUE; END_IF;  (* vulnerable *)
```

### LOGIC_BOMB (CWE-511)
Hidden code that changes behaviour once a counter, date or magic value is
reached. Usually malicious (an insider or a supply-chain attacker).
```pascal
IF cycle_count > 864000 THEN conveyor_motor := hmi_start; END_IF;  (* after ~1 day *)
```

### OOB_INDEX (CWE-129)
An array is indexed with a value nobody checked. PLCs often have no memory
protection, so this can read or overwrite unrelated memory.
```pascal
temp_sp := recipe_temp[hmi_recipe_idx];     (* idx from the HMI, could be 9999 *)
```

### DIV_BY_ZERO (CWE-369)
Division by a variable that can be zero. On many PLCs this faults the CPU,
which stops the whole process.

### UNSAFE_STATE_TRANSITION (CWE-1245)
A state machine (`CASE state OF ...`) can be forced into any state or can skip
a required one, for example skipping the purge step before lighting a burner.
```pascal
state := hmi_state;                  (* the network chooses the state *)
IF skip_purge THEN state := 3; END_IF;
```

### UNPROTECTED_CRITICAL_VAR (CWE-284)
A safety parameter (trip point, limit) lives in a network-writable register
instead of being a constant.
```pascal
trip_pressure AT %MW5 : INT;    (* vulnerable: attacker raises the trip point *)
VAR CONSTANT trip_pressure : INT := 120; END_VAR   (* fixed *)
```

## Why use an LLM for this at all?

Static analysis tools for PLC code exist, but they work on patterns: "an
actuator whose name contains *pump*", "a variable called *pin* compared to a
literal". Real plant code is full of names like `Q_M101_FWD` or `v17`. An LLM
can, in principle, reason about **what a variable does** (it is written to a
`%QX` output and switched by an operator bit, so it is an actuator) instead of
what it is called. Stage 2 tests whether that is true. See
[Stage 2](04-stage2-llm.md).

Next: [Architecture](02-architecture.md)
