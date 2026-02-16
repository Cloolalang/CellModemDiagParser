#!/usr/bin/env python3
# coding: utf8

import scat.iodevices
import scat.writers
import scat.parsers
import scat.parsers.abstractparser

import argparse
import faulthandler
import importlib.metadata
import logging
import os, sys
import signal
import inspect

from serial import SerialException

current_parser: scat.parsers.abstractparser.AbstractParser
logger = logging.getLogger('scat')
__version__ = importlib.metadata.version('signalcat')

if os.name != 'nt':
    faulthandler.register(signal.SIGUSR1)

def sigint_handler(sig, frame):
    global current_parser
    # Only set flag; avoid logging from signal handler to prevent reentrant
    # write to stdout (RuntimeError). run_diag() checks the flag and breaks;
    # main then calls stop_diag() after run_diag() returns.
    setattr(current_parser, '_stop_requested', True)

def hexint(string):
    if string[0:2] == '0x' or string[0:2] == '0X':
        return int(string[2:], 16)
    else:
        return int(string)

class ListUSBAction(argparse.Action):
    # List USB devices and then exit
    def __call__(self, parser, namespace, values, option_string=None):
        from scat.iodevices.usbio import USBIO
        USBIO().list_usb_devices()
        parser.exit()

def scat_main():
    global current_parser
    # Load parser modules
    parser_dict = {}
    for parser_module in dir(scat.parsers):
        if parser_module.startswith('__'):
            continue
        m = getattr(scat.parsers, parser_module)
        if inspect.isclass(m) and issubclass(m, scat.parsers.abstractparser.AbstractParser):
            c = m()
            parser_dict[c.shortname] = c

    valid_layers = ['ip', 'nas', 'rrc', 'pdcp', 'rlc', 'mac', 'qmi']

    parser = argparse.ArgumentParser(description='Reads diagnostic messages from smartphone baseband.')
    parser.register('action', 'listusb', ListUSBAction)

    parser.add_argument('-D', '--debug', help='Print debug information, mostly hexdumps.', action='store_true')
    parser.add_argument('-t', '--type', help='Baseband type to be parsed.\nAvailable types: {}'.format(', '.join(parser_dict.keys())), required=True, choices=list(parser_dict.keys()))
    parser.add_argument('-l', '--list-devices', help='List USB devices and exit', nargs=0, action='listusb')
    parser.add_argument('-V', '--version', action='version', version='SCAT {}'.format(__version__))
    parser.add_argument('-L', '--layer', help='Specify the layers to see as GSMTAP packets (comma separated).\nAvailable layers: {}, Default: "ip,nas,rrc"'.format(', '.join(valid_layers)), type=str, default='ip,nas,rrc')
    parser.add_argument('-f', '--format', help='Select display format for LAC/RAC/TAC/CID: [d]ecimal, he[x]adecimal (default), [b]oth.', type=str, default='x', choices=['d', 'x', 'b'])
    parser.add_argument('-3', '--gsmtapv3', help='Enable GSMTAPv3 for 2G/3G/4G. Default: enabled only for 5G NR', action='store_true')

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-s', '--serial', help='Use serial diagnostic port')
    input_group.add_argument('-u', '--usb', action='store_true', help='Use USB diagnostic port')
    input_group.add_argument('-d', '--dump', help='Read from baseband dump (QMDL, SDM, LPD)', nargs='*')

    serial_group = parser.add_argument_group('Serial device settings')
    serial_group.add_argument('-b', '--baudrate', help='Set the serial baud rate', type=int, default=115200)
    serial_group.add_argument('--no-rts', action='store_true', help='Do not enable the RTS/CTS')
    serial_group.add_argument('--no-dsr', action='store_true', help='Do not enable the DSR/DTR')

    usb_group = parser.add_argument_group('USB device settings')
    usb_group.add_argument('-v', '--vendor', help='Specify USB vendor ID', type=hexint)
    usb_group.add_argument('-p', '--product', help='Specify USB product ID', type=hexint)
    usb_group.add_argument('-a', '--address', help='Specify USB device address(bus:address)', type=str)
    usb_group.add_argument('-c', '--config', help='Specify USB configuration number for DM port', type=int, default=-1)
    usb_group.add_argument('-i', '--interface', help='Specify USB interface number for DM port', type=int, default=2)

    if 'qc' in parser_dict.keys():
        qc_group = parser.add_argument_group('Qualcomm specific settings')
        qc_group.add_argument('--kpi', action='store_true', help='Show KPI in log (DL/UL MCS, TBS, etc.)')
        qc_group.add_argument('--dl-bandwidth', help='DL CC bandwidth for MCS lookup: 1.4, 3, 5, 10, 15, or 20 MHz', type=float, choices=[1.4, 3, 5, 10, 15, 20], metavar='MHz')
        qc_group.add_argument('--ul-ndi-bit', help='Bit index (0-15) in UL grant for NDI for retransmit rate. Default 6; try 10 if UL retransmit looks wrong.', type=int, default=6, metavar='BIT')
        qc_group.add_argument('--invert-ul-ndi', action='store_true', help='Invert NDI logic: use if UL retransmit is ~100%% when link is good (same NDI => new TX, toggled => retx).')
        qc_group.add_argument('--invert-ul-mcs', action='store_true', help='Invert UL avg MCS: display as (28 - MCS). Use when UL MCS goes down as path loss improves.')
        qc_group.add_argument('--no-ul-retransmit', action='store_true', help='Do not show UL retransmit %% on throughput line (use if it stays ~50%% or is unreliable on your modem).')
        qc_group.add_argument('--qmdl', help='Store log as QMDL file (Qualcomm only)')
        qc_group.add_argument('--qsr-hash', help='Specify QSR message hash file (usually QSRMessageHash.db), implies --msgs', type=str)
        qc_group.add_argument('--qsr4-hash', help='Specify QSR4 message hash file (need to obtain from the device firmware), implies --msgs', type=str)
        qc_group.add_argument('--events', action='store_true', help='Decode Events as GSMTAP logging')
        qc_group.add_argument('--msgs', action='store_true', help='Decode Extended Message Reports and QSR Message Reports as GSMTAP logging')
        qc_group.add_argument('--cacombos', action='store_true', help='Display raw values of UE CA combo information on 4G/5G (0xB0CD/0xB826)')
        qc_group.add_argument('--disable-crc-check', action='store_true', help='Disable CRC mismatch checks. Improves performance by avoiding CRC calculations.')

    if 'sec' in parser_dict.keys():
        sec_group = parser.add_argument_group('Samsung specific settings')
        sec_group.add_argument('-m', '--model', help='Override autodetected device model for analyzing diagnostic messages', type=str)
        sec_group.add_argument('--start-magic', help='Magic value provided for starting DM session. Default: 0x41414141', type=str, default='0x41414141')
        sec_group.add_argument('--sdmraw', help='Store log as raw SDM file (Samsung only)')
        sec_group.add_argument('--trace', action='store_true', help='Decode trace')
        sec_group.add_argument('--ilm', action='store_true', help='Decode ILM')
        sec_group.add_argument('--all-items', action='store_true', help='Enable all SDM items')


    if 'hisi' in parser_dict.keys():
        hisi_group = parser.add_argument_group('HiSilicon specific settings')
        try:
            hisi_group.add_argument('--msgs', action='store_true', help='Decode debug messages GSMTAP logging')
            hisi_group.add_argument('--disable-crc-check', action='store_true', help='Disable CRC mismatch checks. Improves performance by avoiding CRC calculations.')
        except argparse.ArgumentError:
            pass

    ip_group = parser.add_argument_group('GSMTAP IP settings')
    ip_group.add_argument('-P', '--port', help='Change UDP port to emit GSMTAP packets', type=int, default=4729)
    ip_group.add_argument('--port-up', help='Change UDP port to emit user plane packets', type=int, default=47290)
    ip_group.add_argument('-H', '--hostname', help='Change base host name/IP to emit GSMTAP packets. For dual SIM devices the subsequent IP address will be used.', type=str, default='127.0.0.1')

    ip_group.add_argument('-F', '--pcap-file', help='Write GSMTAP packets directly to specified PCAP file')
    ip_group.add_argument('-C', '--combine-stdout', action='store_true', help='Write standard output messages as osmocore log file, along with other GSMTAP packets.')
    ip_group.add_argument('--json-udp-port', help='Send log output as JSON over UDP to localhost (e.g. 9999)', type=int, metavar='PORT')
    ip_group.add_argument('--no-gsmtap', action='store_true', help='Do not emit GSMTAP packets (useful with --json-udp-port for JSON-only output)')

    args = parser.parse_args()

    GSMTAP_IP = args.hostname
    GSMTAP_PORT = args.port
    IP_OVER_UDP_PORT = args.port_up

    if not args.type in parser_dict.keys():
        print('Error: invalid baseband type {} specified. Available modules: {}'.format(args.type, ', '.join(parser_dict.keys())))
        sys.exit(1)

    layers = args.layer.split(',')
    if getattr(args, 'kpi', False) and 'mac' not in layers:
        layers = layers + ['mac']
    if getattr(args, 'no_gsmtap', False):
        layers = []
    for l in layers:
        if not l in valid_layers:
            print('Error: invalid layer {} specified. Available layers: {}'.format(l, ', '.join(valid_layers)))
            sys.exit(1)

    # Device preparation
    io_device: scat.iodevices.AbstractIO
    if args.serial:
        try:
            io_device = scat.iodevices.SerialIO(args.serial, args.baudrate, not args.no_rts, not args.no_dsr)
        except SerialException as e:
            print('Error: could not open {}: {}.'.format(args.serial, e))
            print('The port may be in use by another program (QPST, QXDM, PuTTY, another scat, etc.). '
                  'Close it or unplug/replug the device, then try again.')
            sys.exit(1)
    elif args.usb:
        from scat.iodevices.usbio import USBIO
        io_device = USBIO()
        if args.address:
            usb_bus, usb_device = args.address.split(':')
            usb_bus = int(usb_bus, base=10)
            usb_device = int(usb_device, base=10)
            io_device.probe_device_by_bus_dev(usb_bus, usb_device)
        elif args.vendor == None:
            io_device.guess_device()
        else:
            io_device.probe_device_by_vid_pid(args.vendor, args.product)

        if args.config > 0:
            io_device.set_configuration(args.config)
        io_device.claim_interface(args.interface)
    elif args.dump:
        io_device = scat.iodevices.FileIO(args.dump)
    else:
        print('Error: no device specified.')
        sys.exit(1)

    # Writer preparation
    if args.pcap_file == None:
        writer = scat.writers.SocketWriter(GSMTAP_IP, GSMTAP_PORT, IP_OVER_UDP_PORT)
    else:
        writer = scat.writers.PcapWriter(args.pcap_file, GSMTAP_PORT, IP_OVER_UDP_PORT)

    current_parser = parser_dict[args.type]
    current_parser.set_io_device(io_device)
    current_parser.set_writer(writer)

    if args.debug:
        logger.setLevel(logging.DEBUG)
        current_parser.set_parameter({'log_level': logging.DEBUG})
    else:
        logger.setLevel(logging.INFO)
        current_parser.set_parameter({'log_level': logging.INFO})
    ch = logging.StreamHandler(stream = sys.stdout)
    f = logging.Formatter('%(asctime)s %(name)s (%(funcName)s) %(levelname)s: %(message)s')
    ch.setFormatter(f)
    logger.addHandler(ch)

    if args.type == 'qc':
        kpi = getattr(args, 'kpi', False)
        # Enable events when --kpi (needed for RRC state change logging)
        events = args.events or kpi
        current_parser.set_parameter({
            'kpi': kpi,
            'dl-bandwidth': getattr(args, 'dl_bandwidth', None),
            'ul-ndi-bit': getattr(args, 'ul_ndi_bit', 6),
            'invert-ul-ndi': getattr(args, 'invert_ul_ndi', False),
            'invert-ul-mcs': getattr(args, 'invert_ul_mcs', False),
            'no-ul-retransmit': getattr(args, 'no_ul_retransmit', False),
            'events': events,
            'qsr-hash': args.qsr_hash,
            'qsr4-hash': args.qsr4_hash,
            'msgs': args.msgs,
            'cacombos': args.cacombos,
            'combine-stdout': args.combine_stdout,
            'json-udp-port': getattr(args, 'json_udp_port', None),
            'disable-crc-check': args.disable_crc_check,
            'layer': layers,
            'format': args.format,
            'gsmtapv3': args.gsmtapv3})
    elif args.type == 'sec':
        current_parser.set_parameter({
            'model': args.model,
            'start-magic': args.start_magic,
            'trace': args.trace,
            'ilm': args.ilm,
            'combine-stdout': args.combine_stdout,
            'layer': layers,
            'all-items': args.all_items,
            'format': args.format,
            'gsmtapv3': args.gsmtapv3})
    elif args.type == 'hisi':
        current_parser.set_parameter({
            'msgs': args.msgs,
            'combine-stdout': args.combine_stdout,
            'disable-crc-check': args.disable_crc_check,
            'layer': layers,
            'format': args.format,
            'gsmtapv3': args.gsmtapv3})

    # Run process
    if args.serial or args.usb:
        current_parser.stop_diag()
        current_parser.init_diag()
        current_parser.prepare_diag()

        signal.signal(signal.SIGINT, sigint_handler)

        if not (args.qmdl == None) and args.type == 'qc':
            current_parser.run_diag(scat.writers.RawWriter(args.qmdl))
        if not (args.sdmraw == None) and args.type == 'sec':
            current_parser.run_diag(scat.writers.RawWriter(args.sdmraw))
        else:
            current_parser.run_diag()

        current_parser.stop_diag()
    elif args.dump:
        current_parser.read_dump()
    else:
        assert('Invalid input handler?')
        sys.exit(1)

if __name__ == '__main__':
    scat_main()
