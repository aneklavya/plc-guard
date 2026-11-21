# 12. How SCADA systems work

*A refresher from the ground up: what each box is, how they talk, what
happens when an operator presses a button, and where the security holes are.
Everything is tied back to PLCGuard so you can point at a concrete example.*

## 1. The one-paragraph version

**SCADA** (Supervisory Control And Data Acquisition) is the software and
network that lets a few operators watch and steer a process spread over a
plant or a whole region: water treatment, a pipeline, a power grid. The
**PLCs** in the field do the actual control, fast and locally, every few
milliseconds. The **SCADA server** sits above them: it constantly *polls*
every PLC for its values, shows them on **HMI** screens, raises **alarms**,
stores history in a **historian**, and sends the operator's commands back
down to the PLCs. SCADA *supervises*; the PLC *controls*. If the SCADA
server dies, the PLCs keep running the plant on their own.

## 2. The layers (Purdue model)

Industrial networks are usually described with the **Purdue Enterprise
Reference Architecture**, numbered from the physical process upwards:

```
 Level 5  Enterprise / internet         email, ERP, cloud
 Level 4  Business network              office PCs, planning
 ─────────────────────── DMZ (Level 3.5) ───────────────────────
          historian replica, patch server, remote-access jump host
 ───────────────────────────────────────────────────────────────
 Level 3  Site operations               historian, SCADA servers, engineering tools
 Level 2  Supervisory control           HMI screens, SCADA clients, alarm displays
 Level 1  Basic control                 PLCs, RTUs, safety controllers (SIS)
 Level 0  Physical process              sensors, valves, pumps, motors, drives
```

The key rule: traffic should only cross a boundary through a controlled
point (firewall, DMZ, data diode). In practice many plants are "flat": the
office network can reach the PLCs directly, which is how a phishing email at
Level 4 becomes a valve opening at Level 0.

## 3. The components

| Component | Level | What it is | In PLCGuard |
|---|---|---|---|
| **Sensor / transmitter** | 0 | Measures something: level, pressure, flow, temperature. Usually a 4–20 mA analog signal or a dry contact. | `%IW0` (analog), `%IX0.0` (digital) |
| **Actuator** | 0 | Changes the process: pump motor, valve, heater contactor, drive (VFD). | `%QX0.0`, `%QW0` |
| **PLC** | 1 | Industrial computer that reads inputs, runs the control program in a loop (the **scan cycle**, e.g. 20 ms), writes outputs. Works even with no network. | The OpenPLC runtime in Docker |
| **RTU** (Remote Terminal Unit) | 1 | Like a PLC but built for remote sites: low power, radio/cellular links, store-and-forward, often DNP3. Pipelines and substations use them. | — |
| **SIS** (Safety Instrumented System) | 1 | A *separate*, certified controller whose only job is to shut the process down safely (high pressure → close fuel valve). Must stay independent of normal control. | Not modelled; our "trip" programs (08, 13, 26) imitate SIS logic |
| **HMI** | 2 | The operator screen: pictures of tanks and pumps with live values and buttons. Can be a panel on the machine or a SCADA client on a PC. | `%QX1.x` "HMI command bits", `%MW` setpoints |
| **SCADA server** (a.k.a. master, front-end, I/O server) | 2–3 | Polls all PLCs/RTUs, keeps the **tag database**, evaluates alarms, forwards operator commands, feeds HMIs and historian. Usually redundant (primary + hot standby). | Our attack script plays a (rogue) SCADA master |
| **Historian** | 3 | Time-series database of every tag (e.g. every second for years). Used for trends, reports, investigations. | `results/` is our "historian" of experiments, loosely |
| **Engineering workstation** | 3 | PC with the vendor tools to write and download PLC programs. The most powerful machine in the plant for an attacker: it can change the logic itself. | Your laptop + OpenPLC web UI |
| **Alarm system** | 2–3 | Compares tags against limits, notifies operators, records acknowledgements. | `LAH_501`, `PAH_301` outputs |
| **OPC UA / gateways** | 3 | Translate between protocols and expose data upward to business systems. | — |

## 4. Tags: how everything is named

SCADA does not think in "register 1024", it thinks in **tags**: named
variables like `TANK1.LEVEL` or `P501.RUN_CMD`. The **tag database** in the
SCADA server maps each tag to *which device* and *which address*:

| Tag | Device | Protocol address | PLC variable | Direction |
|---|---|---|---|---|
| `TANK1.LEVEL_PCT` | PLC-01 (10.0.1.10) | input register 0 | `level_pct AT %IW0` | read |
| `TANK1.HIGH_SW` | PLC-01 | discrete input 0 | `high_switch AT %IX0.0` | read |
| `TANK1.OUTLET_SP` | PLC-01 | holding register 1024 | `hmi_valve_sp AT %MW0` | read/write |
| `TANK1.OUTLET_CMD` | PLC-01 | holding register 0 | `outlet_cmd AT %QW0` | read |
| `TANK1.AUTO` | PLC-01 | coil 8 | `hmi_auto AT %QX1.0` | write |

