"""
Lakeshore temperature controllers
"""

__all__ = ['lakeshore336', 'lakeshore340', 'lakeshore340ht']

from .lakeshore336 import LS336Device
from .lakeshore340_old import LS340Device
from ..framework import sd

from ..session_logs import logger
logger.info(__file__)

# Lakeshore 336
lakeshore336 = LS336Device("4idd:LS336:TC3:", name="lakeshore336",
                           labels=("lakeshore",))
lakeshore336.loop1.readback.kind = "normal"
lakeshore336.loop1._auto_ranges = {'LOW': (0, 6), 'MEDIUM': (6, 20),
                                   'HIGH': (20, 305)}
lakeshore336.loop2._auto_ranges = {'LOW': (0, 6), 'MEDIUM': (6, 20),
                                   'HIGH': (20, 305)}

# Lakeshore 340 - Low temperature
lakeshore340 = LS340Device('4idd:LS340:TC1:', name="lakeshore340",
                           labels=("lakeshore",))
lakeshore340.control.readback.kind = "normal"
lakeshore340._auto_ranges = {'10 mA': None, '33 mA': None,
                             '100 mA': (0, 8), '333 mA': (8, 20),
                             '1 A': (20, 305)}

# Lakeshore 340 - High temperature
lakeshore340ht = LS340Device('4idd:LS340:TC2:', name="lakeshore340ht",
                             labels=("lakeshore",))
lakeshore340ht.control.readback.kind = "normal"

sd.baseline.append(lakeshore336)
sd.baseline.append(lakeshore340ht)
sd.baseline.append(lakeshore340)
