"""
Filter banks
"""
__all__ = ['filter_pre8c', 'filter_tth']

from ophyd import Component, Device, EpicsSignal, FormattedComponent
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class OneSlot(Device):
    """ Configure one filter slot. """

    label = FormattedComponent(EpicsSignal, '{prefix}{_num}.DESC',
                               kind='config', string=True)
    status = FormattedComponent(EpicsSignal, '{prefix}{_num}.VAL',
                                kind='config', string=True)

    def __init__(self, *args, num=0, **kwargs):
        self._num = num
        super().__init__(*args, **kwargs)


class FilterBank(Device):
    """ Filter bank with 4 slots """

    slot1 = Component(OneSlot, 'bo', num=1)
    slot2 = Component(OneSlot, 'bo', num=2)
    slot3 = Component(OneSlot, 'bo', num=3)
    slot4 = Component(OneSlot, 'bo', num=4)


filter_pre8c = FilterBank('4idd:PCFfilter:1:', name='filter_pre8c',
                          labels=('filters',))
filter_tth = FilterBank('4idd:PCFfilter:2:', name='filter_tth',
                        labels=('filters',))

sd.baseline.append(filter_pre8c)
sd.baseline.append(filter_tth)
