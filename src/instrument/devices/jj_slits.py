"""
JJ Slits
"""
__all__ = [
    'monoslt'
]

from ophyd import Device, FormattedComponent, EpicsMotor
from apstools.devices import PVPositionerSoftDoneWithStop
from ..utils._logging_setup import logger
logger.info(__file__)


class SlitDevice(Device):

    # Setting motors
    top = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[top]}',
                             labels=('motor',))

    bot = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[bot]}',
                             labels=('motor',))

    out = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[out]}',
                             labels=('motor',))

    inb = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[inb]}',
                             labels=('motor',))

    # Setting pseudo positioners
    vcen = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='V:t2.D',
        setpoint_pv='V:center.VAL',
    )

    vsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='V:t2.C',
        setpoint_pv='V:size.VAL',
    )

    hcen = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='H:t2.D',
        setpoint_pv='H:center.VAL',
    )

    hsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='H:t2.C',
        setpoint_pv='H:size.VAL',
    )

    def __init__(self, PV, name, motorsDict, slitnum, **kwargs):

        self._motorsDict = motorsDict
        self._slit_prefix = f'Slit{slitnum}'

        super().__init__(prefix=PV, name=name, **kwargs)


# Mono JJ slit
monoslt = SlitDevice(
    '4idVDCM:',
    'monoslt',
    {'top': 'm14', 'bot': 'm13', 'out': 'm16', 'inb': 'm15'},
    2,
    labels=('slit',)
)
monoslt.vcen.tolerance.put(0.01)
monoslt.vsize.tolerance.put(0.01)
