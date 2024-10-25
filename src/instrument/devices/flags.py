
"""
Flags
"""

__all__ = [
    'flag_4ida_up',
    'flag_4ida_down'
]

from ophyd import EpicsMotor
from ..utils.run_engine import sd
from ..utils._logging_setup import logger
logger.info(__file__)

flag_4ida_up = EpicsMotor(
    "4idVDCM:m6", name="flag_4ida_up", label=("motor", "flag")
)

sd.baseline.append(flag_4ida_up)

flag_4ida_down = EpicsMotor(
    "4idVDCM:m7", name="flag_4ida_down", label=("motor", "flag")
)
sd.baseline.append(flag_4ida_down)
