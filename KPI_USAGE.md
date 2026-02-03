# Qualcomm KPI Logging

This fork adds `--kpi` support to output LTE key performance indicators (KPIs) to the log window.

## Usage

```bash
# USB mode - show KPIs in log
scat -t qc -u --kpi

# Serial mode
scat -t qc -s /dev/ttyUSB0 --kpi

# Dump file
scat -t qc -d capture.qmdl --kpi
```

When `--kpi` is used, the MAC layer is automatically enabled (if not already in `--layer`).

## KPI Output

When `--kpi` is used, the following are printed to the log:

### Cell Measurements

| Output | Description |
|--------|-------------|
| **LTE Primary Cell:** | Serving cell (IDLE): EARFCN, PCI, RSRP, RSSI, RSRQ, **priority** (0–7, cell reselection layer priority from network) |
| **LTE Primary Cell (Connected):** | Serving cell (RRC_CONNECTED): PCI, DL RSRP, RSSI, RSRQ |
| **Neighbor cell N:** | Neighbor cell: EARFCN, PCI, RSRP, RSSI, RSRQ (signal KPIs; per-frequency priority is in SIBs, not in this diag log) |

The log mask now enables `0xB193` (Serving Cell Meas Response) and `0xB195` (Connected Mode Neighbor Meas) to try to get measurements in RRC_CONNECTED. The modem may still emit these less frequently than in IDLE. When `--kpi` is used and the modem does not report SCell in RRC_CONNECTED, the last known SCell (from IDLE or from a previous 0xB193) is re-printed at most every 2 seconds before KPI lines so that you still see EARFCN/PCI/RSRP in connected state.

### MAC Transport Block KPIs

| Field | Description |
|-------|-------------|
| **MCS** | Modulation and Coding Scheme 0–31 (DL: derived from TBS+bandwidth per 36.213; UL: from grant) |
| **TA** | Timing Advance 0–63 (from MAC CE LCID 0x1D in DL MAC PDU; only in RRC_CONNECTED) |

**DL MCS** lines (`X MHz BW MCS=Y`) are throttled to at most **one per 2 seconds per radio** to avoid flooding the log during EPS (LTE) download, when the modem reports a new value on every DL transport block.

**EPS throughput** is computed from MAC transport block sizes (DL + UL). Every **1 second per radio**, and only when **RRC state is RRC_CONNECTED**, a line is printed: **LTE throughput: X.XX Mbps** (combined DL+UL in the last 1 s window). Requires `--kpi` and MAC DL/UL TB logs (packet format v1).

In **RRC_CONNECTED**, UL MCS, TX power, and TA are combined into one throttled line (about once per second per radio): **LTE KPI: UL MCS=…, TX power=… dBm, TA=…**. Last-known values are used for each field; a field shows `-` if not yet received. The three individual lines (LTE KPI UL: MCS=…, LTE KPI TX: est. TX power=… dBm, LTE KPI: TA=…) are **not** printed in RRC_CONNECTED—only the combined line is.

### TX Power (from PHR)

| Field | Description |
|-------|-------------|
| **est. TX power** | Estimated *current* PUSCH TX power (dBm), derived as Pcmax − PHR (Pcmax=23 dBm assumed). **23 dBm is suppressed** in the log (phantom when no real UL/audio); +22 dBm and below print normally. |

This is **current** PUSCH power derived from the Power Headroom Report (PHR = Pcmax − P_PUSCH). **LTE UL power control does reduce TX in good conditions** (eNB power-controls the UE down when path loss is low) and increase TX in bad—so you’d expect good signal → lower TX, bad signal → higher TX. If you see the **opposite** (e.g. good → 23 dBm, bad → -7 dBm), common reasons are: (1) in poor signal the UE may not be in a state to use high power (RRC_SEARCH, no/small grants), so the *reported* current PUSCH power is low; (2) the modem’s PHR event may use a different encoding than standard 3GPP. So the value is “current PUSCH from PHR,” not “what power control would command” in all conditions. If the display looks opposite (good signal → 23 dBm, bad → -7 dBm), use **`--invert-tx-power`** so good signal shows lower TX and bad signal higher TX (matches power-control intuition).

### RACH (Random Access)

When the modem reports an LTE MAC RACH attempt (log 0xB062), a KPI line is printed:

