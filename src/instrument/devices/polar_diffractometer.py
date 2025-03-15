"""
Simulated polar
"""

__all__ = ['polar', 'polar_psi']

from ophyd import (
    Component, PseudoSingle, Kind, Signal, EpicsMotor, EpicsSignalRO
)
from ophyd.sim import SynAxis
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
    # _real = ['theta', 'chi', 'phi', 'tth']
    _real = " tau mu chi phi gamma delta".split()

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


polar = SixCircleDiffractometer(
    "4idgSoft:", name='polar', labels=("diffractometer",)
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


polar_psi = SixcPSI(
    "4idgSoft:", name="polar_psi", engine="psi", labels=("diffractometer",)
)
select_diffractometer(polar)
