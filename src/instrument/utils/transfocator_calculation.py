"""
Transfocator functions.

.. autosummary::
    ~read_delta
    ~transfocator

"""
from hkl.user import current_diffractometer
from numpy import loadtxt
from scipy.interpolate import interp1d

BE_REFR_INDEX_FILE = (
    "/home/beams/POLAR/polar_instrument/src/instrument/utils/Be_refr_index.dat"
)


def read_delta(
    energy=None,
    path=BE_REFR_INDEX_FILE
):
    if energy < 2700 or energy > 27000:
        raise ValueError("Energy {} out of range [2700, 27000].".format(energy))

    energies, deltas = loadtxt(path, skiprows=2, usecols=(0, 1), unpack=True)
    return interp1d(energies, deltas, kind="linear")(energy)


def transfocator_calc(
    distance=None,
    energy=None,
    experiment="diffractometer",
    beamline="polar",
    verbose=True
):
    _geom_ = current_diffractometer()
    if not distance:
        distance = 1800
        distance = float(
            input("Distance to sample in mm [{}]: ".format(distance))
            or distance
        )
        distance = distance * 1e3
    elif distance > 200 and distance < 10000:
        distance = distance * 1e3
    else:
        raise ValueError(
            "Distance {} out of range [200, 10000].".format(energy)
        )

    if not energy:
        energy = _geom_.energy.get() * 1e3
    elif energy < 2600 or energy > 27000:
        raise ValueError(
            "Photon energy {} out of range [2600, 27000].".format(energy)
        )
    else:
        pass

    if beamline == "polar":
        if experiment == "diffractometer":
            source_sample_distance = 67.2e6
        elif experiment == "magnet":
            source_sample_distance = 73.3e6
        else:
            raise ValueError(
                "Calculation limited to focus positions at 67.2 m "
                "(diffractometer) or 73.3 m (magnet)."
                )

        # 4-ID: [1000, 500, 200, 200, 200, 200, 100, 100]
        # 6-ID-B: [1000, 500, 200, 200, 200, 200, 200, 200, 200]
        lens_types = [100, 100, 200, 200, 200, 200, 500, 1000]
        # 4-ID: [1, 1, 1, 2, 4, 8, 8, 16]
        # 6-ID: [1, 1, 1, 2, 4, 8, 12, 16, 32]
        lenses = [16, 8, 8, 4, 2, 1, 1, 1]
        # lenses_used = [0, 0, 0, 0, 0, 0, 0, 0]
    elif beamline == "6-ID-B":
        lens_types = [1000, 500, 200, 200, 200, 200, 200, 200, 200]
        lenses = [1, 1, 1, 2, 4, 8, 12, 16, 32]
        # lenses_used = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        source_sample_distance = 73.3e6
    else:
        raise ValueError("Beamline {} not supported.".format(beamline))

    source_crl_distance = source_sample_distance - distance
    delta = read_delta(energy)
    iradius_eff = []
    focus = source_crl_distance * distance / (source_crl_distance + distance)
    for num, value in enumerate(lens_types):
        iradius_eff.append(lenses[num] / value)
    iR_N = 1 / (2 * delta * focus)
    iR = 0
    lenses_used = []
    for num, value in enumerate(iradius_eff):
        lenses_used.append(0)
        if value < iR_N and iR < iR_N:
            lenses_used[-1] = 1
            iR += value
            if iR > iR_N + 0.001:
                iR -= value
                lenses_used[-1] = 0

    focus_new = 1 / (2 * delta * iR)
    distance_new = (
        focus_new * source_crl_distance / (source_crl_distance - focus_new)
    )

    if verbose:
        print("-" * 65)
        print("Inserted lens packages = {}".format(lenses_used))
        print("Effective radius = {:3.1f} \u03bcm".format(1 / iR))
        print(
            "Position correction = {:6.1f} mm".format(
                (distance - distance_new) / 1e3
            )
        )
        print("-" * 65)
        print(
            "Distance CRLs to sample = {:6.1f} mm at photon energy of "
            "{} eV".format(distance_new / 1e3, energy)
        )
        print("-" * 65)
        print(
            "Absolute sample position {:.1f} m from source at {}".format(
                source_sample_distance / 1e6, experiment
            )
        )
        fh = (
            distance_new / (source_sample_distance - distance_new) * 21.8 * 2.35
        )  # convert rms source size to FWHM
        fv = distance_new / (source_sample_distance - distance_new) * 4.1 * 2.35
        print(
            "Approximate focus size in brightness mode "
            "{:.3f} \u03bcm x {:.3f} \u03bcm".format(fh, fv)
        )
        print("-" * 65)

    return lenses_used, (distance - distance_new) / 1e3


