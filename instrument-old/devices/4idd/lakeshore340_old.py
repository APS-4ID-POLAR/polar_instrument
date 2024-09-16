"""
Lakeshore 340 temperature controller EPICS version 1.1
"""

from apstools.synApps.asyn import AsynRecord
from ophyd import (Component, Device, Signal, EpicsSignal, EpicsSignalRO,
                   FormattedComponent)
from .util_components_old import TrackingSignal
from time import sleep
from apstools.devices import PVPositionerSoftDone

from ..session_logs import logger
logger.info(__file__)


# TODO: This should not be needed.
class SetpointSignal(EpicsSignal):
    """
    Signal for the control setpoint

    This is implemented because sometimes the setpoint PV is not updated. Here,
    it will check for the update, and retry.
    """

    def __init__(self, *args, max_iteractions=5, sleep_default=0.02,
                 ramp_attr='ramp_on', **kwargs):
        super().__init__(*args, **kwargs)
        self.max_iteractions = max_iteractions
        self.sleep_default = sleep_default
        self.ramp_attr = ramp_attr

    def put(self, value, **kwargs):
        super().put(value, **kwargs)
        ramp = getattr(self.parent, self.ramp_attr).get()
        counter = 0
        while abs(value - self._readback) > self.tolerance:
            if counter == self.max_iteractions:
                # Checks that it is not ramping.
                if ramp == 0:
                    raise RuntimeError('Setpoint was not updated after '
                                       f'{self.max_iteractions} attempts.')
                else:
                    break
            sleep(self.sleep_default)
            super().put(value, **kwargs)
            counter += 1


class LS340_LoopBase(PVPositionerSoftDone):
    """ Base settings for both sample and control loops. """

    # position
    readback = Component(Signal, value=0)
    setpoint = FormattedComponent(SetpointSignal, "{prefix}SP{loop_number}",
                                  write_pv="{prefix}wr_SP{loop_number}",
                                  kind="normal", put_complete=True)

    # configuration
    units = Component(Signal, value='K', kind="config")

    pid_P = FormattedComponent(EpicsSignal, "{prefix}P{loop_number}",
                               write_pv='{prefix}setPID{loop_number}.AA',
                               kind="config")
    pid_I = FormattedComponent(EpicsSignal, "{prefix}I{loop_number}",
                               write_pv='{prefix}setPID{loop_number}.BB',
                               kind="config")
    pid_D = FormattedComponent(EpicsSignal, "{prefix}D{loop_number}",
                               write_pv='{prefix}setPID{loop_number}.CC',
                               kind="config")

    ramp_rate = FormattedComponent(EpicsSignal,
                                   "{prefix}Ramp{loop_number}",
                                   write_pv='{prefix}setRamp{loop_number}.BB',
                                   kind="config")
    ramp_on = FormattedComponent(EpicsSignal,
                                 "{prefix}Ramp{loop_number}_on",
                                 kind="config")

    def __init__(self, *args, loop_number=None, timeout=60*60*10, **kwargs):
        self.loop_number = loop_number
        super().__init__(
            *args, timeout=timeout, tolerance=0.1, readback_pv="a",
            update_target=True, **kwargs
        )
        self._settle_time = 0

    @property
    def settle_time(self):
        return self._settle_time

    @settle_time.setter
    def settle_time(self, value):
        if value < 0:
            raise ValueError('Settle value needs to be >= 0.')
        else:
            self._settle_time = value

    @property
    def egu(self):
        return self.units.get(as_string=True)

    # def stop(self, *, success=False):
        # if success is False:
        #     self.setpoint.put(self._position)
        # super().stop(success=success)

    def pause(self):
        self.setpoint.put(self._position, wait=True)


class LS340_LoopControl(LS340_LoopBase):
    """ Control specific """

    readback = Component(EpicsSignalRO, "Control", kind="normal")
    sensor = Component(EpicsSignal, "Ctl_sel", kind="config")


class LS340_LoopSample(LS340_LoopBase):
    """ Sample specific """

    readback = Component(EpicsSignalRO, "Sample", kind="hinted")
    sensor = Component(EpicsSignal, "Spl_sel", kind="config")


class LS340Device(Device):
    """ Lakeshore 340 setup EPICS version 1.1 """

    control = FormattedComponent(LS340_LoopControl, "{prefix}",
                                 loop_number=1)
    sample = FormattedComponent(LS340_LoopSample, "{prefix}",
                                loop_number=2)

    heater = Component(EpicsSignalRO, "Heater")
    heater_range = Component(EpicsSignal, "Rg_rdbk", write_pv="HeatRg",
                             kind="normal", put_complete=True)

    auto_heater = Component(TrackingSignal, value=False, kind="config")

    read_pid = Component(EpicsSignal, "readPID.PROC", kind="omitted")

    # same names as apstools.synApps._common.EpicsRecordDeviceCommonAll
    scanning_rate = Component(EpicsSignal, "read.SCAN", kind="omitted")
    process_record = Component(EpicsSignal, "read.PROC", kind="omitted")

    serial = Component(AsynRecord, "serial", kind="omitted")

    # This must be modified either here, or before using auto_heater.
    _auto_ranges = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: I don't know why this has to be done, otherwise it gets hinted.
        self.control.readback.kind = "normal"

    @auto_heater.sub_value
    def _subscribe_auto_heater(self, value=None, **kwargs):
        if value:
            self.control.setpoint.subscribe(self._switch_heater,
                                            event_type='value')
        else:
            self.control.setpoint.clear_subs(self._switch_heater)

    def _switch_heater(self, value=None, **kwargs):
        # TODO: Find a better way to do this, perhaps with an array?
        for _heater_range, _temp_range in self._auto_ranges.items():
            if _temp_range:
                if _temp_range[0] < value <= _temp_range[1]:
                    self.heater_range.put(_heater_range)

    @property
    def auto_ranges(self):
        return self._auto_ranges

    @auto_ranges.setter
    def auto_ranges(self, value):
        if not isinstance(value, dict):
            raise TypeError('auto_ranges must be a dictionary.')

        for _heater_range, _temp_range in value.items():
            if _heater_range not in self.heater_range.enum_strs:
                raise ValueError("The input dictionary keys must be one of "
                                 f"these: {self.heater_range.enum_strs}, but "
                                 f"{_heater_range} was entered.")

            if _temp_range is not None and len(_temp_range) != 2:
                raise ValueError(f"The value {_temp_range} is invalid! It "
                                 "must be either None or an iterable with two "
                                 "items.")

            self._auto_ranges = value
