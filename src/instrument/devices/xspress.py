""" Eiger 1M setup """

from ophyd import ADComponent, Staged, Component, EpicsSignalRO, Device, EpicsSignal
from ophyd.status import Status
from ophyd.areadetector import DetectorBase, EpicsSignalWithRBV
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
from pathlib import Path
from time import time as ttime, sleep
from .ad_mixins import (
    ROIPlugin,
    AttributePlugin,
    ROIStatPlugin,
    PolarHDF5Plugin,
    VortexDetectorCam,
    AD_plugin_primed_vortex,
    AD_prime_plugin2_vortex
)
from ..utils.config import iconfig
from ..utils._logging_setup import logger
logger.info(__file__)

__all__ = ["load_vortex"]

# Bluesky and IOC have the same path root.
# BLUESKY_FILES_ROOT = PurePath(iconfig["AREA_DETECTOR"]["VORTEX"]["BLUESKY_FILES_ROOT"])
IOC_FILES_ROOT = Path(iconfig["AREA_DETECTOR"]["VORTEX"]["IOC_FILES_ROOT"])

DEFAULT_FOLDER = Path(iconfig["AREA_DETECTOR"]["VORTEX"]["DEFAULT_FOLDER"])

HDF1_NAME_TEMPLATE = iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"]
HDF1_FILE_EXTENSION = iconfig["AREA_DETECTOR"]["HDF5_FILE_EXTENSION"]
HDF1_NAME_FORMAT = HDF1_NAME_TEMPLATE + "." + HDF1_FILE_EXTENSION

MAX_IMAGES = 12216


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
        self._flysetup = False
        self._status = None
        self._collect_image = False

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Internal"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"

    def setup_external_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "TTL Veto Only"
        self.cam.stage_sigs["num_images"] = MAX_IMAGES
        self.cam.stage_sigs["wait_for_plugins"] = "No"

    def stage(self):

        self.cam.erase.set(1).wait(timeout=10)

        if self._flysetup:
            self.setup_external_trigger()

        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self._collect_image = True

        # Make sure that detector is not armed.
        self._acquisition_signal.set(0).wait(timeout=10)
        self._acquire_busy_signal.subscribe(self._acquire_changed)

        super().stage()

        if self._flysetup:
            self._acquisition_signal.set(1).wait(timeout=10)

    def unstage(self):
        super().unstage()
        self.cam.acquire.set(0).wait(timeout=10)
        self._flysetup = False
        self._acquire_busy_signal.clear_sub(self._acquire_changed)
        self._collect_image = False
        self.setup_manual_trigger()

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        # Click the Acquire_button
        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        if self._collect_image:
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


class ROIStatN(Device):
    roi_name = Component(EpicsSignal, "Name", kind="config")
    use = Component(EpicsSignal, "Use", kind="config")

    max_sizex = Component(EpicsSignalRO, "MaxSizeX_RBV", kind="config")
    roi_startx = Component(EpicsSignalWithRBV, "MinY", kind="config")
    roi_sizex = Component(EpicsSignalWithRBV, "SizeY", kind="config")

    max_sizey = Component(EpicsSignalRO, "MaxSizeY_RBV", kind="config")
    roi_startxy = Component(EpicsSignalWithRBV, "MinY", kind="config")
    roi_sizey = Component(EpicsSignalWithRBV, "SizeY", kind="config")

    bdg_width = Component(EpicsSignalWithRBV, "BgdWidth", kind="config")
    min_value = Component(EpicsSignalRO, "MinValue_RBV", kind="normal")
    max_value = Component(EpicsSignalRO, "MaxValue_RBV", kind="normal")
    mean_value = Component(EpicsSignalRO, "MeanValue_RBV", kind="normal")
    total_value = Component(EpicsSignalRO, "Total_RBV", kind="normal")
    net_value = Component(EpicsSignalRO, "Net_RBV", kind="normal")

    reset_button = Component(EpicsSignal, "Reset", kind="omitted")


class VortexROIStatPlugin(ROIStatPlugin):
    #ROIs
    roi1 = Component(ROIStatN, "1:")
    roi2 = Component(ROIStatN, "2:")
    roi3 = Component(ROIStatN, "3:")
    roi4 = Component(ROIStatN, "4:")
    roi5 = Component(ROIStatN, "5:")
    roi6 = Component(ROIStatN, "6:")
    roi7 = Component(ROIStatN, "7:")
    roi8 = Component(ROIStatN, "8:")

    def _status_done(self):

        # Create status that checks when the SCA updates.
        status = Status(self.time_stamp, settle_time=0.01)

        def _set_finished(**kwargs):
            status.set_finished()
            self.time_stamp.clear_sub(_set_finished)

        self.time_stamp.subscribe(_set_finished, event_type='value', run=False)

        return status


class VortexSCA(AttributePlugin):
    clock_ticks = Component(EpicsSignalRO,'0:Value_RBV')
    reset_ticks = Component(EpicsSignalRO,'1:Value_RBV')
    reset_counts = Component(EpicsSignalRO,'2:Value_RBV')
    all_events = Component(EpicsSignalRO,'3:Value_RBV')
    all_good = Component(EpicsSignalRO,'4:Value_RBV')
    window1 = Component(EpicsSignalRO,'5:Value_RBV')
    window2 = Component(EpicsSignalRO,'6:Value_RBV')
    pileup = Component(EpicsSignalRO,'7:Value_RBV')
    event_width = Component(EpicsSignalRO, '8:Value_RBV')
    dt_factor = Component(EpicsSignalRO,'9:Value_RBV')
    dt_percent = Component(EpicsSignalRO,'10:Value_RBV')


