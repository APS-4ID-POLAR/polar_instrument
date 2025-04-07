"""
Simulated polar
"""

__all__ = ["huber_euler", "huber_hp", "huber_euler_psi", "huber_hp_psi"]

from ophyd import (
    Component,
    FormattedComponent,
    PseudoSingle,
    Kind,
    Signal,
    EpicsMotor,
    EpicsSignalRO,
)
from .jj_slits import SlitDevice
from .huber_filter import HuberFilter

# from ..utils import logger
import gi

gi.require_version("Hkl", "5.0")
# MUST come before `import hkl`
from hkl.geometries import ApsPolar
from hkl.user import select_diffractometer
import math

# logger.info(__file__)

# Constants
WAVELENGTH_CONSTANT = 12.39
PTTH_MIN_DEGREES = 79
PTTH_MAX_DEGREES = 101
PTH_MIN_DEGREES = 39
PTH_MAX_DEGREES = 51


class SixCircleDiffractometer(ApsPolar):
    """
    ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

    HKL engine.
    """

    # HKL and 6C motors
    h = Component(PseudoSingle, "", labels=("hkl",))
    k = Component(PseudoSingle, "", labels=("hkl",))
    l = Component(PseudoSingle, "", labels=("hkl",))

    # 03/16/2025 - Tau is the whole diffractometer "theta" angle, but
    # it is not currently setup. m73 is a simulated motor.
    tau = Component(EpicsMotor, "m73", labels=("motor",))
    mu = Component(EpicsMotor, "m4", labels=("motor",))
    gamma = Component(EpicsMotor, "m19", labels=("motor",))
    delta = Component(EpicsMotor, "m20", labels=("motor",))

    # Explicitly selects the real motors
    _real = "tau mu chi phi gamma delta".split()

    # Table vertical/horizontal
    tablex = Component(EpicsMotor, "m3", labels=("motor",))
    tabley = Component(EpicsMotor, "m1", labels=("motor",))

    # Area detector motors
    pad_rail = Component(EpicsMotor, "m21", labels=("motor",))
    point_rail = Component(EpicsMotor, "m22", labels=("motor",))

    # # Guard slit
    # guardslt  = ...

    # Filters
    filter = Component(HuberFilter, "atten:", labels=("filter"))

    # Detector JJ slit
    detslt = Component(
        SlitDevice,
        "",
        motorsDict={"top": "m31", "bot": "m32", "out": "m34", "inb": "m33"},
        slitnum=2,
        labels=("slit",),
    )

    # Analyzer motors
    ana_th = Component(EpicsMotor, "m24", labels=("motor",))
    ana_tth = Component(EpicsMotor, "m25", labels=("motor",))
    ana_eta = Component(EpicsMotor, "m23", labels=("motor",))
    ana_chi = Component(EpicsMotor, "m26", labels=("motor",))

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
                fields.extend(c_hints.get("fields", []))
        return {"fields": fields}

    def anacalc(self):
        # read d_ana and wavelength from PV
        wavelength = self.calc.wavelength
        d_ana = 0.904
        wavelength = WAVELENGTH_CONSTANT / 10
        th_angle = math.degrees(math.asin(wavelength / (2 * d_ana)))
        tth_angle = 2 * th_angle
        print(f"th_angle={th_angle} tth_angle={tth_angle}")
        # Implement movement and/or calibration to angles

    def anasetup(self):
        energy = self.energy.get()
        wavelength = self.calc.wavelength
        ptthmin = math.radians(PTTH_MIN_DEGREES)
        ptthmax = math.radians(PTTH_MAX_DEGREES)

        def calcdhkl(h, k, l, alpha, beta, gamma, symmetry, a, b, c):
            if symmetry == "cub":
                dhkl2inv = (h * h + k * k + l * l) / (a * a)
            elif symmetry == "tet":
                dhkl2inv = (h * h + k * k) / (a * a) + (l * l) / (c * c)
            elif symmetry == "ort":
                dhkl2inv = (h * h) / (a * a) + (k * k) / (b * b) + (l * l) / (c * c)
            elif symmetry == "rho":
                n = (h * h + k * k + l * l) * pow(math.sin(alpha), 2.0) + 2.0 * (h * k + k * l + h * l) * (
                    pow(math.cos(alpha), 2.0) - math.cos(alpha)
                )
                d = a * a * (1.0 - 3.0 * pow(math.cos(alpha), 2.0) + 2.0 * pow(math.cos(alpha), 3.0))
                dhkl2inv = n / d
            elif symmetry == "hex":
                dhkl2inv = (4.0 / 3.0) * (h * h + h * k + k * k) / (a * a) + (l * l) / (c * c)
            elif symmetry == "monoclinic":
                dhkl2inv = (
                    (h * h) / (a * a)
                    + (k * k * pow(math.sin(beta), 2.0)) / (b * b)
                    + (l * l) / (c * c)
                    - (2.0 * h * l * math.cos(beta)) / (a * c)
                ) / (pow(math.sin(beta), 2.0))
            elif symmetry == "triclinic":
                V = (
                    a
                    * b
                    * c
                    * math.sqrt(
                        (
                            1.0
                            - pow(math.cos(alpha), 2.0)
                            - pow(math.cos(beta), 2.0)
                            - pow(math.cos(gamma), 2.0)
                            + 2.0 * math.cos(alpha) * math.cos(beta) * math.cos(gamma)
                        )
                    )
                )
                n1 = (
                    pow(h * b * c * math.sin(alpha), 2)
                    + pow(k * a * c * math.sin(beta), 2)
                    + pow(l * a * b * math.sin(gamma), 2)
                )
                n2 = 2 * h * k * a * b * c * c * (math.cos(alpha) * math.cos(beta) - math.cos(gamma))
                n3 = 2 * k * l * a * a * b * c * (math.cos(beta) * math.cos(gamma) - math.cos(alpha))
                n4 = 2 * h * l * a * b * b * c * (math.cos(alpha) * math.cos(gamma) - math.cos(beta))
                dhkl2inv = (n1 + n2 + n3 + n4) / (pow(V, 2.0))
            else:
                raise ValueError("Lattice system not specified for this analyzer.")
            return 1.0 / math.sqrt(dhkl2inv)

        def check_structure_factor(h, k, l, spacegroupnumber, special):
            if spacegroupnumber == 225 and special == "none":
                return (h + k) % 2 == 0 and (k + l) % 2 == 0 and (h + l) % 2 == 0
            elif spacegroupnumber == 229 and special == "none":
                return (h + k + l) % 2 == 0
            elif spacegroupnumber == 227 and special == "8a":
                return ((h + k + l) % 2 != 0 and (h != 0 and k != 0 and l != 0)) or (
                    (h + k + l) % 2 == 0 and (h + k + l) % 4 == 0
                )
            elif spacegroupnumber == 194 and special == "2c":
                return l % 2 == 0 or (h - k - 1) % 3 == 0 or (h - k - 2) % 3 == 0
            elif spacegroupnumber == 167 and special == "12c":
                return (-h + k + l) % 3 == 0 and l % 2 == 0
            elif spacegroupnumber == 62 and special == "4b":
                return (h + l) % 2 == 0 and k % 2 == 0
            else:
                return True

        d_dict = {}
        print(f"{'#':>2}{'Crystal':>8}{'Refl.':>11}{'Range (keV)':>15}{'d_hkl':>10}{'2th (deg)':>11}")
        with open("analyzerlist.dat") as f:
            for num, line in enumerate(f):
                split = line.split()
                if "##REFERENCES" in line:
                    break
                (
                    analyzer,
                    hh,
                    kk,
                    ll,
                    a,
                    b,
                    c,
                    alpha,
                    beta,
                    gamma,
                    symmetry,
                    spacegroupnumber,
                    special,
                ) = split[:13]
                hh, kk, ll = map(int, [hh, kk, ll])
                a, b, c = map(float, [a, b, c])
                alpha, beta, gamma = map(lambda x: math.radians(float(x)), [alpha, beta, gamma])
                spacegroupnumber = int(spacegroupnumber)

                for i in range(1, 100):  # Arbitrary limit to prevent infinite loop
                    hhh, kkk, lll = hh * i, kk * i, ll * i
                    dhkl = calcdhkl(hhh, kkk, lll, alpha, beta, gamma, symmetry, a, b, c)
                    if check_structure_factor(hhh, kkk, lll, spacegroupnumber, special):
                        ana_emax = WAVELENGTH_CONSTANT / (2 * dhkl * math.sin(ptthmin / 2))
                        ana_emin = WAVELENGTH_CONSTANT / (2 * dhkl * math.sin(ptthmax / 2))

                        if ana_emin <= energy <= ana_emax:
                            tt_angle = 2 * math.degrees(math.asin(wavelength / (2 * dhkl)))
                            print(
                                f"{num:>2} {analyzer:<9} {hhh:>2}{kkk:>3}{lll:>3}  [{ana_emin:5.2f},{ana_emax:5.2f}]{dhkl:10.3f}{tt_angle:11.2f}"
                            )
                            d_dict[num] = [
                                analyzer,
                                hhh,
                                kkk,
                                lll,
                                dhkl,
                                tt_angle,
                            ]
                            break
                        elif ana_emin > energy:
                            break
        ttdiff = max(abs(ptthmax - 90), abs(ptthmin - 90))
        d_best = {}
        for key, value in d_dict.items():
            if abs(value[5] - 90) < ttdiff:
                ttdiff = abs(value[5] - 90)
                d_best = [key, value]
        anum = input(f"Choice of polarization analyzer [{d_best[0]}]: ") or d_best[0]
        anum = int(anum) if isinstance(anum, str) else anum
        if anum in d_dict:
            ana = d_dict[anum]
            cryst = f"{ana[0]}{ana[1]}{ana[2]}{ana[3]}"
        else:
            ana = d_best[1:][0]
            cryst = f"{ana[0]}{ana[1]}{ana[2]}{ana[3]}"
            print(f"Choice not possible, using {cryst}")

        d_ana = ana[4]
        # write variables to PVs
        return cryst, d_ana


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
    psi = Component(PseudoSingle, "")

    # 03/16/2025 - Tau is the whole diffractometer "theta" angle, but
    # it is not currently setup. m73 is a simulated motor.
    tau = Component(EpicsMotor, "m73", labels=("motor",))
    mu = Component(EpicsMotor, "m4", labels=("motor",))
    gamma = Component(EpicsMotor, "m19", labels=("motor",))
    delta = Component(EpicsMotor, "m20", labels=("motor",))


class CradlePSI(PolarPSI):
    chi = Component(EpicsMotor, "m37", labels=("motor",))
    phi = Component(EpicsMotor, "m38", labels=("motor",))


class HPPSI(PolarPSI):
    chi = Component(EpicsMotor, "m5", labels=("motor",))
    phi = Component(EpicsMotor, "m6", labels=("motor",))


huber_euler = CradleDiffractometer(
    "4idgSoft:",
    name="huber_euler",
    labels=(
        "4idg",
        "diffractometer",
    ),
)


huber_hp = HPDiffractometer(
    "4idgSoft:",
    name="huber_hp",
    labels=(
        "4idg",
        "diffractometer",
    ),
)

huber_euler_psi = CradlePSI(
    "4idgSoft:",
    name="huber_euler_psi",
    engine="psi",
    labels=(
        "4idg",
        "diffractometer",
    ),
)

huber_hp_psi = CradlePSI(
    "4idgSoft:",
    name="huber_hp_psi",
    engine="psi",
    labels=(
        "4idg",
        "diffractometer",
    ),
)

select_diffractometer(huber_euler)
huber_euler._update_calc_energy()
huber_euler_psi._update_calc_energy()
