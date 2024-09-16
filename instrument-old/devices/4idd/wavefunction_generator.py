"""
Wavefunction generator.
"""

__all__ = ['wavefunc_gen']

from ophyd import Device, EpicsSignal, Component
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class SRS340(Device):

    frequency = Component(EpicsSignal, 'FREQ.VAL', write_pv='SetFREQ.A',
                          kind='config')

    amplitude = Component(EpicsSignal, 'AMPL.VAL', write_pv='SetAMPL.A',
                          kind='config')

    offset = Component(EpicsSignal, 'OFFS.VAL', write_pv='SetOFFS.A',
                       kind='config')

    function = Component(EpicsSignal, 'FUNC.SVAL', write_pv='FUNCs.VAL',
                         kind='config')


wavefunc_gen = SRS340('4idd:SRS340:1:', name='wavefunction_generator',
                      labels=('phase retarders',))
sd.baseline.append(wavefunc_gen)
