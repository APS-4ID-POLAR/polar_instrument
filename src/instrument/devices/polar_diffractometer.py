"""
Simulated polar
"""

__all__ = ['huber_euler', 'huber_hp', 'huber_euler_psi', 'huber_hp_psi']

from ophyd import (
    Component, FormattedComponent, PseudoSingle, Kind, Signal, EpicsMotor, EpicsSignalRO
)
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

    # 03/16/2025 - Tau is the whole diffractometer "theta" angle, but
    # it is not currently setup. m73 is a simulated motor.
    tau = Component(EpicsMotor, "m73", labels=("motor", ))    
    mu = Component(EpicsMotor, "m4", labels=("motor", ))
    gamma = Component(EpicsMotor, "m19", labels=("motor", ))
    delta = Component(EpicsMotor, "m20", labels=("motor", ))

    # Explicitly selects the real motors
    _real = "tau mu chi phi gamma delta".split()

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
       "",
       motorsDict={'top': 'm31', 'bot': 'm32', 'out': 'm34', 'inb': 'm33'},
       slitnum=2,
       labels=('slit',)
    )

    # Analyzer motors
    ana_th = Component(EpicsMotor, "m24", labels=("motor", ))
    ana_tth = Component(EpicsMotor, "m25", labels=("motor", ))
    ana_eta = Component(EpicsMotor, "m23", labels=("motor", ))
    ana_chi = Component(EpicsMotor, "m26", labels=("motor", ))

    # Energy
    energy = FormattedComponent(EpicsSignalRO, "4idVDCM:BraggERdbkAO", kind="config")
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
    
    def polan(self, param1, param2):
        energy = self.energy.get()
        wv = self.calc.wavelength
    

class CradleDiffractometer(SixCircleDiffractometer):
    chi = Component(EpicsMotor, "m37", labels=("motor",))
    phi = Component(EpicsMotor, "m38", labels=("motor",))

    x = Component(EpicsMotor, "m40", labels=("motor",))
    y = Component(EpicsMotor, "m41", labels=("motor",))
    z = Component(EpicsMotor, "m42", labels=("motor",))


class HPDiffractometer(SixCircleDiffractometer):
    chi = Component(EpicsMotor, "m5", labels=("motor",))
    phi = Component(EpicsMotor, "m6", labels=("motor",))

    basex = Component(EpicsMotor, "m7", labels=("motor",))
    basey = Component(EpicsMotor, "m9", labels=("motor",))
    basez = Component(EpicsMotor, "m8", labels=("motor",))

    sample_tilt = Component(EpicsMotor, "m11", labels=("motor",))

    x = Component(EpicsMotor, "m12", labels=("motor",))
    y = Component(EpicsMotor, "m14", labels=("motor",))
    z = Component(EpicsMotor, "m13", labels=("motor",))

    nanox = FormattedComponent(EpicsMotor, "4idgSoftX:jena:m1", labels=("motors",))
    nanoy = FormattedComponent(EpicsMotor, "4idgSoftX:jena:m2", labels=("motors",))
    nanoz = FormattedComponent(EpicsMotor, "4idgSoftX:jena:m3", labels=("motors",))
SixCircleDiffractometer
class PolarPSI(ApsPolar):
    """
    ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

    Psi engine.
    """
    # the reciprocal axes are called "pseudo" in hklpy
    psi = Component(PseudoSingle, '')

    # 03/16/2025 - Tau is the whole diffractometer "theta" angle, but
    # it is not currently setup. m73 is a simulated motor.
    tau = Component(EpicsMotor, "m73", labels=("motor", ))
    mu = Component(EpicsMotor, "m4", labels=("motor", ))
    gamma = Component(EpicsMotor, "m19", labels=("motor", ))
    delta = Component(EpicsMotor, "m20", labels=("motor", ))


class CradlePSI(PolarPSI):
    chi = Component(EpicsMotor, "m37", labels=("motor",))
    phi = Component(EpicsMotor, "m38", labels=("motor",))


class HPPSI(PolarPSI):
    chi = Component(EpicsMotor, "m5", labels=("motor",))
    phi = Component(EpicsMotor, "m6", labels=("motor",))


huber_euler = CradleDiffractometer(
    "4idgSoft:", name='huber_euler', labels=("4idg", "diffractometer",)
)


huber_hp = HPDiffractometer(
    "4idgSoft:", name='huber_hp', labels=("4idg", "diffractometer",)
)

huber_euler_psi = CradlePSI(
    "4idgSoft:",
    name="huber_euler_psi",
    engine="psi",
    labels=("4idg", "diffractometer",)
)

huber_hp_psi = CradlePSI(
    "4idgSoft:",
    name="huber_hp_psi",
    engine="psi",
    labels=("4idg", "diffractometer",)
)

select_diffractometer(huber_euler)
huber_euler._update_calc_energy()
huber_euler_psi._update_calc_energy()
