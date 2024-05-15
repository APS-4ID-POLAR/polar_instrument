""" AD mixins """

from ophyd import ADComponent, EpicsSignal, Signal
from ophyd.areadetector import EigerDetectorCam
from ophyd.areadetector.plugins import(
    PluginBase_V34,
    ImagePlugin_V34,
    PvaPlugin_V34,
    ROIPlugin_V34,
    StatsPlugin_V34,
    CodecPlugin_V34,
    HDF5Plugin_V34
)
from ophyd.areadetector.filestore_mixins import FileStoreBase
from apstools.devices import CamMixin_V34
from pathlib import PurePath
from os.path import isfile
from datetime import datetime
from itertools import count
from .. import iconfig  # noqa
from ..session_logs import logger
logger.info(__file__)

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


class CodecPlugin(PluginMixin, CodecPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class EigerDetectorCam(CamMixin_V34, EigerDetectorCam):
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


class FileStorePluginBaseEpicsName(FileStoreBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "create_directory"):
            self.stage_sigs.update({"create_directory": -3})
        self.stage_sigs.update(
            [
                ("auto_increment", "Yes"),
                ("array_counter", 0),
                ("auto_save", "Yes"),
                ("num_capture", 0),
            ]
        )
        self._fn = None
        self._fp = None

    # This is the part to change if a different file scheme is chosen.
    def make_write_read_paths(self):
        # Folders - this allows for using dates for folders.
        formatter = datetime.now().strftime
        write_path = formatter(self.write_path_template)
        read_path = formatter(self.read_path_template)

        # File name -- assumes some sort of %s%s_5.5%d.h5 format
        file_read = self.file_template.get() % (
            read_path,
            self.file_name.get(),
            int(self.file_number.get())
        )

        file_write = self.file_template.get() % (
            write_path + "/",
            self.file_name.get(),
            int(self.file_number.get())
        )

        return write_path, file_write, read_path, file_read

    def stage(self):

        # Only save images if the enable is on...
        if self.enable.get() in (True, 1, "on", "Enable"):

            if self.file_write_mode.get(as_string=True) != "Single":
                self.capture.set(0).wait()
            
            write_path, file_write, read_path, file_read = self.make_write_read_paths()

            if isfile(file_write):
                raise OSError(
                    f"{file_write} already exists! Cannot overwrite it, so please "
                    "change the file name."
                )

            self.file_path.set(write_path).wait()
            super().stage()

            self._fn = file_read
            self._fp = read_path
            if not self.file_path_exists.get():
                raise IOError(
                    "Path %s does not exist on IOC." "" % self.file_path.get()
                )


class FileStoreHDF5IterativeWriteEpicsName(FileStorePluginBaseEpicsName):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = "AD_HDF5"  # spec name stored in resource doc
        self.stage_sigs.update(
            [
                ("file_template", "%s%s_%6.6d.h5"),
                ("file_write_mode", "Stream"),
                ("capture", 1),
            ]
        )
        self._point_counter = None

    def get_frames_per_point(self):
        num_capture = self.num_capture.get()
        # If num_capture is 0, then the plugin will capture however many frames
        # it is sent. We can get how frames it will be sent (unless
        # interrupted) by consulting num_images on the detector's camera.
        if num_capture == 0:
            return self.parent.cam.num_images.get()
        # Otherwise, a nonzero num_capture will cut off capturing at the
        # specified number.
        return num_capture

    def stage(self):
        super().stage()
        res_kwargs = {"frame_per_point": self.get_frames_per_point()}
        self._generate_resource(res_kwargs)
        self._point_counter = count()

    def unstage(self):
        self._point_counter = None
        super().unstage()

    def generate_datum(self, key, timestamp, datum_kwargs):
        i = next(self._point_counter)
        datum_kwargs = datum_kwargs or {}
        datum_kwargs.update({"point_number": i})
        return super().generate_datum(key, timestamp, datum_kwargs)


class HDF5Plugin(PluginMixin, HDF5Plugin_V34):
    pass


class EigerHDF5Plugin(HDF5Plugin, FileStoreHDF5IterativeWriteEpicsName):

    """
    Using the filename from EPICS.
    """

    autosave = ADComponent(Signal, value="off", kind="config")

    def __init__(self, *args, write_path_template="", **kwargs):
        # self.filestore_spec = "AD_EIGER_APSPolar"
        super().__init__(*args, write_path_template=write_path_template, **kwargs)
        self.enable.subscribe(self._setup_kind)

    def _setup_kind(self, value, **kwargs):
        if value in (True, 1, "on", "Enable"):
            self.kind = "normal"
        else:
            self.kind = "omitted"

    def stage(self):
        if self.autosave.get() in (True, 1, "on", "Enable"):
            self.parent.save_images_on()
        super().stage()

    def unstage(self):
        if self.autosave.get() in (True, 1, "on", "Enable"):
            self.parent.save_images_off()
        super().unstage()
