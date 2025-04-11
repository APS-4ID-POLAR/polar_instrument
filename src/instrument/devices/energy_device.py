"""
Beamline energy
"""
__all__ = ['energy']

from ophyd import Signal
from ophyd.status import Status, AndStatus, wait as status_wait
from time import time as ttime
from .monochromator import mono
from .aps_undulator import undulators
from .phaseplates import pr1, pr2, pr3
from .transfocator_device import transfocator
from ..utils._logging_setup import logger
logger.info(__file__)


class EnergySignal(Signal):

    """
    Beamline energy.
    Here it is setup so that the monochromator is the beamline energy, but note
    that this can be changed.
    """
    
    # Useful for debugging.
    _status = {}

    @property
    def position(self):
        return mono.energy.position

    @property
    def limits(self):
        return mono.energy.limits

    def get(self, **kwargs):
        """ Uses the mono as the standard beamline energy. """
        self._readback = mono.energy.readback.get(**kwargs)
        return self._readback

    def set(self, position, *, wait=False, timeout=None, settle_time=None,
            moved_cb=None):

        # In case nothing needs to be moved, just create a finished status
        status = Status()
        status.set_finished()

        old_value = self._readback

        # Mono
        mono_status = mono.energy.set(
            position, wait=wait, timeout=timeout, moved_cb=moved_cb
        )
        status = AndStatus(status, mono_status)
        self._status = {mono.name: mono_status}

        # Phase retarders
        for pr in [pr1, pr2, pr3]:
            if pr.tracking.get():
                pr_status = pr.energy.move(
                    position, wait=wait, timeout=timeout, moved_cb=moved_cb
                )
                status = AndStatus(status, pr_status)
                self._status[pr.name] = pr_status

        # Undulator
        for und in [undulators.us, undulators.ds]:
            if und.tracking.get():
                und_pos = position + und.offset.get()
                und_status = und.energy.set(
                    und_pos, wait=wait, timeout=timeout, moved_cb=moved_cb
                )
                status = AndStatus(status, und_status)
                self._status[und.name] = und_status

        # Transfocator
        if transfocator.tracking.get():
            tstatus = transfocator.energy.set(
                position, wait=wait, timeout=timeout, moved_cb=moved_cb
            )
            status = AndStatus(status, tstatus)
            self._status[transfocator.name] = tstatus

        if wait:
            status_wait(status)

        md_for_callback = {'timestamp': ttime()}
        self._run_subs(
            sub_type=self.SUB_VALUE,
            old_value=old_value,
            value=position,
            **md_for_callback
        )

        return status

    def stop(self, *, success=False):
        """
        Stops only energy devices that are tracking.
        """
        mono.energy.stop(success=success)
        for positioner in [pr1, pr2, pr3, undulators.ds, undulators.us]:
            if positioner.tracking.get():
                positioner.energy.stop(success=success)


energy = EnergySignal(
    name='energy', value=10, kind='hinted', labels=("energy",)
)
