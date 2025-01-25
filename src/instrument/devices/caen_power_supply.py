"""
Caen power supply
"""

# WARNING: THIS IS A TEMPORARY SETUP WHILE WE DON'T HAVE THE EPICS SUPPORT #

__all__ = ["pscaen"]

try:
    from caen_libs import caenhvwrapper as hv
except RuntimeError as excerror:
    print(
        "WARNING: could not find the CAEN library, please add the path to the "
        "LD_LIBRARY_PATH to the environment variables."
    )
    raise RuntimeError(excerror)

from ophyd import Component, Signal, SignalRO
from ophyd.status import Status
from apstools.devices import PVPositionerSoftDoneWithStop

DEVICE = hv.Device.open(
    hv.SystemType["SMARTHV"], hv.LinkType["TCPIP"], "10.54.115.56"
)


class CaenSignal(Signal):
    def __init__(self, *args, channel=0, param_name="VMon", **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = channel
        self._param = param_name

    def get(self, **kwargs):
        return DEVICE.get_ch(0, [self._channel], self._param)[0]

    def put(self, value, **kwargs):
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"file_path needs to be a number, but {type(value)} was "
                "entered."
            )
        DEVICE.set_ch_param(0, [self._channel], self._param, value)

    def set(self, value, **kwargs):
        self.put(value, **kwargs)
        # Do not check completion.
        st = Status()
        st.set_finished()
        return st


class CaenSignalRO(SignalRO):
    def __init__(self, *args, channel=0, param_name="VSet", **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = channel
        self._param = param_name

    def get(self, **kwargs):
        return DEVICE.get_ch(0, [self._channel], self._param)[0]


class CaenDevice(PVPositionerSoftDoneWithStop):
    readback = Component(CaenSignalRO)
    setpoint = Component(CaenSignal)

    def __init__(self, *args, channel=0, **kwargs):
        super().__init__(**args, tolerance=0.5, **kwargs)
        self.readback._channel = channel
        self.setpoint._channel = channel
        self.timeout = 120
        self.settle_time = 5


pscaen = CaenDevice("", name="caenps")
