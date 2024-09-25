"""
Utility functions.

.. autosummary::
    ~wm
    ~change_diffractometer
    ~plotselect
    ~set_counting_time
    ~set_experiment
    ~list_functions

"""

import gi

gi.require_version("Hkl", "5.0")
from gi.repository import Hkl
from hkl.user import (
    _check_geom_selected,
    current_diffractometer,
    select_diffractometer,
)

from .run_engine import RE
#from ..devices import counters
from ..devices import polar, diffract, fourc, scaler, counters
from ..utils import hkl_utils
from inspect import getmembers, isfunction
from polartools import (
    load_data,
    diffraction,
    absorption,
    pressure_calibration,
    process_images,
    area_detector_handlers,
    manage_database,
)
from apstools import utils
from hkl import user, util

import fileinput
import pathlib
import sys

path = pathlib.Path("startup_experiment.py")

import pyRestTable

def wm(*argv):
    table = pyRestTable.Table()
    nm=['   ']
    anm=['   ']
    hpos=['   High']
    lpos=['   Low']
    pos=['   Position   ']
    centering =['l']
    for arg in argv:
        nm.append(arg.name)
        anm.append(arg.attr_name)
        hpos.append(arg.high_limit)
        pos.append(arg.position)
        lpos.append(arg.low_limit)
        centering.append('r')
    print(centering)
    table.labels = nm
    table.setTabularColumns(True, centering)
    table.rows.append(anm)
    table.rows.append(hpos)
    table.rows.append(pos)
    table.rows.append(lpos)
    print(table.reST(fmt='plain'))


def change_diffractometer(*args):
    _geom_ = current_diffractometer()
    list = ["diffract", "fourc", "polar", "sixcpsi"]
    print("Available diffractometers {}".format(list))
    diff = input("Diffractometer ({}): ".format(_geom_.name)) or _geom_.name
    if diff == "diffract":
        select_diffractometer(diffract)
    elif diff == "fourc":
        select_diffractometer(fourc)
    elif diff == "polar":
        select_diffractometer(polar)
    elif diff == "sixcpsi":
        select_diffractometer(polar)
    else:
        raise ValueError("Diffractometer type {} does not exist.".format(diff))

    _geom_ = current_diffractometer()
    print("Diffractometer changed to {}".format(_geom_.name))


def plotselect(detector=None):
    """
    Selects scalers plotted during scan
    """
    scalers = scaler.channels_name_map.items()
    if detector is None:
        plotted_scalers = scaler.hints["fields"]
        print("{:>4}{:>12}{:>4}".format("#", "Detector", " "))
        det_list = []
        for num, item in enumerate(scalers):
            if item[0] in plotted_scalers:
                print("{:>4}{:>15}{:>4}".format(num, item[0], "<--"))
                det_list.append(num)
            else:
                print("{:>4}{:>15}".format(num, item[0]))
        dets = input("Scalers to be plotted {}: ".format(det_list)) or det_list
        if isinstance(dets, str):
            dets = [int(x) for x in dets.split(",")]    
    else:
        if isinstance(detector, int):
            dets = [detector]
        elif isinstance(detector, list):
            dets = detector
        else:
            raise ValueError(f"expected int or list got '{detector}'")
        
    det_list = []
    for num, item in enumerate(scalers):
        if num in dets:
            det_list.append(item[0])

    print("Scalers plotted: {}".format(det_list))
    scaler.select_plot_channels(det_list)


