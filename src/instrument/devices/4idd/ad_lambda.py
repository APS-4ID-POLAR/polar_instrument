"""
Lambda area detector
"""

from ophyd import ADComponent, EpicsSignalRO, Kind, Staged
from ophyd.areadetector import (
    CamBase, EpicsSignalWithRBV, DetectorBase, TriggerBase
)
from ophyd.areadetector.trigger_mixins import ADTriggerStatus
from ophyd.areadetector.filestore_mixins import (
    FileStoreHDF5SingleIterativeWrite
)
from ophyd.areadetector.plugins import (
        ROIPlugin_V34, StatsPlugin_V34, HDF5Plugin_V34, CodecPlugin_V34,
        ProcessPlugin_V34
)
from os.path import join
import time as ttime


LAMBDA_FILES_ROOT = "/extdisk/4idd/"
BLUESKY_FILES_ROOT = "/home/sector4/4idd/bluesky_images"
TEST_IMAGE_DIR = "%Y/%m/%d/"


class MySingleTrigger(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    Examples
    --------
    >>> class SimDetector(SingleTrigger):
    ...     pass
    >>> det = SimDetector('..pv..')
    # optionally, customize name of image
    >>> det = SimDetector('..pv..', image_name='fast_detector_image')
    """
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, delay_time=0.1, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name
        self._monitor_status = self.cam.detector_state
        self._sleep_time = delay_time

    def stage(self):
        self._monitor_status.subscribe(self._acquire_changed)
        super().stage()

    def unstage(self):
        super().unstage()
        self._monitor_status.clear_sub(self._acquire_changed)

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        self.dispatch(self._image_name, ttime.time())
        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if (old_value != 0) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            ttime.sleep(self._sleep_time)
            self._status.set_finished()
            self._status = None


class Lambda250kCam(CamBase):
    """
    support for X-Spectrum Lambda 750K detector
    https://x-spectrum.de/products/lambda-350k750k/
    """
    _html_docs = ['Lambda250kCam.html']

    serial_number = ADComponent(EpicsSignalRO, 'SerialNumber_RBV')
    firmware_version = ADComponent(EpicsSignalRO, 'FirmwareVersion_RBV')

    operating_mode = ADComponent(EpicsSignalWithRBV, 'OperatingMode')
    energy_threshold = ADComponent(EpicsSignalWithRBV, 'EnergyThreshold')
    dual_threshold = ADComponent(EpicsSignalWithRBV, 'DualThreshold')

    file_number_sync = None
    file_number_write = None
    pool_max_buffers = None


class MyHDF5Plugin(FileStoreHDF5SingleIterativeWrite, HDF5Plugin_V34):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = 'AD_HDF5_Lambda250k_APSPolar'


class Lambda250kDetector(MySingleTrigger, DetectorBase):

    _default_configuration_attrs = (
        'roi1', 'roi2', 'roi3', 'roi4', 'codec'
    )
    _default_read_attrs = (
        'cam', 'hdf1', 'stats1', 'stats2', 'stats3', 'stats4'
    )

    cam = ADComponent(Lambda250kCam, 'cam1:', kind='normal')
    hdf1 = ADComponent(
        MyHDF5Plugin,
        "HDF1:",
        write_path_template=join(LAMBDA_FILES_ROOT, TEST_IMAGE_DIR),
        read_path_template=join(BLUESKY_FILES_ROOT, TEST_IMAGE_DIR),
        kind='normal'
    )
    roi1 = ADComponent(ROIPlugin_V34, 'ROI1:')
    roi2 = ADComponent(ROIPlugin_V34, 'ROI2:')
    roi3 = ADComponent(ROIPlugin_V34, 'ROI3:')
    roi4 = ADComponent(ROIPlugin_V34, 'ROI4:')

    stats1 = ADComponent(StatsPlugin_V34, 'Stats1:')
    stats2 = ADComponent(StatsPlugin_V34, 'Stats2:')
    stats3 = ADComponent(StatsPlugin_V34, 'Stats3:')
    stats4 = ADComponent(StatsPlugin_V34, 'Stats4:')

    codec = ADComponent(CodecPlugin_V34, 'Codec1:')
    proc = ADComponent(ProcessPlugin_V34, "Proc1:")

    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def default_kinds(self):

        # TODO: This is setting A LOT of stuff as "configuration_attrs", should
        # be revised at some point.

        # Some of the attributes return numpy arrays which Bluesky doesn't
        # accept: configuration_names, stream_hdr_appendix,
        # stream_img_appendix.
        _remove_from_config = (
            "file_number_sync",  # Removed from EPICS
            "file_number_write",  # Removed from EPICS
            "pool_max_buffers",  # Removed from EPICS
            # all below are numpy.ndarray
            "configuration_names",
            "stream_hdr_appendix",
            "stream_img_appendix",
            "dim0_sa",
            "dim1_sa",
            "dim2_sa",
            "nd_attributes_macros",
            "dimensions",
            'asyn_pipeline_config',
            'dim0_sa',
            'dim1_sa',
            'dim2_sa',
            'dimensions',
            'histogram',
            'ts_max_value',
            'ts_mean_value',
            'ts_min_value',
            'ts_net',
            'ts_sigma',
            'ts_sigma_xy',
            'ts_sigma_y',
            'ts_total',
            'ts_timestamp',
            'ts_centroid_total',
            'ts_eccentricity',
            'ts_orientation',
            'histogram_x',
        )

        self.cam.configuration_attrs += [
            item for item in Lambda250kCam.component_names if item not in
            _remove_from_config
        ]

        self.cam.read_attrs += ["num_images_counter"]

        for name in self.component_names:
            comp = getattr(self, name)
            if isinstance(
                comp, (ROIPlugin_V34, StatsPlugin_V34, ProcessPlugin_V34)
            ):
                comp.configuration_attrs += [
                    item for item in comp.component_names if item not in
                    _remove_from_config
                ]
            if isinstance(comp, StatsPlugin_V34):
                comp.total.kind = Kind.hinted
                comp.read_attrs += ["max_value", "min_value"]

    def default_settings(self):
        self.stage_sigs['cam.num_images'] = 1
