"""
Ring XBPM support
"""

__all__ = ["aps_xbpm"]

from ophyd import Component, Device, EpicsSignalRO
from ..utils._logging_setup import logger
logger.info(__file__)


class MyXBPM(Device):
    vertical_position = Component(EpicsSignalRO, "VPositionM")
    vertical_angle = Component(EpicsSignalRO, "VAngleM")
    horizontal_position = Component(EpicsSignalRO, "HPositionM")
    horizontal_angle = Component(EpicsSignalRO, "HAngleM")

aps_xbpm = MyXBPM("S04:ID:SrcPt:", name="aps_xbpm")
# aps_xbpm = MyXBPM("", name="aps_xbpm")
