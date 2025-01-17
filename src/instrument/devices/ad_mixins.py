""" AD mixins """

from ophyd import ADComponent, EpicsSignal, Signal, Component, BlueskyInterface
from ophyd.areadetector import (
    EigerDetectorCam, Xspress3DetectorCam, EpicsSignalWithRBV
)
from ophyd.areadetector.plugins import (
    PluginBase_V34,
    ImagePlugin_V34,
    PvaPlugin_V34,
    ROIPlugin_V34,
    StatsPlugin_V34,
    CodecPlugin_V34,
    HDF5Plugin_V34,
    ROIStatPlugin_V34,
    ROIStatNPlugin_V25,
    AttributePlugin_V34,
)
from ophyd.areadetector.filestore_mixins import FileStoreBase
from apstools.devices import CamMixin_V34
from os.path import isfile
from itertools import count
from time import sleep
from collections import OrderedDict
from pathlib import Path
from ..utils.config import iconfig
from ..utils._logging_setup import logger
logger.info(__file__)


USE_DM_PATH = iconfig["DM_USE_PATH"]
DM_ROOT_PATH = iconfig["DM_ROOT_PATH"]


class PluginMixin(PluginBase_V34):
    """Remove property attribute found in AD IOCs now."""

    _asyn_pipeline_configuration_names = None


