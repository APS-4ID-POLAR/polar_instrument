
"""
Diffractometer motors
"""

__all__ = ['fourc']

from ophyd import (Component, FormattedComponent, PseudoSingle, Kind,
                   EpicsSignal, EpicsMotor, Signal)
from bluesky.suspenders import SuspendBoolLow
from ..framework import RE
from ..framework import sd
from .energy import energy as bl_energy
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

    # theta = Component(EpicsMotor, 'm65', labels=("motor", "fourc"))
    omega = Component(EpicsMotor, 'm65', labels=("motor", "fourc"))
    chi = Component(EpicsMotor, 'm67', labels=("motor", "fourc"))
    phi = Component(EpicsMotor, 'm68', labels=("motor", "fourc"))
    tth = Component(EpicsMotor, 'm66', labels=("motor", "fourc"))

    th_tth_min = Component(EpicsSignal, "userCalc1.C",
                           labels=('fourc', 'limits'),
                           kind='config')
    th_tth_permit = Component(EpicsSignal, "userCalc1.VAL",
                              labels=('fourc', 'limits'),
                              kind='config')

    # Explicitly selects the real motors
    # _real = ['theta', 'chi', 'phi', 'tth']
    _real = ['omega', 'chi', 'phi', 'tth']

    # Cryo carrier
    x = Component(EpicsMotor, 'm14', labels=('motor', 'fourc'))  # Cryo X
    y = Component(EpicsMotor, 'm15', labels=('motor', 'fourc'))  # Cryo Y
    z = Component(EpicsMotor, 'm16', labels=('motor', 'fourc'))  # Cryo Z

    # Base motors
    baseth = Component(EpicsMotor, 'm69', labels=('motor', 'fourc'))
    basetth = Component(EpicsMotor, 'm70', labels=('motor', 'fourc'))

    tablex = Component(EpicsMotor, 'm18', labels=('motor', 'fourc'))
    tabley = Component(EpicsMotor, 'm17', labels=('motor', 'fourc'))

    # Analyzer motors
    ath = Component(EpicsMotor, 'm77', labels=('motor', 'fourc'))
    achi = Component(EpicsMotor, 'm79', labels=('motor', 'fourc'))
    atth = Component(EpicsMotor, 'm78', labels=('motor', 'fourc'))

    # Energy
    # energy = FormattedComponent(EpicsSignalRO, "4idb:BraggERdbkAO",
    #                             kind='omitted')
    energy = FormattedComponent(Signal, value=8)
    # energy_EGU = Component(EpicsSignal, "optics:energy.EGU")
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


def update_energy(value=None, **kwargs):
    fourc.energy.put(value)


bl_energy.wait_for_connection(timeout=10)
bl_energy.subscribe(update_energy)

fourc = FourCircleDiffractometer('4iddx:', name='fourc')
fourc.energy.put(bl_energy.get())
# fourc.calc.physical_axis_names = {'omega': 'theta',
#                                   'chi': 'chi',
#                                   'phi': 'phi',
#                                   'tth': 'tth'}
sus = SuspendBoolLow(fourc.th_tth_permit)
RE.install_suspender(sus)

# TODO: This is a rough workaround...
for attr in "x y z baseth basetth ath achi atth tablex tabley".split():
    getattr(fourc, attr).kind = "normal"

select_diffractometer(fourc)
sd.baseline.append(fourc)
