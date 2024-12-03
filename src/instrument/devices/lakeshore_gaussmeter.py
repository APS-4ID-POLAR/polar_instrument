"""
Lakeshore Gaussmeter 475
"""

from ophyd import Device, Component, EpicsSignalRO, EpicsSignal, Signal


class GaussmeterDevice(Device):
    field = Component(EpicsSignalRO, "Fld.val", kind="hinted")
    field_unit = Component(EpicsSignalRO, "Unit.VAL", kind="normal")
    field_unit_setpoint = Component(EpicsSignal, "FldUnit.SVAL", kind="omitted")
    scan = Component(EpicsSignal, "ReadFld.SCAN", kind="config")
    acquire_dummy = Component(Signal, value=0, kind="omitted")

    @property
    def preset_monitor(self):
        return self.acquire_dummy


gaussmeter = GaussmeterDevice(
    "4idhSoft:Lakeshore745:", name="gaussmeter", labels=("detector",)
)
