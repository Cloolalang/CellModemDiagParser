# SCAT — Signaling Collection and Analysis Tool

SCAT captures and parses cellular baseband diagnostic streams (Qualcomm and others) and can emit GSMTAP packets and KPI-style log output.

## Requirements

- Python ≥ 3.10
- pyserial, pyusb, bitstring, packaging (see `pyproject.toml`)

## Basic usage (Qualcomm)

```bash
python -m scat -t qc -s COM13
```

- `-t qc` — Qualcomm parser  
- `-s COM13` — Serial port (or `/dev/ttyUSB0` on Linux)

## KPI and LTE options

With **`--kpi`**, SCAT prints LTE KPI lines to stdout and (if configured) sends them as JSON over UDP.

### Common Qualcomm options

| Option | Description |
|--------|-------------|
| `--kpi` | Enable KPI output (Primary Cell, Neighbor cells, RACH, throughput, UL avg MCS, etc.) |
| `--dl-bandwidth` | DL bandwidth in MHz for MCS/TBS: `1.4`, `3`, `5`, `10`, `15`, or `20` |
| `--json-udp-port PORT` | Send log lines as JSON to `127.0.0.1:PORT` (e.g. `9999`) |
| `--disable-crc-check` | Disable CRC checks (faster, less CPU) |

### Throughput line

Every 5 seconds in RRC_CONNECTED you get a line like:

```
Radio 0: LTE throughput: 20.02 Mbps [UL avg MCS: 18.5] (UL retransmit: 47.2%)
```

- **Mbps** — Combined DL+UL throughput in the last 5 s window.  
- **UL avg MCS** — Average uplink MCS (0–28) of UL grants in that window. Higher = better UL channel quality.  
- **UL retransmit %** — Inferred from NDI in the UL grant (modem-dependent; can be unreliable).

### UL metrics (Qualcomm)

| Option | Description |
|--------|-------------|
| `--ul-ndi-bit BIT` | Bit index (0–15) in UL grant used for NDI. Default `6`. Try `5` or `10` if retransmit % looks wrong. |
| `--invert-ul-ndi` | Invert NDI logic (same NDI ⇒ new TX, toggled ⇒ retx). Use if UL retransmit is ~100% when link is good. |
| `--invert-ul-mcs` | Display UL avg MCS as `(28 - MCS)`. Use when UL MCS goes down as path loss improves. |
| `--no-ul-retransmit` | Do not show `(UL retransmit: X%)` on the throughput line. |

### Other KPI

- **LTE Primary Cell** — EARFCN, PCI, RSRP, RSSI, RSRQ.  
- **LTE KPI RACH** — Random access: result, attempt, preamble, preamble_power_dB, ta, tc_rnti, earfcn.  
- **LTE RRC State** — Idle / Connected / etc.  
- **LTE Timing Advance** — TA from event 1498 when present.  
- **LTE handover** — RRCConnectionReconfiguration(Complete).

## JSON UDP (e.g. `--json-udp-port 9999`)

Each KPI line is sent as a JSON object. Throughput lines look like:

```json
{"type": "lte_throughput", "mbps": 20.02, "ul_avg_mcs": 18.5, "ul_retx_pct": 47.2}
```

- `ul_avg_mcs` — Present when there were UL TBs in the window (and subject to `--invert-ul-mcs` if set).  
- `ul_retx_pct` — Omitted if you use `--no-ul-retransmit`.

## Example

```bash
python -m scat -t qc -s COM13 --kpi --dl-bandwidth 20 --json-udp-port 9999 --disable-crc-check --invert-ul-mcs
```

## License

GPL-2.0-or-later. See project URLs in `pyproject.toml` (e.g. https://github.com/fgsect/scat).
