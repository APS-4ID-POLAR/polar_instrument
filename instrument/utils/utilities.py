import gi

gi.require_version("Hkl", "5.0")
from gi.repository import Hkl
from hkl.user import (
    _check_geom_selected,
    current_diffractometer,
    select_diffractometer,
)

from instrument.collection import RE, diffract, scaler, counters


def setaz(*args):
    _geom_ = current_diffractometer()
    _check_geom_selected()
    if (
        len(_geom_.calc.physical_axes) == 4
        and _geom_.calc.engine.mode == "psi_constant"
    ):
        _h2, _k2, _l2, psi = _geom_.calc._engine.engine.parameters_values_get(
            Hkl.UnitEnum.USER
        )
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
            [h2, k2, l2], Hkl.UnitEnum.USER
        )
        print("Azimuth = {} {} {} with Psi fixed at {}".format(h2, k2, l2, psi))
    else:
        raise ValueError(
            "Function not available in mode '{}'".format(
                _geom_.calc.engine.mode
            )
        )


def freeze(*args):
    _geom_ = current_diffractometer()
    _check_geom_selected()
    if (
        len(_geom_.calc.physical_axes) == 4
        and _geom_.calc.engine.mode == "psi_constant"
    ):
        h2, k2, l2, psi = _geom_.calc._engine.engine.parameters_values_get(
            Hkl.UnitEnum.USER
        )
        if len(args) == 0:

            psi = int((input("H = ({})? ".format(psi))) or psi)
        elif len(args) == 1:
            psi = args[0]
            # h2, k2, l2, psi= _geom_.calc._engine.engine.parameters_values_get(Hkl.UnitEnum.USER)
        else:
            raise ValueError(
                "either no argument or azimuth needs to be provided."
            )
        _geom_.calc._engine.engine.parameters_values_set(
            [h2, k2, l2, psi], Hkl.UnitEnum.USER
        )
        print("Psi = {}".format(psi))
    else:
        raise ValueError(
            "Function not available in mode '{}'".format(
                _geom_.calc.engine.mode
            )
        )


def change_diffractometer(*args):
    _geom_ = current_diffractometer()
    diff = int(
        (input("Diffractometer ({}): ".format(_geom_.name))) or _geom_.name
    )
    if diff == "diffract":
        select_diffractometer(diffract)
    _geom_ = current_diffractometer()


def wh():
    """
    Retrieve information on the current reciprocal space position.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.
    """
    _geom_ = current_diffractometer()
    h2, k2, l2, psi = _geom_.calc._engine.engine.parameters_values_get(
        Hkl.UnitEnum.USER
    )
    print(
        "\n   H K L = {:5f} {:5f} {:5f}".format(
            _geom_.calc.engine.pseudo_axes["h"],
            _geom_.calc.engine.pseudo_axes["k"],
            _geom_.calc.engine.pseudo_axes["l"],
        )
    )
    print(
        "\n   Lambda (Energy) = {:6.4f} \u212B ({:6.4f} keV)".format(
            _geom_.calc.wavelength, _geom_.calc.energy
        )
    )
    if len(_geom_.calc.physical_axes) == 6:
        print(
            "\n{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}".format(
                "Delta", "Eta", "Chi", "Phi", "Nu", "Mu"
            )
        )
        print(
            "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                _geom_.delta.get()[0],
                _geom_.omega.get()[0],
                _geom_.chi.get()[0],
                _geom_.phi.get()[0],
                _geom_.gamma.get()[0],
                _geom_.mu.get()[0],
            )
        )
    elif len(_geom_.calc.physical_axes) == 4:
        if _geom_.calc.engine.mode == "psi_constant":
            h2, k2, l2, psi = _geom_.calc._engine.engine.parameters_values_get(
                Hkl.UnitEnum.USER
            )
            print("   Psi = {}".format(psi))
        print(
            "\n{:>11}{:>9}{:>9}{:>9}".format("Two Theta", "Theta", "Chi", "Phi")
        )
        print(
            "{:>11.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                _geom_.tth.get()[0],
                _geom_.omega.get()[0],
                _geom_.chi.get()[0],
            )
        )


