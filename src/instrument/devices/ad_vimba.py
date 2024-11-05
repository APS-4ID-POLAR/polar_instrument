"""
Vimba cameras
"""

__all__ = ["flag_camera_4idb"]

from ophyd import EpicsSignal, EpicsSignalRO, Staged
from ophyd.areadetector import (
    CamBase, DetectorBase, ADComponent, EpicsSignalWithRBV
)
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
from pathlib import Path
from time import time as ttime
from .ad_mixins import PolarHDF5Plugin, StatsPlugin, ROIPlugin
from ..utils.config import iconfig
from ..utils._logging_setup import logger
logger.info(__file__)


ad_iconfig = iconfig["AREA_DETECTOR"]
HDF1_NAME_TEMPLATE = ad_iconfig["HDF5_FILE_TEMPLATE"]
HDF1_FILE_EXTENSION = ad_iconfig["HDF5_FILE_EXTENSION"]
HDF1_NAME_FORMAT = HDF1_NAME_TEMPLATE + "." + HDF1_FILE_EXTENSION

vimba_iconfig = ad_iconfig["VIMBA"]
IOC_FILES_ROOT = Path(vimba_iconfig["IOC_FILES_ROOT"])
DEFAULT_FOLDER = IOC_FILES_ROOT / vimba_iconfig["RELATIVE_DEFAULT_FOLDER"]

MAX_IMAGES = 65535


