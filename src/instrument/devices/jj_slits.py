"""
JJ Slits
"""
__all__ = [
    'monoslt'
]

from ophyd import Device, FormattedComponent, EpicsMotor
from apstools.devices import PVPositionerSoftDoneWithStop
from ..utils.run_engine import sd
from ..utils import logger
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
        readback_pv='Vt2.D',
        setpoint_pv='Vcenter.VAL',
    )

    vsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Vt2.C',
        setpoint_pv='Vsize.VAL',
    )

    hcen = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Ht2.D',
        setpoint_pv='Hcenter.VAL',
    )

    hsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Ht2.C',
        setpoint_pv='Hsize.VAL',
    )

    def __init__(self, PV, name, motorsDict, slitnum, **kwargs):

        self._motorsDict = motorsDict
        self._slit_prefix = f'Slit{slitnum}'

        super().__init__(prefix=PV, name=name, **kwargs)


# Mono JJ slit
monoslt = SlitDevice(
    '4idVDCM:',
    'monoslt',
    {'top': 'm1', 'bot': 'm2', 'out': 'm3', 'inb': 'm4'},
    2,
    labels=('slit',)
)
monoslt.vcen.tolerance.put(0.01)
monoslt.vsize.tolerance.put(0.01)
sd.baseline.append(monoslt)
