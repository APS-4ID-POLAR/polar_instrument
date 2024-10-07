'''
SoftGlueZynq
'''

__all__ = ['sgz']

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO, DynamicDeviceComponent
from collections import OrderedDict
from bluesky.plan_stubs import mv, sleep
from ..utils.run_engine import sd
from ..utils import logger
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


class SoftGlueZynqGateDly(Device):
    in_signal = Component(EpicsSignal, "IN_Signal", kind="config")
    clock_signal = Component(EpicsSignal, "CLK_Signal", kind="config")
    delay = Component(EpicsSignal, "DLY", kind="config")
    width = Component(EpicsSignal, "WIDTH", kind="config")
    out_signal = Component(EpicsSignal, "OUT_Signal", kind="config")


class SoftGlueZynqDevice(Device):
    dma = DynamicDeviceComponent(_dma_fields())
    buffers = DynamicDeviceComponent(_buffer_fields())

    # Using channel #4 to count when the gate is off.
    up_counter_interf = Component(SoftGlueZynqUpCounter, "SG:UpCntr-1_", kind="config")
    up_counter_trigger = Component(SoftGlueZynqUpCounter, "SG:UpCntr-2_", kind="config")
    up_counter_gate_on = Component(SoftGlueZynqUpCounter, "SG:UpCntr-3_", kind="config")
    up_counter_gate_off = Component(SoftGlueZynqUpCounter, "SG:UpCntr-4_", kind="config")

    # Setup the frequency of the interferometer and trigger based on 10 MHz clock.
    div_by_n_interf = Component(SoftGlueZynqDevideByN, "SG:DivByN-1_", kind="config")
    div_by_n_trigger = Component(SoftGlueZynqDevideByN, "SG:DivByN-2_", kind="config")

    # Create a gate pulse
    gate_trigger = Component(SoftGlueZynqGateDly, "GateDly-1_", kind="config")

    def __init__(self, *args, reset_sleep_time=0.2, reference_clock=1e7, **kwargs):
        super().__init__(*args, **kwargs)
        self._reset_sleep_time = reset_sleep_time
        self._reference_clock = reference_clock

    def start_softglue(self):
        yield from mv(self.buffers.in4, "1")

    def stop_softglue(self):
        yield from mv(self.buffers.in4, "0")

    def start_detectors(self):
        yield from mv(self.buffers.in2, "1")

    def stop_detectors(self):
        yield from mv(self.buffers.in2, "0")

    def reset_plan(self):
        yield from mv(self.buffers.in1, "1")
        yield from sleep(self._reset_sleep_time)
        yield from mv(self.buffers.in1, "0")

    def setup_trigger_plan(self, period_time, pulse_width_time, pulse_delay_time=0):
        yield from mv(
            self.div_by_n_trigger.n, self._reference_clock*period_time,
            self.gate_trigger.delay, self._reference_clock*pulse_delay_time,
            self.gate_trigger.width, self._reference_clock*pulse_width_time
        )

    def setup_interf_plan(self, time):
        yield from mv(self.div_by_n_interf.n, self._reference_clock*time)


sgz = SoftGlueZynqDevice('4idIF:', name='sgz')
sd.baseline.append(sgz)
