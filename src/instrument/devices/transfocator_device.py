"""
Transfocator
"""

# __all__ = ['transfocator']

from ophyd import (
    Device,
    Component,
    DynamicDeviceComponent,
    FormattedComponent,
    PVPositioner,
    EpicsMotor,
    EpicsSignal,
    EpicsSignalRO,
    DeviceStatus
)
from bluesky.plan_stubs import mv
from toolz import partition
from .energy_device import energy as edevice
from ..utils._logging_setup import logger
from ..utils.transfocator_calculation_new import transfocator_calculation

logger.info(__file__)

MOTORS_IOC = "4idgSoft:"


def _make_lenses_motors(motors: list):
    defn = {}
    for n, mot in enumerate(motors):
        defn[f"l{n}"] = (
            EpicsMotor, f"{mot}", dict(kind="config", labels=("motor",))
        )
    return defn


class PyCRLSingleLens(PVPositioner):
    readback = Component(EpicsSignalRO, "_RBV")
    setpoint = Component(EpicsSignal, "", put_complete=True)

    done = Component(EpicsSignal, "_matchCalc.C")
    done_value = 1

    # Settings
    num_lenses = Component(EpicsSignal, "_NumLens", kind="config")
    radius = Component(EpicsSignal, "_LensRadius", kind="config")
    location = Component(EpicsSignal, "_Location", kind="config")
    material = Component(EpicsSignal, "_Material", kind="config")
    thickness_error = Component(EpicsSignal, "_ThickErr", kind="config")
    in_limit = Component(EpicsSignal, "_RBV_calc.CC", kind="config")

    def set(
        self,
        new_position,
        *,
        timeout: float = None,
        moved_cb=None,
        wait: bool = False,
    ):
        if self.readback.get() == new_position:
            _status = DeviceStatus(self)
            _status.set_finished()
            return _status
        else:
            return super().set(
                new_position, timeout=timeout, moved_cb=moved_cb, wait=wait
            )


class PyCRLSignal(EpicsSignal):
    value = Component(EpicsSignal, "")
    egu = Component(EpicsSignalRO, ".EGU")


class PyCRL(Device):

    # Energy
    energy_mono = Component(PyCRLSignal, "EnergyBeamline", kind="config")
    energy_local = Component(PyCRLSignal, "EnergyLocal", kind="config")
    energy_select = Component(PyCRLSignal, "EnergySelect", kind="config")

    # Slits
    slit_hor_size = Component(PyCRLSignal, "1:slitSize_H_RBV", kind="config")
    slit_hor_pv = Component(
        EpicsSignal, "1:slitSize_H.DOL", string=True, kind="config"
    )
    slit_vert_size = Component(PyCRLSignal, "1:slitSize_V_RBV", kind="config")
    slit_vert_pv = Component(
        EpicsSignal, "1:slitSize_V.DOL", string=True, kind="config"
    )

    # Focus info/control
    focal_size_setpoint = Component(EpicsSignal, "focalSize")
    focal_size_readback = Component(EpicsSignalRO, "fSize_actual")
    focal_power_index_setpoint = Component(EpicsSignal, "1:sortedIndex")
    focal_power_index_readback = Component(EpicsSignal, "1:sortedIndex_RBV")

    # Parameters readbacks
    dq = Component(PyCRLSignal, "dq", kind="config")
    q = Component(PyCRLSignal, "q", kind="config")
    z_offset = Component(PyCRLSignal, "1:oePositionOffset_RBV", kind="config")
    z_offset_pv = Component(
        EpicsSignal, "1:oePositionOffset.DOL", kind="config"
    )
    z_from_source = Component(PyCRLSignal, "1:oePosition_RBV", kind="config")
    sample_offset = Component(
        PyCRLSignal, "samplePositionOffset_RBV", kind="config"
    )
    sample_offset_pv = Component(
        EpicsSignal, "samplePositionOffset.DOL", kind="config"
    )
    sample = Component(PyCRLSignal, "samplePosition_RBV", kind="config")

    # Lenses indices
    binary = Component(EpicsSignalRO, "1:lenses", kind="config")
    ind_control = Component(EpicsSignalRO, "1:lensConfig_BW", kind="config")
    readbacks = Component(EpicsSignalRO, "1:lensConfig_RBV", kind="config")

    # Other options
    preview_index = Component(EpicsSignal, "previewIndex", kind="config")
    focal_size_preview = Component(
        EpicsSignalRO, "fSize_preview", kind="config"
    )
    inter_lens_delay = Component(EpicsSignal, "1:interLensDelay", kind="config")
    verbose_console = Component(EpicsSignal, "verbosity", kind="config")
    thickness_error_flag = Component(
        EpicsSignal, "thickerr_flag", kind="config"
    )

    # Lenses
    lens1 = Component(PyCRLSingleLens, "1:stack01")
    lens2 = Component(PyCRLSingleLens, "1:stack02")
    lens3 = Component(PyCRLSingleLens, "1:stack03")
    lens4 = Component(PyCRLSingleLens, "1:stack04")
    lens5 = Component(PyCRLSingleLens, "1:stack05")
    lens6 = Component(PyCRLSingleLens, "1:stack06")
    lens7 = Component(PyCRLSingleLens, "1:stack07")
    lens8 = Component(PyCRLSingleLens, "1:stack08")


