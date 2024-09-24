'''
Nanopositioner motors
'''

__all__ = ['nanopositioner']

from ophyd import Component, MotorBundle, EpicsMotor
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class NanoPositioner(MotorBundle):
    nanoy = Component(EpicsMotor, 'm89', labels=('motor', 'nanopositioner'))
    nanox = Component(EpicsMotor, 'm90', labels=('motor', 'nanopositioner'))
    nanoz = Component(EpicsMotor, 'm91', labels=('motor', 'nanopositioner'))


nanopositioner = NanoPositioner('4iddx:', name='nanopositioner')
sd.baseline.append(nanopositioner)
