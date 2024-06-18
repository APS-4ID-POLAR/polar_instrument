'''
SoftGlueZynq
'''

__all__ = ['sgz']

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO, DynamicDeviceComponent
from collections import OrderedDict
from bluesky.plan_stubs import mv, sleep
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


def _buffer_fields(num=4):
    defn = OrderedDict()
    for i in range(1, num+1):
        defn[f"in{i}"] = (EpicsSignal, f"SG:BUFFER-{i}_IN_Signal", {"kind": "config"})
        defn[f"out{i}"] = (EpicsSignal, f"SG:BUFFER-{i}_OUT_Signal", {"kind": "config"})
    return defn


def _dma_fields(num=8, first_letter="I"):
    defn = OrderedDict()
    defn["enable"] = (EpicsSignal, "1acquireDmaEnable", {"kind":"config"})
    defn["clear_buffer"] = (EpicsSignal, "1acquireDma.F", {"kind":"omitted"})
    defn["words_in_buffer"] = (EpicsSignalRO, "1acquireDma.VALJ", {"kind":"config"})
    defn["events"] = (EpicsSignalRO, "1acquireDma.VALI", {"kind":"config"})
    for i in range(1, num+1):
        defn[f"channel_{i}_name"] = (
            EpicsSignal, f"1s{i}name", {"kind": "config"}
        )
        defn[f"channel_{i}_scale"] = (
            EpicsSignal, f"1acquireDma.{chr(ord(first_letter)+i-1)}", {"kind": "config"}
        )
    return defn


class SoftGlueZynqDevideByN(Device):
    enable = Component(EpicsSignal, "ENABLE_Signal", kind="config")
    clock = Component(EpicsSignal, "CLOCK_Signal", kind="config")
    reset = Component(EpicsSignal, "RESET_Signal", kind="config")
    out = Component(EpicsSignal, "OUT_Signal", kind="config")
    n = Component(EpicsSignal, "N", kind="config")


class SoftGlueZynqUpCounter(Device):
    enable = Component(EpicsSignal, "ENABLE_Signal", kind="config")
    clock = Component(EpicsSignal, "CLOCK_Signal", kind="config")
    reset = Component(EpicsSignal, "CLEAR_Signal", kind="config")
    counts = Component(EpicsSignalRO, "COUNTS", kind="config")


class SoftGlueZynqDevice(Device):
    dma = DynamicDeviceComponent(_dma_fields())
    buffers = DynamicDeviceComponent(_buffer_fields())
    # Using channel #1 of up counter
    up_counter_interf = Component(SoftGlueZynqUpCounter, "SG:UpCntr-1_", kind="config")
    up_counter_eiger = Component(SoftGlueZynqUpCounter, "SG:UpCntr-2_", kind="config")
    # Using the channel #3 of divide by N
    div_by_n_interf = Component(SoftGlueZynqDevideByN, "SG:DivByN-1_", kind="config")
    div_by_n_eiger = Component(SoftGlueZynqDevideByN, "SG:DivByN-2_", kind="config")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reset_sleep_time = 0.2

    def start_softglue(self):
        yield from mv(self.buffers.in4, "1")

    def stop_softglue(self):
        yield from mv(self.buffers.in4, "0")

    def start_eiger(self):
        yield from mv(self.buffers.in2, "1")

    def stop_eiger(self):
        yield from mv(self.buffers.in2, "0")

    def reset_plan(self):
        yield from mv(self.buffers.in1, "1")
        yield from sleep(self._reset_sleep_time)
        yield from mv(self.buffers.in1, "0")

    def setup_eiger_trigger_plan(self, time):
        # We are using the 10 MHz clock as a refence
        yield from mv(self.div_by_n_eiger.n, 1e7/(1/time))

    def setup_interf_trigger_plan(self, time):
        # We are using the 10 MHz clock as a refence
        yield from mv(self.div_by_n_interf.n, 1e7/(1/time))


sgz = SoftGlueZynqDevice('4idIF:', name='sgz')
sd.baseline.append(sgz)
