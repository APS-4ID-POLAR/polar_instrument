'''
Magnet Nanopositioner motors
'''

__all__ = ['magnet_nano']

from ophyd import Component, MotorBundle, EpicsMotor
from ..utils.run_engine import sd
from ..utils import logger
logger.info(__file__)


class NanoPositioner(MotorBundle):
    x = Component(EpicsMotor, 'm1', labels=('motor', 'nanopositioner'))
    y = Component(EpicsMotor, 'm2', labels=('motor', 'nanopositioner'))
    z = Component(EpicsMotor, 'm3', labels=('motor', 'nanopositioner'))


magnet_nano = NanoPositioner('cpscIOC:', name='magnet_nano')
sd.baseline.append(magnet_nano)
