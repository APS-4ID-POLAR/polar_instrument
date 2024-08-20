"""
User Calculator
"""

__all__ = ['absorption_calc', 'normalize_calc']

from bluesky.plan_stubs import mv
from ophyd import Device, EpicsSignal, Kind, Signal
from ophyd import Component, FormattedComponent, DynamicDeviceComponent
from string import ascii_uppercase
from collections import OrderedDict
from ..framework import sd

from ..session_logs import logger
logger.info(__file__)


class UserCalcChannel(Device):

    trigger_option = FormattedComponent(EpicsSignal,
                                        '{self.prefix}.IN{self._ch}P',
                                        kind=Kind.config)

    PVname = FormattedComponent(EpicsSignal,
                                '{self.prefix}.IN{self._ch}N',
                                kind=Kind.config)

    value = FormattedComponent(EpicsSignal,
                               '{self.prefix}.{self._ch}',
                               kind=Kind.config)

    def __init__(self, prefix, ch, **kwargs):
        self._ch = ch
        super().__init__(prefix, **kwargs)


def _sc_chans(attr_fix, id_range):
    defn = OrderedDict()
    for k in id_range:
        defn['{}{}'.format(attr_fix, k)] = (UserCalcChannel,
                                            '', {'ch': k,
                                                 'kind': Kind.config})

    return defn


class UserCalc(Device):

    channels = DynamicDeviceComponent(_sc_chans('chan',
                                                list(ascii_uppercase)[:12]),
                                      kind=Kind.config)

    scan = Component(EpicsSignal, '.SCAN', kind=Kind.omitted)
    expression = Component(EpicsSignal, '.CALC$', string=True,
                           kind=Kind.config)
    calc_value = Component(EpicsSignal, '.VAL', kind=Kind.hinted)
    enable = Component(EpicsSignal, '.DESC', string=True, kind=Kind.config)

    # Dummy signal for compatibility
    preset_monitor = Component(Signal, value=0, kind='omitted')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_attrs = ['calc_value']

    @property
    def read_attrs(self):
        return self._read_attrs

    @read_attrs.setter
    def read_attrs(self, value):
        if type(value) is not list:
            raise TypeError('read_attrs has to be a list!')
        else:
            self._read_attrs = value

    def SetCountTimePlan(self, value, **kwargs):
        yield from mv(self.preset_monitor, value, **kwargs)


absorption_calc = UserCalc('4id:userCalc9', name='absorption_calc')
# TODO: this times out frequently during startup
# absorption_calc.scan.put(2)

normalize_calc = UserCalc('4id:userCalc10', name='normalize_calc')
# TODO: this times out frequently during startups
# normalize_calc.scan.put(2)

sd.baseline.append(absorption_calc)
sd.baseline.append(normalize_calc)
