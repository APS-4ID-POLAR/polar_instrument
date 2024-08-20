"""
APD detector parameters
"""

__all__ = ['apd_parameters']

from ophyd import Component, Device, EpicsSignal
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class APDDevice(Device):
    """ Hold APD parameters, it is read through scaler channel. """

    source = Component(EpicsSignal, 'SetCSRC', kind='config')
    read_scan = Component(EpicsSignal, 'ReadCounts.SCAN', kind='config')
    count_time = Component(EpicsSignal, 'CountTime.A', kind='config')
    hv = Component(EpicsSignal, 'HV.VAL', write_pv='SetHV.A', kind='config')
    hv_on = Component(EpicsSignal, 'HVOnOff.VAL', kind='config')

    sca_mode = Component(EpicsSignal, 'SetSCAMode.VAL', kind='config')
    sca_outtime = Component(EpicsSignal, 'SetOutTime.VAL', kind='config')
    sca_low = Component(EpicsSignal, 'SCAlow.VAL', write_pv='SetSCALevel.A',
                        kind='config')
    sca_window = Component(EpicsSignal, 'SCAwin.VAL',
                           write_pv='SetSCALevel.B', kind='config')


apd_parameters = APDDevice('4idd:apd:1:', name='apd',
                           labels=('apd', 'detectors'))
sd.baseline.append(apd_parameters)
