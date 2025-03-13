"""
Transfocator functions.

.. autosummary::
    ~read_delta
    ~transfocator
"""

from numpy import loadtxt, array, eye, dot, inf
from scipy.interpolate import interp1d
from pandas import read_csv, DataFrame
from itertools import combinations

BE_REFR_INDEX_FILE = (
    "/home/beams/POLAR/polar_instrument/src/instrument/utils/Be_refr_index.dat"
)

LENS_SETTINGS = (
    "/home/beams/POLAR/polar_instrument/src/instrument/utils/"
    "transfocator_settings.csv"
)


def read_delta(
    energy,
    path=BE_REFR_INDEX_FILE
):
    if energy < 2700 or energy > 27000:
        raise ValueError("Energy {} out of range [2700, 27000].".format(energy))

    energies, deltas = loadtxt(path, skiprows=2, usecols=(0, 1), unpack=True)
    return interp1d(energies, deltas, kind="linear")(energy)


def _lens_matrix(f):
    """Return the transfer matrix for a thin lens with focal length f."""
    return array([[1, 0], [-1/f, 1]])


def _propagation_matrix(d):
    """Return the transfer matrix for free-space propagation over distance d."""
    return array([[1, d], [0, 1]])


def _compute_effective_focal_length(focuses, positions):
    """
    Compute the effective focal length.
    """

    # Initialize system matrix as identity matrix
    M = eye(2)

    # Note that len(distances) = len(focuses)-1
    distances = abs(positions[1:] - positions[:-1])

    # Multiply matrices for N lenses with spacing d between them
    for f, d in zip(focuses, distances):
        M = dot(_lens_matrix(f), M)  # Apply lens matrix
        M = dot(_propagation_matrix(d), M)  # Apply propagation matrix

    # Last lens
    M = dot(_lens_matrix(focuses[-1]), M)

    # Extract the (2,1) element (C term) to compute effective focal length
    C = M[1, 0]

    if C != 0:
        f_eff = -1 / C
    else:
        f_eff = inf  # If C is zero, the system is collimating

    return f_eff


def _find_optimal_combination(lenses, f_eff):

    lenses_list = [i for _, i in lenses.iterrows()]

    # Find the best combination of lens packages
    best_combination = None
    min_error = float('inf')

    for r in range(len(lenses_list), 0, -1):
        for lens_combination in combinations(lenses_list, r):
            lens_combination = DataFrame(lens_combination)

            focal_length = _compute_effective_focal_length(
                lens_combination["focus"].values,
                lens_combination["distance"].values,
            )

            # Calculate the error between the desired and actual focal length
            error = abs(focal_length - f_eff)

            if error < min_error:
                min_error = error
                best_combination = list(lens_combination.index)
                best_focal_length = focal_length

    return best_combination, best_focal_length


def _find_optimal_focus(lenses):
    return _compute_effective_focal_length(
        lenses["focus"].values,
        lenses["distance"].values,
    )


def transfocator_calculation(
    energy,
    optimize_position: float = None,
    experiment: str = "diffractometer",
    reference_distance: float = 2591,
    distance_only: bool = False,
    selected_lenses: list = None,
    verbose: bool = True
):
    """
    Calculate the transfocator position and lenses set.

    PARAMETERS
    ----------
        energy : float
            Beamline energy in keV.
        optimize_position : float
            CRL motor Z position that will be used to optimize the lenses for the calculation, in mm.
        experiment : "diffractometer" or "magnet"
            Name of the experimental configuration to focus.
        reference_distance : float
            Distance between CRL and sample when the CRL Z motor is at zero. This will normally not
            change. In mm.
        distance_only : bool
            If True it will only calculate the optimal distance, and won't try to switch lenses.
        selected_lenses : iterable
            If distance_only == True, then this is the lenses you want to use for the calculation.
        verbose : bool
            Toggle to print information.
    """

    # _geom_ = current_diffractometer()
    if optimize_position is None:
        optimize_position = float(
            input("Target CRL Z position in mm [0]: ") or 0
        )

    if (optimize_position < -150) or (optimize_position > 150):
        raise ValueError(
            "CRL Z {} out of range [-150, 150].".format(energy)
        )

    if energy < 2.6 or energy > 27:
        raise ValueError(
            "Photon energy {} out of range [2.6, 27].".format(energy)
        )

    if distance_only and not selected_lenses:
        _inp = input(
            "Enter the number of the lenses that will be used (space separated)"
            ": "
        )
        selected_lenses = [int(i) for i in _inp.split()]

    # Collect setup
    if experiment == "diffractometer":
        source_sample_distance = 67.2e6
    elif experiment == "magnet":
        source_sample_distance = 73.3e6
    else:
        raise ValueError(
            "Calculation limited to focus positions at 67.2 m "
            "(diffractometer) or 73.3 m (magnet)."
        )

    delta = read_delta(energy*1e3)  # delta table uses eV.

    # Effective focal point for the desired distance

    optimize_distance = (optimize_position + reference_distance)*1e3  # in microns

    source_crl_distance = source_sample_distance - optimize_distance
    f_eff = source_crl_distance * optimize_distance / (source_crl_distance + optimize_distance)

    lenses = read_csv(LENS_SETTINGS, skiprows=1).set_index("index")

    lenses["focus"] = (
        lenses["single_lens_radius"] / (2 * lenses["number_of_lenses"] * delta)
    )

    if not distance_only:
        best_combination, best_focal_length = _find_optimal_combination(
            lenses, f_eff
        )
    else:
        best_combination = selected_lenses
        best_focal_length = _find_optimal_focus(lenses.loc[selected_lenses])

    # Calculating some extra parameters
    best_effective_radius = 2 * delta * best_focal_length

    # The calculation is based on the center of the selected stack which may
    # not be the same as the center of the transfocator.
    _selected = lenses.loc[best_combination]
    power = _selected["number_of_lenses"]*2/_selected["single_lens_radius"]
    effective_center = (power*_selected["distance"]).sum()/power.sum()
    
    crl_center = source_crl_distance + effective_center
    best_sample_distance = (
        best_focal_length*crl_center/(crl_center-best_focal_length)
    )

    effective_reference_distance = reference_distance - effective_center/1e3 # correct for lens selection
    crlz_position = effective_reference_distance - best_sample_distance/1e3  # get relative position

    if verbose:
        print("-" * 65)
        if distance_only:
            print("Lens packages not optmized!")
            print("Inserted lens packages = {}".format(best_combination))
        else:
            print("Optimal lens packages = {}".format(best_combination))

        print("Effective radius = {:3.1f} \u03bcm".format(
            best_effective_radius
        ))
        print("CRL Z position = {:6.1f} mm".format(crlz_position))
        print("-" * 65)
        print(
            "Distance CRLs to sample = {:6.1f} mm at photon energy of "
            "{} eV".format(best_sample_distance / 1e3, energy)
        )
        print("-" * 65)
        print(
            "Absolute sample position {:.1f} m from source at {}".format(
                source_sample_distance / 1e6, experiment
            )
        )
        fh = (
            21.8 * 2.35 * best_sample_distance /
            (source_sample_distance - best_sample_distance)
        )  # convert rms source size to FWHM
        fv = (
            4.1 * 2.35 * best_sample_distance /
            (source_sample_distance - best_sample_distance)
        )
        print(
            "Approximate focus size in brightness mode "
            "{:.3f} \u03bcm x {:.3f} \u03bcm".format(fh, fv)
        )
        print("-" * 65)

    return best_combination, crlz_position
