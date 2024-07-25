"""
Labjacks
"""

__all__ = ["labjack"]

from apstools.devices import LabJackT7
from apstools.devices.labjack import (
    make_analog_outputs, KIND_CONFIG_OR_NORMAL, DigitalIO, Output
)
from ophyd import DynamicDeviceComponent, EpicsSignalRO, Component, EpicsSignal
from ..session_logs import logger
from ..framework import sd
logger.info(__file__)


class AnalogOutput(Output):
    description = Component(EpicsSignal, ".DESC", kind="config")
    value = Component(EpicsSignal, "", kind="normal")
    readback_value = None
    desired_value = None


def make_analog_outputs(num_aos: int):
    """Create a dictionary with analog output device definitions.

    For use with an ophyd DynamicDeviceComponent.

    Parameters
    ==========
    num_aos
      How many analog outputs to create.

    """
    defn = {}
    for n in range(num_aos):
        defn[f"ao{n}"] = (AnalogOutput, f"Ao{n}", {})
    return defn


def make_digital_ios(channels_list: list):
    """Create a dictionary with digital I/O device definitions.

    For use with an ophyd DynamicDeviceComponent.

    Parameters
    ==========
    num_dios
      How many digital I/Os to create.
    """
    defn = {}
    for n in channels_list:
        defn[f"dio{n}"] = (DigitalIO, "", dict(ch_num=n))

    # Add the digital word outputs
    defn["dio"] = (EpicsSignalRO, "DIOIn", dict(kind="config"))
    defn["fio"] = (EpicsSignalRO, "FIOIn", dict(kind="config"))
    defn["eio"] = (EpicsSignalRO, "EIOIn", dict(kind="config"))
    defn["cio"] = (EpicsSignalRO, "CIOIn", dict(kind="config"))
    defn["mio"] = (EpicsSignalRO, "MIOIn", dict(kind="config"))
    return defn


class CustomLabJackT7(LabJackT7):
    # In the "default" BCDA setup, four IO channels (all CIO, #16-19) are converted
    # into analog outputs (thus now 6 DACs)

    analog_outputs = DynamicDeviceComponent(
        make_analog_outputs(6),
        kind=KIND_CONFIG_OR_NORMAL
    )

    digital_ios = make_digital_ios(list(range(0, 16)) + list(range(20, 23)))

labjack = CustomLabJackT7("4idLabJackT7_1:", name="labjack")
