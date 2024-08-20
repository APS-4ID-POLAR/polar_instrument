""" Eiger 1M setup """

from ophyd import ADComponent, Staged
from ophyd.status import wait as status_wait, SubscriptionStatus
from ophyd.areadetector import DetectorBase
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
from apstools.devices import AD_plugin_primed, AD_prime_plugin2
from apstools.utils import run_in_thread
from pathlib import PurePath
from time import time as ttime, sleep
from .ad_mixins import (
    EigerDetectorCam,
    CodecPlugin,
    ImagePlugin,
    ROIPlugin,
    StatsPlugin,
    PvaPlugin,
    EigerHDF5Plugin
)
from .. import iconfig  # noqa
from ..session_logs import logger
logger.info(__file__)

__all__ = ["load_eiger1m"]

BLUESKY_FILES_ROOT = PurePath(iconfig["AREA_DETECTOR"]["BLUESKY_FILES_ROOT"])
IOC_FILES_ROOT = PurePath(iconfig["AREA_DETECTOR"]["EIGER_1M"]["IOC_FILES_ROOT"])
IMAGE_DIR = iconfig["AREA_DETECTOR"].get("IMAGE_DIR", "%Y/%m/%d/")


class TriggerTime(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, min_period=0.2, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name
        self._acquisition_signal = self.cam.special_trigger_button
        self._min_period = min_period
        self._flysetup = False

    @property
    def min_period(self):
        return self._min_period

    @min_period.setter
    def min_period(self, value):
        try:
            self._min_period = float(value)
        except ValueError:
            raise ValueError("min_period must be a number.")

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Internal Enable"
        self.cam.stage_sigs["manual_trigger"] = "Enable"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["num_exposures"] = 1
        # TODO: I don't like this too much, would prefer that we set this for each scan.
        self.cam.stage_sigs["num_triggers"] = int(1e5)

    def setup_external_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "External Enable"
        self.cam.stage_sigs["manual_trigger"] = "Disable"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["num_exposures"] = 1
        # TODO: We may not need this.
        self.cam.stage_sigs["num_triggers"] = int(1e6)

    def stage(self):
        if self._flysetup:
            self.setup_external_trigger()

        # Make sure that detector is not armed.
        self.cam.acquire.set(0).wait(timeout=10)
        super().stage()
        self.cam.acquire.set(1).wait(timeout=10)

    def unstage(self):
        super().unstage()
        self.cam.acquire.set(0).wait(timeout=10)

        def check_value(*, old_value, value, **kwargs):
            "Return True when detector is done"
            return (value == "Ready" or value == "Acquisition aborted")

        # When stopping the detector, it may take some time processing the images.
        # This will block until it's done.
        status_wait(
            SubscriptionStatus(
                self.cam.status_message, check_value, timeout=10
            )
        )
        self._flysetup = False
        self.setup_manual_trigger()

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        @run_in_thread
        def add_delay(status_obj, min_period):
            count_time = self.cam.acquire_time.get()
            total_sleep = count_time if count_time > min_period else min_period
            sleep(total_sleep)
            status_obj.set_finished()

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self.generate_datum(self._image_name, ttime(), {})
        add_delay(self._status, self._min_period)
        return self._status


class Eiger1MDetector(TriggerTime, DetectorBase):

    _default_configuration_attrs = ('roi1', 'codec1', 'image', 'pva')
    _default_read_attrs = ('cam', 'hdf1', 'stats1')
    
    cam = ADComponent(EigerDetectorCam, "cam1:")
    codec1 = ADComponent(CodecPlugin, "Codec1:")
    image = ADComponent(ImagePlugin, "image1:")
    roi1 = ADComponent(ROIPlugin, "ROI1:")
    stats1 = ADComponent(StatsPlugin, "Stats1:", kind="normal")
    pva = ADComponent(PvaPlugin, "Pva1:")

    hdf1 = ADComponent(
        EigerHDF5Plugin,
        "HDF1:",
        write_path_template=f"{IOC_FILES_ROOT / IMAGE_DIR}/",
        read_path_template=f"{BLUESKY_FILES_ROOT / IMAGE_DIR}/",
    )

    # Make this compatible with other detectors
    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.manual_trigger.set("Disable").wait(timeout=10)
        self.cam.num_triggers.set(int(1e6)).wait(timeout=10)
        self.cam.trigger_mode.set("Internal Enable").wait(timeout=10)
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
        self.cam.num_triggers.put(1)
        self.cam.manual_trigger.put("Disable")
        self.cam.trigger_mode.put("Internal Enable")
        self.cam.acquire.put(0)

        self.hdf1.file_template.put("%s%s_%6.6d.h5")
        self.hdf1.num_capture.put(0)

        self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
    
        self.setup_manual_trigger()
        self.save_images_off()
        self.plot_roi1()

    def plot_roi1(self):
        self.stats1.total.kind="hinted"


def load_eiger1m(prefix="4idEiger:"):

    t0 = ttime()
    try:
        connection_timeout = iconfig.get("PV_CONNECTION_TIMEOUT", 15)
        eiger1m = Eiger1MDetector(prefix, name="eiger1m")
        eiger1m.wait_for_connection(timeout=connection_timeout)
    except (KeyError, NameError, TimeoutError) as exinfo:
        # fmt: off
        logger.warning(
            "Error connecting with PV='%s in %.2fs, %s",
            prefix, ttime() - t0, str(exinfo),
        )
        logger.warning("Setting eiger1m to 'None'.")
        eiger1m = None
        # fmt: on

    else:
        # just in case these things are not defined in the class source code
        eiger1m.cam.stage_sigs["wait_for_plugins"] = "Yes"
        for nm in eiger1m.component_names:
            obj = getattr(eiger1m, nm)
            if "blocking_callbacks" in dir(obj):  # is it a plugin?
                obj.stage_sigs["blocking_callbacks"] = "No"

        if iconfig.get("ALLOW_AREA_DETECTOR_WARMUP", False):
            if eiger1m.connected:
                if not AD_plugin_primed(eiger1m.hdf1):
                    AD_prime_plugin2(eiger1m.hdf1)

        eiger1m.default_settings()

        # Sometimes we get errors that bluesky gets the wrong value (just the first)
        # character. This should fix it.
        for component in "file_path file_name file_template".split():
            _ = getattr(eiger1m.hdf1, component).get(use_monitor=False)

    return eiger1m
