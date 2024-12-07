"""
4-ID-B diamond window motors
"""

__all__ = [
    'diamond_window'
]

from ophyd import Component, Device, EpicsMotor
from ..utils._logging_setup import logger
logger.info(__file__)


class WindowStages(Device):
    x = Component(EpicsMotor, "m1", label=("motor",))
    y = Component(EpicsMotor, "m2", label=("motor",))


diamond_window = WindowStages("4idbSoft:", name="diamond_window")
