"""
LightField based area detector
"""

__all__ = ["spectrometer"]

from ophyd import ADComponent, EpicsSignalRO, Staged, Device, Signal
from ophyd.areadetector import (
    EpicsSignalWithRBV, EpicsSignal, DetectorBase, TriggerBase, LightFieldDetectorCam
)
from ophyd.areadetector.trigger_mixins import ADTriggerStatus
from ophyd.areadetector.filestore_mixins import FileStoreBase

from os.path import join, isfile
import time as ttime
from pathlib import PurePath
from datetime import datetime


LIGHTFIELD_FILES_ROOT = r"Z:\4idd\bluesky_images\raman"
BLUESKY_FILES_ROOT = "/home/sector4/4idd/bluesky_images/raman"
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


# TODO: I will leave this here for now in case we switch to HDF5.
# class MyHDF5Plugin(FileStoreHDF5SingleIterativeWrite, HDF5Plugin_V34):
#     pass


# Based on Eiger
class LightFieldFilePlugin(Device, FileStoreBase):
    """
    Using the filename from EPICS.
    """

    # Note: all PVs are defined in cam.

    enable = ADComponent(Signal, value=True, kind="config")

    def __init__(self, *args, **kwargs):
        self.filestore_spec = "AD_SPE_APSPOLAR"
        super().__init__(*args, **kwargs)
        self.enable.subscribe(self._set_kind)
        # This is a workaround to enable setting these values in the detector
        # startup. Needed because we don't have a stable solution on where
        # these images would be.
        #TODO: not sure how to handle windows paths...
        self.write_path_template = rf"{LIGHTFIELD_FILES_ROOT}\{IMAGE_DIR_WINDOWS}"
        self.read_path_template = join(BLUESKY_FILES_ROOT, IMAGE_DIR_UNIX)

    def _set_kind(self, value, **kwargs):
        if value in (True, 1, "on", "enable"):
            self.kind = "normal"
        else:
            self.kind = "omitted"
    
    @property
    def base_name(self):
        return self.parent.cam.file_name_base.get()

    @base_name.setter
    def base_name(self, value):
        self.parent.cam.file_name_base.put(value)

    def make_write_read_paths(self):
        formatter = datetime.now().strftime
        write_path = formatter(self.write_path_template)
        read_path = formatter(self.read_path_template)
        return write_path, read_path

    def stage(self):

        # TODO: is there a way to check if the file already exists? The issue is that
        # the IOC is in another windows machine.
        write_path, read_path = self.make_write_read_paths()
        fname_template = self.parent.cam.file_template.get(as_string=True) + ".spe"

        fname_base = self.parent.cam.file_name_base.get(as_string=True)
        fname_number = self.parent.cam.file_number.get()
        fname = fname_template % (fname_base, fname_number)

        if isfile(join(read_path, fname)):
            raise FileExistsError(
                f"The file {join(read_path, fname)} already exists! Please change the "
                "file name."
            )

        self.parent.cam.file_path.put(write_path)
        self._fn = PurePath(read_path)
    
        super().stage()

        ipf = int(self.parent.cam.num_images.get())
    
        res_kwargs = {
            'template' : join('%s', fname_template),
            'filename' : self.parent.cam.file_name_base.get(as_string=True),
            'frame_per_point' : ipf,
            }
        self._generate_resource(res_kwargs)

    def generate_datum(self, key, timestamp, datum_kwargs):
        """Using the num_images_counter to pick image from scan."""
        datum_kwargs.update({'point_number': int(self.parent.cam.file_number.get())})
        return super().generate_datum(key, timestamp, datum_kwargs)


class MyLightFieldCam(LightFieldDetectorCam):
    file_name_base = ADComponent(EpicsSignal, "FileName", kind="config")
    file_path = ADComponent(EpicsSignalWithRBV, "FilePath", string=True, kind="normal")
    file_name = ADComponent(EpicsSignalRO, "LFFileName_RBV", string=True, kind="normal")
    file_number = ADComponent(EpicsSignalWithRBV, "FileNumber", kind="config")
    file_template = ADComponent(EpicsSignalWithRBV, "FileTemplate", kind="config")
    num_images_counter = ADComponent(EpicsSignalRO, 'NumImagesCounter_RBV')
    grating_wavelength = ADComponent(EpicsSignalWithRBV, "LFGratingWL")
    pool_max_buffers = None


class LightFieldDetector(MySingleTrigger, DetectorBase):

    _default_read_attrs = (
        'cam', 'file'
    )

    cam = ADComponent(MyLightFieldCam, 'cam1:', kind='normal')

    # TODO: I will leave this here in case we switch to HDF5 at some point. Note that
    # 'hdf1' needs to be added to the _default_read_attrs.
    # hdf1 = ADComponent(
    #     MyHDF5Plugin,
    #     "HDF1:",
    #     write_path_template=rf"{LIGHTFIELD_FILES_ROOT}\{IMAGE_DIR_WINDOWS}" ,  
    #     read_path_template=join(BLUESKY_FILES_ROOT, IMAGE_DIR_UNIX),
    #     kind='normal'
    # )

    file = ADComponent(
        LightFieldFilePlugin,
        "cam1:",
        write_path_template="",
        read_path_template="",
        kind="normal"
    )

    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def default_kinds(self):

        # TODO: This is setting A LOT of stuff as "configuration_attrs", should
        # be revised at some point.

        # Some of the attributes return numpy arrays which Bluesky doesn't accept.
        _remove_from_config = [
            # "file_number_sync",  # Removed from EPICS
            # "file_number_write",  # Removed from EPICS
            # "pool_max_buffers",  # Removed from EPICS
            # # all below are numpy.ndarray
            # "configuration_names",
            # "stream_hdr_appendix",
            # "stream_img_appendix",
            # "dim0_sa",
            # "dim1_sa",
            # "dim2_sa",
            # "nd_attributes_macros",
            # "dimensions",
            # 'asyn_pipeline_config',
            # 'dim0_sa',
            # 'dim1_sa',
            # 'dim2_sa',
            # 'dimensions',
            # 'histogram',
            # 'ts_max_value',
            # 'ts_mean_value',
            # 'ts_min_value',
            # 'ts_net',
            # 'ts_sigma',
            # 'ts_sigma_xy',
            # 'ts_sigma_y',
            # 'ts_total',
            # 'ts_timestamp',
            # 'ts_centroid_total',
            # 'ts_eccentricity',
            # 'ts_orientation',
            # 'histogram_x',
        ]

        self.cam.configuration_attrs += [
            item for item in MyLightFieldCam.component_names if item not in
            _remove_from_config
        ]

        # self.cam.read_attrs += ["num_images_counter"]

        # for name in self.component_names:
        #     comp = getattr(self, name)
        #     if isinstance(
        #         comp, (ROIPlugin_V34, StatsPlugin_V34, ProcessPlugin_V34)
        #     ):
        #         comp.configuration_attrs += [
        #             item for item in comp.component_names if item not in
        #             _remove_from_config
        #         ]
        #     if isinstance(comp, StatsPlugin_V34):
        #         comp.total.kind = Kind.hinted
        #         comp.read_attrs += ["max_value", "min_value"]

    def default_settings(self):
        self.stage_sigs['cam.image_mode'] = 0

        # Default to preview mode
        self.cam.trigger_mode.put(1)

        self.cam.file_path.kind = "normal"
        self.cam.file_name.kind = "normal"


spectrometer = LightFieldDetector("4LF1:", name="spectrometer")
spectrometer.default_settings()
