"""
Undulator support
"""

from apstools.devices import STI_Undulator
from ophyd import Device, Component


class PolarUndulators(Device):
    undulator_us = Component(STI_Undulator, "USID:")
    undulator_ds = Component(STI_Undulator, "DSID:")


undulators = PolarUndulators("S04ID:", name="undulators")
