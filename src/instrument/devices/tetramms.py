"""
TetrAMMs
"""

__all__ = ["tetramm_4idb"]

from ophyd import TetrAMM
from ..utils._logging_setup import logger
logger.info(__file__)


tetramm_4idb = TetrAMM(
    "4idbSoft:TetrAMM:", name="tetramm_4idb", labels=("detector",)
)
