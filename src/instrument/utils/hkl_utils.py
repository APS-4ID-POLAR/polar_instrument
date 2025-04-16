"""
Auxilary HKL functions.

.. autosummary::
    ~select_engine_for_psi
    ~engine_for_psi
    ~set_experiment
    ~set_diffractometer
    ~sampleNew
    ~sampleChange
    ~sampleList
    ~sampleRemove
    ~list_reflections
    ~or_swap
    ~setor0
    ~setor1
    ~set_orienting
    ~del_reflection
    ~list_orienting
    ~or0
    ~or1
    ~compute_UB
    ~calc_UB
    ~setmode
    ~ca
    ~br
    ~uan
    ~wh
    ~setlat
    ~setaz
    ~freeze
    ~update_lattice
    ~write_config
    ~read_config
    ~show_constraints
    ~reset_constraints
    ~set_constraints
"""

import pathlib
from ophyd import SoftPositioner
from bluesky import RunEngineInterrupted
from bluesky.utils import ProgressBarManager
from bluesky.plan_stubs import mv
from hkl.util import (
    restore_sample, restore_constraints, restore_reflections, run_orientation_info
)
from hkl.user import current_diffractometer
from polartools.manage_database import db_query
from .run_engine import RE
from ..devices.polar_diffractometer import huber_euler, huber_euler_psi
from ..devices.simulated_fourc_vertical import fourc
from ._logging_setup import logger

from .catalog import full_cat
from .polartools_hklpy_imports import pa

cat = db_query(full_cat, dict(instrument_name = 'polar-4idg'))

try:
    from hkl import cahkl
    from hkl.util import Lattice
    from hkl.user import (
        _check_geom_selected,
        _geom_,
        select_diffractometer,
        current_diffractometer,
    )
    from hkl.util import Constraint
    from hkl.configuration import DiffractometerConfiguration
    from hkl.diffract import Diffractometer
except ModuleNotFoundError:
    print("gi module is not installed, the hkl_utils functions will not work!")
    cahkl = _check_geom_selected = _geom_ = None

logger.info(__file__)

polar_config = pathlib.Path("polar-config.json")
fourc_config = pathlib.Path("fourc-config.json")
pbar_manager = ProgressBarManager()
_geom_for_psi_ = None
POLAR_DIFFRACTOMETER = "huber"


def select_engine_for_psi(instrument=None):
    """Name the diffractometer to be used."""
    global _geom_for_psi_
    if instrument is None or isinstance(instrument, Diffractometer):
        _geom_for_psi_ = instrument
    else:
        raise TypeError(f"{instrument} must be a 'Diffractometer' subclass")


def engine_for_psi():
    """Return the currently-selected psi calc engine (or ``None``)."""
    return _geom_for_psi_


def set_diffractometer(instrument=None):
    """Name the diffractometer to be used."""
    _geom_ = current_diffractometer()
    if instrument:
        diff = instrument.name
    elif instrument is None:
        diff = (input("Diffractometer [polar or fourc] ({})? ".format(_geom_.name))) or _geom_.name
    else:
        raise ValueError(
            "either no argument or diffractometer polar or fourc to be provided."
        )
    if diff == 'fourc':
        select_diffractometer(fourc)
        print("Diffractometer {} selected".format(diff))
    elif diff == 'polar':
        select_diffractometer(huber)
        print("Diffractometer {} selected".format(diff))
    else:
        raise ValueError(
            "{} not an existing diffractometer".format(diff)
        )

def sampleNew(*args):
    """
    Set the lattice constants.

    Parameters
    ----------
    a, b, c, alpha, beta, gamma : float, optional
        Lattice constants. If None, it will ask for input.
    """
    _geom_ = current_diffractometer()
    current_sample = _geom_.calc.sample_name
    sample = _geom_.calc._samples[current_sample]
    lattice = [getattr(sample.lattice, parm) for parm in sample.lattice._fields]

    if len(args) == 7:
        nm, a, b, c, alpha, beta, gamma = args
    elif len(args) == 0:
        nm = (
            input("Sample name ({})? ".format(current_sample))
        ) or current_sample
        a = (input("Lattice a ({})? ".format(lattice[0]))) or lattice[0]
        b = (input("Lattice b ({})? ".format(lattice[1]))) or lattice[1]
        c = (input("Lattice c ({})? ".format(lattice[2]))) or lattice[2]
        alpha = (input("Lattice alpha ({})? ".format(lattice[3]))) or lattice[3]
        beta = (input("Lattice beta ({})? ".format(lattice[4]))) or lattice[4]
        gamma = (input("Lattice gamma ({})? ".format(lattice[5]))) or lattice[5]
    else:
        raise ValueError(
            "either no arguments or name, a, b, c, alpha, beta, gamma need to be provided."
        )

    if nm in _geom_.calc._samples:
        logger.warning(
            ("Sample '%s' is already defined."),
            nm,
        )
    else:
        lattice = Lattice(
            a=float(a),
            b=float(b),
            c=float(c),
            alpha=float(alpha),
            beta=float(beta),
            gamma=float(gamma),
        )
        _geom_.calc.new_sample(nm, lattice=lattice)

        sample = _geom_.calc._sample
        if len(_geom_.calc.physical_axes) == 6:
            sample.add_reflection(
                0,
                0,
                2,
                position=_geom_.calc.Position(
                    gamma=40,
                    mu=20,
                    chi=-90,
                    phi=0,
                    delta=0,
                    tau=0,
                ),
            )
            sample._orientation_reflections.insert(
                0, sample._sample.reflections_get()[-1]
            )
            sample.add_reflection(
                2,
                0,
                0,
                position=_geom_.calc.Position(
                    gamma=40,
                    mu=20,
                    chi=0,
                    phi=0,
                    delta=0,
                    tau=0,
                ),
            )
        if len(_geom_.calc.physical_axes) == 4:
            sample.add_reflection(
                0,
                0,
                2,
                position=_geom_.calc.Position(
                    tth=40,
                    omega=20,
                    chi=-90,
                    phi=0,
                ),
            )
            sample._orientation_reflections.insert(
                0, sample._sample.reflections_get()[-1]
            )
            sample.add_reflection(
                2,
                0,
                0,
                position=_geom_.calc.Position(
                    tth=40,
                    omega=20,
                    chi=0,
                    phi=0,
                ),
            )
        sample._orientation_reflections.insert(
            1, sample._sample.reflections_get()[-1]
        )
        compute_UB()
        if POLAR_DIFFRACTOMETER in _geom_.name:
            set_constraints('mu',-100,100)
            set_constraints('gamma',-10,180)
            set_constraints('delta',-20,60)
            set_constraints('tau',-0.5,0.5)
        if _geom_.name == "fourc":
            set_constraints('omega',-100,100)
            set_constraints('tth',-10,180)            
        setaz(0,1,0)


