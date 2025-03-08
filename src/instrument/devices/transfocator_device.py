"""
Transfocator
"""

__all__ = ['transfocator']

from ophyd import Device, Component, EpicsMotor
# from bluesky.plan_stubs import mvr
from toolz import partition
from .energy_device import energy as edevice
from ..utils._logging_setup import logger
from ..utils.transfocator_calculation import transfocator_calc

logger.info(__file__)


class TranfocatorClass(Device):
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

    @property
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

    def __init__(self, *args, lens_step=30, **kwargs):
        super().__init__(*args, **kwargs)
        self._lens_step = lens_step

    def _move_lenses(self, lenses: list, type="noplan"):
        if len(lenses) != 8:
            raise ValueError("Lenses must be an iterable with length=8.")

        # Positive/negative step moves lens in/out respectively.
        # We want to move it to the hard limit.

        args = []
        for i, lens in enumerate(lenses):
            # If the lens is already in the correct place --> do nothing
            if (
                ((self.lens_status(i) == "in") and (lens == 1)) or
                ((self.lens_status(i) == "out") and (lens == 0))
            ):
                continue

            step_sign = 1 if lens == 1 else -1
            args += [
                getattr(self, f"lens{i}"), step_sign*self._lens_step
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

    def set_lenses(self, lenses: list):
        self._move_lenses(lenses, type="noplan")

    # TODO: Need to create plans for these motions, but we are having problems
    # with moving the lenses in EPICS now.

    def optimize_lenses(
        self,
        energy=None,
        distance=2581,
        experiment="diffractometer",
        beamline="polar"
    ):
        lenses, distance = self.calc(
            distance=distance,
            energy=energy,
            experiment=experiment,
            beamline=beamline,
            verbose=False
        )

        self.set_lenses(lenses)
        self.z.move(distance).wait()

    def calc(
        self,
        distance=None,
        energy=None,
        experiment="diffractometer",
        beamline="polar",
        verbose=True
    ):
        if energy is None:
            energy = edevice.get() * 1e3

        return transfocator_calc(
            distance=distance,
            energy=energy,
            experiment=experiment,
            beamline=beamline,
            verbose=verbose
        )


transfocator = TranfocatorClass(
    "4idgSoft:", name="transfocator", labels=("4idg", "optics")
)
