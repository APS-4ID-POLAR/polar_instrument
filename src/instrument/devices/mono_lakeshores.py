"""
Mono Lakeshores
"""

__all__ = ['mono_lakeshore_1', 'mono_lakeshore_2']

from apstools.devices import LakeShore336Device
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)

mono_lakeshore_1 = LakeShore336Device(
    "4idaSoft:LS336:TC1:",
    name="mono_lakeshore_1",
    labels=("lakeshore",)
)

mono_lakeshore_2 = LakeShore336Device(
    "4idaSoft:LS336:TC2:",
    name="mono_lakeshore_2",
    labels=("lakeshore",)
)

sd.baseline.append(mono_lakeshore_1)
sd.baseline.append(mono_lakeshore_2)