def sampleChange(sample_key=None):
    """
    Change selected sample in hklpy.

    Parameters
    ----------
    sample_key : string, optional
        Name of the sample as set in hklpy. If None it will ask for which
        sample.
    """
    _geom_ = current_diffractometer()

    if sample_key is None:
        d = _geom_.calc._samples.keys()
        print("Sample keys:", list(d))
        sample_key = (
            input("\nEnter sample key [{}]: ".format(_geom_.calc.sample.name))
            or _geom_.calc.sample.name
        )
    try:
        _geom_.calc.sample = _geom_.calc._samples[
            sample_key
        ]  # define the current sample
        print("\nCurrent sample: " + _geom_.calc.sample.name)
        # to be done: check if orienting reflections exist
        compute_UB()

    except KeyError:
        print("Not a valid sample key")


def sampleRemove(sample_key=None):
    """
    Remove selected sample in hklpy.

    Parameters
    ----------
    sample_key : string, optional
        Name of the sample as set in hklpy. If None it will ask for which
        sample.
    """
    _geom_ = current_diffractometer()
    if sample_key is None:
        d = _geom_.calc._samples.keys()
        print("Sample keys:", list(d))
        sample_key = input("\nEnter sample key to remove: ")
        if sample_key == _geom_.calc.sample.name:
            print("The current sample cannot be removed.")
            sample_key = " "
    try:
        _geom_.calc._samples.pop(sample_key)  # remove the sample
        print("\n[{}] sample is removed.".format(sample_key))

    except KeyError:
        print("Not a valid sample key")

# In development
"""
def sampleWrite(sample_key=None):
 
    _geom_ = current_diffractometer()
    config = DiffractometerConfiguration(_geom_)

    if sample_key is None:
        d = _geom_.calc._samples.keys()
        print("Sample keys:", list(d))
        sample_key = input("\nEnter sample key to write: ")
    try:
        print(config.export('dict')['samples'][sample_key])
        print("\n[{}] sample info written to file.".format(sample_key))

    except KeyError:
        print("Not a valid sample key")



def sampelRestore(sample_key=None):

    _geom_ = current_diffractometer()
    config = DiffractometerConfiguration(_geom_)

    config.restore('test', clear=True)


def eslave(selection=None):
    if selection is None:
        print("No slave device          (0)")
        print("Undulator                (1)")
        print("Polarization analyzer    (2)")
        print("Phase plate 1            (4)")
        print("Phase plate 2            (8)")
        selection = int(input("\nEnter number: "))

"""
def _sampleList():
    """List all samples currently defined in hklpy; specify  current one."""

    _geom_ = current_diffractometer()
    samples = _geom_.calc._samples
    for x in list(samples.keys())[1:]:
        orienting_refl = samples[x]._orientation_reflections
        print("\nSample = {}".format(x))
        print("Lattice:", end=" ")
        print(*samples[x].lattice._fields, sep=", ", end=" = ")
        print(*samples[x].lattice, sep=", ")
        if len(orienting_refl) > 1:
            if len(_geom_.calc.physical_axes) == 6:
                print(
                    "\n{:>3}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}".format(
                        "#",
                        "H",
                        "K",
                        "L",
                        "Gamma",
                        "Mu",
                        "Chi",
                        "Phi",
                        "Delta",
                        "Tau",
                    )
                )
            if len(_geom_.calc.physical_axes) == 4:
                print(
                    "\n{:>3}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}".format(
                        "#",
                        "H",
                        "K",
                        "L",
                        "tth",
                        "th",
                        "chi",
                        "phi",
                    )
                )
        for ref in samples[x]._sample.reflections_get():
            if len(orienting_refl) > 1:
                if orienting_refl[0] == ref:
                    h, k, l = ref.hkl_get()
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    if len(_geom_.calc.physical_axes) == 6:
                        print(
                            "{:>3}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   ".format(
                                "or0",
                                int(h),
                                int(k),
                                int(l),
                                pos[4],
                                pos[1],
                                pos[2],
                                pos[3],
                                pos[5],
                                pos[0],
                            )
                        )
                    elif len(_geom_.calc.physical_axes) == 4:
                        print(
                            "{:>3}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   ".format(
                                "or0",
                                int(h),
                                int(k),
                                int(l),
                                pos[3],
                                pos[0],
                                pos[1],
                                pos[2],
                            )
                        )
                    else:
                        raise ValueError(
                            "Geometry {} not supported.".format(_geom_.name)
                        )

                elif orienting_refl[1] == ref:
                    h, k, l = ref.hkl_get()
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    if len(_geom_.calc.physical_axes) == 6:
                        print(
                            "{:>3}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}  ".format(
                                "or1",
                                int(h),
                                int(k),
                                int(l),
                                pos[4],
                                pos[1],
                                pos[2],
                                pos[3],
                                pos[5],
                                pos[0],
                            )
                        )
                    elif len(_geom_.calc.physical_axes) == 4:
                        print(
                            "{:>3}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}  ".format(
                                "or1",
                                int(h),
                                int(k),
                                int(l),
                                pos[3],
                                pos[0],
                                pos[1],
                                pos[2],
                            )
                        )
                    else:
                        raise ValueError(
                            "Geometry {} not supported.".format(_geom_.name)
                        )
        print(
            "======================================================================"
        )
    print("\nCurrent sample: " + _geom_.calc.sample.name)


