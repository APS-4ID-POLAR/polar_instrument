"""
4idg XBPM
"""

from ophyd import Device, Component, EpicsMotor


class XBPM(Device):
    x = Component(EpicsMotor, "m6", labels=("motor",))
    y = Component(EpicsMotor, "m5", labels=("motor",))
    # detector
