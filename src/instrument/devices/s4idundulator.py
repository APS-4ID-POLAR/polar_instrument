"""
Undulator support
"""

from apstools.devices import STI_Undulator, TrackingSignal
from ophyd import Component


class PolarUndulator(STI_Undulator):
    tracking = Component(TrackingSignal, value=False, kind='config')


class PolarUndulatorPair(PolarUndulator):
    us = Component(STI_Undulator, "USID:")
    ds = Component(STI_Undulator, "DSID:")


undulators = PolarUndulatorPair("S04ID:", name="undulators")
