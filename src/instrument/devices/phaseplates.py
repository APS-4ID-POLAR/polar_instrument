"""
Phase retarders.
"""

from ophyd import Device, EpicsMotor, PseudoPositioner, PseudoSingle
from ophyd import Component, FormattedComponent
from ophyd import EpicsSignal, EpicsSignalRO, Signal, DerivedSignal
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from scipy.constants import speed_of_light, Planck
from numpy import arcsin, pi, sin
from apstools.devices import TrackingSignal, PVPositionerSoftDoneWithStop

# This is here because PRDevice.select_pr has a micron symbol that utf-8
# cannot read. See: https://github.com/bluesky/ophyd/issues/930
from epics import utils
utils.IOENCODING = "latin-1"


class MicronsSignal(DerivedSignal):
    '''A signal that converts the offset from degrees to microns'''

    def __init__(self, parent_attr, *, parent=None, **kwargs):
        degrees_signal = getattr(parent, parent_attr)
        super().__init__(derived_from=degrees_signal, parent=parent, **kwargs)

    def describe(self):
        desc = super().describe()
        desc[self.name]['units'] = 'microns'
        return desc

    def inverse(self, value):
        '''Compute original signal value -> derived signal value'''
        return value / self.parent.conversion_factor.get()

    def forward(self, value):
        '''Compute derived signal value -> original signal value'''
        return value * self.parent.conversion_factor.get()


class PRPzt(Device):
    """ Phase retarder PZT """

    remote_setpoint = Component(EpicsSignal, 'set_microns.VAL')
    remote_readback = Component(EpicsSignalRO, 'microns')

    localdc = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="DC_read_microns",
        setpoint_pv="DC_set_microns",
        tolerance=0.01
    )

    center = Component(EpicsSignal, 'AC_put_center.A', kind='config')
    offset_degrees = Component(EpicsSignal, 'AC_put_offset.A', kind='config')

    offset_microns = Component(
        MicronsSignal, parent_attr='offset_degrees', kind='config'
    )

    servoon = Component(EpicsSignal, 'servo_ON.PROC', kind='omitted')
    servooff = Component(EpicsSignal, 'servo_OFF.PROC', kind='omitted')
    servostatus = Component(EpicsSignalRO, 'svo', kind='config')

    selectDC = FormattedComponent(
        EpicsSignal,
        '4idaSoft:232DRIO:1:OFF_ch{_prnum}.PROC',
        kind='omitted',
        put_complete=True
    )

    selectAC = FormattedComponent(
        EpicsSignal,
        '4idaSoft:232DRIO:1:ON_ch{_prnum}.PROC',
        kind='omitted',
        put_complete=True
    )

    ACstatus = FormattedComponent(
        EpicsSignal, '4idaSoft:232DRIO:1:status', kind='config'
    )

    conversion_factor = Component(Signal, value=0.1, kind='config')

    def __init__(self, PV, *args, **kwargs):
        self._prnum = PV.split(':')[-2]
        super().__init__(PV, *args, **kwargs)


class PRDeviceBase(PseudoPositioner):

    energy = Component(PseudoSingle, limits=(2.7, 20))
    th = FormattedComponent(
        EpicsMotor, '{prefix}:{_motorsDict[th]}', labels=('motor',)
    )

    # Explicitly selects the real motor
    _real = ['th']

    x = FormattedComponent(
        EpicsMotor, '{prefix}:{_motorsDict[x]}', labels=('motor',)
    )

    y = FormattedComponent(
        EpicsMotor, '{prefix}:{_motorsDict[y]}', labels=('motor',)
    )

    d_spacing = Component(Signal, value=0, kind='config')

    # This offset is used when the motor is used to switch polarization
    offset_degrees = Component(Signal, value=0.0, kind='config')

    tracking = Component(TrackingSignal, value=False, kind='config')

    def __init__(self, prefix, name, motorsDict, **kwargs):
        self._motorsDict = motorsDict
        super().__init__(prefix, name=name, **kwargs)
        self._energy_cid = None

    def convert_energy_to_theta(self, energy):
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = speed_of_light*Planck*6.241509e15*1e10/energy
        theta = arcsin(lamb/2/self.d_spacing.get())*180./pi
        return theta

    def convert_theta_to_energy(self, theta):
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = 2*self.d_spacing.get()*sin(theta*pi/180)
        energy = speed_of_light*Planck*6.241509e15*1e10/lamb
        return energy

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        '''Run a forward (pseudo -> real) calculation'''
        return self.RealPosition(
            th=self.convert_energy_to_theta(pseudo_pos.energy)
            )

    @real_position_argument
    def inverse(self, real_pos):
        '''Run an inverse (real -> pseudo) calculation'''
        return self.PseudoPosition(
            energy=self.convert_theta_to_energy(real_pos.th)
            )

    def set_energy(self, energy):
        # energy in keV, theta in degrees.
        theta = self.convert_energy_to_theta(energy)
        self.th.set_current_position(theta)

    def default_settings(self):
        if self.name == "pr3":
            self.d_spacing.put(3.135)


class PRDevice(PRDeviceBase):

    pzt = FormattedComponent(PRPzt, '{prefix}Soft:E665:{_prnum}:')
    select_pr = FormattedComponent(
        EpicsSignal,
        '{prefix}:PRA{_prnum}',
        string=True,
        auto_monitor=True,
        kind='config'
    )

    def __init__(self, prefix, name, prnum, motorsDict, **kwargs):
        self._prnum = prnum
        super().__init__(prefix, name, motorsDict, **kwargs)

    @select_pr.sub_value
    def _set_d_spacing(self, **kwargs):
        value = self.select_pr.get()
        spacing_dictionary = {'111': 2.0595, '220': 1.26118}
        plane = value.split('(')[1].split(')')[0]
        self.d_spacing.put(spacing_dictionary[plane])

    def default_settings(self):
        conv_factor = 0.00165122 if self._prnum == 1 else 0.00190893
        self.pzt.conversion_factor.put(conv_factor)

        self._set_d_spacing()
