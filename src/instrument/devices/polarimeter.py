"""
Polarization analyzer
"""

__all__ = ["polanalyzer"]

from ophyd import Device, Component, EpicsMotor
from .preamps import LocalPreAmp
from ..utils._logging_setup import logger
logger.info(__file__)


class PolAnalyzer(Device):
    y = Component(EpicsMotor, "m17", labels=("motor",))
    # th = Component(EpicsMotor, "XXX", labels=("motor",))

    vertical_preamp = LocalPreAmp(
        'A1', labels=('preamp', 'detector',), kind="config"
    )
    horizontal_preamp = LocalPreAmp(
        'A2', labels=('preamp', 'detector',), kind="config"
    )


polanalyzer = PolAnalyzer("4idbSoft:", name="polanalyzer")

for pa in [polanalyzer.vertical_preamp, polanalyzer.horizontal_preamp]:
    pa.offset_fine._string = False
    for item in (
        "offset_fine set_all offset_value offset_unit offset_fine"
    ).split():
        getattr(pa, item).put_complete = True
