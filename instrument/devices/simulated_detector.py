
__all__ = ['simdet']

from ophyd.signal import SignalRO
from numpy.random import default_rng
from ..framework import sd
from ..session_logs import logger
logger.info(__file__)


class RandomDet(SignalRO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gen = default_rng()

    def get(self, **kwargs):
        return self._gen.random()


simdet = RandomDet(name="simdet")
