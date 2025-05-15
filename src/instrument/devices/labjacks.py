"""
Labjacks
"""

from apstools.devices import LabJackT7
from apstools.devices.labjack import (
    KIND_CONFIG_OR_NORMAL, DigitalIO, Output
)
from ophyd import DynamicDeviceComponent, EpicsSignalRO, Component, EpicsSignal


class AnalogOutput(Output):
    description = Component(EpicsSignal, ".DESC", kind="config")
    value = Component(EpicsSignal, "", kind="hinted")

    low_limit = Component(EpicsSignal, ".DRVL", kind="config")
    high_limit = Component(EpicsSignal, ".DRVH", kind="config")

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
        defn[f"ao{n}"] = (
            AnalogOutput, f"Ao{n}", dict(kind=KIND_CONFIG_OR_NORMAL)
        )
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
        defn[f"dio{n}"] = (
            DigitalIO, "", dict(ch_num=n, kind=KIND_CONFIG_OR_NORMAL)
        )

    # Add the digital word outputs
    defn["dio"] = (EpicsSignalRO, "DIOIn", dict(kind=KIND_CONFIG_OR_NORMAL))
    defn["fio"] = (EpicsSignalRO, "FIOIn", dict(kind=KIND_CONFIG_OR_NORMAL))
    defn["eio"] = (EpicsSignalRO, "EIOIn", dict(kind=KIND_CONFIG_OR_NORMAL))
    defn["cio"] = (EpicsSignalRO, "CIOIn", dict(kind=KIND_CONFIG_OR_NORMAL))
    defn["mio"] = (EpicsSignalRO, "MIOIn", dict(kind=KIND_CONFIG_OR_NORMAL))
    return defn


class CustomLabJackT7(LabJackT7):
    # In the "default" BCDA setup, four IO channels (all CIO, #16-19) are
    # converted into analog outputs (thus now 6 DACs)

    analog_outputs = DynamicDeviceComponent(
        make_analog_outputs(6), kind=KIND_CONFIG_OR_NORMAL
    )

    digital_ios = DynamicDeviceComponent(
        make_digital_ios(list(range(0, 16)) + list(range(20, 23))),
        kind=KIND_CONFIG_OR_NORMAL
    )

    def default_settings(self):
        self.analog_outputs.kind = "normal"
        self.waveform_digitizer.kind = "omitted"
        self.digital_ios.kind = "omitted"
        self.analog_inputs.kind = "omitted"
        for i in range(4):
            getattr(self.analog_outputs, f"ao{i}").kind = "normal"
