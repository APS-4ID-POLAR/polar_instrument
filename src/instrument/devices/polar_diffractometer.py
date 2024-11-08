"""
Simulated polar
"""

__all__ = ['polar', 'polar_psi']

from ophyd import Component, PseudoSingle, Kind, Signal, EpicsMotor
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
    h = Component(PseudoSingle, '', labels=("hkl", "polar"))
    k = Component(PseudoSingle, '', labels=("hkl", "polar"))
    l = Component(PseudoSingle, '', labels=("hkl", "polar"))

    tau = Component(EpicsMotor, "m9", labels=("motor", "polar"))
    mu = Component(EpicsMotor, "m10", labels=("motor", "polar"))
    chi = Component(EpicsMotor, "m11", labels=("motor", "polar"))
    phi = Component(EpicsMotor, "m12", labels=("motor", "polar"))
    gamma = Component(EpicsMotor, "m13", labels=("motor", "polar"))
    delta = Component(EpicsMotor, "m14", labels=("motor", "polar"))

    # Explicitly selects the real motors
    # _real = ['theta', 'chi', 'phi', 'tth']
    _real = " tau mu chi phi gamma delta".split()

    # Energy
    energy = Component(Signal, value=8)
    energy_update_calc_flag = Component(Signal, value=1)
    energy_offset = Component(Signal, value=0)

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
    "4idsoftmotors:", name='polar', labels=("diffractometer",)
)


class SixcPSI(ApsPolar):
    """
    ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

    Psi engine.
    """
    # the reciprocal axes are called "pseudo" in hklpy
    psi = Component(PseudoSingle, '')
    # the motor axes are called "real" in hklpy
    tau = Component(EpicsMotor, "m9", labels=("motor", "polar_psi"))
    mu = Component(EpicsMotor, "m10", labels=("motor", "polar_psi"))
    chi = Component(EpicsMotor, "m11", labels=("motor", "polar_psi"))
    phi = Component(EpicsMotor, "m12", labels=("motor", "polar_psi"))
    gamma = Component(EpicsMotor, "m13", labels=("motor", "polar_psi"))
    delta = Component(EpicsMotor, "m14", labels=("motor", "polar_psi"))


polar_psi = SixcPSI(
    "4idsoftmotors:", name="polar_psi", engine="psi", labels=("diffractometer",)
)
select_diffractometer(polar)
