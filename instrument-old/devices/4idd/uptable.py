'''
Uptable motors
'''

__all__ = ['uptable']

from ophyd import Component, MotorBundle, EpicsMotor
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class UpTable(MotorBundle):
    y = Component(EpicsMotor, 'm10', labels=('motor', 'uptable'))
    x = Component(EpicsMotor, 'm9', labels=('motor', 'uptable'))


uptable = UpTable('4iddx:', name='uptable')
sd.baseline.append(uptable)
