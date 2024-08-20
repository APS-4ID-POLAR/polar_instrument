"""
LM 510 Level Monitor
"""

__all__ = ['cryolevels']
from ..session_logs import logger
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ..framework import sd

logger.info(__file__)


class CryoLevelMonitor(Device):

    # Cryo_1 LHe
    level_he = Component(EpicsSignalRO, 'cryo_1:LEVEL')
    alarm_threshold_he = Component(
        EpicsSignal,
        'cryo_1:HALARM',
        write_pv='cryo_1:SETHALARM',
        kind='config',
    )
    low_threshold_he = Component(
        EpicsSignal, 'cryo_1:LOW', write_pv='cryo_1:SETLOW', kind='config'
    )
    high_threshold_he = Component(
        EpicsSignal, 'cryo_1:HIGH', write_pv='cryo_1:SETHIGH', kind='config'
    )
    automated_refill_he = Component(
        EpicsSignal, 'cryo_1:CTRL', write_pv='cryo_1:SETCTRL', kind='config',
    )
    scan_he = Component(EpicsSignal, 'cryo_1:scanSeq.SCAN', kind='config')

    # Cryo_2 LN2
    level_n2 = Component(EpicsSignalRO, 'cryo_2:LEVEL')
    alarm_threshold_n2 = Component(
        EpicsSignal,
        'cryo_2:HALARM',
        write_pv='cryo_2:SETHALARM',
        kind='config'
    )
    low_threshold_n2 = Component(
        EpicsSignal, 'cryo_2:LOW', write_pv='cryo_2:SETLOW', kind='config'
    )
    high_threshold_n2 = Component(
        EpicsSignal, 'cryo_2:HIGH', write_pv='cryo_2:SETHIGH', kind='config'
    )
    automated_refill_n2 = Component(
        EpicsSignal, 'cryo_2:CTRL', write_pv='cryo_2:SETCTRL', kind='config'
    )


cryolevels = CryoLevelMonitor(
    '4idd:', name='cryolevels', labels=("cryolevels")
)
sd.baseline.append(cryolevels)
