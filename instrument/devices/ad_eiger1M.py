""" Eiger 1M setup """

from ophyd import ADComponent, EpicsSignal, Kind
from ophyd.status import Status
from ophyd.areadetector import DetectorBase, EigerDetectorCam, SingleTrigger
from ophyd.areadetector.plugins import(
    PluginBase_V34,
    ImagePlugin_V34,
    PvaPlugin_V34,
    ROIPlugin_V34,
    StatsPlugin_V34,
    CodecPlugin_V34
)
from apstools.devices import (
    AD_EpicsFileNameHDF5Plugin, AD_plugin_primed, AD_prime_plugin2, CamMixin_V34, AD_EpicsHdf5FileName
)
from pathlib import PurePath
from time import time
from .. import iconfig  # noqa
from ..session_logs import logger
logger.info(__file__)

__all__ = ["load_eiger1m"]

BLUESKY_FILES_ROOT = PurePath(iconfig["AREA_DETECTOR"]["BLUESKY_FILES_ROOT"])
IOC_FILES_ROOT = PurePath(iconfig["AREA_DETECTOR"]["EIGER_1M"]["IOC_FILES_ROOT"])
IMAGE_DIR = iconfig["AREA_DETECTOR"].get("IMAGE_DIR", "%Y/%m/%d/")


class PluginMixin(PluginBase_V34):
    """Remove property attribute found in AD IOCs now."""

    _asyn_pipeline_configuration_names = None


class ImagePlugin(PluginMixin, ImagePlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class PvaPlugin(PluginMixin, PvaPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIPlugin(PluginMixin, ROIPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class StatsPlugin(PluginMixin, StatsPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class EigerDetectorCam_V34(CamMixin_V34, EigerDetectorCam):
    """Revise EigerDetectorCam for ADCore revisions."""

    initialize = ADComponent(EpicsSignal, "Initialize", kind="config")

    # These components not found on Eiger 4M at 8-ID-I
    file_number_sync = None
    file_number_write = None
    fw_clear = None
    link_0 = None
    link_1 = None
    link_2 = None
    link_3 = None
    dcu_buff_free = None
    offset = None


# from ophyd.areadetector.plugins import HDF5Plugin_V34 as HDF5Plugin
# from ophyd.areadetector.filestore_mixins import FileStoreHDF5SingleIterativeWrite, FileStoreHDF5Single


# class AD_EpicsHDF5IterativeWriter(AD_EpicsHdf5FileName, FileStoreHDF5Single):
#     pass

# class AD_EpicsFileNameHDF5Plugin(HDF5Plugin, AD_EpicsHDF5IterativeWriter):
#     pass


class EpicsFileNameHDF5Plugin(PluginMixin, AD_EpicsFileNameHDF5Plugin):
    """Remove property attribute not found in AD IOCs now."""

    @property
    def _plugin_enabled(self):
        return self.stage_sigs.get("enable") in (1, "Enable")

    def generate_datum(self, *args, **kwargs):
        if self._plugin_enabled:
            super().generate_datum(*args, **kwargs)

    def read(self):
        if self._plugin_enabled:
            readings = super().read()
        else:
            readings = {}
        return readings

    def stage(self):
        if self._plugin_enabled:
            staged_objects = super().stage()
        else:
            staged_objects = []
        return staged_objects

    def trigger(self):
        if self._plugin_enabled:
            trigger_status = super().trigger()
        else:
            trigger_status = Status(self)
            trigger_status.set_finished()
        return trigger_status


class Eiger1MDetector(SingleTrigger, DetectorBase):
    
    cam = ADComponent(EigerDetectorCam_V34, "cam1:")
    codec1 = ADComponent(CodecPlugin_V34, "Codec1:")
    image = ADComponent(ImagePlugin, "image1:")
    roi1 = ADComponent(ROIPlugin, "ROI1:")
    stats1 = ADComponent(StatsPlugin, "Stats1:")
    pva = ADComponent(PvaPlugin, "Pva1:")

    hdf1 = ADComponent(
        EpicsFileNameHDF5Plugin,
        "HDF1:",
        write_path_template=f"{IOC_FILES_ROOT / IMAGE_DIR}/",
        read_path_template=f"{BLUESKY_FILES_ROOT / IMAGE_DIR}/",
        kind="normal",
    )


def load_eiger1m(prefix="4idEiger:"):

    t0 = time()
    try:
        connection_timeout = iconfig.get("PV_CONNECTION_TIMEOUT", 15)
        eiger1m = Eiger1MDetector(prefix, name="eiger1m")
        eiger1m.wait_for_connection(timeout=connection_timeout)
    except (KeyError, NameError, TimeoutError) as exinfo:
        # fmt: off
        logger.warning(
            "Error connecting with PV='%s in %.2fs, %s",
            prefix, time() - t0, str(exinfo),
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

        plugin = eiger1m.hdf1  # for convenience below
        plugin.kind = Kind.config | Kind.normal  # Ensure plugin's read is called.
        plugin.stage_sigs.move_to_end("capture", last=True)

        if iconfig.get("ALLOW_AREA_DETECTOR_WARMUP", False):
            if eiger1m.connected:
                if not AD_plugin_primed(plugin):
                    AD_prime_plugin2(plugin)

    return eiger1m