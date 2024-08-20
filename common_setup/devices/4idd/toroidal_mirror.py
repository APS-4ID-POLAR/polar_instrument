
"""
Toroidal mirror
"""
__all__ = ['toroidal_mirror']

from ophyd import Component, Device, EpicsMotor, EpicsSignal
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class ToroidalMirror(Device):
    """ Beamline toroidal mirror components. """

    y_upstream = Component(EpicsMotor, 'm35', labels=('motor', 'mirrors'),
                           kind='config')
    y_downstream = Component(EpicsMotor, 'm36', labels=('motor', 'mirrors'),
                             kind='config')
    y = Component(EpicsSignal, 'M1t2.D', write_pv='M1avg',
                  labels=('motor', 'mirrors'), kind='config')
    angle = Component(EpicsSignal, 'M1t2.C', write_pv='M1angl',
                      labels=('motor', 'mirrors'), kind='config')

    x_upstream = Component(EpicsMotor, 'm33', labels=('motor', 'mirrors'))
    x_downstream = Component(EpicsMotor, 'm34', labels=('motor', 'mirrors'),
                             kind='config')
    x = Component(EpicsSignal, 'M1xt2.D', write_pv='M1xavg',
                  labels=('mirrors',), kind='config')
    x_angle = Component(EpicsSignal, 'M1xt2.C', write_pv='M1xangl',
                        labels=('mirrors',), kind='config')

    bender = Component(EpicsMotor, 'm32', labels=('motor', 'mirrors'),
                       kind='config')

    stripe = Component(EpicsSignal, 'DMir:Xpos:Mir1.VAL', string=True,
                       labels=('mirrors',), kind='config')


toroidal_mirror = ToroidalMirror('4idb:', name='toroidal_mirror')
sd.baseline.append(toroidal_mirror)
