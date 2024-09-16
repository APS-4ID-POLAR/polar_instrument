"""
Ruby spectrometer motors and controls.
"""

__all__ = ['ruby']

from ophyd import (
    Component, Device, EpicsMotor, EpicsSignal, FormattedComponent
)
from ..framework import sd
from apstools.devices import PVPositionerSoftDoneWithStop
from ..session_logs import logger
logger.info(__file__)


class DAC(PVPositionerSoftDoneWithStop):
    """ Setup DAC as a PVPositioner """

    low_limit = Component(EpicsSignal, '.DRVL', kind='config')
    high_limit = Component(EpicsSignal, '.DRVH', kind='config')

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            readback_pv="_rbv.VAL",
            setpoint_pv=".VAL",
            tolerance=0.001,
            **kwargs
        )

    @property
    def limits(self):
        return (self.low_limit.get(), self.high_limit.get())


class RubyDevice(Device):
    """ Ruby system """

    focus = Component(EpicsMotor, 'm37', labels=('motor', 'ruby'))
    y = Component(EpicsMotor, 'm38', labels=('motor', 'ruby'))
    z = Component(EpicsMotor, 'm39', labels=('motor', 'ruby'))
    zoom = Component(EpicsMotor, 'm40', labels=('motor', 'ruby'))

    led = FormattedComponent(DAC, '4idd:DAC1_1', labels=('ruby',))
    laser = FormattedComponent(DAC, '4idd:DAC1_2', labels=('ruby',))


ruby = RubyDevice('4iddx:', name='ruby')
sd.baseline.append(ruby)