### OpenPLC's address map (what the demo uses)

| PLC address | Modbus object | Modbus address | Function codes |
|---|---|---|---|
| `%IX0.0` … `%IX99.7` | Discrete input | 0 … 799 (byte×8+bit) | read: 02 |
| `%QX0.0` … `%QX99.7` | Coil | 0 … 799 (`%QX1.0` = 8) | read 01, write 05 / 15 |
| `%IW0` … | Input register | 0 … | read 04 |
| `%QW0` … | Holding register | 0 … 1023 | read 03, write 06 / 16 |
| `%MW0` … | Holding register | 1024 … | read 03, write 06 / 16 |
| `%MD0`, `%ML0` | Holding registers (32/64-bit) | 2048 …, 4096 … | 03 / 16 |

Note what is **writable**: coils (`%QX`) and holding registers (`%QW`,
`%MW`). Physical inputs (`%IX`, `%IW`) are read-only over Modbus because the
real world writes them. That is exactly why PLCGuard treats `%M` registers as
untrusted.

## 5. How the communication actually happens

### 5.1 Polling (master/slave, or client/server)

Modbus is **request/response**. The SCADA server is the *client* (master); the
PLC is the *server* (slave) and only ever answers. The SCADA server runs a
**poll cycle**, for example every 1 second for each PLC:

```
SCADA server                                       PLC-01
     │  FC 04  read input registers 0..9              │
     │ ──────────────────────────────────────────────►│
     │ ◄──────────────────────────────────────────────│ values
     │  FC 02  read discrete inputs 0..15             │
     │ ──────────────────────────────────────────────►│
     │ ◄──────────────────────────────────────────────│
     │  FC 03  read holding registers 0..9, 1024..1033│
     │ ──────────────────────────────────────────────►│
     │ ◄──────────────────────────────────────────────│
     │        ... same for PLC-02, PLC-03 ...         │
```

Meanwhile the PLC keeps scanning every 20 ms regardless of the network. The
PLC's I/O and memory image is like a shared whiteboard: the program writes
outputs to it each scan, the Modbus server inside the PLC reads from and
writes to the same whiteboard when requests arrive.

Other protocols do better: **DNP3** (water, power, North America) supports
*report by exception* (the outstation sends only changes) and time-stamped
events; **IEC 60870-5-104** (European power grids) is similar; **OPC UA** is
a modern, object-oriented protocol *with* built-in security (certificates,
encryption), increasingly used above Level 1.

### 5.2 One operator action, end to end

Operator clicks **"Set outlet valve to 60 %"** on the HMI:

1. HMI client sends the new value for tag `TANK1.OUTLET_SP` to the SCADA
   server (often over a vendor protocol or OPC).
2. SCADA server looks up the tag: PLC-01, holding register 1024.
3. SCADA server sends a Modbus **Write Single Register** request to
   10.0.1.10:502.
4. The PLC's Modbus server writes 60 into `%MW0` in its memory image.
5. On the next scan (≤ 20 ms later) the program runs
   `outlet_cmd := hmi_valve_sp;` → `%QW0` becomes 60 → the analog output card
   drives 13.6 mA into the valve positioner → the valve opens to 60 %.
6. On the next poll the SCADA server reads holding register 0 (= 60), updates
   the tag, the HMI shows 60 %, the historian stores it.
7. Alarm logic checks the new value; nothing to raise.

### 5.3 What that write looks like on the wire

Write 32767 into holding register 1024 (what the demo attacker does):

```
00 01   transaction id 1
00 00   protocol id 0 (= Modbus)
00 06   length: 6 bytes follow
01      unit id 1
06      function code 06 = Write Single Register
04 00   register address 1024
7F FF   value 32767
```

Twelve bytes. No user name, no password, no signature, no encryption. The
PLC cannot tell this packet from the SCADA server's packet. That is the
fundamental problem, and `demo/modbus.py` builds exactly these bytes in about
30 lines.

## 6. Why SCADA is hard to secure

- **Protocols without authentication**: Modbus (1979), DNP3 (unless the
  Secure Authentication extension is used), S7comm, EtherNet/IP. Designed for
  closed serial links, later put on TCP/IP unchanged.
- **Flat networks**: office and control networks connected, so one infected
  laptop reaches every PLC.
- **Default and weak credentials**: e.g. OpenPLC's web login is
  `openplc / openplc` and the server compares passwords in plain text
  (see `webserver.py`, `login()`).
