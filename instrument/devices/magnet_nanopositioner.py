'''
Magnet Nanopositioner motors
'''

__all__ = ['magnet_nano']

from ophyd import Component, MotorBundle, EpicsMotor
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class NanoPositioner(MotorBundle):
    nanoy = Component(EpicsMotor, 'm1', labels=('motor', 'nanopositioner'))
    nanox = Component(EpicsMotor, 'm2', labels=('motor', 'nanopositioner'))
    nanoz = Component(EpicsMotor, 'm3', labels=('motor', 'nanopositioner'))


magnet_nano = NanoPositioner('cpscIOC:', name='magnet_nano')
sd.baseline.append(magnet_nano)
