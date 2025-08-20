"""
Electromagnet
"""

from ophyd import Component, Device, EpicsMotor
from .magnet_kepco_4idb import KepcoController


class Magnet2T(Device):
    sx = Component(EpicsMotor, "4idb:m18", labels=("motor",))
    sy = Component(EpicsMotor, "4idb:m17", labels=("motor",))
    srot = Component(EpicsMotor, "4idb:m19", labels=("motor",))

    mx = Component(EpicsMotor, "4idb:m22", labels=("motor",))
    my = Component(EpicsMotor, "4idb:m21", labels=("motor",))
    mrot = Component(EpicsMotor, "4idb:m20", labels=("motor",))

    kepco = Component(KepcoController, "4idbSoft:BOP:PS1:", labels=("magnet",))

    def default_settings(self):
        self.kepco.default_settings()