- **Long lifetimes**: controllers run 15–30 years; patching means stopping
  production, so it rarely happens.
- **Remote access**: vendors and engineers connect in via VPN/TeamViewer;
  Oldsmar (2021) was a remote-desktop takeover of an HMI.
- **Engineering workstations** can download new logic: the attacker does not
  need a protocol bug if they can change the program (Stuxnet did this).
- **Trust in the HMI**: operators see what the HMI shows. Stuxnet replayed
  normal values to the screens while the centrifuges were destroyed.

### Real incidents to know

| Year | Incident | What happened | Layer attacked |
|---|---|---|---|
| 2010 | **Stuxnet** | Modified Siemens S7 PLC logic to change centrifuge speeds, replayed normal values to the HMI | Engineering workstation → PLC logic |
| 2015 | **Ukraine grid** | Attackers used the SCADA/HMI systems themselves to open breakers; ~225,000 customers lost power | SCADA / HMI, remote access |
| 2016 | **Industroyer / CrashOverride** | Malware that spoke IEC 104 and IEC 61850 directly to substation equipment | Protocol level |
| 2017 | **Triton / Trisis** | Targeted Schneider Triconex safety controllers (SIS) at a petrochemical plant | Safety system |
| 2021 | **Oldsmar, Florida** | Remote access to an HMI; sodium hydroxide setpoint raised 100× (caught by an operator) | HMI setpoint without PLC-side limits |

Oldsmar is the closest to PLCGuard: if the PLC had clamped the setpoint (our
INPUT_VALIDATION class, scenario 11 `chlorine_dosing`), the HMI write would
have done nothing dangerous.

## 7. Defences, and where PLCGuard fits

**Defence in depth**: no single control is enough.

| Layer | Defence | Standard / example |
|---|---|---|
| Network | Zones and conduits, firewalls between Purdue levels, DMZ, no direct internet | IEC 62443-3-2 |
| Network | Allow-list which master may talk to which PLC; Modbus-aware firewalls that block writes | Deep packet inspection |
| Monitoring | ICS intrusion detection that learns normal polls and flags new writes | Network IDS |
| Access | Unique accounts, MFA for remote access, no default passwords | IEC 62443-4-2 |
| Protocol | OPC UA with certificates, DNP3 Secure Authentication, Modbus/TCP Security (TLS) | — |
| **PLC program** | **Range checks, interlocks, constants for trip points, no backdoors, state machines that cannot be forced** | *Top 20 Secure PLC Coding Practices* |
| Safety | Independent SIS with hard-wired trips that software cannot override | IEC 61511 |

PLCGuard works on the **PLC program** row. It assumes the network *is*
reachable by an attacker (realistic) and asks: does the logic itself stay
safe when someone writes arbitrary values? The demo shows both sides:

- the **register attack** (writing 32767 to the setpoint) is stopped by the
  repaired code, which clamps the value to 0–100;
- the **coil attack** (pressing the HMI "auto" button over Modbus) still
  works after the repair, because pressing that button is a *legitimate*
  operator command. Code cannot tell a real operator from an attacker; only
  network controls and authentication can. That is why secure code is one
  layer of defence in depth, not a replacement for it.

## 8. Mapping the PLCGuard demo onto a real plant

```
 Real plant                          PLCGuard demo
 ──────────                          ─────────────
 Field devices (Level 0)             (none: inputs stay 0, outputs are just values)
 PLC (Level 1)                       OpenPLC runtime in Docker, scanning every 20 ms
 Modbus/TCP on port 502              Same, exposed on localhost:502
 SCADA server / HMI (Level 2)        not present; attack_demo.py plays both the
                                     legitimate operator and the attacker
 Engineering workstation (Level 3)   OpenPLC web UI on :8080, driven by demo/openplc.py
 Attacker                            attack_demo.py writing registers and coils
```

## 9. Self-test

1. Which device keeps controlling the process if the SCADA server crashes?
   *(The PLC.)*
2. Why can an attacker write `%MW0` but not `%IW0` over Modbus? *(Holding
   registers are writable; input registers mirror physical inputs.)*
3. What is in a Modbus write request, and what is missing from it? *(Address,
   function code, value; no authentication.)*
4. Why was Triton especially dangerous? *(It targeted the safety system, the
   last line of defence.)*
5. Our repair stops the register attack but not the coil attack. Why is that
   correct behaviour for the PLC code? *(The coil is a legitimate operator
   command; distinguishing operators from attackers is a network /
   authentication problem.)*
6. In the Purdue model, where should the historian that office users read
   from live? *(A replica in the DMZ, not the Level 3 original.)*

Next: back to the [index](README.md)