**LTE KPI RACH:** `result=success|failure`, `attempt=N`, `contention=0|1`, `preamble=X`, `preamble_power_dB=Y`, `ta=Z`, `tc_rnti=0x…`, `earfcn=E`

- **result** — `success` (0x00) or `failure`
- **attempt** — RACH attempt number
- **contention** — Contention-based (1) or non-contention (0)
- **preamble** — Preamble index (Msg1); `-` if not present
- **preamble_power_dB** — Preamble power offset (raw); `-` if not present
- **ta** — Timing Advance from Msg2; `-` if not present
- **tc_rnti** — Temporary C-RNTI from Msg2; `-` if not present
- **earfcn** — DL EARFCN (from add-info when available); `-` otherwise

The line is emitted on both success and failure (and when Msg1/Msg2/Msg3 are incomplete). RACH data is also sent to Wireshark as GSMTAP MAC-LTE when the full 4-step sequence is present. When `--json-udp-port` is used, each RACH line is sent as a JSON object with `type: "lte_rach"` and the parsed fields (result, attempt, preamble, ta, tc_rnti, earfcn, etc.).

**When you see RACH:** The modem only reports RACH (log 0xB062) when a random access attempt occurs—e.g. initial attach, reconnection from idle, handover, or after radio recovery. To see RACH in the log and JSON, trigger a new connection (e.g. toggle airplane mode, or disable then re-enable mobile data) while scat is running with `--kpi` and `--json-udp-port`. RACH response packet versions 0x01, 0x31, and 0x32 are supported for different device formats.

### RRC State Changes

When the LTE RRC connection state changes, the new state and cause are logged:

| Output | Description |
|--------|-------------|
| **LTE RRC State:** | New state: RRC_SEARCH, RRC_IDLE_NOT_CAMPED, RRC_IDLE_CAMPED, RRC_CONNECTING, RRC_CONNECTED, RRC_INACTIVE, RRC_CLOSING |
| **LTE RRC State Cause:** | Cause/trigger: RRCConnectionSetup, RRCConnectionRelease, RRCConnectionSetupComplete, etc. |

**RRC_SEARCH** (state 0) means the modem is in search (no RRC context yet)—e.g. after power-on or when signal is low but the modem can still decode (degraded link). **RRC_INACTIVE** (state 5) is connected-but-suspended (power saving).

RRC signalling messages (RRCConnectionRequest, Paging, etc.) are sent to Wireshark via GSMTAP—use Wireshark on the configured port to decode them.

When `--kpi` is used, event reporting is automatically enabled (required for RRC state).

### LTE handover events

When you run with **`--kpi`**, event reporting is already enabled (same as for RRC state), so LTE RRC DL/UL messages are reported. When a handover occurs you will see:

| Output | Description |
|--------|-------------|
| **LTE handover: RRCConnectionReconfiguration (network command)** | Network sent handover command (RRC Reconfiguration with mobilityControlInfo). |
| **LTE handover: RRCConnectionReconfigurationComplete (UE completed)** | UE sent handover complete. |

RRC message types (RRCConnectionReconfiguration, RRCConnectionReconfigurationComplete, etc.) are also sent to GSMTAP for Wireshark. If your modem uses different message-type codes, you may see `Unknown (xx)` in the event; the handover lines above are emitted when the known codes (0x83 for Reconfiguration on DL, 0x83 for ReconfigurationComplete on UL) are reported.

### RRC FAILURE events

When **`--kpi`** is used, any Qualcomm event whose name contains **FAILURE** is printed to the log as **RRC event: EVENT_…**. Examples: **EVENT_LTE_RRC_RADIO_LINK_FAILURE**, **EVENT_LTE_RRC_HO_FAILURE**, **EVENT_LTE_RRC_CELL_RESEL_FAILURE**, **EVENT_LTE_RRC_IRAT_HO_FROM_EUTRAN_FAILURE**, **EVENT_LTE_RRC_SIB_READ_FAILURE**, and other FAILURE events from the fallback event list. These lines are also sent to JSON UDP when `--json-udp-port` is set.

### JSON over UDP

Use `--json-udp-port PORT` to send log output as JSON over UDP to localhost. Each line is converted to structured JSON and sent as a separate UDP packet. Use **`--no-gsmtap`** to disable GSMTAP output entirely so only JSON is sent (no traffic on port 4729).