class ImagePlugin(PluginMixin, ImagePlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class PvaPlugin(PluginMixin, PvaPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIPlugin(PluginMixin, ROIPlugin_V34):
    """Remove property attribute found in AD IOCs now."""
    _default_configuration_attrs = (
        ROIPlugin_V34._default_configuration_attrs + (
            "driver_version",
            "data_type",
            "color_mode",
            "enable",
            "enable_scale",
            "scale",
            "collapse_dims",
            'dimensions',
            'data_type_out',
            'name_',
            'roi_enable',
            'bin_',
            'min_xyz',
            'size',
            'reverse',
        )
    )


class StatsPlugin(PluginMixin, StatsPlugin_V34):
    """Remove property attribute found in AD IOCs now."""
    _default_configuration_attrs = (
        StatsPlugin_V34._default_configuration_attrs + (
            'array_size',
            'blocking_callbacks',
            'color_mode',
            'data_type',
            'dimensions',
            'enable',
            'driver_version',
            'compute_statistics',
            'bgd_width',
            'compute_centroid',
            'centroid_threshold',
            'compute_profiles',
            'profile_average',
            'profile_centroid',
            'profile_cursor',
            'profile_size',
            'profile_threshold',
            'cursor',
            'compute_histogram',
            'hist_entropy',
            'hist_max',
            'hist_min',
            'hist_size',
            'histogram',
            'hist_above',
            'hist_below',
            'histogram_x',
        )
    )

    _default_read_attrs = (
        StatsPlugin_V34._default_read_attrs + (
            'max_value',
            'max_xy.x',
            'max_xy.y',
            'mean_value',
            'min_value',
            'min_xy.x',
            'min_xy.y',
            'net',
            'total',
            'centroid.x',
            'centroid.y',
            'sigma_xy',
            'sigma.x',
            'sigma.y',
            'orientation',
            'kurtosis',
            'skew',
            'centroid_total',
            'eccentricity',
        )
    )


class CodecPlugin(PluginMixin, CodecPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIStatPlugin(PluginMixin, ROIStatPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIStatNPlugin(PluginMixin, ROIStatNPlugin_V25):
    """Remove property attribute found in AD IOCs now."""


class AttributePlugin(PluginMixin, AttributePlugin_V34):
    """Remove property attribute found in AD IOCs now."""
    ts_acquiring = None
    ts_control = None
    ts_current_point = None
    ts_num_points = None
    ts_read = None


class EigerDetectorCam(CamMixin_V34, EigerDetectorCam):
    """Revise EigerDetectorCam for ADCore revisions."""

    initialize = ADComponent(EpicsSignal, "Initialize", kind="config")
    counting_mode = ADComponent(EpicsSignal, "CountingMode", kind="config")

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


class VortexDetectorCam(CamMixin_V34, Xspress3DetectorCam):
    trigger_mode = Component(EpicsSignalWithRBV, "TriggerMode", kind="config")
    erase_on_start = Component(
        EpicsSignal, "EraseOnStart", string=True, kind="config"
    )

    # Removed
    offset = None
    num_exposures = None
    acquire_period = None


class FileStorePluginBaseEpicsName(FileStoreBase):

    def __init__(self, *args, ioc_path_root=None, **kwargs):
        super().__init__(*args, **kwargs)
        # if hasattr(self, "create_directory"):
        #     self.stage_sigs.update({"create_directory": -3})
        self.stage_sigs.update(
            [
                ("create_directory", -3),
                ("auto_increment", "Yes"),
                ("array_counter", 0),
                ("auto_save", "Yes"),
                ("num_capture", 0),
            ]
        )
        # This is needed if you want to start bluesky and run a no-image scan
        # first.
        self._fn = None
        self._fp = None
        self._use_dm = USE_DM_PATH
        self._ioc_path_root = ioc_path_root

    @property
    def use_dm(self):
        return self._use_dm

    @use_dm.setter
    def use_dm(self, value):
        if isinstance(value, bool):
            self._use_dm = value
        else:
            raise ValueError(
                f"use_dm must be set to True or False, but {value} was entered."
            )

    def make_write_read_paths(self, path=None):
        # This will generate the folder name and the full path.
        # - Folder is either determined by data management, or just use the one
        # in EPICS.
        # - File name uses everything from EPICS (template, base name and file
        # number).

        # Setting up the path.
        # If not using DM, it will simply take the values from EPICS!!
        if path is None:
            path = Path(self.file_path.get())

        # Create full path based on EPICS file template - assumes some sort of
        # %s%s_5.5%d.h5 format
        full_path = self.file_template.get() % (
            str(path) + "/",
            self.file_name.get(),
            int(self.file_number.get())
        )

        relative_path = self.file_template.get() % (
            f"{self.parent.name}/",
            self.file_name.get(),
            int(self.file_number.get())
        )

        return str(path), full_path, relative_path

    def stage(self):

        # Only save images if the enable is on...
        if self.enable.get() in (True, 1, "on", "Enable"):

            if self.file_write_mode.get(as_string=True) != "Single":
                self.capture.set(0).wait()

            path, full_path, _ = self.make_write_read_paths()

            if isfile(full_path):
                raise OSError(
                    f"{full_path} already exists! Cannot overwrite it, so "
                    "please change the file name."
                )

            if not self.file_path_exists.get():
                raise IOError(
                    f"Path {self.file_path.get()} does not exist on IOC."
                )

            self.file_path.set(path).wait(timeout=10)

            super().stage()

            self._fn = full_path
            self._fp = full_path


class FileStoreHDF5IterativeWriteEpicsName(FileStorePluginBaseEpicsName):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = "AD_HDF5"  # spec name stored in resource doc
        self.stage_sigs.update(
            [
                ("file_template", "%s%s_%6.6d.h5"),
                ("file_write_mode", "Stream"),
                ("capture", 0),  # TODO: Is this true for the EIGER???? --> NO!
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
        if self._fn is None:
            self._fn = self.reg_root
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


class PolarHDF5Plugin(HDF5Plugin, FileStoreHDF5IterativeWriteEpicsName):

    """
    Using the filename from EPICS.
    """
    _default_configuration_attrs = HDF5Plugin._default_configuration_attrs + (
            'auto_increment',
            'auto_save',
            'file_format',
            'file_name',
            'file_number',
            'file_path',
            'file_path_exists',
            'file_template',
            'file_write_mode',
            'array_size',
            'color_mode',
            'data_type',
            'dimensions',
            'enable',
            'plugin_type',
            'compression',
            'szip_num_pixels',
            'store_attr',
            'store_perform',
            'zlevel',
            'xml_file_name',
            'swmr_active',
            'swmr_cb_counter',
            'swmr_mode',
            'swmr_supported',
            'driver_version',
            'blosc_compressor',
            'blosc_level',
            'blosc_shuffle',
            'autosave'
    )
    _default_read_attrs = HDF5Plugin._default_read_attrs + ('full_file_name',)

    autosave = ADComponent(Signal, value="off", kind="config")

    def __init__(self, *args, write_path_template="", **kwargs):
        # self.filestore_spec = "AD_EIGER_APSPolar"
        super().__init__(
            *args, write_path_template=write_path_template, **kwargs
        )
        # self.enable.subscribe(self._setup_kind, run=False)

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


def AD_plugin_primed_vortex(plugin):
    """
    Modification of the APS AD_plugin_primed for Vortex.

    Uses the timestamp = 0 as a sign of an unprimed plugin. Not sure this is
    generic.
    """

    return plugin.time_stamp.get() != 0


def AD_prime_plugin2_vortex(plugin):
    """
    Modification of the APS AD_plugin_primed for Vortex.

    Some area detectors PVs are not setup in the Vortex.
    """
    if AD_plugin_primed_vortex(plugin):
        logger.debug("'%s' plugin is already primed", plugin.name)
        return

    sigs = OrderedDict(
        [
            (plugin.enable, 1),
            (plugin.parent.cam.array_callbacks, 1),  # set by number
            (plugin.parent.cam.image_mode, 0),  # Single, set by number
            # Trigger mode names are not identical for every camera.
            # Assume here that the first item in the list is
            # the best default choice to prime the plugin.
            (plugin.parent.cam.trigger_mode, 1),  # set by number
            # just in case the acquisition time is set very long...
            (plugin.parent.cam.acquire_time, 1),
            (plugin.parent.cam.acquire, 1),  # set by number
        ]
    )

    original_vals = {sig: sig.get() for sig in sigs}

    for sig, val in sigs.items():
        sleep(0.1)  # abundance of caution
        sig.set(val).wait()

    sleep(2)  # wait for acquisition

    for sig, val in reversed(list(original_vals.items())):
        sleep(0.1)
        sig.set(val).wait()


class TriggerBase(BlueskyInterface):
    """Base class for trigger mixin classes

    Subclasses must define a method with this signature:

    ``acquire_changed(self, value=None, old_value=None, **kwargs)``
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # settings
        # careful here: quadEM devices have areadetector components but,
        # they have no 'cam' plugin. See QuadEM initializer.
        if hasattr(self, "cam"):
            self.stage_sigs.update(
                [
                    ("cam.acquire", 0),  # If acquiring, stop
                    ("cam.image_mode", 1),  # 'Multiple' mode
                ]
            )
            self._acquisition_signal_pv = "cam.acquire"
            self._acquire_busy_signal_pv = "cam.acquire_busy"

        self._status = None

    @property
    def _acquisition_signal(self):
        getattr(self, self._acquisition_signal_pv)

    @property
    def _acquire_busy_signal(self):
        getattr(self, self._acquire_busy_signal_pv)