class VortexDetector(Trigger, DetectorBase):

    _default_configuration_attrs = ('cam', 'chan1', 'chan2', 'chan3', 'chan4')
    _default_read_attrs = (
        'hdf1',
        'stats1',
        'stats2',
        'stats3',
        'stats4',
        'sca1',
        'sca2',
        'sca3',
        'sca4'
    )

    cam = ADComponent(VortexDetectorCam, "det1:")
    
    chan1 = ADComponent(ROIPlugin, "ROI1:")
    chan2 = ADComponent(ROIPlugin, "ROI2:")
    chan3 = ADComponent(ROIPlugin, "ROI3:")
    chan4 = ADComponent(ROIPlugin, "ROI4:")

    stats1 = ADComponent(VortexROIStatPlugin, "MCA1ROI:")
    stats2 = ADComponent(VortexROIStatPlugin, "MCA2ROI:")
    stats3 = ADComponent(VortexROIStatPlugin, "MCA3ROI:")
    stats4 = ADComponent(VortexROIStatPlugin, "MCA4ROI:")

    sca1 = ADComponent(VortexSCA, "C1SCA:")
    sca2 = ADComponent(VortexSCA, "C2SCA:")
    sca3 = ADComponent(VortexSCA, "C3SCA:")
    sca4 = ADComponent(VortexSCA, "C4SCA:")
    
    hdf1 = ADComponent(
        PolarHDF5Plugin,
        "HDF1:",
        ioc_path_root=IOC_FILES_ROOT,
    )

    VORTEX_SLEEP = 5

    # Make this compatible with other detectors
    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.trigger_mode.set("Internal").wait(timeout=10)
        self.cam.num_images.set(MAX_IMAGES).wait(timeout=10)
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

        self.hdf1.file_template.put(HDF1_NAME_FORMAT)
        self.hdf1.file_path.put(str(DEFAULT_FOLDER))
        self.hdf1.num_capture.put(0)

        self.cam.trigger_mode.put("Internal")
        self.cam.acquire.put(0)

        self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
        self.hdf1.stage_sigs["capture"] = 1
    
        self.setup_manual_trigger()
        self.save_images_off()
        self.plot_roi1()

        self.stage_sigs.pop("cam.image_mode")
        self.cam.stage_sigs["erase_on_start"] = "No"

        # t0 = ttime()
        # while ttime() - t0 < self.VORTEX_SLEEP:
        for component in self.component_names:
            try:
                logger.info(f"Connecting to {component}")
                getattr(self, component).wait_for_connection(all_signals=True, timeout=10)
                logger.info(f"Connecting to {component}")
                if "blocking_callbacks" in getattr(self, component).stage_sigs.keys():
                    getattr(self, component).stage_sigs["blocking_callbacks"] = "No"
            except AttributeError:
                pass




        for component in self.component_names:
            try:
                logger.info(f"Connecting to {component}")
                getattr(self, component).wait_for_connection(all_signals=True, timeout=10)
                logger.info(f"Connecting to {component}")
                if "blocking_callbacks" in getattr(self, component).stage_sigs.keys():
                    getattr(self, component).stage_sigs["blocking_callbacks"] = "No"
            except AttributeError:
                pass

    def plot_roi1(self):
        # TODO: This is just temporary to have something.
        self.stats1.roi1.total_value.kind="hinted"

    def setup_images(
            self, file_name_base, file_number, flyscan=False
        ):

        self.hdf1.file_name.set(file_name_base).wait(timeout=10)
        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.auto_save_on()
        self._flysetup = flyscan

        _, full_path, relative_path = self.hdf1.make_write_read_paths()

        return Path(full_path), Path(relative_path)


def load_vortex(prefix="S4QX4:"):

    t0 = ttime()
    try:
        connection_timeout = iconfig.get("OPHYD", {}).get("TIMEOUTS", {}).get(
            "PV_CONNECTION", 15
        )
        logger.info("Connecting to vortex")
        detector = VortexDetector(prefix, name="vortex")
        logger.info("Waiting for connection")
        detector.wait_for_connection(timeout=connection_timeout)
        logger.info("Connected")
    except (KeyError, NameError, TimeoutError) as exinfo:
        # fmt: off
        logger.warning(
            "Error connecting with PV='%s in %.2fs, %s",
            prefix, ttime() - t0, str(exinfo),
        )
        logger.warning("Setting eiger1m to 'None'.")
        detector = None
        # fmt: on

    else:
        prime = iconfig.get("AREA_DETECTOR", {}).get("VORTEX", {})
        if prime.get("ALLOW_PLUGIN_WARMUP", False):
            if detector.connected:
                if not AD_plugin_primed_vortex(detector.hdf1):
                    logger.info("Priming HDF1 plugin")
                    AD_prime_plugin2_vortex(detector.hdf1)

        logger.info("Loading default settings")

        detector.VORTEX_SLEEP = 60

        detector.default_settings()

        # Sometimes we get errors that bluesky gets the wrong value (just the first)
        # character. This should fix it.
        for component in "file_path file_name file_template".split():
            _ = getattr(detector.hdf1, component).get(use_monitor=False)

    return detector