def list_reflections(all_samples=False):
    """
    Lists all reflections in defined in hklpy.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    all_samples : boolean, optional
        If True, it will list the reflections for all samples, if False, only
        the current sample. Defaults to False.
    """
    _geom_ = current_diffractometer()
    _check_geom_selected()

    if all_samples:
        samples = _geom_.calc._samples.values()
    else:
        samples = [_geom_.calc._sample]
    for sample in samples:
        print("Sample: {}".format(sample.name))
        orienting_refl = sample._orientation_reflections
        if len(_geom_.calc.physical_axes) == 6:
            print(
                "\n{:>2}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}   {:<12}".format(
                    "#",
                    "H",
                    "K",
                    "L",
                    "Delta",
                    "Eta",
                    "Chi",
                    "Phi",
                    "Nu",
                    "Mu",
                    "orienting",
                )
            )
        elif len(_geom_.calc.physical_axes) == 4:
            print(
                "\n{:>2}{:>4}{:>3}{:>3}{:>12}{:>9}{:>9}{:>9}   {:<12}".format(
                    "#",
                    "H",
                    "K",
                    "L",
                    "Two Theta",
                    "Theta",
                    "Chi",
                    "Phi",
                    "orienting",
                )
            )
        else:
            raise ValueError("Geometry {} not supported.".format(_geom_.name))

        for i, ref in enumerate(sample._sample.reflections_get()):
            if orienting_refl[0] == ref:
                h, k, l = ref.hkl_get()
                pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                if len(_geom_.calc.physical_axes) == 6:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[4],
                            pos[1],
                            pos[2],
                            pos[3],
                            pos[5],
                            pos[0],
                            "first",
                        )
                    )
                elif len(_geom_.calc.physical_axes) == 4:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[3],
                            pos[0],
                            pos[1],
                            pos[2],
                            "first",
                        )
                    )
                else:
                    raise ValueError(
                        "Geometry {} not supported.".format(_geom_.name)
                    )
            elif orienting_refl[1] == ref:
                h, k, l = ref.hkl_get()
                pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                if len(_geom_.calc.physical_axes) == 6:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[4],
                            pos[1],
                            pos[2],
                            pos[3],
                            pos[5],
                            pos[0],
                            "second",
                        )
                    )
                elif len(_geom_.calc.physical_axes) == 4:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[3],
                            pos[0],
                            pos[1],
                            pos[2],
                            "second",
                        )
                    )
                else:
                    raise ValueError(
                        "Geometry {} not supported.".format(_geom_.name)
                    )
            else:
                h, k, l = ref.hkl_get()
                pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                if len(_geom_.calc.physical_axes) == 6:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[4],
                            pos[1],
                            pos[2],
                            pos[3],
                            pos[5],
                            pos[0],
                        )
                    )
                elif len(_geom_.calc.physical_axes) == 4:
                    print(
                        "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                            i,
                            int(h),
                            int(k),
                            int(l),
                            pos[3],
                            pos[0],
                            pos[1],
                            pos[2],
                        )
                    )
                else:
                    raise ValueError(
                        "Geometry {} not supported.".format(_geom_.name)
                    )
        if len(samples) > 1 and all_samples:
            print(
                "============================================================================"
            )


def or_swap():
    """Swaps the two orientation reflections in hklpy."""
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if len(orienting_refl) > 1:
        sample.swap_orientation_reflections()
        list_reflections()
    else:
        print("Missing orienting reflections!")
    compute_UB()

