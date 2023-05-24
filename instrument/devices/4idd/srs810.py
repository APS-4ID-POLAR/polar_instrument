"""
SRS 810 Lock-in
"""

__all__ = ['lockin']

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class LockinDevice(Device):

    # Time constant
    time_multiplier = Component(EpicsSignal, 'TC1', kind='omitted')
    time_decade = Component(EpicsSignal, 'TC2', kind='omitted')
    time_unit = Component(EpicsSignal, 'TC3', kind='config')
    time_filter = Component(EpicsSignal, 'FiltCh', kind='omitted')
    time_readback = Component(EpicsSignalRO, 'TC.SVAL', kind='config')

    # Gain
    gain_multiplier = Component(EpicsSignal, 'Sens1', kind='omitted')
    gain_decade = Component(EpicsSignal, 'Sens2', kind='omitted')
    gain_unit = Component(EpicsSignal, 'Sens3', kind='config')
    gain_readback = Component(EpicsSignalRO, 'Sens.SVAL', kind='config')

    # Reserve
    reserve = Component(EpicsSignal, 'ResvCh', kind='config')

    # Reference
    reference_freq = Component(EpicsSignalRO, 'Freq.SVAL', kind='config')
    reference_phase = Component(EpicsSignal, 'Phas.SVAL', write_pv='Phas.SVAL',
                                kind='config')

    # Channel 1 outputs
    chan1_x = Component(EpicsSignalRO, 'X.SVAL', kind='hinted')
    chan1_y = Component(EpicsSignalRO, 'Y.SVAL', kind='hinted')
    chan1_r = Component(EpicsSignalRO, 'R.SVAL', kind='hinted')
    chan1_q = Component(EpicsSignalRO, 'Th.SVAL', kind='hinted')


lockin = LockinDevice('4idd:SRS810:1:', name='lockin', labels=('detectors',))
sd.baseline.append(lockin)
