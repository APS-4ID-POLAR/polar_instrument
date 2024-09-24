"""
APS only: connect with facility information
"""

__all__ = ['undulator']

from apstools.devices import (
    ApsMachineParametersDevice, ApsUndulator, TrackingSignal
)
from ..framework import sd
from ophyd import (Device, Component, Signal, EpicsSignal, EpicsSignalRO,
                   PVPositioner)
from ophyd.status import Status, wait as status_wait
from ophyd.utils import InvalidState
from threading import Thread
from ..session_logs import logger
logger.info(__file__)

aps = ApsMachineParametersDevice(name="aps")
sd.baseline.append(aps)


class UndulatorEnergy(PVPositioner):
    """
    Undulator energy positioner.

    Always move the undulator to final position from the high to low energy
    direction, by applying a backlash (hysteresis) correction as needed.
    """

    # Position
    readback = Component(EpicsSignalRO, 'Energy', kind='hinted',
                         auto_monitor=True)
    setpoint = Component(EpicsSignal, 'EnergySet', put_complete=True,
                         auto_monitor=True, kind='normal')

    # Configuration
    deadband = Component(Signal, value=0.002, kind='config')
    backlash = Component(Signal, value=0.25, kind='config')
    offset = Component(Signal, value=0, kind='config')

    # Buttons
    actuate = Component(EpicsSignal, "Start.VAL", kind='omitted',
                        put_complete=True)
    actuate_value = 3

    stop_signal = Component(EpicsSignal, "Stop.VAL", kind='omitted')
    stop_value = 1

    done = Component(EpicsSignal, "Busy.VAL", kind="omitted")
    done_value = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tolerance = 0.002
        self.readback.subscribe(self.done.get)
        self.setpoint.subscribe(self.done.get)
        self._status_obj = Status(self)

        # Make the default alias for the readback the name of the
        # positioner itself as in EpicsMotor.
        self.readback.name = self.name

    @deadband.sub_value
    def _change_tolerance(self, value=None, **kwargs):
        if value:
            self.tolerance = value

    def move(self, position, wait=True, **kwargs):
        """
        Moves the undulator energy.

        Currently, the backlash has to be handled within Bluesky. The actual
        motion is done by `self._move` using threading. kwargs are passed to
        PVPositioner.move().

        Parameters
        ----------
        position : float
            Position to move to
        wait : boolean, optional
            Flag to block the execution until motion is completed.

        Returns
        -------
        status : Status
        """

        self._status_obj = Status(self)

        # If position is in the the deadband -> do nothing.
        if abs(position - self.readback.get()) <= self.tolerance:
            self._status_obj.set_finished()

        # Otherwise -> let's move!
        else:
            thread = Thread(target=self._move, args=(position,),
                            kwargs=kwargs)
            thread.start()

        if wait:
            status_wait(self._status_obj)

        return self._status_obj

    def _move(self, position, **kwargs):
        """
        Moves undulator.

        This is meant to run using threading, so the move will block by
        construction.
        """

        # Applies backlash if needed.
        if position > self.readback.get():
            self._move_and_wait(position + self.backlash.get(), **kwargs)

        # Check if stop was requested during first part of the motion.
        if not self._status_obj.done:
            self._move_and_wait(position, **kwargs)
            self._finish_status()

    def _move_and_wait(self, position, **kwargs):
        status = super().move(position, wait=False, **kwargs)
        status_wait(status)

    def _finish_status(self):
        try:
            self._status_obj.set_finished()
        except InvalidState:
            pass

    def stop(self, *, success=False):
        super().stop(success=success)
        self._finish_status()


class MyUndulator(ApsUndulator):
    """
    Undulator setup.

    Differences from `apstools` standard:
    - `energy` is a PVPositioner.
    - `start_button`, `stop_button` and `device_status` go into `energy`.
    - Has a flag used to track the mono energy.
    - Has an interactive undulator_setup.
    """

    energy = Component(UndulatorEnergy, '')
    tracking = Component(TrackingSignal, value=False, kind='config')

    start_button = None
    stop_button = None
    device_status = None

    def undulator_setup(self):
        """Interactive setup of usual undulator parameters."""
        while True:
            _tracking = input("Do you want to track the undulator energy? "
                              "(yes/no): ")
            if _tracking == 'yes':
                self.tracking.put(True)
                break
            elif _tracking == 'no':
                self.tracking.put(False)
            else:
                print("Only yes or no are valid answers.")

        if _tracking == 'yes':
            while True:
                _offset = input("Undulator offset (keV) ({:0.3f}): ".format(
                    self.energy.offset.get()))
                try:
                    self.energy.offset.put(float(_offset))
                    break
                except ValueError:
                    if _offset == '':
                        print('Using offset = {:0.3f} keV'.format(
                            self.energy.offset.get()))
                        break
                    else:
                        print("The undulator offset has to be a number.")


class MyDualUndulator(Device):
    """ 4-ID has two undulators, we use only the downstream. """
    upstream = None
    downstream = Component(MyUndulator, 'ds:')


undulator = MyDualUndulator("ID04", name="undulator")
sd.baseline.append(undulator)