def setor0(*args):
    """
    Sets the primary orientation in hklpy.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    delta, th, chi, phi, gamma, mu : float, optional
        Values of motor positions for current reflection. If None, it will ask
        for it.
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections

    if POLAR_DIFFRACTOMETER in _geom_.name and len(args) == 9:
        gamma, mu, chi, phi, delta, tau, h, k, l = args
    elif _geom_.name == "fourc" and len(args) == 7:
        delta, mu, chi, phi, h, k, l = args
    else:
        if len(orienting_refl) > 1:
            for ref in sample._sample.reflections_get():
                if ref == orienting_refl[0] and POLAR_DIFFRACTOMETER in _geom_.name:
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    old_delta = pos[5]
                    old_mu = pos[1]
                    old_chi = pos[2]
                    old_phi = pos[3]
                    old_gamma = pos[4]
                    old_tau = pos[0]
                    old_h, old_k, old_l = ref.hkl_get()
                elif ref == orienting_refl[0] and _geom_.name == "fourc":
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    old_delta = pos[3]
                    old_mu = pos[0]
                    old_chi = pos[1]
                    old_phi = pos[2]
                    old_h, old_k, old_l = ref.hkl_get()

        else:
            old_delta = 0
            old_mu = 30
            old_chi = 90
            old_phi = 0
            old_h = 0
            old_k = 0
            old_l = 2
            old_gamma = 60
            old_tau = 0

        print("Enter primary-reflection angles:")
        gamma = input("Gamma = [{:6.2f}]: ".format(old_gamma)) or old_gamma
        mu = input("Mu = [{:6.2f}]: ".format(old_mu)) or old_mu
        chi = input("Chi = [{:6.2f}]: ".format(old_chi)) or old_chi
        phi = input("Phi = [{:6.2f}]: ".format(old_phi)) or old_phi
        delta = input("Delta = [{:6.2f}]: ".format(old_delta)) or old_delta
        tau = input("Tau = [{:6.2f}]: ".format(old_tau)) or old_tau
        h = input("H = [{}]: ".format(old_h)) or old_h
        k = input("K = [{}]: ".format(old_k)) or old_k
        l = input("L = [{}]: ".format(old_l)) or old_l

    if POLAR_DIFFRACTOMETER in _geom_.name:
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                gamma=float(gamma),
                mu=float(mu),
                chi=float(chi),
                phi=float(phi),
                delta=float(delta),
                tau=float(tau),
            ),
        )
    elif _geom_.name == "fourc":
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                tth=float(delta),
                omega=float(mu),
                chi=float(chi),
                phi=float(phi),
            ),
        )

    if len(orienting_refl) > 1:
        sample._orientation_reflections.pop(0)
    sample._orientation_reflections.insert(
        0, sample._sample.reflections_get()[-1]
    )
    compute_UB()


def setor1(*args):
    """
    Sets the primary secondary in hklpy.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    delta, th, chi, phi, gamma, mu : float, optional
        Values of motor positions for current reflection. If None, it will ask
        for it.
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """

    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections

    if POLAR_DIFFRACTOMETER in _geom_.name and len(args) == 9:
        gamma, mu, chi, phi, delta, tau, h, k, l = args
    elif _geom_.name == "fourc" and len(args) == 7:
        delta, mu, chi, phi, h, k, l = args
    else:
        if len(orienting_refl) > 1:
            for ref in sample._sample.reflections_get():
                if ref == orienting_refl[1] and POLAR_DIFFRACTOMETER in _geom_.name:
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    old_gamma = pos[4]
                    old_mu = pos[1]
                    old_chi = pos[2]
                    old_phi = pos[3]
                    old_delta = pos[5]
                    old_tau = pos[0]
                    old_h, old_k, old_l = ref.hkl_get()
                elif ref == orienting_refl[1] and _geom_.name == "fourc":
                    pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
                    old_delta = pos[3]
                    old_mu = pos[0]
                    old_chi = pos[1]
                    old_phi = pos[2]
                    old_h, old_k, old_l = ref.hkl_get()

        else:
            old_delta = 0
            old_mu = 30
            old_chi = 0
            old_phi = 0
            old_h = 2
            old_k = 0
            old_l = 0
            old_gamma = 60
            old_tau = 0

        print("Enter secondary-reflection angles:")
        gamma = input("Gamma = [{:6.2f}]: ".format(old_gamma)) or old_gamma
        mu = input("Mu = [{:6.2f}]: ".format(old_mu)) or old_mu
        chi = input("Chi = [{:6.2f}]: ".format(old_chi)) or old_chi
        phi = input("Phi = [{:6.2f}]: ".format(old_phi)) or old_phi
        delta = input("Delta = [{:6.2f}]: ".format(old_delta)) or old_delta
        tau = input("Theta = [{:6.2f}]: ".format(old_tau)) or old_tau

        h = input("H = [{}]: ".format(old_h)) or old_h
        k = input("K = [{}]: ".format(old_k)) or old_k
        l = input("L = [{}]: ".format(old_l)) or old_l

    if POLAR_DIFFRACTOMETER in _geom_.name:
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                gamma=float(gamma),
                mu=float(mu),
                chi=float(chi),
                phi=float(phi),
                delta=float(delta),
                tau=float(tau),
            ),
        )
    elif _geom_.name == "fourc":
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                tth=float(delta),
                omega=float(mu),
                chi=float(chi),
                phi=float(phi),
            ),
        )
    if len(orienting_refl) > 1:
        sample._orientation_reflections.pop(1)
    sample._orientation_reflections.insert(
        1, sample._sample.reflections_get()[-1]
    )
    compute_UB()


def set_orienting():
    """
    Change the primary and/or secondary orienting reflections to existing reflecitons
    in reflection list in hklpy.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.
    """
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if POLAR_DIFFRACTOMETER in _geom_.name:
        print(
            "\n{:>2}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}   {:<12}".format(
                "#",
                "H",
                "K",
                "L",
                "Gamma",
                "Mu",
                "Chi",
                "Phi",
                "Delta",
                "Tau",
                "orienting",
            )
        )
    elif _geom_.name == "fourc":
        print(
            "\n{:>2}{:>4}{:>3}{:>3}{:>12}{:>9}{:>9}{:>9}   {:<12}".format(
                "#",
                "H",
                "K",
                "L",
                "Two Theta",
                "Theta",
                "Chi",
                "Phi",
                "orienting",
            )
        )
    else:
        raise ValueError("Geometry {} not supported.".format(_geom_.name))

    for i, ref in enumerate(sample._sample.reflections_get()):
        if orienting_refl[0] == ref:
            or0_old = i
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "first",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "first",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )
        elif orienting_refl[1] == ref:
            or1_old = i
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "second",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "second",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )
        else:
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )

    or0 = input("\nFirst orienting ({})? ".format(or0_old)) or or0_old
    or1 = input("Second orienting ({})? ".format(or1_old)) or or1_old
    sample._orientation_reflections.pop(0)
    sample._orientation_reflections.insert(
        0, sample._sample.reflections_get()[int(or0)]
    )
    sample._orientation_reflections.pop(1)
    sample._orientation_reflections.insert(
        1, sample._sample.reflections_get()[int(or1)]
    )
    compute_UB()


def del_reflection():
    """
    Delete existing reflection from in reflection list in hklpy.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.
    """
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if POLAR_DIFFRACTOMETER in _geom_.name:
        print(
            "\n{:>2}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}   {:<12}".format(
                "#",
                "H",
                "K",
                "L",
                "Gamma",
                "Mu",
                "Chi",
                "Phi",
                "Delta",
                "Tau",
                "orienting",
            )
        )
    elif _geom_.name == "fourc":
        print(
            "\n{:>2}{:>4}{:>3}{:>3}{:>12}{:>9}{:>9}{:>9}   {:<12}".format(
                "#",
                "H",
                "K",
                "L",
                "Two Theta",
                "Theta",
                "Chi",
                "Phi",
                "orienting",
            )
        )
    else:
        raise ValueError("Geometry {} not supported.".format(_geom_.name))

    for i, ref in enumerate(sample._sample.reflections_get()):
        if orienting_refl[0] == ref:
            or0_old = i
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "first",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "first",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )
        elif orienting_refl[1] == ref:
            or1_old = i
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "second",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "second",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )
        else:
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )

    remove = input("\nRemove reflection # ")
    if not remove:
        print("No reflection removed")
    elif int(remove) == or0_old or int(remove) == or1_old:
        print("Orienting reflection not removable!")
        print(
            "Use 'set_orienting()' first to select different orienting reflection."
        )
    else:
        sample._sample.del_reflection(
            sample._sample.reflections_get()[int(remove)]
        )


def list_orienting(all_samples=False):
    """
    Prints the two reflections used in the UB matrix.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    all_samples : boolean, optional
        If True, it will print the reflections of all samples, if False, only of
        the current one.
    """
    _geom_ = current_diffractometer()
    _check_geom_selected()
    if all_samples:
        samples = _geom_.calc._samples.values()
    else:
        samples = [_geom_.calc._sample]
    for sample in samples:
        orienting_refl = sample._orientation_reflections
        if POLAR_DIFFRACTOMETER in _geom_.name:
            print(
                "\n{:>2}{:>4}{:>3}{:>3}{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}   {:<12}".format(
                    "#",
                    "H",
                    "K",
                    "L",
                    "Gamma",
                    "Mu",
                    "Chi",
                    "Phi",
                    "Delta",
                    "Tau",
                    "orienting",
                )
            )
        elif _geom_.name == "fourc":
            print(
                "\n{:>2}{:>4}{:>3}{:>3}{:>12}{:>9}{:>9}{:>9}   {:<12}".format(
                    "#",
                    "H",
                    "K",
                    "L",
                    "Two Theta",
                    "Theta",
                    "Chi",
                    "Phi",
                    "orienting",
                )
            )
        else:
            raise ValueError("Geometry {} not supported.".format(_geom_.name))

    for i, ref in enumerate(sample._sample.reflections_get()):
        if orienting_refl[0] == ref:
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "first",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "first",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )
        elif orienting_refl[1] == ref:
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                        "second",
                    )
                )
            elif _geom_.name == "fourc":
                print(
                    "{:>2}{:>4}{:>3}{:>3}{:>12.3f}{:>9.3f}{:>9.3f}{:>9.3f}   {:<12} ".format(
                        i,
                        int(h),
                        int(k),
                        int(l),
                        pos[3],
                        pos[0],
                        pos[1],
                        pos[2],
                        "second",
                    )
                )
            else:
                raise ValueError(
                    "Geometry {} not supported.".format(_geom_.name)
                )


def or0(h=None, k=None, l=None):
    """
    Sets the primary orientation in hklpy using the current motor positions.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if not h and not k and not l:
        if len(orienting_refl) > 1:
            for ref in sample._sample.reflections_get():
                if ref == orienting_refl[0]:
                    hr, kr, lr = ref.hkl_get()
        else:
            hr = 2
            kr = 0
            lr = 0
        h = (input("H ({})? ".format(hr)) if not h else h) or hr
        k = (input("K ({})? ".format(kr)) if not k else k) or kr
        l = (input("L ({})? ".format(lr)) if not l else l) or lr
    if POLAR_DIFFRACTOMETER in _geom_.name:
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                gamma=_geom_.gamma.position,
                mu=_geom_.mu.position,
                chi=_geom_.chi.position,
                phi=_geom_.phi.position,
                delta=_geom_.delta.position,
                tau=_geom_.tau.position,
            ),
        )
    if _geom_.name == "fourc":
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                tth=_geom_.tth.position,
                omega=_geom_.omega.position,
                chi=_geom_.chi.position,
                phi=_geom_.phi.position,
            ),
        )

    if len(orienting_refl) > 1:
        sample._orientation_reflections.pop(0)
    sample._orientation_reflections.insert(
        0, sample._sample.reflections_get()[-1]
    )

    compute_UB()


