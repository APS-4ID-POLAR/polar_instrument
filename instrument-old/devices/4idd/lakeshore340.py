"""
Lakeshore 340 temperature controller EPICS version 1.1
"""

from ophyd import Component
from apstools.devices import LakeShore340Device, TrackingSignal
from ..session_logs import logger
logger.info(__file__)


class LS340Device(LakeShore340Device):
    """ Lakeshore 340 setup EPICS version 1.1 """

    auto_heater = Component(TrackingSignal, value=False, kind="config")

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
