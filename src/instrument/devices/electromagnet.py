
"""
Electromagnet
"""

__all__ = ['emag']

from ophyd import Component, Device, EpicsMotor
from .magnet_kepco import KepcoController
from ..utils._logging_setup import logger
logger.info(__file__)


class Magnet2T(Device):
    # tablex = Component(EpicsMotor, "4idbSoft:m15")
    # tabley = Component(EpicsMotor, "4idbSoft:m16")
    samplex = Component(EpicsMotor, "4idb:m25", labels=("motor",))
    sampley = Component(EpicsMotor, "4idb:m17", labels=("motor",))
    kepco = Component(KepcoController, '4idbSoft:BOP:PS1:', labels=("magnet",))

emag = Magnet2T("", name="electromagnet", labels=("4idb", "magnet"))
emag.kepco.mode_change(value=emag.kepco.mode.get())