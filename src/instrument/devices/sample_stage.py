'''
Sample motors
'''

__all__ = "sx sy sz".split()

from ophyd import EpicsMotor
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


sx = EpicsMotor('4tst:m1', labels=('motor'), name="sx")
sy = EpicsMotor('4tst:m2', labels=('motor'), name="sy")
sz = EpicsMotor('4tst:m3', labels=('motor'), name="sz")

for item in [sx, sy, sz]:
    sd.baseline.append(item)
