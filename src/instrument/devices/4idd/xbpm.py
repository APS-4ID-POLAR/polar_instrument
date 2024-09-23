'''
XBPM motors
'''

__all__ = ['xbpm']

from ophyd import MotorBundle, Component, EpicsMotor
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class XBPM(MotorBundle):
    y = Component(EpicsMotor, 'm20', labels=('motor', 'xbpm'))
    x = Component(EpicsMotor, 'm19', labels=('motor', 'xbpm'))


xbpm = XBPM('4iddx:', name='xbpm')
sd.baseline.append(xbpm)
