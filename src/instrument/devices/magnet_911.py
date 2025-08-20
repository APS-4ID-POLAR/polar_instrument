"""
Table in middle of 4idb
"""

from ophyd import (
    Device,
    Component,
    DynamicDeviceComponent,
    FormattedComponent,
    EpicsMotor,
    EpicsSignalRO,
    EpicsSignal,
)
from apstools.devices import PVPositionerSoftDoneWithStop
from collections import OrderedDict


class TableMotors(Device):
    x = Component(EpicsMotor, "m14", labels=("motor",))
    y = Component(EpicsMotor, "m15", labels=("motor",))
    z = Component(EpicsMotor, "m16", labels=("motor",))

    sx = Component(EpicsMotor, "m18", labels=("motor",))
    sz = Component(EpicsMotor, "m19", labels=("motor",))
    srot = Component(EpicsMotor, "m17", labels=("motor",))


class RamanMotors(Device):
    x = Component(EpicsMotor, "m24", labels=("motor",))
    y = Component(EpicsMotor, "m25", labels=("motor",))
    z = Component(EpicsMotor, "m26", labels=("motor",))

    tilt = Component(EpicsMotor, "m27", labels=("motor",))
    rot = Component(EpicsMotor, "m28", labels=("motor",))


class MagnetMotors(Device):
    y = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Height",
        setpoint_pv="SetHeight.VAL",
        tolerance=0.0005,
    )

    rot = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Angle",
        setpoint_pv="SetAngle.VAL",
        tolerance=0.05,
    )


class PowerSupply(Device):
    ready = Component(EpicsSignalRO, "Ready", kind="config")
    heater = Component(EpicsSignalRO, "Heater", string=True, kind="config")
    quench = Component(EpicsSignalRO, "Quench", string=True, kind="config")

    field = Component(EpicsSignalRO, "Field", kind="hinted")
    field_unit = Component(EpicsSignalRO, "TargetFieldUnits", kind="config")

    field = Component(EpicsSignalRO, "Field", kind="hinted")
    target_field = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetField.VAL",
        readback_pv="TargetField",
        tolerance=0.01,  # TODO: Enough?
    )
    field_unit = Component(
        EpicsSignal,
        "TargetFieldUnits",
        write_pv="SetTargetFieldUnits",
        string=True,
        kind="config",
    )

    persistant_field = Component(EpicsSignalRO, "PersField")
    current = Component(EpicsSignalRO, "Current")
    voltage = Component(EpicsSignalRO, "Voltage")
    helium = Component(EpicsSignalRO, "HeliumLevel")

    ramp_rate = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetRampRate.VAL",
        readback_pv="RampRate",
        tolerance=0.001,  # TODO: Enough?
    )
    ramp_rate_unit = Component(
        EpicsSignal,
        "RampRateUnits",
        write_pv="SetRampRateUnits",
        string=True,
        kind="config",
    )

    ramp_pause = Component(EpicsSignal, "SetPause", kind="config")
    ramp_start = Component(EpicsSignal, "StartRamp.PROC", kind="omitted")
    ramp_abort = Component(EpicsSignal, "SetAbort.PROC", kind="omitted")

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class MonChannel(Device):
    temperature_name = FormattedComponent(EpicsSignalRO, "{prefix}TempName{ch}")
    temperature = FormattedComponent(EpicsSignalRO, "{prefix}Temp{ch}")
    hall_resistance = FormattedComponent(EpicsSignalRO, "{prefix}HallRes{ch}")
    hall_field = FormattedComponent(EpicsSignalRO, "{prefix}HallField{ch}")

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")

    def __init__(self, *args, ch_num=1, **kwargs):
        self.ch = ch_num
        super().__init__(*args, **kwargs)


def _make_monitors(num=1):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"m{i :02d}"] = (
            MonChannel,
            "911TMagnet:TMon:",
            {"ch_num": i, "kind": "normal"},
        )

    return defn


# TODO: Change these names to something more meaningful.
class VTIDevice(Device):
    sensor_a = Component(
        EpicsSignalRO, "SensorA", kind="hinted", labels=["temperature"]
    )

    sensor_b = Component(
        EpicsSignalRO, "SensorB", kind="hinted", labels=["temperature"]
    )

    sensor_c = Component(
        EpicsSignalRO, "SensorC", kind="hinted", labels=["temperature"]
    )

    sensor_d = Component(
        EpicsSignalRO, "SensorD", kind="hinted", labels=["temperature"]
    )

    setpoint_1 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint1",
        setpoint_pv="SetTemp1",
        tolerance=0.01,
    )

    setpoint_2 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint2",
        setpoint_pv="SetTemp2",
        tolerance=0.01,
    )

    setpoint_3 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint3",
        setpoint_pv="SetTemp3",
        tolerance=0.01,
    )

    setpoint_4 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint4",
        setpoint_pv="SetTemp4",
        tolerance=0.01,
    )

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class NVDevice(Device):
    control_mode = Component(
        EpicsSignal, "SetControlMode", string=True, kind="config"
    )

    pressure_control_switch = Component(
        EpicsSignal, "SetPressureControl", string=True, kind="config"
    )

    temp = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetTargetTemperature",
        readback_pv="Temperature",
        kind="config",
    )

    pressure = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetTargetPressure",
        readback_pv="Pressure",
        kind="config",
    )

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class Magnet911(Device):

    connection = Component(EpicsSignalRO, "911TMagnet:asyn.CNCT", kind="config")

    tab = Component(TableMotors, "")
    raman = Component(RamanMotors, "")
    samp = Component(MagnetMotors, "911TMagnet:Motor:")

    ps = Component(PowerSupply, "911TMagnet:PSU:", labels=["magnet"])

    monitors = DynamicDeviceComponent(_make_monitors(num=6))

    temps = Component(VTIDevice, "911TMagnet:VTI:")

    needle_valve = Component(NVDevice, "911TMagnet:NV:")
