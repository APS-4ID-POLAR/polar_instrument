"""
Beamline energy
"""

from ophyd import Signal, OphydObject
from ophyd.status import Status, AndStatus, wait as status_wait
from time import time as ttime
from pyRestTable import Table
from apsbits.core.instrument_init import oregistry
from collections.abc import Iterable

# Mono is a special device as it's the reference. It will always be tracked.
mono = oregistry("mono")


class EnergySignal(Signal):

    """
    Beamline energy.
    The monochromator defines the beamline energy.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status = {}  # Useful for debugging
        self._extra_devices = []

    @property
    def trackable_devices(self):
        return oregistry.findall("track_energy") + self.extra_devices

    # This is here as an way to force the use of a particular device that may
    # not be tagged with "track_energy". Note that the API requires two
    # subdevices: "device.energy" positioner and "device.tracking" flag.
    @property
    def extra_devices(self):
        return self._extra_devices

    @extra_devices.setter
    def extra_devices(self, devices):
        # Ensure that devices is a list
        devices = list(devices) if isinstance(devices, Iterable) else [devices]

        # Option to clear the extra_devices list if an empty list is given.
        if len(devices) == 0:
            self._extra_devices.clear()
            return

        # Check that all items are OphydObject instances
        for device in devices:
            if not isinstance(device, OphydObject):
                raise ValueError(
                    f"Device {device} is not an instance of OphydObject"
                )

        self._extra_devices.extend(devices)

    @property
    def tracking(self):
        result = Table()
        result.labels = ("Index", "Device", "Tracking?")

        for i, d in enumerate(self.trackable_devices):
            result.rows.append((i+1, d.name, d.tracking.get()))

        print("=== Tracking Status ===")
        print(result.reST(fmt="grid"))
        print("=== note that the monochromator is always tracked ===")

    def tracking_setup(self, devices_names: Iterable = []):

        # Checks needed in case one wants to skip the prompts.

        available_devices = {d.name: d for d in self.trackable_devices}

        # Check that devices_names is a valid iterable.
        if (
            isinstance(devices_names, str)
            or not isinstance(devices_names, Iterable)
        ):
            raise ValueError(
                "devices_names must be an iterable with names of devices to be "
                "tracked. Available names are: "
                f"{', '.join(available_devices.keys())}."
            )

        # Check that the names are in the available devices list.
        if (
            len(devices_names) != 0 and not all(
                name in available_devices.keys() for name in devices_names
            )
        ):
            raise ValueError(
                "Some device names are not available for tracking. Available "
                f"names are: {', '.join(available_devices.keys())}."
            )

        if len(devices_names) == 0:
            self._tracking_prompts()
        else:
            for name, device in available_devices.items():
                flag = True if name in devices_names else False
                device.tracking.put(flag)

    def _tracking_prompts(self):
        self.tracking

        current_selection = []
        for i, device in enumerate(self.trackable_devices):
            if device.tracking.get():
                current_selection.append(i+1)

        while True:
            new_selection = input(
                "Enter the index of the devices to track ("
                f"{' '.join(current_selection)}'): "
            ) or current_selection

            try:
                new_selection = [
                    int(i) for i in new_selection.replace(",", "").split()
                ]
            except ValueError as err:
                raise ValueError(
                    "Invalid input. Please enter comma or space separated list "
                    "of indices corresponding to the devices you wish to track."
                    f"{err}"
                )

            if not all(
                0 < i <= len(self.trackable_devices) for i in new_selection
            ):
                print("Invalid selection. Please choose valid indices.")
                continue

            break

        for i, device in enumerate(self.trackable_devices):
            track = True if i+1 in new_selection else False
            device.tracking.put(track)

        self.tracking

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

    def set(
        self,
        position,
        *,
        wait=False,
        timeout=None,
        settle_time=None,
        moved_cb=None
    ):

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

        # All other devices - PR MAY BE A PROBLEM!
        for d in self.trackable_devices:
            if d.tracking.get():
                offset_device = getattr(d, "energy_offset", None)
                offset = 0 if offset_device is None else offset_device.get()
                d_status = d.energy.set(
                    position + offset,
                    wait=wait,
                    timeout=timeout,
                    moved_cb=moved_cb
                )
                status = AndStatus(status, d_status)
                self._status[d.name] = d_status

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
        for positioner in self.trackable_devices:
            if positioner.tracking.get():
                positioner.energy.stop(success=success)
