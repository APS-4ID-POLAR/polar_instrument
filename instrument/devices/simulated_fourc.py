"""
Simulated fourc
"""

from ophyd import Component, Device
from ophyd.sim import SynAxis


__all__ = ['fourc']

from ophyd import (Component, PseudoSingle, Kind, Signal)
from ..framework import sd
import gi
gi.require_version('Hkl', '5.0')
# MUST come before `import hkl`
from hkl.geometries import E4CV
from hkl.user import select_diffractometer
from ..session_logs import logger
logger.info(__file__)


class FourCircleDiffractometer(E4CV):
    """
    E4CV: huber diffractometer in 4-circle vertical geometry with energy.

    4-ID-D setup.
    """

    # HKL and 4C motors
    h = Component(PseudoSingle, '', labels=("hkl", "fourc"))
    k = Component(PseudoSingle, '', labels=("hkl", "fourc"))
    l = Component(PseudoSingle, '', labels=("hkl", "fourc"))

    omega = Component(SynAxis, name="omega", labels=("motor", "fourc"))
    chi = Component(SynAxis, name="chi", labels=("motor", "fourc"))
    phi = Component(SynAxis, name="phi", labels=("motor", "fourc"))
    tth = Component(SynAxis, name="tth", labels=("motor", "fourc"))

    # Explicitly selects the real motors
    # _real = ['theta', 'chi', 'phi', 'tth']
    _real = ['omega', 'chi', 'phi', 'tth']

    # Energy
    energy = Component(Signal, value=8)
    energy_update_calc_flag = Component(Signal, value=1)
    energy_offset = Component(Signal, value=0)

    # TODO: This is needed to prevent busy plotting.
    @property
    def hints_test(self):
        fields = []
        for _, component in self._get_components_of_kind(Kind.hinted):
            if (~Kind.normal & Kind.hinted) & component.kind:
                c_hints = component.hints
                fields.extend(c_hints.get('fields', []))
        return {'fields': fields}


fourc = FourCircleDiffractometer("", name='fourc')
fourc.omega.setpoint.put(1)
fourc.chi.setpoint.put(0)
fourc.phi.setpoint.put(0)
fourc.tth.setpoint.put(2)
select_diffractometer(fourc)
sd.baseline.append(fourc)

