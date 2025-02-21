"""
Kepko power supply
"""

__all__ = ['kepko']

from ophyd import Component, FormattedComponent, Device, Kind
from ophyd import EpicsSignal, EpicsSignalRO
from apstools.devices import PVPositionerSoftDoneWithStop
from ..utils._logging_setup import logger
logger.info(__file__)


class LocalPositioner(PVPositionerSoftDoneWithStop):
    """ Voltage/Current positioner """

    readback = FormattedComponent(
        EpicsSignalRO, '{prefix}d{_type}', kind='normal',
        labels=('kepko', 'magnet')
        )

    setpoint = FormattedComponent(
        EpicsSignal, "{prefix}{_type}", write_pv="{prefix}set{_type}",
        kind='normal', labels=('kepko', 'magnet')
        )

    def __init__(self, *args, progtype, **kwargs):
        self._type = progtype
        # TODO: This tolerance seems good, but may need to be tested.
        super().__init__(*args, readback_pv="1", tolerance=0.02, **kwargs)


class KepkoController(Device):

    voltage = Component(LocalPositioner, '', progtype='V')
    current = Component(LocalPositioner, '', progtype='C')

    mode = Component(
        EpicsSignal, 'setMode', kind='config', string=True,
        auto_monitor=True, labels=('kepko', 'magnet')
        )

    remote = Component(
        EpicsSignal, 'setRemote', kind='config', string=True,
        auto_monitor=True, labels=('kepko', 'magnet')
        )

    enable = Component(
        EpicsSignal, 'Enable.VAL', kind='omitted', string=True,
        labels=('kepko', 'magnet')
        )

    @mode.sub_value
    def mode_change(self, value=None, **kwargs):
        if value == 'Current':
            self.current.readback.kind = Kind.hinted
            self.voltage.readback.kind = Kind.normal

        if value == 'Voltage':
            self.current.readback.kind = Kind.normal
            self.voltage.readback.kind = Kind.hinted


kepko = KepkoController('4idbSoft:BOP:PS1:', name='kepko')
kepko.mode_change(value=kepko.mode.get())