def plotselect(detector=None):
    scalers = scaler.channels_name_map.items()
    plotted_scalers = scaler.hints["fields"]
    print("{:>4}{:>12}{:>4}".format("#", "Detector", " "))
    det_list = []
    for num, item in enumerate(scalers):
        if item[0] in plotted_scalers:
            print("{:>4}{:>12}{:>4}".format(num, item[0], "<--"))
            det_list.append(num)
        else:
            print("{:>4}{:>12}".format(num, item[0]))
    dets = input("Scalers to be plotted {}: ".format(det_list)) or det_list
    if isinstance(dets, str):
        dets = [int(x) for x in dets.split(",")]
    det_list = []
    for num, item in enumerate(scalers):
        if num in dets:
            det_list.append(item[0])
    print("Scalers plotted: {}".format(det_list))
    scaler.select_plot_channels(det_list)


def set_counting_time(time=None, monitor=False):
    if time:
        if monitor:
            if monitor != "Time" and time > 199:
                counters.monitor_counts = time
                counters._mon = scaler.monitor = monitor
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        monitor, time
                    )
                )
            elif monitor == "Time" and time < 200:
                counters._mon = scaler.monitor = "Time"
                scaler.preset_monitor.put(time)
                print("New counting time = {}".format(time))
            else:
                raise ValueError("Counting time of {} too high.".format(time))
        else:
            monitor = scaler.monitor
            if monitor != "Time" and time > 199:
                counters.monitor_counts = time
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        monitor, time
                    )
                )
            elif monitor != "Time" and time < 200:
                counters._mon = scaler.monitor = "Time"
                scaler.preset_monitor.put(time)
                print("New counting time: {} s".format(time))
            elif monitor == "Time" and time < 200:
                scaler.preset_monitor.put(time)
                print("New counting time: {} s".format(time))

            else:
                counters.monitor_counts = time
                monitor = "Ion Ch 3"
                counters._mon = scaler.monitor = monitor
                print(
                    "Counting against monitor using '{}' as default for {} counts".format(
                        monitor, time
                    )
                )
                # raise ValueError(
                #    "Counting time of {} too high.".format(time)
                # )

    else:

        for item in scaler.preset_monitor.read().items():
            time = (
                input("Counting time [{}]: ".format(item[1]["value"]))
                or item[1]["value"]
            )
        if int(time) < 100:
            print("New counting time: {} s".format(time))
            counters._mon = scaler.monitor = "Time"
            scaler.preset_monitor.put(int(time))
        else:
            if monitor:
                monitor = input("Monitor [{}]: ".format(monitor)) or monitor
            else:
                monitor = scaler.monitor if not "Time" else "Ion Ch 3"
                monitor = input("Monitor [{}]: ".format(monitor)) or monitor
            counters._mon = scaler.monitor = monitor
            counters.monitor_counts = int(time)


def transfocator(distance=None, energy=None):
    # 10 keV
    if distance:
        distance = distance * 1e6
    else:
        distance = 2  # 2m in microns
        distance = float(
            input("Distance to sample [{}]: ".format(distance)) or distance
        )
        distance = distance * 1e6
    source_crl_distance = 67e6 - distance
    delta = 38e-6
    # available_lenses={"1000": 1, "500": 1, "200": 1, "200": 2, "200": 4, "200": 8, "100": 8, "100": 16}
    lens_types = [1000, 500, 200, 200, 200, 200, 100, 100]
    lenses = [1, 1, 1, 2, 4, 8, 8, 16]
    lenses_used = [0, 0, 0, 0, 0, 0, 0, 0]
    radius_eff = []
    # L_1 = f*L_0/(L_0-f)
    # f = L_0*L_1/(L_0+L_1)
    focus = source_crl_distance * distance / (source_crl_distance + distance)
    for num, value in enumerate(lens_types):
        # print(lenses[num], value, lenses[num]/value)
        radius_eff.append(lenses[num] / value)
    # print(radius_eff)
    iR_N = 1 / (2 * delta * focus)
    # print(iR_N)
    R = 0
    for num, value in enumerate(reversed(radius_eff)):
        # print(num,value, iR_N)
        if value < iR_N and R < iR_N:
            lenses_used[len(lenses) - num - 1] = 1
            R += value
            if R > iR_N + 0.001:
                R -= value
                lenses_used[len(lenses) - num - 1] = 0
    print("Inserted lens packages = {}".format(lenses_used))
    focus_new = 1 / (2 * delta * R)
    distance_new = (
        focus_new * source_crl_distance / (source_crl_distance - focus_new)
    )
    print(
        "Position correction = {:6.3f} mm".format(
            (distance - distance_new) / 1e3
        )
    )
