"""
Undulator support
"""

from apstools.devices import STI_Undulator, TrackingSignal
from ophyd import Device, Component


class PolarUndulators(Device):

    tracking = Component(TrackingSignal, value=False, kind='config')

    us = Component(STI_Undulator, "USID:")
    ds = Component(STI_Undulator, "DSID:")


undulators = PolarUndulators("S04ID:", name="undulators")
