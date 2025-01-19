"""
Monochromator with energy controller by bluesky
"""

__all__ = ["mono"]

from ophyd import (
    Component,
    FormattedComponent,
    EpicsMotor,
    EpicsSignal,
    PseudoPositioner,
    PseudoSingle
)
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from scipy.constants import speed_of_light, Planck
from numpy import arcsin, pi, sin, cos
from ..utils._logging_setup import logger

logger.info(__file__)


class MonoDevice(PseudoPositioner):

    energy = Component(PseudoSingle, limits=(2.7, 30))
    th = FormattedComponent(EpicsMotor, 'm1', labels=('motor',))

    y = FormattedComponent(
        EpicsMotor, 'm3', labels=('motor',)
    )

    # Explicitly selects the real motors
    _real = ['th', 'y']

    crystal_2d = Component(EpicsSignal, "Bragg2dSpacingAO", kind="config")
    y_offset = Component(EpicsSignal, "Kohzu_yOffsetAO.VAL", kind="config")

    def convert_energy_to_theta(self, energy):
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = speed_of_light*Planck*6.241509e15*1e10/energy
        theta = arcsin(lamb/self.crystal_2d.get())*180./pi
        return theta

    def convert_energy_to_y(self, energy):
        # lambda in angstroms, theta in degrees, energy in keV
        theta = self.convert_energy_to_theta(energy)
        return self.y_offset/(2*cos(theta*pi/180))

    def convert_theta_to_energy(self, theta):
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = 2*self.d_spacing.get()*sin(theta*pi/180)
        energy = speed_of_light*Planck*6.241509e15*1e10/lamb
        return energy

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        '''Run a forward (pseudo -> real) calculation'''
        return self.RealPosition(
            th=self.convert_energy_to_theta(pseudo_pos.energy),
            y=self.convert_energy_to_y(pseudo_pos.energy)
        )

    @real_position_argument
    def inverse(self, real_pos):
        '''Run an inverse (real -> pseudo) calculation'''
        # Changing y does not change the energy.
        return self.PseudoPosition(
            energy=self.convert_theta_to_energy(real_pos.th)
        )

    def set_energy(self, energy):
        # energy in keV, theta in degrees.
        theta = self.convert_energy_to_theta(energy)
        self.th.set_current_position(theta)


mono = MonoDevice("4idVDCM:", name="mono", labels=("monochromator",))
