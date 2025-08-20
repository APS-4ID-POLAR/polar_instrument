"""
SoftGlueZynq
"""

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from collections import OrderedDict
from logging import getLogger

logger = getLogger(__name__)


def _io_fields(num=16):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"fi{i}"] = (SoftGlueSignal, f"SG:FI{i}", {"kind": "config"})
        defn[f"fo{i}"] = (SoftGlueSignal, f"SG:FO{i}", {"kind": "config"})
    return defn


def _buffer_fields(num=4):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"in{i}"] = (
            SoftGlueSignal,
            f"SG:BUFFER-{i}_IN",
            {"kind": "config"},
        )
        defn[f"out{i}"] = (
            SoftGlueSignal,
            f"SG:BUFFER-{i}_OUT",
            {"kind": "config"},
        )
    return defn


class SoftGlueSignal(Device):
    signal = Component(EpicsSignal, "_Signal", kind="config")
    bi = Component(EpicsSignal, "_BI", kind="config")


class SGZDevideByN(Device):
    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    reset = Component(SoftGlueSignal, "RESET", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")
    n = Component(EpicsSignal, "N", kind="config")


class SGZUpCounter(Device):
    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    reset = Component(SoftGlueSignal, "CLEAR", kind="config")
    counts = Component(EpicsSignalRO, "COUNTS", kind="config")


class SGZDownCounter(Device):
    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    load = Component(SoftGlueSignal, "LOAD", kind="config")
    preset = Component(EpicsSignal, "PRESET", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZGateDly(Device):
    input = Component(SoftGlueSignal, "IN", kind="config")
    clock = Component(SoftGlueSignal, "CLK", kind="config")
    delay = Component(EpicsSignal, "DLY", kind="config")
    width = Component(EpicsSignal, "WIDTH", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZClocks(Device):
    clock_10MHz = Component(SoftGlueSignal, "10MHZ_CLOCK", kind="config")
    clock_20MHz = Component(SoftGlueSignal, "20MHZ_CLOCK", kind="config")
    clock_50MHz = Component(SoftGlueSignal, "50MHZ_CLOCK", kind="config")
    clock_variable = Component(SoftGlueSignal, "VAR_CLOCK", kind="config")


class SGZGates(Device):
    in1 = Component(SoftGlueSignal, "IN1", kind="config")
    in2 = Component(SoftGlueSignal, "IN2", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZDFF(Device):
    set_ = Component(SoftGlueSignal, "SET", kind="config")
    d = Component(SoftGlueSignal, "D", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    clear = Component(SoftGlueSignal, "CLEAR", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZHistScal(Device):
    en = Component(SoftGlueSignal, "EN", kind="config")
    sync = Component(SoftGlueSignal, "SYNC", kind="config")
    det = Component(SoftGlueSignal, "DET", kind="config")
    det2 = Component(SoftGlueSignal, "DET2", kind="config")
    mode = Component(SoftGlueSignal, "MODE", kind="config")
    clock = Component(SoftGlueSignal, "CLK", kind="config")
    read_ = Component(SoftGlueSignal, "READ", kind="config")
    clear = Component(SoftGlueSignal, "CLEAR", kind="config")


class SGZhistScalerDma(Device):
    enable = Component(EpicsSignal, "Enable", kind="config")

    scan = Component(EpicsSignal, ".SCAN", kind="config", string=True)
    read_button = Component(EpicsSignal, ".PROC", kind="omitted")
    clear_button = Component(EpicsSignal, ".D", kind="omitted")

    debug = Component(EpicsSignal, ".H", kind="config")

    # TODO: maybe we can breakdown the histogram into channels here
    # already?
    hist = Component(EpicsSignalRO, ".VALA", kind="normal")