class TransfocatorClass(PyCRL):

    # Motors -- setup in 4idgSoft
    x = FormattedComponent(EpicsMotor, "{_motors_IOC}m58", labels=("motor",))
    y = FormattedComponent(EpicsMotor, "{_motors_IOC}m57", labels=("motor",))
    z = FormattedComponent(EpicsMotor, "{_motors_IOC}m61", labels=("motor",))
    pitch = FormattedComponent(
        EpicsMotor, "{_motors_IOC}m60", labels=("motor",)
    )
    yaw = FormattedComponent(EpicsMotor, "{_motors_IOC}m59", labels=("motor",))

    lens_motors = DynamicDeviceComponent(
        _make_lenses_motors(
            [
                f"{MOTORS_IOC}m69",
                f"{MOTORS_IOC}m68",
                f"{MOTORS_IOC}m67",
                f"{MOTORS_IOC}m66",
                f"{MOTORS_IOC}m65",
                f"{MOTORS_IOC}m64",
                f"{MOTORS_IOC}m63",
                f"{MOTORS_IOC}m62"
            ]
        ),
        component_class=FormattedComponent
    )

    def __init__(
            self, *args, lens_pos=30, default_distance=2591, **kwargs
    ):
        self._motors_IOC = MOTORS_IOC
        PyCRL.__init__(self, *args, **kwargs)
        self._lens_pos = lens_pos
        self._default_distance = default_distance  # mm

    def lens_status(self, i):
        return getattr(self, f"lens{i}").readback.get(as_string=True)

    @property
    def lenses_in(self):
        selected = []
        for i in range(1, 9):
            _status = self.lens_status(i)
            if _status == "In":
                selected.append(i)
            elif _status == "Both out":
                pass
                # logger.info(f"WARNING: the status of lens #{i} is unknown.")
        return selected

    def _setup_lenses_move(self, lenses_in: list = []):
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
            step = 1 if lens in lenses_in else 0
            args += [
                getattr(self, f"lens{lens}"), step
            ]

        return args

    def set_lenses(self, selected_lenses: list):
        args = self._setup_lenses_move(selected_lenses)
        for dev, pos in partition(2, args):
            dev.setpoint.put(pos)

    def set_lenses_plan(self, selected_lenses: list):
        args = self._setup_lenses_move(selected_lenses)
        return (yield from mv(*args))

    def _check_z_lims(self, position):
        if (
            (position > self.z.low_limit_travel.get()) &
            (position < self.z.high_limit_travel.get())
        ):
            return True
        else:
            return False

    def _setup_optimize_lenses(
        self,
        energy=None,
        optimize_position=None,
        reference_distance=None,
        experiment="diffractometer",
    ):

        lenses, distance = self.calc(
            energy=energy,
            optimize_position=optimize_position,
            reference_distance=reference_distance,
            experiment=experiment,
            verbose=False
        )

        if not self._check_z_lims(distance):
            raise ValueError(
                f"The distance {distance} is outsize the Z travel range. No"
                "motion will occur."
            )

        return lenses, distance

    def optimize_lenses(
        self,
        energy=None,
        optimize_position=0,
        reference_distance=None,
        experiment="diffractometer",
    ):
        lenses, distance = self._setup_optimize_lenses(
            energy=energy,
            optimize_position=optimize_position,
            reference_distance=reference_distance,
            experiment=experiment,
        )

        self.set_lenses(lenses)
        self.z.move(distance).wait()

    def optimize_lenses_plan(
        self,
        energy=None,
        optimize_position=0,
        reference_distance=None,
        experiment="diffractometer",
    ):
        lenses, distance = self._setup_optimize_lenses(
            energy=energy,
            optimize_position=optimize_position,
            reference_distance=reference_distance,
            experiment=experiment,
        )
        args = self._setup_lenses_move(lenses)
        return (yield from mv(self.z, distance, *args))

    def _setup_optimize_distance(
        self,
        energy=None,
        experiment="diffractometer",
        selected_lenses=None,
    ):
        _, distance = self.calc(
            energy=energy,
            experiment=experiment,
            distance_only=True,
            selected_lenses=selected_lenses,
            verbose=False
        )

        if not self._check_z_lims(distance):
            raise ValueError(
                f"The distance {distance} is outsize the Z travel range. No"
                "motion will occur."
            )

        return distance

    def optimize_distance(
        self,
        energy=None,
        selected_lenses=None,
        experiment="diffractometer",
    ):
        distance = self._setup_optimize_distance(
            energy=energy,
            experiment=experiment,
            selected_lenses=selected_lenses
        )

        self.z.move(distance).wait()

    def optimize_distance_plan(
        self,
        energy=None,
        experiment="diffractometer",
        selected_lenses=None,
    ):
        distance = self._setup_optimize_distance(
            energy=energy,
            experiment=experiment,
            selected_lenses=selected_lenses,
        )

        return (yield from mv(self.z, distance))

    def calc(
        self,
        optimize_position=None,
        reference_distance=None,
        energy=None,
        experiment="diffractometer",
        distance_only=False,
        selected_lenses=None,
        verbose=True
    ):
        if energy is None:
            energy = edevice.get()

        if selected_lenses is None:
            selected_lenses = self.lenses_in

        if reference_distance is None:
            reference_distance = self._default_distance

        if optimize_position is None:
            optimize_position = 0

        return transfocator_calculation(
            energy,
            optimize_position=optimize_position,
            reference_distance=reference_distance,
            experiment=experiment,
            distance_only=distance_only,
            selected_lenses=selected_lenses,
            verbose=verbose
        )


transfocator = TransfocatorClass(
    "4idPyCRL:CRL4ID:", name="transfocator", labels=("4idg", "optics")
)
