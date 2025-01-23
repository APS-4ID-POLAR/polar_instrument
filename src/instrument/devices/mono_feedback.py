"""
Monochromator feedback
"""

__all__ = ['mono_feedback']

from ophyd import Device, Component, EpicsSignal, EpicsSignalRO
from ..utils._logging_setup import logger

logger.info(__file__)


class FeedbackDirection(Device):
    status = Component(EpicsSignal, ":on", string=True)

    readback_pv = Component(EpicsSignal, ".INP", string=True)
    control_pv = Component(EpicsSignal, ".OUTL", string=True)

    setpoint = Component(EpicsSignal, ".VAL")
    readback = Component(EpicsSignalRO, ".CVAL")
    following_error = Component(EpicsSignalRO, ".ERR")

    scan = Component(EpicsSignal, ".SCAN", string=True)

    kp = Component(EpicsSignal, ".KP")
    ki = Component(EpicsSignal, ".KI")
    kd = Component(EpicsSignal, ".KD")

    p = Component(EpicsSignalRO, ".P")
    i = Component(EpicsSignal, ".I")
    d = Component(EpicsSignalRO, ".D")

    low_limit = Component(EpicsSignal, ".DRVL")
    high_limit = Component(EpicsSignal, ".DRVH")


class FeedbackStation(Device):
    horizontal = Component(FeedbackDirection, "h")
    vertical = Component(FeedbackDirection, "v")


class MonoFeedback(Device):
    station = Component(EpicsSignal, "MonoFBStation", string=True)
    enable = Component(EpicsSignal, "MonoFBEnable", string=True)

    b = Component(FeedbackStation, "epidB")
    g = Component(FeedbackStation, "epidG")
    h = Component(FeedbackStation, "epidH")


mono_feedback = MonoFeedback("4idbSoft:", name="mono_feedback", kind="config")