def set_counting_time(time=None, monitor=False):
    """
    Sets counting time / monitor counts:
        time <  500: counting time in seconds
        time >= 500: monitor counts

    Needs to be adapted to other detectors than scalers
    """
    threshold = 500
    if time:
        if monitor:
            if monitor != "Time" and time > threshold-1:
                counters.monitor_counts = time
                counters._mon = scaler.monitor = monitor
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        monitor, time
                    )
                )
            elif monitor == "Time" and time < threshold:
                counters._mon = scaler.monitor = "Time"
                scaler.preset_monitor.put(time)
                print("New counting time = {}".format(time))
            else:
                raise ValueError("Counting time of {} too high.".format(time))
        else:
            monitor = scaler.monitor
            if monitor != "Time" and time > threshold-1:
                counters.monitor_counts = time
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        monitor, time
                    )
                )
            elif monitor != "Time" and time < threshold:
                counters._mon = scaler.monitor = "Time"
                scaler.preset_monitor.put(time)
                print("New counting time: {} s".format(time))
            elif monitor == "Time" and time < threshold:
                scaler.preset_monitor.put(time)
                print("New counting time: {} s".format(time))

            else:
                counters.monitor_counts = time
                monitor = "Test7"
                counters._mon = scaler.monitor = monitor
                print(
                    "Counting against monitor using '{}' as default for {} counts".format(
                        monitor, time
                    )
                )

    else:

        for item in scaler.preset_monitor.read().items():
            time = (
                input("Counting time [{}]: ".format(item[1]["value"]))
                or item[1]["value"]
            )
        if int(time) < threshold:
            print("New counting time: {} s".format(time))
            counters._mon = scaler.monitor = "Time"
            scaler.preset_monitor.put(int(time))
        else:
            if monitor:
                monitor = input("Monitor [{}]: ".format(monitor)) or monitor
            else:
                monitor = scaler.monitor if not "Time" else "Test7"
                monitor = input("Monitor [{}]: ".format(monitor)) or monitor
            counters._mon = scaler.monitor = monitor
            counters.monitor_counts = int(time)


def set_experiment(name=None, proposal_id=None, sample=None):
    """
    Set experiment parameters.

    Parameters
    ----------
    name : string, optional
    proposal_id: integer, optional
    sample: string, optional
    """
    # fileinput.close()
    _name = name if name else RE.md["user"]
    _proposal_id = proposal_id if proposal_id else RE.md["proposal_id"]
    _sample = sample if sample else RE.md["sample"]
    name = _name if name else input(f"User [{_name}]: ") or _name
    proposal_id = (
        _proposal_id
        if proposal_id
        else input(f"Proposal ID [{_proposal_id}]: ") or _proposal_id
    )
    sample = _sample if sample else input(f"Sample [{_sample}]: ") or _sample

    RE.md["user"] = name
    RE.md["proposal_id"] = proposal_id
    RE.md["sample"] = sample
    if path.exists():
        print("Updating experiment information in '{}'".format(path.name))
        for line in fileinput.input([path.name], inplace=True):
            if line.strip().startswith("RE.md['user']"):
                line = f"RE.md['user']='{name}'\n"
            elif line.strip().startswith("RE.md['proposal_id']"):
                line = f"RE.md['proposal_id']='{proposal_id}'\n"
            elif line.strip().startswith("RE.md['sample']"):
                line = f"RE.md['sample']='{sample}'\n"

            sys.stdout.write(line)

    else:
        print("Writing experiment information to '{}'".format(path.name))
        f = open(path.name, "w")
        f.write("from instrument.utils.run_engine import RE\n")
        f.write(f"RE.md['user']='{name}'\n")
        f.write(f"RE.md['proposal_id']='{proposal_id}'\n")
        f.write(f"RE.md['sample']='{sample}'\n")
        f.close()


def list_functions(select=None):
    """
    List available functions

    select: string, optional
        None: all packages
        "absorption": functions related to absorption experiments
        "diffraction": functions related to diffraction experiments
        "hklpy": functions related to reciprocal space
    """
    if select == "absorption":
        packages = [absorption]
    elif select == "diffraction":
        packages = [load_data, diffraction, utils]
    elif select == "hklpy":
        packages = [user, util]
    else:
        packages = [
            hkl_utils,
            load_data,
            diffraction,
            absorption,
            pressure_calibration,
            process_images,
            area_detector_handlers,
            manage_database,
            utils,
            user,
            util,
        ]

    for item in packages:
        function_list = getmembers(item, isfunction)
        print("-" * len(item.__name__))
        print(item.__name__)
        print("-" * len(item.__name__))
        for funct in function_list:
            print(funct[0])
