"""
Lakeshore 336 temperature controller EPICS version 1.0
"""

from ophyd import Component, FormattedComponent
from apstools.devices import TrackingSignal, LakeShore336Device
from apstools.devices.lakeshore_controllers import LakeShore336_LoopControl
from numpy import argsort, array
from ..session_logs import logger
logger.info(__file__)


class LS336_LoopControl(LakeShore336_LoopControl):
    """
    Setup for loop with heater control.

    The lakeshore 336 accepts up to two heaters.
    """

    auto_heater = Component(TrackingSignal, value=False, kind="config")

    # This must be modified either here, or before using auto_heater.
    _auto_ranges = None

    def __init__(self, *args, loop_number=None, timeout=60*60*10, **kwargs):
        super().__init__(
            *args, loop_number=loop_number, timeout=timeout, **kwargs
        )
        self._settle_time = 0
        self.tolerance.put(0.1)

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

    @auto_heater.sub_value
    def _subscribe_auto_heater(self, value=None, **kwargs):
        if value:
            self.setpoint.subscribe(self._switch_heater, event_type='value')
        else:
            self.setpoint.clear_subs(self._switch_heater)

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

    # TODO: This is a workaround from a potential problem in the apstools
    # PVPositionerSoftDone
    def _setup_move(self, position):
        self.cb_setpoint()
        super()._setup_move(position)


class LoopSample(LS336_LoopControl):
    """ Sample will move the vaporizer temperature if track_vaporizer=True """

    def __init__(self, *args, **kwargs):
        self.vaporizer_ranges = dict(
            limits=[6, 20, 100, 200, 300],
            offsets=[1, 2, 5, 10, 20]
        )

        super().__init__(*args, **kwargs)

    def move(self, position, **kwargs):
        wait = kwargs.pop("wait", False)

        # Just changes the sample temperature if not tracking vaporizer.
        if self.parent.track_vaporizer.get() is True:
            vaporizer_position = self._get_vaporizer_position(position)
            # Will not wait for vaporizer.
            _ = self.root.loop1.move(vaporizer_position, wait=False, **kwargs)

        self.cb_setpoint()
        return super().move(position, wait=wait, **kwargs)

    def _get_vaporizer_position(self, sample_position):
        """ Returns vaporizer setpoint based on the sample setpoint. """

        limits = array(self.vaporizer_ranges["limits"])
        offsets = array(self.vaporizer_ranges["offsets"])
        sort = argsort(limits)

        # If nothing works, it will just go to 80% of sample position
        vaporizer_position = sample_position*0.8
        for limit, offset in zip(limits[sort], offsets[sort]):
            if sample_position <= limit:
                vaporizer_position = sample_position - offset
                break

        return vaporizer_position


class LS336Device(LakeShore336Device):
    """
    Support for Lakeshore 336 temperature controller
    """
    loop1 = FormattedComponent(LS336_LoopControl, "{prefix}",
                               loop_number=1)
    loop2 = FormattedComponent(LoopSample, "{prefix}",
                               loop_number=2)

    track_vaporizer = Component(TrackingSignal, value=True, kind="config")
