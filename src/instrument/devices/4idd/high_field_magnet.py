"""
6T magnet
"""

__all__ = ['mag6t']

from ophyd import (
    Component, Device, EpicsMotor, EpicsSignal, EpicsSignalRO, Signal
)
from apstools.devices import PVPositionerSoftDoneWithStop
from ophyd.status import Status
from numpy import allclose
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class AMIZones(Device):
    high_field = Component(EpicsSignal, "Field.VAL", write_pv="FieldSet",
                           kind="config")
    ramp_rate = Component(EpicsSignal, "Rate", write_pv="RateSet",
                          kind="config")


class AMIController(PVPositionerSoftDoneWithStop):
    """ Magnetic field controler """

    # positions
    setpoint = Component(
        EpicsSignal, "PField", write_pv="PField:Wrt.A", auto_monitor=True,
        put_complete=True, kind="normal", labels=('ami_controller', 'magnets')
    )

    current = Component(EpicsSignalRO, "Current", auto_monitor=True,
                        kind="normal", labels=('ami_controller', 'magnets'))

    voltage = Component(EpicsSignalRO, "Voltage", auto_monitor=True,
                        kind="normal", labels=('ami_controller', 'magnets'))

    supply_current = Component(
        EpicsSignalRO, "CurrentSP", auto_monitor=True, kind="normal",
        labels=('ami_controller', 'magnets')
    )

    # status
    magnet_status = Component(
        EpicsSignalRO, "StateInt.A", auto_monitor=True, kind="config",
        labels=('ami_controller', 'magnets')
    )

    # configuration
    units = Component(EpicsSignalRO, "FieldUnits.SVAL", kind="config",
                      labels=('ami_controller', 'magnets'))

    field_limit = Component(EpicsSignalRO, "Field:Limit", kind="config",
                            labels=('ami_controller', 'magnets'))
    current_limit = Component(EpicsSignalRO, "Curr:Limit.VAL",
                              kind="config",
                              labels=('ami_controller', 'magnets'))
    voltage_limit = Component(EpicsSignalRO, "Volt:Limit.VAL",
                              kind="config",
                              labels=('ami_controller', 'magnets'))

    switch_heater = Component(EpicsSignal, "PSOnOff", string=True,
                              kind="config",
                              labels=('ami_controller', 'magnets'))

    zone_1 = Component(AMIZones, "RampR1:", kind="config",
                       labels=('ami_controller', 'magnets'))
    zone_2 = Component(AMIZones, "RampR2:", kind="config",
                       labels=('ami_controller', 'magnets'))
    zone_3 = Component(AMIZones, "RampR3:", kind="config",
                       labels=('ami_controller', 'magnets'))
    ramp_units = Component(EpicsSignalRO, "RampR:Units.SVAL", kind="config",
                           labels=('ami_controller', 'magnets'))
    tolerance = Component(Signal, value=0.0005, kind="config",
                          labels=('ami_controller', 'magnets'))

    # Update rate
    update_rate = Component(
        EpicsSignal, "StateIO.SCAN", put_complete=True,
        kind="omitted"
    )

    # Buttons
    ramp_button = Component(EpicsSignal, "Ramp.PROC", kind="omitted",
                            put_complete=True)
    pause_button = Component(EpicsSignal, "Pause.PROC", kind="omitted",
                             put_complete=True)
    zero_button = Component(EpicsSignal, "Zero.PROC", kind="omitted",
                            put_complete=True)

    @property
    def egu(self):
        return self.units.get(as_string=True)

    def move(self, position, wait=True, timeout=None, moved_cb=None):
        # Magnet would get stuck if sent to the same position. The 0.01 is a
        # bit arbritary.
        if allclose(self.readback.get(), position, 0.01):
            status = Status()
            status.set_finished()
            return status
        else:
            return super().move(
                position, wait=wait, timeout=timeout, moved_cb=moved_cb
            )


# Magnet and sample motors
class Magnet6T(Device):
    """ 6T magnet setup """

    # Motors #
    tabth = Component(EpicsMotor, 'm53', labels=('motors', 'magnets'))
    tabx = Component(EpicsMotor, 'm49', labels=('motors', 'magnets'))
    taby = Component(EpicsMotor, 'm50', labels=('motors', 'magnets'))

    tabth2 = Component(EpicsMotor, 'm56', labels=('motors', 'magnets'))
    tabz2 = Component(EpicsMotor, 'm51', labels=('motors', 'magnets'))
    tabx2 = Component(EpicsMotor, 'm52', labels=('motors', 'magnets'))

    sampy = Component(EpicsMotor, 'm63', labels=('motors', 'magnets'))
    sampth = Component(EpicsMotor, 'm58', labels=('motors', 'magnets'))

    # Magnetic field controller
    field = Component(
        AMIController, '4idd:AMI430:', readback_pv="Field", add_prefix=''
    )


mag6t = Magnet6T('4iddx:', name='mag6t')
sd.baseline.append(mag6t)
