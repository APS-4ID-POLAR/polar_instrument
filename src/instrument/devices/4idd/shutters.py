
"""
Shutters
"""
__all__ = ["status4id", "ashutter", "bshutter", "dshutter"]

from ..framework import sd
from apstools.devices import ApsPssShutterWithStatus
from ..session_logs import logger
from ophyd import (
    Component, EpicsSignal, FormattedComponent, EpicsSignalRO, Device
)
logger.info(__file__)


class PolarShutter(ApsPssShutterWithStatus):

    open_signal = Component(EpicsSignal, "OPEN_REQUEST")
    close_signal = Component(EpicsSignal, "CLOSE_REQUEST")

    # Extra info
    user_enable = FormattedComponent(
        EpicsSignalRO, "PA:04ID:{self._hutch}_USER_KEY"
    )
    aps_enable = FormattedComponent(
        EpicsSignalRO, "PA:04ID:{self._hutch}_APS_KEY"
    )
    searched = FormattedComponent(
        EpicsSignalRO, "PA:04ID:{self._hutch}_SEARCHED"
    )
    bleps = FormattedComponent(
        EpicsSignalRO, "{self._bleps_pv}"
    )

    def __init__(self, prefix, state_pv, hutch, *args, timeout=20, **kwargs):

        # this is very specific to 4ID
        self._hutch = hutch
        if hutch == "A":
            self._bleps_pv = "4ideps:A_TRIP_EXISTS"
        elif hutch in ["B", "D"]:
            self._bleps_pv = f"PC:04ID:S{hutch}S_BLEPS_PERMIT"
        else:
            raise ValueError(
                f"Invalid hutch {hutch}. It must to be 'A', 'B' or 'D'"
            )
        self._timeout = timeout
        super().__init__(prefix, state_pv, *args, **kwargs)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = float(value)

    def open(self):
        super().open(timeout=self.timeout)

    def close(self):
        super().close(timeout=self.timeout)


class Status4ID(Device):
    online = Component(
        EpicsSignalRO, "PA:04ID:ACIS_GLOBAL_ONLINE.VAL", string=True
    )
    acis = Component(
        EpicsSignalRO, "PA:04ID:ACIS_FES_PERMIT.VAL", string=True
    )
    feeps = Component(
        EpicsSignalRO, "PC:04ID:FEEPS_FES_PERMIT.VAL", string=True
    )


status4id = Status4ID("", name="status4id")
ashutter = PolarShutter(
    "PC:04ID:FES_", "PA:04ID:A_BEAM_PRESENT", hutch="A", name="ashutter"
)
bshutter = PolarShutter(
    "PC:04ID:SBS_", "PA:04ID:B_BEAM_PRESENT", hutch="B", name="bshutter"
)
dshutter = PolarShutter(
    "PC:04ID:SDS_", "PA:04ID:D_BEAM_PRESENT", hutch="D", name="dshutter"
)

sd.baseline.extend((status4id, ashutter, bshutter, dshutter))
