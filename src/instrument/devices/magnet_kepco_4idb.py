"""
Kepko power supply
"""

from ophyd import Component, FormattedComponent, Device, Kind
from ophyd import EpicsSignal, EpicsSignalRO
from apstools.devices import PVPositionerSoftDone


class LocalPositioner(PVPositionerSoftDone):
    """Voltage/Current positioner"""

    readback = FormattedComponent(
        EpicsSignalRO,
        "{prefix}d{_type}",
        kind="hinted",
    )

    setpoint = FormattedComponent(
        EpicsSignal,
        "{prefix}{_type}",
        write_pv="{prefix}set{_type}",
    )

    def __init__(self, *args, progtype, **kwargs):
        self._type = progtype
        super().__init__(*args, readback_pv="1", **kwargs)


class KepcoController(Device):

    voltage = Component(LocalPositioner, "", progtype="V", tolerance=0.02)
    current = Component(LocalPositioner, "", progtype="C", tolerance=0.03)

    mode = Component(
        EpicsSignal, "setMode", kind="config", string=True, auto_monitor=True
    )

    remote = Component(
        EpicsSignal, "setRemote", kind="config", string=True, auto_monitor=True
    )

    enable = Component(EpicsSignal, "Enable.VAL", kind="omitted", string=True)

    id = Component(EpicsSignalRO, "IDN", kind="config")
    id_read = Component(EpicsSignal, "IDN.PROC", kind="omitted")

    scan_rate = Component(
        EpicsSignal, "seq_rd.SCAN", kind="omitted", string=True
    )

    @mode.sub_value
    def mode_change(self, value=None, **kwargs):
        if value == "Current":
            self.current.readback.kind = Kind.hinted
            self.voltage.readback.kind = Kind.normal

        if value == "Voltage":
            self.current.readback.kind = Kind.normal
            self.voltage.readback.kind = Kind.hinted

    def default_settings(self):
        self.scan_rate.set(".1 second").wait(5)
        self.remote.set("Remote").wait(5)
        self.id_read.set(1).wait(5)
        self.mode.set("Current").wait(5)
        self.mode_change(value=self.mode.get())
