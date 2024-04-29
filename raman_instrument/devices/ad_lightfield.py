"""
LightField based area detector
"""

__all__ = ["spectrometer"]

from ophyd import ADComponent, EpicsSignalRO, Kind, Staged
from ophyd.areadetector import (
    CamBase, EpicsSignalWithRBV, DetectorBase, TriggerBase, LightFieldDetectorCam

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


LIGHTFIELD_FILES_ROOT = r"Z:\4idd\bluesky_images\raman"
BLUESKY_FILES_ROOT = "/home/sector4/4idd/bluesky_images"
IMAGE_DIR_UNIX = "%Y/%m/%d/"
IMAGE_DIR_WINDOWS = r"%Y\%m\%d"


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


class MyHDF5Plugin(FileStoreHDF5SingleIterativeWrite, HDF5Plugin_V34):
    pass
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.filestore_spec = 'AD_HDF5_Lambda250k_APSPolar'


class LightFieldDetector(MySingleTrigger, DetectorBase):

    _default_read_attrs = (
        'cam', 'hdf1'
    )

    cam = ADComponent(LightFieldDetectorCam, 'cam1:', kind='normal')
    hdf1 = ADComponent(
        MyHDF5Plugin,
        "HDF1:",
        write_path_template=rf"{LIGHTFIELD_FILES_ROOT}\{IMAGE_DIR_WINDOWS}" ,  #TODO: not sure how to handle windows paths...
        read_path_template=join(BLUESKY_FILES_ROOT, IMAGE_DIR_UNIX),
        kind='normal'
    )

    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    # def default_kinds(self):

    #     # TODO: This is setting A LOT of stuff as "configuration_attrs", should
    #     # be revised at some point.

    #     # Some of the attributes return numpy arrays which Bluesky doesn't
    #     # accept: configuration_names, stream_hdr_appendix,
    #     # stream_img_appendix.
    #     _remove_from_config = (
    #         "file_number_sync",  # Removed from EPICS
    #         "file_number_write",  # Removed from EPICS
    #         "pool_max_buffers",  # Removed from EPICS
    #         # all below are numpy.ndarray
    #         "configuration_names",
    #         "stream_hdr_appendix",
    #         "stream_img_appendix",
    #         "dim0_sa",
    #         "dim1_sa",
    #         "dim2_sa",
    #         "nd_attributes_macros",
    #         "dimensions",
    #         'asyn_pipeline_config',
    #         'dim0_sa',
    #         'dim1_sa',
    #         'dim2_sa',
    #         'dimensions',
    #         'histogram',
    #         'ts_max_value',
    #         'ts_mean_value',
    #         'ts_min_value',
    #         'ts_net',
    #         'ts_sigma',
    #         'ts_sigma_xy',
    #         'ts_sigma_y',
    #         'ts_total',
    #         'ts_timestamp',
    #         'ts_centroid_total',
    #         'ts_eccentricity',
    #         'ts_orientation',
    #         'histogram_x',
    #     )

    #     self.cam.configuration_attrs += [
    #         item for item in Lambda250kCam.component_names if item not in
    #         _remove_from_config
    #     ]

    #     self.cam.read_attrs += ["num_images_counter"]

    #     for name in self.component_names:
    #         comp = getattr(self, name)
    #         if isinstance(
    #             comp, (ROIPlugin_V34, StatsPlugin_V34, ProcessPlugin_V34)
    #         ):
    #             comp.configuration_attrs += [
    #                 item for item in comp.component_names if item not in
    #                 _remove_from_config
    #             ]
    #         if isinstance(comp, StatsPlugin_V34):
    #             comp.total.kind = Kind.hinted
    #             comp.read_attrs += ["max_value", "min_value"]

    # def default_settings(self):
    #     self.stage_sigs['cam.num_images'] = 1

spectrometer = LightFieldDetector("4LF1:", name="spectrometer")
