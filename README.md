# SCAT: Signaling Collection and Analysis Tool

This application parses diagnostic messages of Qualcomm and Samsung baseband
(from diagnostic interfaces such as USB or serial), and generates a stream of
GSMTAP packet containing cellular control plane messages. This fork additionally provides more detailed KPIs via application
log messages and via UDP as JSON.

## About this fork

This fork extends SCAT to expose **KPIs and event messages** that are not normally available via AT commands. The main goal is to feed real-time cellular metrics and events into automation and dashboards (e.g. [Node-RED](https://nodered.org) on Windows) for monitoring and visualization.

**Tested hardware:** Qualcomm-based **SIM7600 Cat 4** modem (serial diagnostic port on Windows). Windows drivers for the SIM7600 are available on the [Waveshare wiki](https://www.waveshare.com/wiki/SIM7600X_Windows_Drive).

**Typical use-case:** Run SCAT on a **Windows 10 PC** with the modem on a diag serial port (e.g. COM14). A suitable method of controlling the modem with AT commands on the AT comm port is required (e.g. a separate terminal, script or Node-Red). Use **Node-RED** to receive the JSON KPI stream (e.g. `--json-udp-port 9999`) and build a **web dashboard** to visualize serving cell (RSRP, RSRQ, PCI, EARFCN), RRC state, throughput, RACH, RRC failure events, and other KPIs. This gives visibility into link quality, handovers, and failures without relying only on AT commands. For GSMTAP, **Wireshark** is needed; the main SCAT output (GSMTAP) is monitored there to inspect LTE SIBs and RRC configuration (e.g. radio parameters)—for example, use a display filter such as `gsmtap && frame contains "RRC" && !icmp` to focus on RRC-related traffic.

**Features and changes in this fork (Qualcomm / LTE):**

* **KPI output** (`--kpi`): Serving and neighbor cell (RSRP, RSRQ, RSSI, PCI, EARFCN, priority), RRC state (including RRC_SEARCH, RRC_INACTIVE), DL/UL MCS, estimated TX power (from PHR), TA, RACH result, and combined throughput (from MAC TB sizes). TX power can be inverted for power-control intuition (`--invert-tx-power`); 23 dBm is suppressed in the log to avoid phantom values.
* **JSON over UDP** (`--json-udp-port`): Each KPI line is sent as a structured JSON packet to localhost (e.g. for Node-RED). Types include `lte_primary_cell`, `lte_rrc_state`, `lte_rach`, `rrc_event`, `lte_throughput`, and others (see [KPI_USAGE.md](KPI_USAGE.md)).
* **RRC failure events**: Any Qualcomm event whose name contains `FAILURE` (e.g. `EVENT_LTE_RRC_RADIO_LINK_FAILURE`, `EVENT_LTE_RRC_HO_FAILURE`) is printed to the log and sent as JSON (`type: "rrc_event"`) when `--kpi` is used.
* **LTE handover**: RRC Connection Reconfiguration and ReconfigurationComplete are detected and printed (and sent to GSMTAP) when `--kpi` is used.
* **Serial / init robustness**: Clear error handling when the COM port is in use or the modem is unresponsive; optional init retries; clean exit on serial errors during run (no traceback).
* **Documentation**: [KPI_USAGE.md](KPI_USAGE.md) describes all KPI output, JSON types, and options.

This fork was developed using [Cursor](https://cursor.com). Credit also goes to [RifkyTheCyber](https://www.youtube.com/@RifkyTheCyber).

For details on original SCAT (requirements, installation, usage, and options), see the [SCAT repository](https://github.com/fgsect/scat).

## Requirements

### On PC

**This fork** is used and tested on **Windows 10** (serial COM port, Node-RED dashboard). A SIM card for the modem is required. Python 3.10 is a minimum requirement. Required external modules: [pyUSB](https://pypi.org/project/pyusb/), [pySerial](https://pypi.org/project/pyserial/), [bitstring](https://bitstring.readthedocs.io/en/stable/), [packaging](https://pypi.org/project/packaging/). Optional: [libscrc](https://github.com/hex-in/libscrc). For Wireshark versions, GSMTAPv3, and other upstream requirements, see the [SCAT repository](https://github.com/fgsect/scat).

## Installation

Install before use (running from a git checkout without installing will not work):

```
$ pip install signalcat
```

For development: `pip install -e .` on your checkout directory. For Linux udev/ModemManager and other installation details, see the [SCAT repository](https://github.com/fgsect/scat).

## Usage

For baseband types (`-t qc`, `-t sec`, `-t hisi`), USB access, dump mode, default ports (GSMTAP 4729, etc.), and advanced options, see the [SCAT repository](https://github.com/fgsect/scat). This section covers only usage relevant to this fork.

### Qualcomm KPI and JSON output (LTE)

With `-t qc` you can enable KPI logging and optional JSON over UDP:

* **`--kpi`** — Show LTE KPIs in the log: DL/UL MCS, serving cell (EARFCN, PCI, RSRP, RSSI, RSRQ), neighbor cells, RRC state, and estimated TX power. In RRC_CONNECTED, if the modem does not report serving cell, the last known SCell is re-printed at most every 2 seconds so you still see EARFCN/PCI/RSRP.
* **`--dl-bandwidth`** — DL bandwidth in MHz (1.4, 3, 5, 10, 15, or 20) for MCS lookup when cell info is not yet available.
* **`--json-udp-port`** — Send each log line as JSON over UDP to `127.0.0.1:PORT` (e.g. for automation or dashboards).
* **`--no-gsmtap`** — Do not emit GSMTAP packets (use with `--json-udp-port` for JSON-only output; no traffic on port 4729).

Example (serial + KPI + 20 MHz DL + JSON to port 9999, no GSMTAP):

```bash
python -m scat -t qc -s COM14 --kpi --dl-bandwidth 20 --json-udp-port 9999 --no-gsmtap
```

GSMTAP control-plane packets use `-H` (host) and `-P` (port); see the [SCAT repository](https://github.com/fgsect/scat) for defaults. See **[KPI_USAGE.md](KPI_USAGE.md)** for full KPI output description, JSON types, and notes.

### Tested Devices

**This fork:** Tested on a **SIM7600 Cat 4** modem (Qualcomm-based) over **serial (COM port)** on **Windows 10**, with Node-RED consuming the JSON KPI stream for dashboard visualization. For the upstream device list, see the [SCAT wiki](https://github.com/fgsect/scat/wiki/Devices).

## Known Bugs

For known upstream issues (e.g. init hangs, secure log), see the [SCAT repository](https://github.com/fgsect/scat).

## License

SCAT is free software; you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

## References

For academic citation and upstream acknowledgements, see the [SCAT repository](https://github.com/fgsect/scat).
