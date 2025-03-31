
"""
Shutters
"""
__all__ = ["ashutter", "bshutter"]

from apstools.devices import ApsPssShutterWithStatus
from ..utils._logging_setup import logger
logger.info(__file__)


ashutter = ApsPssShutterWithStatus(
    "",
    "PA:04ID:A_BEAM_PRESENT",
    open_pv="PC:04ID:FES_OPEN_REQUEST",
    close_pv="PC:04ID:FES_CLOSE_REQUEST",
    name="ashutter"
)

bshutter = ApsPssShutterWithStatus(
    "",
    "PA:04ID:B_BEAM_PRESENT",
    open_pv="PC:04ID:SBS_OPEN_REQUEST",
    close_pv="PC:04ID:SBS_CLOSE_REQUEST",
    name="bshutter"
)
