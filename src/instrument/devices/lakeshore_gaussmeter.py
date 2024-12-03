"""
Lakeshore Gaussmeter 475
"""

from ophyd import Device, Component, EpicsSignalRO, EpicsSignal


class GaussmeterDevice(Device):
    field = Component(EpicsSignalRO, "Fld.val", kind="hinted")
    field_unit = Component(EpicsSignalRO, "Unit.VAL", kind="normal")
    field_unit_setpoint = Component(EpicsSignal, "FldUnit.SVAL", kind="omitted")
    scan = Component(EpicsSignal, "ReadFld.SCAN", kind="config")


gaussmeter = GaussmeterDevice(
    "4idhSoft:Lakeshore745:", name="gaussmeter", labels=("detector",)
)
