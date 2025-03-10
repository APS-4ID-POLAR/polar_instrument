"""
Transfocator
"""

__all__ = ['transfocator']

from ophyd import Device, Component, EpicsMotor
# from bluesky.plan_stubs import mvr
from toolz import partition
from .energy_device import energy as edevice
from ..utils._logging_setup import logger
from ..utils.transfocator_calculation_new import transfocator_calculation

logger.info(__file__)


class TransfocatorClass(Device):
    x = Component(EpicsMotor, "m58", labels=("motor",))
    y = Component(EpicsMotor, "m57", labels=("motor",))
    z = Component(EpicsMotor, "m61", labels=("motor",))
    pitch = Component(EpicsMotor, "m60", labels=("motor",))
    yaw = Component(EpicsMotor, "m59", labels=("motor",))

    lens1 = Component(EpicsMotor, "m62", labels=("motor",))
    lens2 = Component(EpicsMotor, "m63", labels=("motor",))
    lens3 = Component(EpicsMotor, "m64", labels=("motor",))
    lens4 = Component(EpicsMotor, "m65", labels=("motor",))
    lens5 = Component(EpicsMotor, "m66", labels=("motor",))
    lens6 = Component(EpicsMotor, "m67", labels=("motor",))
    lens7 = Component(EpicsMotor, "m68", labels=("motor",))
    lens8 = Component(EpicsMotor, "m69", labels=("motor",))

    def __init__(self, *args, lens_step=30, **kwargs):
        super().__init__(*args, **kwargs)
        self._lens_step = lens_step
        self._default_distance = 2581  # mm

    def lens_status(self, i):
        device = getattr(self, f"lens{i}")
        limits = [device.low_limit_switch.get(), device.high_limit_switch.get()]
        if limits == [1, 1]:
            raise ValueError(f"Both limit swiches of lens{i} are on!")
        elif limits == [1, 0]:
            return "in"
        elif limits == [0, 1]:
            return "out"
        else:  # limits = [0, 0]
            return "unknown"

    @property
    def lenses_in(self):
        selected = []
        for i in range(1, 9):
            _status = self.lens_status(i)
            if _status == "in":
                selected.append(i)
            elif _status == "unknown":
                logger.info(f"WARNING: the status of lens #{i} is unknown.")
        return selected

    def _move_lenses(self, lenses_in: list = [], type="noplan"):
        """
        Adjust lenses

        PARAMETERS
        ----------
        lenses_in : list or iterable
            Index of the lenses that will be inserted. The ones not in this list
            will be removed.
        type : "plan" or "noplan"
            Determines how the lenses will be used, using a bluesky plan
            ("plan" option), or "noplan".
        """

        for i in lenses_in:
            if (i > 8) or (i < 1):
                raise ValueError("Lens index must be from 1 to 8.")

        # Positive/negative step moves lens in/out respectively.
        # We want to move it to the hard limit.

        args = []
        for lens in range(1, 9):
            # If the lens is already in the correct place --> do nothing
            if (
                ((self.lens_status(lens) == "in") and (lens in lenses_in)) or
                ((self.lens_status(lens) == "out") and (lens not in lenses_in))
            ):
                continue

            step_sign = 1 if lens in lenses_in else -1
            args += [
                getattr(self, f"lens{lens}"), step_sign*self._lens_step
            ]

        if type == "plan":
            raise NotImplementedError(
                "plan option not implemented due to problem with limit switches"
            )
            # return (yield from mvr(*args))
        else:
            for dev, pos in partition(2, args):
                dev.user_setpoint.put(dev.position + pos)
            return None

    def set_lenses(self, selected_lenses: list):
        self._move_lenses(selected_lenses, type="noplan")

    # TODO: Need to create plans for these motions, but we are having problems
    # with moving the lenses in EPICS now.

    def _check_z_lims(self, position):
        if (
            (position > self.z.low_limit_travel.get()) & 
            (position < self.z.high_limit_travel.get())
        ):
            return True
        else:
            return False


    def optimize_lenses(
        self,
        energy=None,
        distance=None,
        experiment="diffractometer",
    ):
        lenses, distance = self.calc(
            distance=distance,
            energy=energy,
            experiment=experiment,
            verbose=False
        )

        if not self._check_z_lims(distance):
            raise ValueError(
                f"The distance {distance} is outsize the Z travel range. No motion"
                " will occur."
            )

        self.set_lenses(lenses)
        self.z.move(distance).wait()

    def optimize_distance(
        self,
        energy=None,
        distance=None,
        experiment="diffractometer",
        selected_lenses=None
    ):
        _, distance = self.calc(
            distance=distance,
            energy=energy,
            experiment=experiment,
            distance_only=True,
            selected_lenses=selected_lenses,
            verbose=False
        )

        if not self._check_z_lims(distance):
            raise ValueError(
                f"The distance {distance} is outsize the Z travel range. No motion"
                " will occur."
            )

        self.z.move(distance).wait()

    def calc(
        self,
        distance=None,
        energy=None,
        experiment="diffractometer",
        beamline="polar",
        distance_only=False,
        selected_lenses=None,
        verbose=True
    ):
        if energy is None:
            energy = edevice.get() * 1e3

        if not selected_lenses:
            selected_lenses = self.lenses_in

        if not distance:
            distance = self._default_distance

        return transfocator_calculation(
            distance=distance,
            energy=energy,
            experiment=experiment,
            beamline=beamline,
            distance_only=distance_only,
            selected_lenses=selected_lenses,
            verbose=verbose
        )


transfocator = TransfocatorClass(
    "4idgSoft:", name="transfocator", labels=("4idg", "optics")
)