def transfocator_calc_old(
    distance=None, energy=None, experiment="diffractometer", beamline="polar"
):
    _geom_ = current_diffractometer()
    if not distance:
        distance = 1800
        distance = float(
            input("Distance to sample in mm [{}]: ".format(distance))
            or distance
        )
        distance = distance * 1e3
    elif distance > 200 and distance < 10000:
        distance = distance * 1e3
    else:
        raise ValueError(
            "Distance {} out of range [200, 10000].".format(energy)
        )

    if not energy:
        energy = _geom_.energy.get() * 1e3
    elif energy < 2600 or energy > 27000:
        raise ValueError(
            "Photon energy {} out of range [2600, 27000].".format(energy)
        )
    else:
        pass

    if beamline == "polar":
        if experiment == "diffractometer":
            source_sample_distance = 67.2e6
        elif experiment == "magnet":
            source_sample_distance = 73.3e6
        else:
            raise ValueError(
                "Calculation limited to focus positions at 67.2 m (diffractometer) or 73.3 m (magnet).".format(
                    energy
                )
            )
        # 4-ID: [1000, 500, 200, 200, 200, 200, 100, 100]
        # 6-ID-B: [1000, 500, 200, 200, 200, 200, 200, 200, 200]
        lens_types = [1000, 500, 200, 200, 200, 200, 100, 100]
        # 4-ID: [1, 1, 1, 2, 4, 8, 8, 16]
        # 6-ID: [1, 1, 1, 2, 4, 8, 12, 16, 32]
        lenses = [1, 1, 1, 2, 4, 8, 8, 16]
        lenses_used = [0, 0, 0, 0, 0, 0, 0, 0]
    elif beamline == "6-ID-B":
        lens_types = [1000, 500, 200, 200, 200, 200, 200, 200, 200]
        lenses = [1, 1, 1, 2, 4, 8, 12, 16, 32]
        lenses_used = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        source_sample_distance = 73.3e6
    else:
        raise ValueError("Beamline {} not supported.".format(beamline))

    source_crl_distance = source_sample_distance - distance
    delta = read_delta(energy)
    iradius_eff = []
    focus = source_crl_distance * distance / (source_crl_distance + distance)
    for num, value in enumerate(lens_types):
        iradius_eff.append(lenses[num] / value)
    iR_N = 1 / (2 * delta * focus)
    iR = 0
    for num, value in enumerate(reversed(iradius_eff)):
        if value < iR_N and iR < iR_N:
            lenses_used[len(lenses) - num - 1] = 1
            iR += value
            if iR > iR_N + 0.001:
                iR -= value
                lenses_used[len(lenses) - num - 1] = 0
    print("-" * 65)
    print("Inserted lens packages = {}".format(lenses_used))
    print("Effective radius = {:3.1f} \u03bcm".format(1 / iR))
    focus_new = 1 / (2 * delta * iR)
    distance_new = (
        focus_new * source_crl_distance / (source_crl_distance - focus_new)
    )
    print(
        "Position correction = {:6.1f} mm".format(
            (distance - distance_new) / 1e3
        )
    )
    print("-" * 65)
    print(
        "Distance CRLs to sample = {:6.1f} mm at photon energy of {} eV".format(
            distance_new / 1e3, energy
        )
    )
    print("-" * 65)
    print(
        "Absolute sample position {:.1f} m from source at {}".format(
            source_sample_distance / 1e6, experiment
        )
    )
    fh = (
        distance_new / (source_sample_distance - distance_new) * 21.8 * 2.35
    )  # convert rms source size to FWHM
    fv = distance_new / (source_sample_distance - distance_new) * 4.1 * 2.35
    print(
        "Approximate focus size in brightness mode {:.3f} \u03bcm x {:.3f} \u03bcm".format(
            fh, fv
        )
    )
    print("-" * 65)