def or1(h=None, k=None, l=None):
    """
    Sets the secondary orientation in hklpy using the current motor positions.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = current_diffractometer()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if not h and not k and not l:
        if len(orienting_refl) > 1:
            for ref in sample._sample.reflections_get():
                if ref == orienting_refl[1]:
                    hr, kr, lr = ref.hkl_get()
        else:
            hr = 0
            kr = 2
            lr = 0
        h = (input("H ({})? ".format(hr)) if not h else h) or hr
        k = (input("K ({})? ".format(kr)) if not k else k) or kr
        l = (input("L ({})? ".format(lr)) if not l else l) or lr
    if POLAR_DIFFRACTOMETER in _geom_.name:
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                gamma=_geom_.gamma.position,
                mu=_geom_.mu.position,
                chi=_geom_.chi.position,
                phi=_geom_.phi.position,
                delta=_geom_.delta.position,
                tau=_geom_.tau.position,
            ),
        )
    if _geom_.name == "fourc":
        sample.add_reflection(
            float(h),
            float(k),
            float(l),
            position=_geom_.calc.Position(
                tth=_geom_.tth.position,
                omega=_geom_.omega.position,
                chi=_geom_.chi.position,
                phi=_geom_.phi.position,
            ),
        )

    if len(orienting_refl) > 1:
        sample._orientation_reflections.pop(1)
    sample._orientation_reflections.insert(
        1, sample._sample.reflections_get()[-1]
    )

    compute_UB()


def compute_UB():
    """
    Calculates the UB matrix.

    This fixes one issue with the hklpy calc_UB in that using wh() right after
    will not work, it needs to run one calculation first.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """

    _geom_ = current_diffractometer()
    _geom_for_psi_ = engine_for_psi()
    sample = _geom_.calc._sample
    orienting_refl = sample._orientation_reflections
    if len(orienting_refl) > 1:
        print("Computing UB!")
        calc_UB(
            sample._orientation_reflections[0],
            sample._orientation_reflections[1],
        )
        _geom_.forward(1, 0, 0)
        if POLAR_DIFFRACTOMETER in _geom_.name:
            Sync_UB_Matrix(_geom_, _geom_for_psi_)


def calc_UB(r1, r2, wavelength=None, output=False):
    """
    Compute the UB matrix with two reflections.

    Parameters
    ----------
    r1, r2 : hklpy reflections
        Orienting reflections from hklpy.
    wavelength : float, optional
        This is not used...
    output : boolean
        Toggle to decide whether to print the UB matrix.
    """
    _check_geom_selected()
    _geom_ = current_diffractometer()
    _geom_.calc.sample.compute_UB(r1, r2)
    if output:
        print(_geom_.calc.sample.UB)


def setmode(mode=None):
    """
    Set the mode of the currently selected diffractometer.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    mode : string, optional
        Mode to be selected. If None, it will ask.
    """
    _geom_ = current_diffractometer()
    current_mode = _geom_.calc.engine.mode
    for index, item in enumerate(_geom_.calc.engine.modes):
        print("{:2d}. {}".format(index + 1, item))
        if current_mode == item:
            current_index = index
    if mode:
        _geom_.calc.engine.mode = _geom_.calc.engine.modes[int(mode) - 1]
        print("\nSet mode to {}".format(mode))
    else:
        mode = input("\nMode ({})? ".format(current_index + 1)) or (
            current_index + 1
        )
        _geom_.calc.engine.mode = _geom_.calc.engine.modes[int(mode) - 1]


def ca(h, k, l):
    """
    Calculate the motors position of a reflection.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.
    """
    _geom_ = current_diffractometer()
    pos = cahkl(h, k, l)
    print("\n   Calculated Positions:")
    print(
        "\n   H K L = {:5f} {:5f} {:5f}".format(
            h,
            k,
            l,
        )
    )
    print(
        f"\n   Lambda (Energy) = {_geom_.calc.wavelength:6.4f} \u212b"
        f" ({_geom_.calc.energy:6.4f}) keV"
    )
    if POLAR_DIFFRACTOMETER in _geom_.name:
        print(
            "\n{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}".format(
                "Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"
            )
        )
        print(
            "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                pos[4],
                pos[1],
                pos[2],
                pos[3],
                pos[5],
                pos[0],
            )
        )
    if _geom_.name == "fourc":
        print("\n{:>9}{:>9}{:>9}{:>9}".format("Delta", "Theta", "Chi", "Phi"))
        print(
            "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                pos[3],
                pos[0],
                pos[1],
                pos[2],
            )
        )


def _ensure_idle():
    if RE.state != "idle":
        print("The RunEngine invoked by magics cannot be resumed.")
        print("Aborting...")
        RE.abort()


def ubr(h, k, l):
    """
    Move the motors to a reciprocal space point.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.

    Returns
    -------
    """
    _geom_ = current_diffractometer()
    def _plan():
        yield from mv(
            _geom_.h, float(h),
            _geom_.k, float(k),
            _geom_.l, float(l)
        )
    RE.waiting_hook = ProgressBarManager()
    try:
        RE(_plan())
    except RunEngineInterrupted:
        ...
    RE.waiting_hook = None
    _ensure_idle()
    return None


def br(h, k, l):
    """
    Move the motors to a reciprocal space point.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.

    Returns
    -------
    Generator for the bluesky Run Engine.
    """
    _geom_ = current_diffractometer()
    yield from mv(_geom_.h, float(h), _geom_.k, float(k), _geom_.l, float(l))


def uan(*args):
    """
    Moves the delta and theta motors.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    gamma, mu: float, optional??
        Delta and th motor angles to be moved to.

    Returns
    -------
    """
    _geom_ = current_diffractometer()
    if len(args) != 2:
        raise ValueError("Usage: uan(gamma/tth,mu/th)")
    else:
        delta, th = args
        if len(_geom_.calc.physical_axes) == 6:
            print("Moving to (delta,eta)=({},{})".format(delta, th))
            plan = mv(_geom_.gamma, delta, _geom_.mu, th)
        elif len(_geom_.calc.physical_axes) == 4:
            print("Moving to (tth,th)=({},{})".format(delta, th))
            plan = mv(_geom_.tth, delta, _geom_.omega, th)
    RE.waiting_hook = pbar_manager
    try:
        RE(plan)
    except RunEngineInterrupted:
        ...
    RE.waiting_hook = None
    _ensure_idle()
    return None


def an(*args):
    """
    Moves the delta and theta motors.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    delta, th: float, optional??
        Delta and th motor angles to be moved to.

    Returns
    -------
    Generator for the bluesky Run Engine.
    """
    _geom_ = current_diffractometer()
    if len(args) != 2:
        raise ValueError("Usage: uan(delta/tth,eta/th)")
    else:
        delta, th = args
        if len(_geom_.calc.physical_axes) == 6:
            print("Moving to (delta,eta)=({},{})".format(delta, th))
            yield from mv(_geom_.gamma, delta, _geom_.mu, th)
        elif len(_geom_.calc.physical_axes) == 4:
            print("Moving to (tth,th)=({},{})".format(delta, th))
            yield from mv(_geom_.tth, delta, _geom_.omega, th)


def _wh():
    """
    Retrieve information on the current reciprocal space position.

    """
    _geom_ = current_diffractometer()
    _geom_for_psi_ = engine_for_psi()
    _geom_for_psi_.calc.sample.UB = _geom_.calc._sample.UB
    print(
        "\n   H K L = {:5f} {:5f} {:5f}".format(
            _geom_.calc.engine.pseudo_axes["h"],
            _geom_.calc.engine.pseudo_axes["k"],
            _geom_.calc.engine.pseudo_axes["l"],
        )
    )
    if _geom_.name == 'polar':
        print(
            "   Azimuth = {:6.4f}".format(
                _geom_for_psi_.inverse(0).psi,
            )
        )
    print(
        "   Lambda (Energy) = {:6.4f} \u212B ({:6.4f} keV)".format(
            _geom_.calc.wavelength, _geom_.calc.energy
        )
    )
    if len(_geom_.calc.physical_axes) == 6:
        print(
            "\n{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}".format(
                "Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"
            )
        )
        print(
            "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                _geom_.gamma.position,
                _geom_.mu.position,
                _geom_.chi.position,
                _geom_.phi.position,
                _geom_.delta.position,
                _geom_.tau.position,
            )
        )
    else:
        print(
            "\n{:>9}{:>9}{:>9}{:>9}".format(
                "tth", "th", "Chi", "Phi"
            )
        )
        print(
            "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                _geom_.tth.position,
                _geom_.omega.position,
                _geom_.chi.position,
                _geom_.phi.position,
            )
        )


def pa_new():
    """
    Retrieve information on the current reciprocal space position.

    """
    _geom_ = current_diffractometer()
    _geom_for_psi_ = engine_for_psi()
    _geom_for_psi_.calc.sample.UB = _geom_.calc._sample.UB
    sample = _geom_.calc._sample
    geometry = _geom_.calc._geometry.name_get()
    orienting_refl = sample._orientation_reflections
    current_mode = _geom_.calc.engine.mode

    print("{},  {} geometry, {} diffractometer".format(_geom_.__class__.__name__, geometry, _geom_.name))
    print("{} mode".format(huber_euler.calc.engine.mode))

    print("Sample = {}".format(sample.name))
    for i, ref in enumerate(sample._sample.reflections_get()):
        if orienting_refl[0] == ref:
            print("\nPrimary reflection at (lambda = {:.3f})".format(orienting_refl[0].geometry_get().wavelength_get(0)))
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if len(_geom_.calc.physical_axes) == 6:
                print(
                    "     gamma, mu, chi, phi, delta, tau = {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}".format(
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
                print(
                    "                               H K L = {:>2}{:>2}{:>2}".format(
                        int(h),
                        int(k),
                        int(l),
                    )
                )
            else:
                print(
                    "     tth, th, chi, phi  = {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}".format(
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
                print(
                    "                   H K L = {:>2}{:>2}{:>2}".format(
                        int(h),
                        int(k),
                        int(l),
                    )
                )

    for i, ref in enumerate(sample._sample.reflections_get()):
        if orienting_refl[1] == ref:
            print("\nSecondary reflection at (lambda = {:.3f})".format(orienting_refl[1].geometry_get().wavelength_get(0)))
            h, k, l = ref.hkl_get()
            pos = ref.geometry_get().axis_values_get(_geom_.calc._units)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                print(
                    "     gamma, mu, chi, phi, delta, tau = {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}".format(
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
                print(
                    "                               H K L = {:>2}{:>2}{:>2}".format(
                        int(h),
                        int(k),
                        int(l),
                    )
                )
            else:
                print(
                    "     tth, th, chi, phi = {:>3.3f}, {:>3.3f}, {:>3.3f}, {:>3.3f}".format(
                        pos[4],
                        pos[1],
                        pos[2],
                        pos[3],
                        pos[5],
                        pos[0],
                    )
                )
                print(
                    "                 H K L = {:>2}{:>2}{:>2}".format(
                        int(h),
                        int(k),
                        int(l),
                    )
                )


    print("\nLattice constants:")
    print("                          real space =", end=" ")
    print(*sample.lattice, sep=", ")    
    print("                    reciprocal space =", end=" ")
    print("{:>3.3f}, {:3.3f}, {:>3.3f}, {:3.3f}, {:>3.3f}, {:3.3f} ".format(sample.reciprocal[0],sample.reciprocal[1],sample.reciprocal[2],sample.reciprocal[3],sample.reciprocal[4],sample.reciprocal[5]))
    if current_mode == 'psi constant horizontal' or current_mode == 'psi constant vertical':
        _h2, _k2, _l2, psi = _geom_.calc._engine.engine.parameters_values_get(1)
        print("\nAzimuthal reference:")
        print("                               H K L = {:2.0f}{:2.0f}{:2.0f}".format(_h2,_k2,_l2))
        #print("                               Psi frozen to {}".format(psi))


    print("\nMonochromator:")
    print("                 Energy (wavelength) = {:3.3f} ({:3.3f})".format(_geom_.calc.energy, _geom_.calc.wavelength))


def setlat(*args):
    """
    Set the lattice constants.

    Parameters
    ----------
    a, b, c, alpha, beta, gamma : float, optional
        Lattice constants. If None, it will ask for input.
    """

    _geom_ = current_diffractometer()
    current_sample = _geom_.calc.sample_name
    sample = _geom_.calc._samples[current_sample]
    lattice = [getattr(sample.lattice, parm) for parm in sample.lattice._fields]

    if len(args) == 6:
        a, b, c, alpha, beta, gamma = args
    elif len(args) == 0:
        a = (input("Lattice a ({})? ".format(lattice[0]))) or lattice[0]
        b = (input("Lattice b ({})? ".format(lattice[1]))) or lattice[1]
        c = (input("Lattice c ({})? ".format(lattice[2]))) or lattice[2]
        alpha = (input("Lattice alpha ({})? ".format(lattice[3]))) or lattice[3]
        beta = (input("Lattice beta ({})? ".format(lattice[4]))) or lattice[4]
        gamma = (input("Lattice gamma ({})? ".format(lattice[5]))) or lattice[5]
    else:
        raise ValueError(
            "either no arguments or a, b, c, alpha, beta, gamma need to be provided."
        )

    _geom_.calc.sample.lattice = (
        float(a),
        float(b),
        float(c),
        float(alpha),
        float(beta),
        float(gamma),
    )
    orienting_refl = sample._orientation_reflections
    if len(orienting_refl) > 1:
        print("Compute UB!")
        sample.compute_UB(
            sample._orientation_reflections[0],
            sample._orientation_reflections[1],
        )
        _geom_.forward(1, 0, 0)


def setaz(*args):
    _geom_ = current_diffractometer()
    _geom_for_psi_ = engine_for_psi()
    _check_geom_selected()
    if len(_geom_.calc.physical_axes) == 4:
        mode_temp = _geom_.calc.engine.mode
        _geom_.calc.engine.mode = "psi_constant"
        _h2, _k2, _l2, psi = _geom_.calc._engine.engine.parameters_values_get(1)
        if len(args) == 3:
            h2, k2, l2 = args
        elif len(args) == 0:
            h2 = int((input("H = ({})? ".format(_h2))) or _h2)
            k2 = int((input("K = ({})? ".format(_k2))) or _k2)
            l2 = int((input("L = ({})? ".format(_l2))) or _l2)

        else:
            raise ValueError(
                "either no arguments or h, k, l need to be provided."
            )
        _geom_.calc._engine.engine.parameters_values_set(
            [h2, k2, l2], 1
        )
        _geom_for_psi_.calc._engine.engine.parameters_values_set(
            [h2, k2, l2], 1
        )
        print("Azimuth = {} {} {} with Psi fixed at {}".format(h2, k2, l2, psi))
        _geom_.calc.engine.mode = mode_temp
    elif len(_geom_.calc.physical_axes) == 6:
        mode_temp = _geom_.calc.engine.mode
        _geom_.calc.engine.mode = "psi constant horizontal"
        _h2, _k2, _l2, psi = _geom_.calc._engine.engine.parameters_values_get(1)
        if len(args) == 3:
            h2, k2, l2 = args
        elif len(args) == 0:
            h2 = int((input("H = ({})? ".format(_h2))) or _h2)
            k2 = int((input("K = ({})? ".format(_k2))) or _k2)
            l2 = int((input("L = ({})? ".format(_l2))) or _l2)
            #_geom_.calc._engine.engine.parameters_values_set([h2, k2, l2], 1)
            #_geom_.calc.engine.mode = mode_temp
        else:
            raise ValueError(
                "either no arguments or h, k, l need to be provided."
            )
        _geom_.calc._engine.engine.parameters_values_set(
            [h2, k2, l2], 1
        )
        _geom_for_psi_.calc._engine.engine.parameters_values_set(
            [h2, k2, l2], 1
        )
        print("Azimuth = {} {} {} with Psi fixed at {}".format(h2, k2, l2, psi))
        _geom_.calc.engine.mode = mode_temp
    else:
        raise ValueError(
            "Function not available in mode '{}'".format(
                _geom_.calc.engine.mode
            )
        )


def freeze(*args):
    _geom_ = current_diffractometer()
    _check_geom_selected()
    if _geom_.calc.engine.mode == "psi constant horizontal" or  _geom_.calc.engine.mode == "psi_constant" :
        h2, k2, l2, psi = _geom_.calc._engine.engine.parameters_values_get(1)
        if len(args) == 1:
            psi = args[0]
        _geom_.calc._engine.engine.parameters_values_set([h2, k2, l2, psi], 1)
        print("Psi = {}".format(psi))
    elif _geom_.calc.engine.mode == "4-circles constant phi horizontal":
        print("freeze phi not yet implemented")
    else:
        raise ValueError(
            "Function not available in mode '{}'".format(
                _geom_.calc.engine.mode
            )
        )


def update_lattice(lattice_constant=None):
    """
    Update lattice constants.

    Parameters
    ----------
    lattice_constant: string, optional
        a, b or c or auto (default)
    """
    _geom_ = current_diffractometer()
    current_sample = _geom_.calc.sample_name
    sample = _geom_.calc._samples[current_sample]
    lattice = [getattr(sample.lattice, parm) for parm in sample.lattice._fields]
    a = lattice[0]
    b = lattice[1]
    c = lattice[2]
    alpha = lattice[3]
    beta = lattice[4]
    gamma = lattice[5]
    hh = _geom_.calc.engine.pseudo_axes["h"]
    kk = _geom_.calc.engine.pseudo_axes["k"]
    ll = _geom_.calc.engine.pseudo_axes["l"]

    if round(hh) == 0 and round(kk) == 0:
        lattice_auto = "c"
    elif round(hh) == 0 and round(ll) == 0:
        lattice_auto = "b"
    elif round(kk) == 0 and round(ll) == 0:
        lattice_auto = "a"
    else:
        lattice_auto = None
    if not lattice_constant:
        lattice_constant = (
            input("Lattice parameter (a, b, or c or [auto])? ") or lattice_auto
        )
    else:
        print("Specify lattice parameter 'a', 'b' or 'c' or none")
    if lattice_constant == "a" and round(hh) > 0:
        a = a / hh * round(hh)
    elif lattice_constant == "b" and round(kk) > 0:
        b = b / kk * round(kk)
    elif lattice_constant == "c" and round(ll) > 0:
        c = c / ll * round(ll)
    else:
        raise ValueError("Auto calc not possible.")
    print("Refining lattice parameter {}".format(lattice_constant))
    _geom_.calc.sample.lattice = (
        float(a),
        float(b),
        float(c),
        float(alpha),
        float(beta),
        float(gamma),
    )
    orienting_refl = sample._orientation_reflections
    if len(orienting_refl) > 1:
        print("Compute UB!")
        sample.compute_UB(
            sample._orientation_reflections[0],
            sample._orientation_reflections[1],
        )
        _geom_.forward(1, 0, 0)
    print(
        "\n   H K L = {:5.4f} {:5.4f} {:5.4f}".format(
            _geom_.calc.engine.pseudo_axes["h"],
            _geom_.calc.engine.pseudo_axes["k"],
            _geom_.calc.engine.pseudo_axes["l"],
        )
    )
    lattice = [getattr(sample.lattice, parm) for parm in sample.lattice._fields]
    print(
        "   a, b, c, alpha, beta, gamma = {:5.4f} {:5.4f} {:5.4f} {:5.4f} {:5.4f} {:5.4f}".format(
            lattice[0],
            lattice[1],
            lattice[2],
            lattice[3],
            lattice[4],
            lattice[5],
        )
    )


def write_config(method="File", overwrite=False):
    """
    Write configuration from file in current directory.

    Parameters
    ----------
    method: string, optional
        right now only "File" possible, but later PV or other
    overwrite: Boolean, optional
        asks if existing file hould be overwritten
    """
    _geom_ = current_diffractometer()
    config = DiffractometerConfiguration(_geom_)
    settings = config.export("json")
    if POLAR_DIFFRACTOMETER in _geom_.name and polar_config.exists():
        if not overwrite:
            value = input("Overwrite existing configuration file (y/[n])? ")
            if value == "y":
                overwrite = True
        if overwrite:
            if method == "File":
                print("Writing configuration file.")
                with open(polar_config.name, "w") as f:
                    f.write(settings)
    elif _geom_.name == "fourc" and fourc_config.exists():
        if not overwrite:
            value = input("Overwrite existing configuration file (y/[n])? ")
            if value == "y":
                overwrite = True
        if overwrite:
            if method == "File":
                print("Writing configuration file.")
                with open(fourc_config.name, "w") as f:
                    f.write(settings)
    else:
        if method == "File":
            print("Writing configuration file.")
            print(_geom_.name)
            if POLAR_DIFFRACTOMETER in _geom_.name:
                with open(polar_config.name, "w") as f:
                    f.write(settings)
            if _geom_.name == "fourc":
                with open(polar_config.name, "w") as f:
                    f.write(settings)
            else:
                print("Only available for 'polar' and 'fourc' geometries.")


def read_config(method="File"):
    """
    Read configuration from file in current directory.

    Parameters
    ----------
    method: string, optional
        right now only "File" possible, but later PV or other
    """
    _geom_ = current_diffractometer()
    config = DiffractometerConfiguration(_geom_)
    if POLAR_DIFFRACTOMETER in _geom_.name and polar_config.exists():
        if method == "File":
            print("Read configuration file '{}'.".format(polar_config.name))
            method = input("Method ([o]verwrite/[a]ppend)? ")
            if method == "a":
                config.restore(polar_config, clear=False)
                compute_UB()
            elif method == "o":
                config.restore(polar_config, clear=True)
                compute_UB()
            else:
                print("Config file not read!")
    elif _geom_.name == "fourc" and fourc_config.exists():
        if method == "File":
            print("Read configuration file '{}'.".format(fourc_config.name))
            method = input("Method ([o]verwrite/[a]ppend)? ")
            if method == "a":
                config.restore(fourc_config, clear=False)
                compute_UB()
            elif method == "o":
                config.restore(fourc_config, clear=True)
                compute_UB()
            else:
                print("Config file not read!")

def show_constraints():
    """
    Show constraints and freeze angles (value)
    """
    _geom_ = current_diffractometer()
    _geom_.show_constraints()


def reset_constraints():
    """
    Reset all constraints
    """
    _geom_ = current_diffractometer()
    _geom_.reset_constraints()
    _geom_.show_constraints()


def set_constraints(*args):
    """
    Change constraint values for specific axis
    """
    _geom_ = current_diffractometer()
    axes = _geom_.calc._engine.engine.axis_names_get(0)

    if len(args) == 12:
        i = -1
        for axis in axes:
            i+=2
            low = args[i-1]
            high = args[i]
            angle = _geom_.get_axis_constraints(axis).value
            _geom_.apply_constraints(
                {axis: Constraint(low, high, angle, True)}
        )
        
    elif len(args) == 3:
        axis, low, high = args
        angle = _geom_.get_axis_constraints(axis).value
        _geom_.apply_constraints(
            {axis: Constraint(low, high, angle, True)}
        )
    elif len(args) == 1:
        axis = args[0]
        print(axis)
        low = _geom_.get_axis_constraints(axis).low_limit
        high = _geom_.get_axis_constraints(axis).high_limit
        angle = _geom_.get_axis_constraints(axis).value
        value = (
            input(
                "{} constraints low, high = [{:3.3f}, {:3.3f}]: ".format(
                    axis, low, high
                )
            )
        ) or [low, high]
        if isinstance(value, str):
            value = value.replace(",", " ").split(" ")
        _geom_.apply_constraints(
            {axis: Constraint(value[0], value[1], angle, True)}
        )
    elif len(args) == 0:
        for axis in axes:
            low = _geom_.get_axis_constraints(axis).low_limit
            high = _geom_.get_axis_constraints(axis).high_limit
            angle = _geom_.get_axis_constraints(axis).value
            value = (
                input(
                    "{} constraints low, high = [{:3.3f}, {:3.3f}]: ".format(
                        axis, low, high
                    )
                )
            ) or [low, high]
            if isinstance(value, str):
                value = value.replace(",", " ").split(" ")
            _geom_.apply_constraints(
                {axis: Constraint(value[0], value[1], angle, True)}
        )


select_diffractometer(huber_euler)
select_engine_for_psi(huber_euler_psi)


class whClass:
    """
    _wh function used without parenthesis
    """

    def __repr__(self):
        print("")
        _wh()
        return ""


wh = whClass()


class sampleListClass:
    """
    _sampleList function used without parenthesis
    """

    def __repr__(self):
        print("")
        _sampleList()
        return ""


sampleList = sampleListClass()

class Sync_UB_Matrix:
    """Copy the UB matrix from source to target diffractometers."""

    _geom_ = current_diffractometer()
    _geom_for_psi_ = engine_for_psi()
    def __init__(self, source: Diffractometer, target: Diffractometer):
        self.source = source
        self.target = target
        self.source.UB.subscribe(self.sync_callback)

        # initialize
        self.sync_callback(self.source.UB.get())

    def cleanup(self, *args, **kwargs):
        """Remove all our subscriptions to ophyd objects."""
        self.source.UB.clear_sub(self.sync_callback)

    def sync_callback(self, value=None, **kwargs):
        if value is None:
            raise RuntimeError(f"sync_callback: {value=!r}  {kwargs=!r}")
        ub_source = value
        #print(f"Copy UB={ub_source=} from {self.source.name} to {self.target.name}")
        print(f"Copy UB from {self.source.name} to {self.target.name}")
        self.target.UB.put(ub_source)

        for axis in self.source.real_positioners._fields:
            ptarget = getattr(self.target, axis)
            if isinstance(ptarget, SoftPositioner):
                # If the target is a simulated motor, sync it with the source.
                psource = getattr(self.source, axis)
                ptarget.move(psource.position)
                print(f"Sync {self.target.name}.{axis}={ptarget.position}")


def restore_huber_from_scan(
    scan_id, diffractometer=None, sample_name=None, force=False
):
    info = run_orientation_info(cat[scan_id])

    if diffractometer is None:
        diffractometer = current_diffractometer()
  
    if diffractometer.name not in info.keys():
        if force == True:
            print(
                "WARNING: could not find information on the "
                f"{diffractometer.name} in the scan {scan_id}. "
                "Since force = True, then will try to setup using "
                f"{list(info.keys())[0]}."
            )
        else:
            raise NameError(
                f"Could not find a setup for {diffractometer.name} "
                f"in scan {scan_id}."
            )
        inp = list(info.items())[0]
    else:
        inp = info[diffractometer.name]

    if sample_name is not None:
        inp["sample_name"] = sample_name

    try:
        restore_sample(inp, diffractometer)
    except ValueError as exc:
        raise ValueError(
            f"{exc} Use the sample_name keyword argument to change "
            "the name."
        )
    restore_constraints(inp, diffractometer)
    restore_reflections(inp, diffractometer)
    print(pa())
