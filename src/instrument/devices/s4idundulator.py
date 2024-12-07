"""
Undulator support
"""

from apstools.devices import STI_Undulator, TrackingSignal
from apstools.devices.aps_undulator import UndulatorPositioner
from ophyd import Component, Device, Signal
from ophyd.status import Status, StatusBase
from typing import Any, Callable
from numpy import abs


class PolarUndulatorPositioner(UndulatorPositioner):

    def set(
        self,
        new_position: Any,
        *,
        timeout: float = None,
        moved_cb: Callable = None,
        wait: bool = False,
    ) -> StatusBase:
        # If position is within the deadband --> do nothing.
        if (
            abs(new_position - self.readback.get()) <=
            self.parent.energy_deadband.get()
        ):
            _status = Status()
            _status.set_finished()
        else:
            _status = super().set(
                new_position, timeout=timeout, moved_cb=moved_cb, wait=wait
            )
        return _status


class PolarUndulator(STI_Undulator):
    tracking = Component(TrackingSignal, value=False, kind='config')
    offset = Component(Signal, value=0, kind='config')
    energy_deadband = Component(Signal, value=0.001, kind='config')
    energy = Component(PolarUndulatorPositioner, "Energy")
    version_hpmu = None


class PolarUndulatorPair(Device):
    us = Component(PolarUndulator, "USID:")
    ds = Component(PolarUndulator, "DSID:")


undulators = PolarUndulatorPair("S04ID:", name="undulators", labels=("energy",))
