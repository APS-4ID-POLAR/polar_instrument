"""
Lakeshore 336 temperature controller EPICS version 1.0
"""

from apstools.synApps.asyn import AsynRecord
from ophyd import (Component, FormattedComponent, Device, EpicsSignal, Signal,
                   EpicsSignalRO, EpicsSignalWithRBV)
from ophyd.status import wait as status_wait
from .util_components_old import TrackingSignal, PVPositionerSoftDone

from ..session_logs import logger
logger.info(__file__)


def _get_vaporizer_position(sample_position):
    """ Returns vaporizer setpoint based on the sample setpoint. """

    # TODO: I would like to have this stored in some variable that we can
    # change.
    if sample_position < 6:
        vaporizer_position = sample_position - 1
    elif sample_position < 20:
        vaporizer_position = sample_position - 2
    elif sample_position < 100:
        vaporizer_position = sample_position - 5
    else:
        vaporizer_position = 100
    return vaporizer_position


class LS336_LoopControl(PVPositionerSoftDone):
    """
    Setup for loop with heater control.

    The lakeshore 336 accepts up to two heaters.
    """

    # position
    # TODO: Not sure this will work. May need to separate the RO again.
    readback = FormattedComponent(EpicsSignalRO, "{prefix}IN{loop_number}",
                                  auto_monitor=True, kind="hinted")
    setpoint = FormattedComponent(EpicsSignalWithRBV,
                                  "{prefix}OUT{loop_number}:SP",
                                  put_complete=True, kind="normal")
    # Due to ramping the setpoint will change slowly and the readback may catch
    # up even if the motion is not done.
    target = Component(Signal, value=0, kind="omitted")

    heater = FormattedComponent(EpicsSignalRO, "{prefix}HTR{loop_number}",
                                auto_monitor=True, kind="normal")

    # configuration
    units = FormattedComponent(EpicsSignalWithRBV,
                               "{prefix}IN{loop_number}:Units",
                               kind="config")
    pid_P = FormattedComponent(EpicsSignalWithRBV,
                               "{prefix}P{loop_number}",
                               kind="config")
    pid_I = FormattedComponent(EpicsSignalWithRBV,
                               "{prefix}I{loop_number}",
                               kind="config")
    pid_D = FormattedComponent(EpicsSignalWithRBV,
                               "{prefix}D{loop_number}",
                               kind="config")
    ramp_rate = FormattedComponent(EpicsSignalWithRBV,
                                   "{prefix}RampR{loop_number}",
                                   kind="config")
    ramp_on = FormattedComponent(EpicsSignalWithRBV,
                                 "{prefix}OnRamp{loop_number}",
                                 kind="config")

    loop_name = FormattedComponent(EpicsSignalRO,
                                   "{prefix}IN{loop_number}:Name_RBV",
                                   kind="config")
    control = FormattedComponent(EpicsSignalWithRBV,
                                 "{prefix}OUT{loop_number}:Cntrl",
                                 kind="config")
    manual = FormattedComponent(EpicsSignalWithRBV,
                                "{prefix}OUT{loop_number}:MOUT",
                                kind="config")
    mode = FormattedComponent(EpicsSignalWithRBV,
                              "{prefix}OUT{loop_number}:Mode",
                              kind="config")
    heater_range = FormattedComponent(EpicsSignalWithRBV,
                                      "{prefix}HTR{loop_number}:Range",
                                      kind="config", auto_monitor=True,
                                      string=True)

    auto_heater = Component(TrackingSignal, value=False, kind="config")

    # This must be modified either here, or before using auto_heater.
    _auto_ranges = None

    def __init__(self, *args, loop_number=None, timeout=60*60*10, **kwargs):
        self.loop_number = loop_number
        super().__init__(*args, timeout=timeout, tolerance=0.1,
                         target_attr="target", **kwargs)
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

    def stop(self, *, success=False):
        if success is False:
            self.setpoint.put(self._position)
        super().stop(success=success)

    def pause(self):
        self.setpoint.put(self._position)

    @auto_heater.sub_value
    def _subscribe_auto_heater(self, value=None, **kwargs):
        if value:
            self.setpointRO.subscribe(self._switch_heater, event_type='value')
        else:
            self.setpointRO.clear_subs(self._switch_heater)

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


class LS336_LoopRO(Device):
    """
    loop3 and loop4 do not use the heaters.
    """
    # Set this to normal because we don't use it.
    readback = FormattedComponent(EpicsSignalRO,
                                  "{prefix}IN{loop_number}",
                                  kind="normal")
    units = FormattedComponent(EpicsSignalWithRBV,
                               "{prefix}IN{loop_number}:Units",
                               kind="omitted")
    loop_name = FormattedComponent(EpicsSignalRO,
                                   "{prefix}IN{loop_number}:Name_RBV",
                                   kind="omitted")

    def __init__(self, *args, loop_number=None, **kwargs):
        self.loop_number = loop_number
        super().__init__(*args, **kwargs)


class LoopSample(LS336_LoopControl):
    """ Sample will move the vaporizer temperature if track_vaporizer=True """

    def move(self, position, **kwargs):
        # Just changes the sample temperature if not tracking vaporizer.
        if self.parent.track_vaporizer.get() is False:
            return super().move(position, **kwargs)

        wait = kwargs.pop('wait', True)
        sample_status = super().move(position, wait=False, **kwargs)

        vaporizer_position = self._get_vaporizer_position(position)
        # Will not wait for vaporizer.
        _ = self.root.loop1.move(vaporizer_position, wait=False, **kwargs)

        if wait:
            status_wait(sample_status)

        return sample_status


class LS336Device(Device):
    """
    Support for Lakeshore 336 temperature controller
    """
    loop1 = FormattedComponent(LS336_LoopControl, "{prefix}",
                               loop_number=1)
    loop2 = FormattedComponent(LoopSample, "{prefix}",
                               loop_number=2)
    loop3 = FormattedComponent(LS336_LoopRO, "{prefix}",
                               loop_number=3)
    loop4 = FormattedComponent(LS336_LoopRO, "{prefix}", loop_number=4)

    # same names as apstools.synApps._common.EpicsRecordDeviceCommonAll
    scanning_rate = Component(EpicsSignal, "read.SCAN", kind="omitted")
    process_record = Component(EpicsSignal, "read.PROC", kind="omitted")

    read_all = Component(EpicsSignal, "readAll.PROC", kind="omitted")
    serial = Component(AsynRecord, "serial", kind="omitted")

    track_vaporizer = Component(TrackingSignal, value=True, kind="config")
