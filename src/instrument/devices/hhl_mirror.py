
"""
HHL mirror
"""
__all__ = ['hhl_mirror']

from ophyd import Component, Device, EpicsMotor, EpicsSignal, EpicsSignalRO
from ..utils.run_engine import sd
from ..utils._logging_setup import logger
logger.info(__file__)


class ToroidalMirror(Device):
    """ Beamline toroidal mirror components. """

    # Motors
    y = Component(EpicsMotor, 'm1', labels=('motor'))
    x1 = Component(EpicsMotor, 'm2', labels=('motor'))
    x2 = Component(EpicsMotor, 'm3', labels=('motor'))
    us_bend = Component(EpicsMotor, 'm4', labels=('motor'))
    ds_bend = Component(EpicsMotor, 'm5', labels=('motor'))

    # Combined motions
    lateral = Component(EpicsMotor, 'pm1', labels=('motor'))
    pitch = Component(EpicsMotor, 'pm2', labels=('motor'))
    # TODO: this fine pitch is in 4ida?
    # fine_pitch = Component(EpicsMotor, 'pm1', labels=('motor'))
    curvature = Component(EpicsMotor, 'pm3', labels=('motor'))
    elipticity = Component(EpicsMotor, 'pm4', labels=('motor'))

    # Other parameters
    stripe = Component(EpicsSignal, 'stripe', string=True)
    radius_target = Component(EpicsSignalRO, 'EstimatedRoC')
    critical_energy = Component(EpicsSignalRO, 'Ecritical')
    beam_offset = Component(EpicsSignalRO, 'beam_offset')
    alpha = Component(EpicsSignalRO, 'alpha')


hhl_mirror = ToroidalMirror(
    '4idHHLM:', name='toroidal_mirror', labels=("mirror",)
)
sd.baseline.append(hhl_mirror)