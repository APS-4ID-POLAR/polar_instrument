"""
Slits
"""
__all__ = ['wbslt', 'enslt', 'inslt', 'grdslt', 'detslt', 'magslt']

from ophyd import Device, FormattedComponent, EpicsMotor
from apstools.devices import PVPositionerSoftDoneWithStop
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class SlitDevice(Device):

    # Setting motors
    top = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[top]}',
                             labels=('motors', 'slits'))

    bot = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[bot]}',
                             labels=('motors', 'slits'))

    out = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[out]}',
                             labels=('motors', 'slits'))

    inb = FormattedComponent(EpicsMotor, '{prefix}{_motorsDict[inb]}',
                             labels=('motors', 'slits'))

    # Setting pseudo positioners
    vcen = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Vt2.D',
        setpoint_pv='Vcenter.VAL',
        labels=('slits',)
    )

    vsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Vt2.C',
        setpoint_pv='Vsize.VAL',
        labels=('slits',)
    )

    hcen = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Ht2.D',
        setpoint_pv='Hcenter.VAL',
        labels=('slits',)
    )

    hsize = FormattedComponent(
        PVPositionerSoftDoneWithStop,
        '{prefix}{_slit_prefix}',
        readback_pv='Ht2.C',
        setpoint_pv='Hsize.VAL',
        labels=('slits',)
    )

    def __init__(self, PV, name, motorsDict, slitnum, **kwargs):

        self._motorsDict = motorsDict
        self._slit_prefix = f'Slit{slitnum}'

        super().__init__(prefix=PV, name=name, **kwargs)


# White beam slit
wbslt = SlitDevice('4idb:', 'wbslt',
                   {'top': 'm25', 'bot': 'm26', 'out': 'm27', 'inb': 'm28'},
                   1)
sd.baseline.append(wbslt)

# Entrance slit
enslt = SlitDevice('4iddx:', 'enslt',
                   {'top': 'm1', 'bot': 'm2', 'out': 'm3', 'inb': 'm4'},
                   1)
enslt.vcen.tolerance.put(0.003)
enslt.vsize.tolerance.put(0.009)
sd.baseline.append(enslt)

# 8C incident slit
inslt = SlitDevice('4iddx:', 'inslt',
                   {'top': 'm5', 'bot': 'm6', 'out': 'm7', 'inb': 'm11'},
                   2)
sd.baseline.append(inslt)

# 2th guard slit
grdslt = SlitDevice('4iddx:', 'grdslt',
                    {'top': 'm21', 'bot': 'm22', 'out': 'm23', 'inb': 'm24'},
                    3)
sd.baseline.append(grdslt)

# 2th detector slit
detslt = SlitDevice('4iddx:', 'detslt',
                    {'top': 'm25', 'bot': 'm26', 'out': 'm27', 'inb': 'm28'},
                    4)
sd.baseline.append(detslt)

# Magnet incident slit
magslt = SlitDevice('4iddx:', 'magslt',
                    {'top': 'm29', 'bot': 'm30', 'out': 'm31', 'inb': 'm32'},
                    5)
sd.baseline.append(magslt)
