
"""
Utilities
"""

from ophyd import (
    Component, FormattedComponent, Signal, EpicsSignal, EpicsSignalRO,
    PVPositioner
)
from ..session_logs import logger
logger.info(__file__)


class DoneSignal(Signal):
    """ Signal that tracks if two values become the same. """
    def __init__(self, *args, readback_attr='readback',
                 setpoint_attr='setpoint', tolerance_attr='tolerance',
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._readback_attr = readback_attr
        self._setpoint_attr = setpoint_attr
        self._tolerance_attr = tolerance_attr

    def get(self, **kwargs):
        readback = getattr(self.parent, self._readback_attr)
        setpoint = getattr(self.parent, self._setpoint_attr)
        tolerance = getattr(self.parent, self._tolerance_attr)
        if abs(readback.get()-setpoint.get()) <= tolerance:
            self.put(1)
        else:
            self.put(0)
        return self._readback


class TrackingSignal(Signal):
    """ Signal that forces value to be a boolean. """
    def check_value(self, value):
        """
        Check if the value is a boolean.

        Raises
        ------
        ValueError
        """
        if not isinstance(value, bool):
            raise ValueError('tracking is boolean, it can only be True or '
                             'False.')


class PVPositionerSoftDone(PVPositioner):
    """
    PVPositioner that uses an internal "done" signal.

    Parameters
    ----------
    prefix : str, optional
        The device prefix used for all sub-positioners. This is optional as it
        may be desirable to specify full PV names for PVPositioners.
    readback_pv : str, optional
        PV prefix of the readback signal. Disregarded if readback attribute is
        created.
    setpoint_pv : str, optional
        PV prefix of the setpoint signal. Disregarded if setpoint attribute is
        created.
    tolerance : float, optional
        Motion tolerance. The motion is considered done if
        `abs(readback-setpoint) <= tolerance`. Defaults to `10^(-1*precision)`,
        where `precision = setpoint.precision`
    target_attr : str, optional
        Used if the setpoint if incrementally controlled by EPICS (like with a
        ramp). Then a target attribute signal must be defined, and its name
        passed in this variable.
    kwargs :
        Passed to `ophyd.PVPositioner`

    Attributes
    ----------
    setpoint : Signal
        The setpoint (request) signal
    readback : Signal or None
        The readback PV (e.g., encoder position PV)
    actuate : Signal or None
        The actuation PV to set when movement is requested
    actuate_value : any, optional
        The actuation value, sent to the actuate signal when motion is
        requested
    stop_signal : Signal or None
        The stop PV to set when motion should be stopped
    stop_value : any, optional
        The value sent to stop_signal when a stop is requested
    """

    # positioner
    readback = FormattedComponent(EpicsSignalRO, "{prefix}{_readback_pv}",
                                  kind="hinted", auto_monitor=True)
    setpoint = FormattedComponent(EpicsSignal, "{prefix}{_setpoint_pv}",
                                  kind="normal", put_complete=True)
    done = Component(Signal, value=True, kind="config")
    done_value = True

    tolerance = Component(Signal, value=-1, kind="config")
    report_dmov_changes = Component(Signal, value=False, kind="omitted")

    @property
    def precision(self):
        return self.setpoint.precision

    def cb_readback(self, *args, **kwargs):
        """
        Called when readback changes (EPICS CA monitor event).
        """
        diff = self.readback.get() - self._target.get()
        _tolerance = (self.tolerance.get() if self.tolerance.get() >= 0 else
                      10**(-1*self.precision))
        dmov = abs(diff) <= _tolerance
        if self.report_dmov_changes.get() and dmov != self.done.get():
            logger.debug(f"{self.name} reached: {dmov}")
        self.done.put(dmov)

    def cb_setpoint(self, *args, **kwargs):
        """
        Called when setpoint changes (EPICS CA monitor event).
        When the setpoint is changed, force done=False.  For any move,
        done must go != done_value, then back to done_value (True).
        Without this response, a small move (within tolerance) will not return.
        Next update of readback will compute self.done.
        """
        self.done.put(not self.done_value)

    def __init__(self, prefix="", *, readback_pv="", setpoint_pv="",
                 tolerance=None, target_attr="setpoint", **kwargs):

        self._setpoint_pv = setpoint_pv
        self._readback_pv = readback_pv

        super().__init__(prefix=prefix, **kwargs)

        self._target = getattr(self, target_attr)

        # Make the default alias for the readback the name of the
        # positioner itself as in EpicsMotor.
        self.readback.name = self.name

        self.readback.subscribe(self.cb_readback)
        self.setpoint.subscribe(self.cb_setpoint)
        if tolerance:
            self.tolerance.put(tolerance)

    def _setup_move(self, position):
        '''Move and do not wait until motion is complete (asynchronous)'''
        self.log.debug('%s.setpoint = %s', self.name, position)
        self._target.put(position, wait=True)
        if self._target != self.setpoint:
            self.setpoint.put(position, wait=True)
        if self.actuate is not None:
            self.log.debug('%s.actuate = %s', self.name, self.actuate_value)
            self.actuate.put(self.actuate_value, wait=False)
        self.cb_readback()  # This is needed to force the first check.