class Trigger(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name
        self._acquisition_signal = self.cam.acquire
        self._acquire_busy_signal = self.cam.acquire_busy
        # self._flysetup = False
        self._status = None

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["image_mode"] = "Single"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"

    def setup_external_trigger(self):
        # Stage signals
        # self.cam.stage_sigs["trigger_mode"] = "TTL Veto Only"
        # self.cam.stage_sigs["num_images"] = MAX_IMAGES
        # self.cam.stage_sigs["wait_for_plugins"] = "No"
        raise NotImplementedError(
            f"Cannot use external trigger with the {self.name} detector."
        )

    def stage(self):

        self.cam.erase.set(1).wait(timeout=10)

        # if self._flysetup:
        #     self.setup_external_trigger()

        # Make sure that detector is not armed.
        self._acquisition_signal.set(0).wait(timeout=10)
        self._acquire_busy_signal.subscribe(self._acquire_changed)

        super().stage()

        # if self._flysetup:
        #     self._acquisition_signal.set(1).wait(timeout=10)

    def unstage(self):
        super().unstage()
        self.cam.acquire.set(0).wait(timeout=10)
        # self._flysetup = False
        self._acquire_busy_signal.clear_sub(self._acquire_changed)
        self.setup_manual_trigger()

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        # Click the Acquire_button
        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self.generate_datum(self._image_name, ttime(), {})

        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire_busy' signal changes."

        if self._status is None:
            return
        if (old_value != 0) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            # sleep(self._delay)
            self._status.set_finished()
            self._status = None


class VimbaCam(CamBase):
    # NOTE: There are A LOT of camera-specific EPICS features that are not added
    # here.
    pool_max_buffers = None

    # PV exists, but not used.
    num_exposures = ADComponent(EpicsSignalRO, "NumExposures")  

    # Trigger
    trigger_source = ADComponent(
        EpicsSignalWithRBV, "TriggerSource", string=True
    )
    trigger_overlap = ADComponent(
        EpicsSignalWithRBV, "TriggerOverlap", string=True
    )
    trigger_exposure_mode = ADComponent(
        EpicsSignalWithRBV, "ExposureMode", string=True
    )
    trigger_button = ADComponent(
        EpicsSignal, "TriggerSoftware", kind="omitted"
    )

    # Exposure
    exposure_auto = ADComponent(
        EpicsSignalWithRBV, "ExposureAuto", string=True
    )
    frame_rate = ADComponent(
        EpicsSignalWithRBV, "FrameRate", string=True
    )
    image_mode = ADComponent(
        EpicsSignalWithRBV, "ImageMode", string=True
    )

    # Detector state
    acquire_busy = ADComponent(EpicsSignal, "AcquireBusy")
    wait_for_plugins = ADComponent(EpicsSignal, "WaitForPlugins", string=True)

    # Detector Status
    frames_delivered = ADComponent(EpicsSignalRO, "GC_StatFrameDelivered_RBV")
    frames_dropped = ADComponent(EpicsSignalRO, "GC_StatFrameDropped_RBV")
    frames_underrun = ADComponent(EpicsSignalRO, "GC_StatFrameUnderrun_RBV")
    packets_received = ADComponent(EpicsSignalRO, "GC_StatPacketReceived_RBV")
    packets_missed = ADComponent(EpicsSignalRO, "GC_StatPacketMissed_RBV")
    packets_errors = ADComponent(EpicsSignalRO, "GC_StatPacketErrors_RBV")
    packets_requested = ADComponent(EpicsSignalRO, "GC_StatPacketRequested_RBV")
    packets_resent = ADComponent(EpicsSignalRO, "GC_StatPacketResent_RBV")
    poll_features = ADComponent(EpicsSignal, "ReadStatus.SCAN", string=True)
    temperature = ADComponent(EpicsSignalRO, "TemperatureActual")

    # Gain
    gain_auto = ADComponent(
        EpicsSignalWithRBV, "GainAuto", string=True
    )


class VimbaDetector(Trigger, DetectorBase):

    _default_configuration_attrs = (
        'cam', 'roi1', 'roi2', 'roi3', 'roi4'
    )
    _default_read_attrs = (
        'hdf1', 'stats1', 'stats2', 'stats3', 'stats4',
    )

    cam = ADComponent(VimbaCam, "cam1:")
    hdf1 = ADComponent(PolarHDF5Plugin, "HDF1:")

    roi1 = ADComponent(ROIPlugin, "ROI1:")
    roi2 = ADComponent(ROIPlugin, "ROI2:")
    roi3 = ADComponent(ROIPlugin, "ROI3:")
    roi4 = ADComponent(ROIPlugin, "ROI4:")

    stats1 = ADComponent(StatsPlugin, "Stats1:")
    stats2 = ADComponent(StatsPlugin, "Stats2:")
    stats3 = ADComponent(StatsPlugin, "Stats3:")
    stats4 = ADComponent(StatsPlugin, "Stats4:")

    # Make this compatible with other detectors
    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.num_images.set(MAX_IMAGES).wait(timeout=10)
        self.cam.trigger_mode.set("Continuous").wait(timeout=10)
        self.preset_monitor.set(time).wait(timeout=10)
        self.cam.acquire.set(1).wait(timeout=10)

    def align_off(self):
        """Stop detector"""
        self.cam.acquire.set(0).wait(timeout=10)

    def save_images_on(self):
        self.hdf1.enable.set("Enable").wait(timeout=10)

    def save_images_off(self):
        self.hdf1.enable.set("Disable").wait(timeout=10)

    def auto_save_on(self):
        self.hdf1.autosave.put("on")

    def auto_save_off(self):
        self.hdf1.autosave.put("off")

    def default_settings(self):

        self.cam.num_images.put(1)
        self.cam.trigger_mode.put("Single")
        self.cam.acquire.put(0)

        self.hdf1.file_template.put(HDF1_NAME_FORMAT)
        self.hdf1.file_path.put(str(DEFAULT_FOLDER))
        self.hdf1.num_capture.put(0)

        self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
        self.hdf1.stage_sigs["capture"] = 1

        self.setup_manual_trigger()
        self.save_images_off()
        self.plot_roi1()

    def plot_roi1(self):
        self.stats1.total.kind = "hinted"

    def setup_images(
            self, base_path, name_template, file_number, flyscan=False
    ):

        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.hdf1.file_name.set(name_template).wait(timeout=10)
        # Make sure eiger will save image
        self.auto_save_on()
        # Changes the stage_sigs to the external trigger mode
        self._flysetup = flyscan

        base_path = str(base_path) + f"/{self.name}/"

        _, full_path, relative_path = self.hdf1.make_write_read_paths(base_path)

        return Path(full_path), Path(relative_path)

    @property
    def save_image_flag(self):
        _hdf1_auto = True if self.hdf1.autosave.get() == "on" else False
        _hdf1_on = True if self.hdf1.enable.get() == "Enable" else False
        return _hdf1_on or _hdf1_auto


flag_camera_4idb = VimbaDetector(
    "4idbPostToroBeam:", name="flag_camera_4idb", labels=("camera",)
)
