"""
Cyberstar detector parameters
"""
__all__ = ['cyberstar_mag_parameters', 'cyberstar_8c_parameters']

from ophyd import Component, Device, EpicsSignal
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class CyberstarDevice(Device):
    """ Hold cyberstar parameters, it is read through scaler channel. """

    hv = Component(EpicsSignal, 'HV.VAL', write_pv='SetHV.A', kind='config')

    remote_on = Component(EpicsSignal, 'Remote.VAL', kind='config')

    gain = Component(EpicsSignal, 'Gain.VAL', write_pv='SetGain.VAL',
                     kind='config')

    peak_time = Component(EpicsSignal, 'Pktime.VAL', write_pv='SetPktime.VAL',
                          kind='config')

    sca_low = Component(EpicsSignal, 'SCAlo.VAL', write_pv='SetSCAlo.VAL',
                        kind='config')

    sca_window = Component(EpicsSignal, 'SCAhi.VAL', write_pv='SetSCAhi.VAL',
                           kind='config')


cyberstar_mag_parameters = CyberstarDevice(
    '4idd:x1k:2:', name='cyberstar_mag', labels=('cyberstar',)
    )
cyberstar_8c_parameters = CyberstarDevice(
    '4idd:x1k:1:', name='cyberstar_8c', labels=('cyberstar',)
    )
sd.baseline.append(cyberstar_8c_parameters)
sd.baseline.append(cyberstar_mag_parameters)
