"""
Monochromator feedback
"""

__all__ = ['mono_feedback']

from ophyd import Device, Component, EpicsSignal
from ..utils._logging_setup import logger

logger.info(__file__)


class FeedbackDirection(Device):
    status = Component(EpicsSignal, ":on", string=True)
    readback_pv = Component(EpicsSignal, ".INP", string=True)
    control_pv = Component(EpicsSignal, ".OUTL", string=True)
    setpoint = Component(EpicsSignal, ".VAL", string=True)
    readback = Component(EpicsSignal, ".CVAL", string=True)
    scan = Component(EpicsSignal, ".SCAN", string=True)


class FeedbackStation(Device):
    horizontal = Component(FeedbackDirection, "h")
    vertical = Component(FeedbackDirection, "v")


class MonoFeedback(Device):
    station = Component(EpicsSignal, "MonoFBStation", string=True)
    enable = Component(EpicsSignal, "MonoFBEnable", string=True)

    b = Component(FeedbackStation, "epidB")
    g = Component(FeedbackStation, "epidG")
    h = Component(FeedbackStation, "epidH")


mono_feedback = MonoFeedback("4idbSoft:", name="mono_feedback")
