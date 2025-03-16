"""
Simulated polar
"""

__all__ = ['huber', 'huber_psi']

from ophyd import (
    Component, PseudoSingle, Kind, Signal, EpicsMotor, EpicsSignalRO
)
from ophyd.sim import SynAxis
from .jj_slits import SlitDevice
from .huber_filter import HuberFilter
from ..utils import logger
import gi
gi.require_version('Hkl', '5.0')
# MUST come before `import hkl`
from hkl.geometries import ApsPolar
from hkl.user import select_diffractometer
logger.info(__file__)


class SixCircleDiffractometer(ApsPolar):
    """
    ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

    HKL engine.
    """

    # HKL and 6C motors
    h = Component(PseudoSingle, '', labels=("hkl", ))
    k = Component(PseudoSingle, '', labels=("hkl", ))
    l = Component(PseudoSingle, '', labels=("hkl", ))

    tau = Component(SynAxis)
    mu = Component(EpicsMotor, "m4", labels=("motor", ))
    chi = Component(EpicsMotor, "m37", labels=("motor", ))
    phi = Component(EpicsMotor, "m38", labels=("motor", ))
    gamma = Component(EpicsMotor, "m19", labels=("motor", ))
    delta = Component(EpicsMotor, "m20", labels=("motor", ))

    # Explicitly selects the real motors
    _real = " tau mu chi phi gamma delta".split()

    # Table vertical/horizontal
    tablex = Component(EpicsMotor, "m3", labels=("motor", ))
    tabley = Component(EpicsMotor, "m1", labels=("motor", ))

    # Area detector motors
    pad_rail = Component(EpicsMotor, "m21", labels=("motor", ))
    point_rail = Component(EpicsMotor, "m22", labels=("motor", ))

    # # Guard slit
    # guardslt  = ...

    # Filters
    filter = Component(HuberFilter, "atten:", labels=("filter"))

    # Detector JJ slit
    detslt = Component(
        SlitDevice,
        {'top': 'm31', 'bot': 'm32', 'out': 'm34', 'inb': 'm33'},
        2,
        labels=('slit',)
    )

    # Analyzer motors
    ana_th = Component(EpicsMotor, "m24", labels=("motor", ))
    ana_tth = Component(EpicsMotor, "m25", labels=("motor", ))
    ana_eta = Component(EpicsMotor, "m23", labels=("motor", ))
    ana_chi = Component(EpicsMotor, "m26", labels=("motor", ))

    # Energy
    energy = Component(EpicsSignalRO, "4idVDCM:BraggERdbkAO", kind="config")
    energy_update_calc_flag = Component(Signal, value=1, kind="config")
    energy_offset = Component(Signal, value=0, kind="config")

    # TODO: This is needed to prevent busy plotting.
    @property
    def hints(self):
        fields = []
        for _, component in self._get_components_of_kind(Kind.hinted):
            if (~Kind.normal & Kind.hinted) & component.kind:
                c_hints = component.hints
                fields.extend(c_hints.get('fields', []))
        return {'fields': fields}


huber = SixCircleDiffractometer(
    "4idgSoft:", name='huber', labels=("4idg", "diffractometer",)
)


class SixcPSI(ApsPolar):
    """
    ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

    Psi engine.
    """
    # the reciprocal axes are called "pseudo" in hklpy
    psi = Component(PseudoSingle, '')
    # the motor axes are called "real" in hklpy
    tau = Component(SynAxis)
    mu = Component(EpicsMotor, "m4", labels=("motor", ))
    chi = Component(EpicsMotor, "m37", labels=("motor", ))
    phi = Component(EpicsMotor, "m38", labels=("motor", ))
    gamma = Component(EpicsMotor, "m19", labels=("motor", ))
    delta = Component(EpicsMotor, "m20", labels=("motor", ))


huber_psi = SixcPSI(
    "4idgSoft:",
    name="huber_psi",
    engine="psi",
    labels=("4idg", "diffractometer",)
)
select_diffractometer(huber)
