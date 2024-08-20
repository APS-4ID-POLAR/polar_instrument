
"""
Flat mirror
"""
__all__ = ['flat_mirror']

from ophyd import Component, Device, EpicsMotor, EpicsSignal
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class FlatMirror(Device):
    """ Beamline flat mirror components. """

    y_upstream = Component(EpicsMotor, 'm39', labels=('motor', 'mirrors'),
                           kind='config')
    y_downstream = Component(EpicsMotor, 'm40', labels=('motor', 'mirrors'),
                             kind='config')
    y = Component(EpicsSignal, 'M2t2.D', write_pv='M2avg',
                  labels=('mirrors',), kind='config')
    angle = Component(EpicsSignal, 'M2t2.C', write_pv='M2angl',
                      labels=('mirrors',), kind='config')

    x_upstream = Component(EpicsMotor, 'm37', labels=('motor', 'mirrors'),
                           kind='config')
    x_downstream = Component(EpicsMotor, 'm38', labels=('motor', 'mirrors'),
                             kind='config')
    x = Component(EpicsSignal, 'M2xt2.D', write_pv='M1xavg',
                  labels=('mirrors',), kind='config')
    x_angle = Component(EpicsSignal, 'M1xt2.C', write_pv='M1xangl',
                        labels=('mirrors',), kind='config')

    stripe = Component(EpicsSignal, 'DMir:Xpos:Mir2.VAL', string=True,
                       labels=('mirrors',), kind='config')


flat_mirror = FlatMirror('4idb:', name='flat_mirror')
sd.baseline.append(flat_mirror)