```bash
python -m scat -t qc -s COM14 --kpi --dl-bandwidth 20 --json-udp-port 9999 --no-gsmtap
```

Start a receiver on port 9999 to consume the JSON (e.g. `nc -ul 9999` or a Python script).

**JSON structure** (parsed when possible; otherwise `type: "log"` with raw `message`):

| type | Fields |
|------|--------|
| `lte_kpi_dl` | bw_mhz, mcs |
| `lte_kpi_ul` | mcs |
| `lte_kpi_tx` | tx_power_dbm |
| `lte_kpi_ta` | ta (0–63) |
| `lte_uplink_kpi` | ul_mcs, tx_power_dbm, ta (each int or null if missing; emitted in RRC_CONNECTED instead of the three individual UL/TX/TA lines) |
| `lte_rach` | result (success\|failure), attempt, contention, preamble, preamble_power_dbm, ta, tc_rnti, earfcn (each numeric field int or null if missing) |
| `lte_rrc_state` | state |
| `lte_rrc_state_cause` | cause |
| `lte_primary_cell` | earfcn, pci, rsrp, rssi, rsrq, priority (optional, 0–7 when from SERVING_CELL_MEAS_AND_EVAL) |
| `lte_scell_connected` | pci, rsrp, rssi, rsrq |
| `lte_ncell` | cell_index, earfcn, pci, rsrp, rssi, rsrq |
| `lte_throughput` | mbps (combined DL+UL, 1 s window; only when RRC_CONNECTED) |
| `log` | message (unparsed) |

All objects include `ts` (ISO8601) and `radio` (0 or 1).

Example JSON (Primary Cell): `{"ts":"2026-01-31T16:34:36.123456","radio":0,"type":"lte_primary_cell","earfcn":6300,"pci":106,"rsrp":-100,"rssi":-68,"rsrq":-15,"priority":5}` (priority present when from SERVING_CELL_MEAS_AND_EVAL log)

Example JSON (TX power): `{"ts":"2026-01-31T16:34:36.123456","radio":0,"type":"lte_kpi_tx","tx_power_dbm":8}`

Example JSON (combined KPI): `{"ts":"2026-01-31T16:34:36.123456","radio":0,"type":"lte_uplink_kpi","ul_mcs":25,"tx_power_dbm":23,"ta":1}` (missing fields are `null`)

Example JSON (RACH): `{"ts":"2026-01-31T16:34:36.123456","radio":0,"type":"lte_rach","result":"success","attempt":1,"contention":1,"preamble":10,"preamble_power_dbm":-104,"ta":7,"tc_rnti":18460,"earfcn":3749}` (missing fields are `null`)

### Example Output

```
Radio 0: 20MHz BW MCS=20
Radio 0: LTE KPI: UL MCS=20, TX power=8 dBm, TA=1
Radio 0: LTE RRC State: RRC_CONNECTED
Radio 0: LTE RRC State Cause: RRCConnectionSetup
Radio 0: LTE KPI RACH: result=success, attempt=1, contention=1, preamble=5, preamble_power_dB=-96, ta=23, tc_rnti=0xf7d8, earfcn=-
Radio 0: LTE RRC State: RRC_IDLE_CAMPED
Radio 0: LTE RRC State Cause: RRCConnectionRelease
```

## Notes

- **DL MCS**: Derived from TBS and cell bandwidth (N_PRB) using 3GPP TS 36.213. If cell info (MIB, RRC, ML1) is not received, use `--dl-bandwidth 20` to specify DL CC bandwidth in MHz (1.4, 3, 5, 10, 15, or 20).
- **UL MCS**: UL MCS is extracted from the 5 LSBs of the grant field (common convention in LTE DCI format 0). If your device uses a different grant encoding, the value may need adjustment.
- **Device support**: Uses LTE MAC transport block logs (0xB063 DL, 0xB064 UL). Packet format v1 is supported. Newer devices using v49 (0x31/0x32) format do not yet have KPI extraction.
- **TX power**: From LTE_ML1_PHR_REPORT event. Uses Pcmax=23 dBm; actual Pcmax may vary by device/band. PHR is reported when pathloss changes or periodically.
