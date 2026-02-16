#!/usr/bin/env python3
# coding: utf8

import time
import serial
import scat.util as util
from scat.iodevices.abstractio import AbstractIO

class SerialIO(AbstractIO):
    def __init__(self, port_name: str, baudrate: int=115200, rts: bool=True, dsr: bool=True):
        self.port_name = port_name
        self.baudrate = baudrate
        self.rts = rts
        self.dsr = dsr
        self.port = serial.Serial(port_name, baudrate=baudrate, timeout=0.5, rtscts=rts, dsrdtr=dsr)
        self.block_until_data = True
        self.file_available = False
        self.fname = ''

    def __enter__(self):
        return self

    def open_next_file(self) -> None:
        pass

    def read(self, read_size: int, decode_hdlc: bool = False) -> bytes:
        buf = b''
        buf = self.port.read(read_size)
        buf = bytes(buf)
        if decode_hdlc:
            buf = util.unwrap(buf)
        return buf

    def write(self, write_buf: bytes, encode_hdlc: bool = False) -> None:
        if encode_hdlc:
            write_buf = util.wrap(write_buf)
        self.port.write(write_buf)

    def write_then_read_discard(self, write_buf: bytes, read_size: int = 0x1000, encode_hdlc: bool = False) -> None:
        self.write(write_buf, encode_hdlc)
        self.read(read_size)

    def reopen(self) -> None:
        """Close and reopen the serial port. Use after COM port errors (e.g. during EPS download)."""
        try:
            self.port.close()
        except Exception:
            pass
        # Retry opening: during heavy traffic (e.g. file download) the OS may briefly deny access
        for attempt in range(1, 4):
            try:
                self.port = serial.Serial(
                    self.port_name, baudrate=self.baudrate, timeout=0.5,
                    rtscts=self.rts, dsrdtr=self.dsr
                )
                return
            except (OSError, serial.SerialException) as e:
                if attempt < 3:
                    time.sleep(2)
                else:
                    raise RuntimeError(
                        'Cannot configure port, something went wrong. Original message: %s' % (e,)
                    ) from e

    def __exit__(self, exc_type, exc_value, traceback):
        self.port.close()
