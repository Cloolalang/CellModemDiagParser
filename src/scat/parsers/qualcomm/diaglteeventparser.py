#!/usr/bin/env python3

from functools import wraps
import binascii
import calendar, datetime
import logging
import struct

from scat.parsers.qualcomm import diagcmd
import scat.util as util

class DiagLteEventParser:
    def __init__(self, parent):
        self.parent = parent
        self.header = b''

        if self.parent:
            self.display_format = self.parent.display_format
            self.gsmtapv3 = self.parent.gsmtapv3
        else:
            self.display_format = 'x'
            self.gsmtapv3 = False

        # Event IDs are available at:
        # https://source.codeaurora.org/quic/la/platform/vendor/qcom-opensource/wlan/qcacld-2.0/tree/CORE/VOSS/inc/event_defs.h
        # https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/staging/qcacld-2.0/CORE/VOSS/inc/event_defs.h
        self.process = {
            # event ID, (function, event name)
            1605: (self.parse_event_lte_rrc_timer_status, 'LTE_RRC_TIMER_STATUS'),
            1606: (self.parse_event_lte_rrc_state_change, 'LTE_RRC_STATE_CHANGE'),
            1609: (self.parse_event_lte_rrc_dl_msg, 'LTE_RRC_DL_MSG'),
            1610: (self.parse_event_lte_rrc_ul_msg, 'LTE_RRC_UL_MSG'),
            1611: (self.parse_event_lte_rrc_new_cell_ind, 'LTE_RRC_NEW_CELL_IND'),
            1614: (self.parse_event_lte_rrc_paging_drx_cycle, 'LTE_RRC_PAGING_DRX_CYCLE'),

            1498: (self.parse_event_lte_timing_advance, 'LTE_TIMING_ADVANCE'),

            1627: (self.parse_event_lte_nas_msg, 'LTE_CM_INCOMING_MSG'),
            1628: (self.parse_event_lte_nas_msg, 'LTE_CM_OUTGOING_MSG'),
            1629: (self.parse_event_lte_nas_msg, 'LTE_EMM_INCOMING_MSG'),
            1630: (self.parse_event_lte_nas_msg, 'LTE_EMM_OUTGOING_MSG'),
            1633: (self.parse_event_lte_nas_msg, 'LTE_REG_INCOMING_MSG'),
            1634: (self.parse_event_lte_nas_msg, 'LTE_REG_OUTGOING_MSG'),
            1635: (self.parse_event_lte_nas_msg, 'LTE_ESM_INCOMING_MSG'),
            1636: (self.parse_event_lte_nas_msg, 'LTE_ESM_OUTGOING_MSG'),

            1966: (self.parse_event_lte_nas_ota_msg, 'LTE_EMM_OTA_INCOMING_MSG'),
            1967: (self.parse_event_lte_nas_ota_msg, 'LTE_EMM_OTA_OUTGOING_MSG'),
            1968: (self.parse_event_lte_nas_ota_msg, 'LTE_ESM_OTA_INCOMING_MSG'),
            1969: (self.parse_event_lte_nas_ota_msg, 'LTE_ESM_OTA_OUTGOING_MSG'),

            1631: (self.parse_event_lte_emm_esm_timer, 'LTE_EMM_TIMER_START'),
            1632: (self.parse_event_lte_emm_esm_timer, 'LTE_EMM_TIMER_EXPIRY'),
            1637: (self.parse_event_lte_emm_esm_timer, 'LTE_ESM_TIMER_START'),
            1638: (self.parse_event_lte_emm_esm_timer, 'LTE_ESM_TIMER_EXPIRY'),

            1994: (self.parse_event_lte_rrc_state_change_trigger, 'LTE_RRC_STATE_CHANGE_TRIGGER'),
        }

    def update_parameters(self, display_format: str, gsmtapv3: bool):
        self.display_format = display_format
        self.gsmtapv3 = gsmtapv3

    def build_header(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            osmocore_log_hdr = util.create_osmocore_logging_header(
                timestamp = args[0],
                process_name = b'Event',
                pid = args[1],
            )

            gsmtap_hdr = util.create_gsmtap_header(
                version = 2,
                payload_type = util.gsmtap_type.OSMOCORE_LOG)

            log_precontent = "{}: ".format(self.process[args[1]][1]).encode('utf-8')

            self.header = gsmtap_hdr + osmocore_log_hdr + log_precontent
            return func(self, *args, **kwargs)
        return wrapped_function

    @build_header
    def parse_event_lte_rrc_timer_status(self, ts, event_id: int, arg_bin: bytes):
        log_content = "{}".format(' '.join('{:02x}'.format(x) for x in arg_bin)).encode('utf-8')

        return self.header + log_content

    @build_header
    def parse_event_lte_rrc_state_change(self, ts, event_id: int, arg1: int):
        rrc_state_map = {
            0: "RRC_SEARCH",  # modem in search (no RRC context yet)
            1: "RRC_IDLE_NOT_CAMPED",
            2: "RRC_IDLE_CAMPED",
            3: "RRC_CONNECTING",
            4: "RRC_CONNECTED",
            5: "RRC_INACTIVE",  # connected but suspended (Rel-16 / vendor)
            7: "RRC_CLOSING",
        }
        if arg1 in rrc_state_map.keys():
            rrc_state = rrc_state_map[arg1]
        else:
            rrc_state = "{:02x}".format(arg1)

        log_content = "rrc_state={}".format(rrc_state).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        # With --kpi: print state change to stdout
        stdout = None
        if self.parent and getattr(self.parent, 'show_kpi', False):
            stdout = 'LTE RRC State: {}'.format(rrc_state)
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt

    @build_header
    def parse_event_lte_rrc_dl_msg(self, ts, event_id: int, arg1: int, arg2: int):
        channel_dl_map = {
            1: "BCCH",
            2: "PCCH",
            3: "CCCH",
            4: "DCCH"
        }

        message_type_map = {
            0x00: "MasterInformationBlock",
            0x01: "SystemInformationBlockType1",
            0x02: "SystemInformationBlockType2",
            0x03: "SystemInformationBlockType3",
            0x04: "SystemInformationBlockType4",
            0x05: "SystemInformationBlockType5",
            0x06: "SystemInformationBlockType6",
            0x07: "SystemInformationBlockType7",
            0x40: "Paging",
            0x4b: "RRCConnectionSetup",
            0x81: "DLInformationTransfer",
            0x83: "RRCConnectionReconfiguration",  # handover / reconfig
            0x85: "RRCConnectionRelease",
        }

        if arg1 in channel_dl_map.keys():
            channel = channel_dl_map[arg1]
        else:
            channel = "Unknown"

        if arg2 in message_type_map.keys():
            message_type = message_type_map[arg2]
        else:
            message_type = "Unknown ({:2x})".format(arg2)

        log_content = "channel={}, message_type={}".format(channel, message_type).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        # With --kpi: print handover when we see RRCConnectionReconfiguration (handover command)
        stdout = None
        if message_type == "RRCConnectionReconfiguration" and self.parent and getattr(self.parent, 'show_kpi', False):
            stdout = 'LTE handover: RRCConnectionReconfiguration (network command)'
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt

    @build_header
    def parse_event_lte_rrc_ul_msg(self, ts, event_id: int, arg1: int, arg2: int):
        channel_ul_map = {
            5: "CCCH",
            6: "DCCH"
        }

        message_type_map = {
            0x01: "RRCConnectionRequest",
            0x84: "RRCConnectionSetupComplete",
            0x83: "RRCConnectionReconfigurationComplete",  # handover complete
            0x89: "ULInformationTransfer",
        }

        if arg1 in channel_ul_map.keys():
            channel = channel_ul_map[arg1]
        else:
            channel = "Unknown"

        if arg2 in message_type_map.keys():
            message_type = message_type_map[arg2]
        else:
            message_type = "Unknown ({:2x})".format(arg2)

        log_content = "channel={}, message_type={}".format(channel, message_type).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        # With --kpi: print handover complete when we see RRCConnectionReconfigurationComplete
        stdout = None
        if message_type == "RRCConnectionReconfigurationComplete" and self.parent and getattr(self.parent, 'show_kpi', False):
            stdout = 'LTE handover: RRCConnectionReconfigurationComplete (UE completed)'
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt

    @build_header
    def parse_event_lte_timing_advance(self, ts, event_id: int, arg_bin: bytes):
        """Parse EVENT_LTE_TIMING_ADVANCE (1498). Payload 3 bytes: often [reserved, reserved, TA] with TA 6-bit (0-63). 0xFF = invalid."""
        log_content = ' '.join('{:02x}'.format(x) for x in arg_bin).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        stdout = None
        if self.parent and getattr(self.parent, 'show_kpi', False) and len(arg_bin) >= 3:
            ta_val = arg_bin[2] & 0x3F
            if arg_bin[2] == 0xFF:
                stdout = 'LTE Timing Advance: invalid (0xff)'
            else:
                stdout = 'LTE Timing Advance: TA={}'.format(ta_val)
        elif self.parent and getattr(self.parent, 'show_kpi', False) and len(arg_bin) > 0:
            stdout = 'LTE Timing Advance: {}'.format(' '.join('{:02x}'.format(x) for x in arg_bin))
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt

    @build_header
    def parse_event_lte_rrc_new_cell_ind(self, ts, event_id: int, arg_bin: bytes):
        """Parse EVENT_LTE_RRC_NEW_CELL_IND (1611). Some modems (e.g. 9607) use 1-byte header then EARFCN(2) PCI(2) LE."""
        log_content = ' '.join('{:02x}'.format(x) for x in arg_bin).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        stdout = None
        if self.parent and getattr(self.parent, 'show_kpi', False) and len(arg_bin) >= 4:
            # Try offset 1 first (1-byte header), then offset 0
            for start in (1, 0) if len(arg_bin) >= 5 else (0,):
                if start + 4 > len(arg_bin):
                    continue
                w0 = struct.unpack('<H', arg_bin[start:start + 2])[0]
                w1 = struct.unpack('<H', arg_bin[start + 2:start + 4])[0]
                if w0 <= 503 and w1 <= 65535:
                    pci, earfcn = w0, w1
                elif w1 <= 503 and w0 <= 65535:
                    earfcn, pci = w0, w1
                else:
                    earfcn = w0
                    pci = min(503, w1 & 0x1FF)
                if 0 <= earfcn <= 65535 and 0 <= pci <= 503:
                    stdout = 'LTE RRC NEW_CELL_IND: EARFCN={}, PCI={}'.format(earfcn, pci)
                    break
            if stdout is None:
                w0 = struct.unpack('<H', arg_bin[0:2])[0]
                w1 = struct.unpack('<H', arg_bin[2:4])[0]
                if w0 <= 503 and w1 <= 65535:
                    pci, earfcn = w0, w1
                else:
                    earfcn, pci = w0, min(503, w1 & 0x1FF)
                stdout = 'LTE RRC NEW_CELL_IND: EARFCN={}, PCI={}'.format(earfcn, pci)
        elif self.parent and getattr(self.parent, 'show_kpi', False) and len(arg_bin) > 0:
            stdout = 'LTE RRC NEW_CELL_IND: {}'.format(' '.join('{:02x}'.format(x) for x in arg_bin))
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt

    @build_header
    def parse_event_lte_rrc_paging_drx_cycle(self, ts, event_id: int, arg1: int, arg2: int):
        log_content = "{:02x} {:02x}".format(arg1, arg2).encode('utf-8')

        return self.header + log_content

    @build_header
    def parse_event_lte_nas_msg(self, ts, event_id: int, arg1: bytes):
        message_id = struct.unpack('<L', arg1[:4])[0]
        log_content = "0x{:04x}".format(message_id).encode('utf-8')

        return self.header + log_content

    @build_header
    def parse_event_lte_nas_ota_msg(self, ts, event_id: int, arg1: int):
        log_content = "{:02x}".format(arg1).encode('utf-8')

        return self.header + log_content

    @build_header
    def parse_event_lte_emm_esm_timer(self, ts, event_id: int, arg1: int):
        log_content = "{:02x}".format(arg1).encode('utf-8')

        return self.header + log_content

    @build_header
    def parse_event_lte_rrc_state_change_trigger(self, ts, event_id: int, arg1: int):
        # Cause/trigger for the state change (3GPP 36.331)
        cause_map = {
            0x01: "RRCConnectionRequest",
            0x4b: "RRCConnectionSetup",
            0x84: "RRCConnectionSetupComplete",
            0x85: "RRCConnectionRelease",
            0x89: "ULInformationTransfer",
            0x81: "DLInformationTransfer",
        }
        cause_str = cause_map.get(arg1, "0x{:02x}".format(arg1))
        log_content = "{:02x}".format(arg1).encode('utf-8')
        gsmtap_pkt = self.header + log_content

        # With --kpi: print cause to stdout
        stdout = None
        if self.parent and getattr(self.parent, 'show_kpi', False):
            stdout = 'LTE RRC State Cause: {}'.format(cause_str)
        return (gsmtap_pkt, stdout) if stdout else gsmtap_pkt
