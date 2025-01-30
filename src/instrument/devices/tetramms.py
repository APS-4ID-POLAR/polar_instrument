"""
TetrAMMs
"""

__all__ = ["tetramm_4idb"]

from ophyd import TetrAMM, Device, Component, EpicsSignalRO
from ..utils._logging_setup import logger
logger.info(__file__)


tetramm_4idb = TetrAMM(
    "4idbSoft:TetrAMM:", name="tetramm_4idb", labels=("detector",)
)


class TetrAMMRO(Device):
    posx = Component(EpicsSignalRO, "PosX:MeanValue_RBV")
    posy = Component(EpicsSignalRO, "PosY:MeanValue_RBV")
    sum =  Component(EpicsSignalRO, "SumAll:MeanValue_RBV")


tetramm_4idb_ro = TetrAMMRO(
    "4idbSoft:TetrAMM:", name="tetramm_4idb_ro", labels=("detector",)
)