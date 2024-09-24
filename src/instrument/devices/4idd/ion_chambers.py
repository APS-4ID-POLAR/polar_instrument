'''
Ion chambers/Photodiodes configuration
'''

__all__ = ['ic1', 'ic2', 'ic3', 'ic4', 'ic5', 'ic6']


from ophyd import Device, Component, FormattedComponent, EpicsMotor, Signal
from ..framework import sd
from apstools.devices import SRS570_PreAmplifier
from .scaler import scalerd
from ..session_logs import logger
logger.info(__file__)


class ICDeviceBase(Device):
    """ Holds basic configuration of ion chambers/photodiodes. """

    # SRS amplifier
    preamp = FormattedComponent(
        SRS570_PreAmplifier,
        '4idd:A{_num}',
        kind='config',
        labels=('preamps', 'detectors',)
    )

    # Scaler channel name
    scaler_name = Component(Signal, value=0, kind='config')

    def __init__(self, prefix, name, scaler_num, preamp_num, **kwargs):
        """
        Parameters
        ----------
        prefix : str
            PV prefix, here for ophyd compatibility, it won't be used.
        name : str
            Unique device name.
        scaler_num : int
            Scaler channel number.
        preamp_num: int
            SRS pre-amplifier number.
        kwargs : dict
            Passed to `ophyd.Device`
        """

        # preamp_num
        self._num = preamp_num

        super().__init__(prefix=prefix, name=name, **kwargs)

        # Scaler channel name
        self.scaler_name.put(
            getattr(scalerd.channels, 'chan{:02d}'.format(scaler_num)).s.name
            )


class ICDevicewMotor(ICDeviceBase):
    """ ICDeviceBase with detector motors """

    # motors
    x = FormattedComponent(EpicsMotor, '4iddx:{_motorx}',
                           labels=('motors', 'detectors'))
    y = FormattedComponent(EpicsMotor, '4iddx:{_motory}',
                           labels=('motors', 'detectors'))

    def __init__(self, prefix, name, motorx, motory, scaler_num, preamp_num,
                 **kwargs):
        """
        Parameters
        ----------
        prefix : str
            PV prefix, here for ophyd compatibility, it won't be used.
        name : str
            Unique device name.
        motorx, motory : str
            PV sufix for the x, y motors.
        scaler_num : int
            Scaler channel number.
        preamp_num: int
            SRS pre-amplifier number.
        kwargs : dict
            Passed to `ophyd.Device`
        """
        self._motorx = motorx
        self._motory = motory
        super().__init__(prefix, name, scaler_num, preamp_num, **kwargs)


ic1 = ICDeviceBase('', 'ic1', 2, 1)
ic2 = ICDeviceBase('', 'ic2', 3, 2)
ic3 = ICDeviceBase('', 'ic3', 4, 3)
ic4 = ICDevicewMotor('', 'ic4', 'm62', 'm61', 5, 4)
ic5 = ICDevicewMotor('', 'ic5', 'm41', 'm43', 6, 5)
ic6 = ICDeviceBase('', 'ic6', 7, 6)

for ic in [ic1, ic2, ic3, ic4, ic5, ic6]:
    sd.baseline.append(ic)
