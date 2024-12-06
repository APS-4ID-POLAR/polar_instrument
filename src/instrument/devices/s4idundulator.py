"""
Undulator support
"""

from apstools.devices import STI_Undulator, TrackingSignal
from ophyd import Component, Device, Signal


class PolarUndulator(STI_Undulator):
    tracking = Component(TrackingSignal, value=False, kind='config')
    offset = Component(Signal, value=0, kind='config')
    version_hpmu = None


class PolarUndulatorPair(Device):
    us = Component(PolarUndulator, "USID:")
    ds = Component(PolarUndulator, "DSID:")


undulators = PolarUndulatorPair("S04ID:", name="undulators", labels=("energy",))
