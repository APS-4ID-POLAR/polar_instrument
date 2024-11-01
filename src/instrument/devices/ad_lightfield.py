"""
LightField based area detector
"""

__all__ = ["spectrometer"]

from ophyd import ADComponent, EpicsSignalRO, Staged, Device, Signal
from ophyd.areadetector import (
    EpicsSignalWithRBV,
    EpicsSignal,
    DetectorBase,
    TriggerBase,
    LightFieldDetectorCam
)
from ophyd.areadetector.trigger_mixins import ADTriggerStatus
from ophyd.areadetector.filestore_mixins import FileStoreBase

from os.path import join
import time as ttime
from pathlib import Path

from .ad_mixins import PolarHDF5Plugin, ImagePlugin
from ..utils.config import iconfig
from ..utils._logging_setup import logger

logger.info(__file__)

ad_config = iconfig["AREA_DETECTOR"]
HDF1_NAME_TEMPLATE = ad_config["HDF5_FILE_TEMPLATE"]
HDF1_FILE_EXTENSION = ad_config["HDF5_FILE_EXTENSION"]
HDF1_NAME_FORMAT = HDF1_NAME_TEMPLATE + "." + HDF1_FILE_EXTENSION

lf_config = ad_config["LIGHTFIELD"]
BLUESKY_FILES_ROOT = Path(lf_config["BLUESKY_FILES_ROOT"])
WINDOWS_FILES_ROOT = Path(lf_config["IOC_FILES_ROOT"])
DEFAULT_IOC_FOLDER = (
    rf"{WINDOWS_FILES_ROOT}\{lf_config['RELATIVE_DEFAULT_FOLDER']}"
).replace("/", "\\")


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
        self.generate_datum(self._image_name, ttime.time(), {})
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


class LF_HDF(PolarHDF5Plugin):
    def make_write_read_paths(self, write_path=None, read_path=None):

        if write_path is None:
            write_path = Path(self.hdf1.file_path.get(as_string=True))
        if read_path is None:
            _rel_path = Path(
                str(write_path).replace("\\", "/")
            ).relative_to(
                str(WINDOWS_FILES_ROOT).replace("\\", "/")
            )
            read_path = Path(BLUESKY_FILES_ROOT) / _rel_path

        fname_template = (
            self.parent.cam.file_template.get(as_string=True) + ".spe"
        )

        fname_base = self.parent.cam.file_name_base.get()
        fname_number = self.parent.cam.file_number.get()
        fname = fname_template % (fname_base, fname_number)

        full_path = Path(read_path) / fname
        relative_path = Path(f"{read_path.name}/{fname}")

        return str(write_path), full_path, relative_path


# Based on Eiger
class LightFieldFilePlugin(Device, FileStoreBase):
    """
    Using the filename from EPICS.
    """

    # Note: all PVs are defined in cam.

    enable = ADComponent(Signal, value=True, kind="config")

    def __init__(self, *args, **kwargs):
        self.filestore_spec = "AD_SPE_APSPolar"
        super().__init__(*args, write_path_template="", **kwargs)
        self.enable.subscribe(self._set_kind)

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

    def make_write_read_paths(self, write_path=None, read_path=None):

        if write_path is None:
            write_path = Path(self.parent.cam.file_path.get(as_string=True))
        if read_path is None:
            _rel_path = Path(
                str(write_path).replace("\\", "/")
            ).relative_to(
                str(WINDOWS_FILES_ROOT).replace("\\", "/")
            )
            read_path = Path(BLUESKY_FILES_ROOT) / _rel_path

        fname_template = (
            self.parent.cam.file_template.get(as_string=True) + ".spe"
        )

        fname_base = self.parent.cam.file_name_base.get()
        fname_number = self.parent.cam.file_number.get()
        fname = fname_template % (fname_base, fname_number)

        full_path = Path(read_path) / fname
        relative_path = Path(f"{read_path.name}/{fname}")

        return read_path, full_path, relative_path

    def stage(self):

        # TODO: is there a way to check if the file already exists? The issue is
        # that the IOC is in another windows machine.
        read_path, full_path, _ = self.make_write_read_paths()

        if full_path.is_file():
            raise FileExistsError(
                f"The file {full_path} already exists! Please change the file "
                "name."
            )

        self._fn = Path(read_path)

        super().stage()

        ipf = int(self.parent.cam.num_images.get())

        fname_template = (
            self.parent.cam.file_template.get(as_string=True) + ".spe"
        )

        res_kwargs = {
            'template': join('%s', fname_template),
            'filename': self.parent.cam.file_name_base.get(),
            'frame_per_point': ipf,
            }
        self._generate_resource(res_kwargs)

    def generate_datum(self, key, timestamp, datum_kwargs):
        """Using the num_images_counter to pick image from scan."""
        datum_kwargs.update(
            {'point_number': int(self.parent.cam.file_number.get())}
        )
        return super().generate_datum(key, timestamp, datum_kwargs)


class MyLightFieldCam(LightFieldDetectorCam):
    file_name_base = ADComponent(EpicsSignal, "FileName", string=True)
    file_path = ADComponent(
        EpicsSignalWithRBV, "FilePath", string=True, kind="normal"
    )
    file_name = ADComponent(
        EpicsSignalRO, "LFFileName_RBV", string=True, kind="normal"
    )
    file_number = ADComponent(EpicsSignalWithRBV, "FileNumber")
    file_template = ADComponent(EpicsSignalWithRBV, "FileTemplate")
    num_images_counter = ADComponent(EpicsSignalRO, 'NumImagesCounter_RBV')
    # The PV below works better as an EpicsSignal as it gets reported done after
    # the grating reached the target.
    grating_wavelength = ADComponent(EpicsSignal, "LFGratingWL")
    pool_max_buffers = None
    background_file = ADComponent(
        EpicsSignalWithRBV, "LFBackgroundFile", string=True
    )
    background_full_file = ADComponent(
        EpicsSignalRO, "LFBackgroundFullFile_RBV", string=True
    )
    background_path = ADComponent(
        EpicsSignalWithRBV, "LFBackgroundPath", string=True
    )


class LightFieldDetector(MySingleTrigger, DetectorBase):

    _default_read_attrs = ('cam', 'file', 'hdf1')
    _default_configuration_attrs = ("image",)

    cam = ADComponent(MyLightFieldCam, 'cam1:')
    image = ADComponent(ImagePlugin, "image1:")
    hdf1 = ADComponent(LF_HDF, "HDF1:")
    file = ADComponent(LightFieldFilePlugin, "cam1:")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flyscan = False

    @property
    def preset_monitor(self):
        return self.cam.acquire_time

    def save_images_on(self):
        self.hdf1.enable.set("Enable").wait(timeout=10)

    def save_images_off(self):
        self.hdf1.enable.set("Disable").wait(timeout=10)

    def auto_save_on(self):
        self.hdf1.autosave.put("on")

    def auto_save_off(self):
        self.hdf1.autosave.put("off")

    def default_settings(self):
        self.stage_sigs['cam.image_mode'] = 0

        # Default to preview mode
        self.cam.trigger_mode.put(1)
        self.cam.file_path.kind = "normal"
        self.cam.file_name.kind = "normal"

        self.save_images_off()

        self.hdf1.file_template.put(HDF1_NAME_FORMAT)
        self.hdf1.file_path.put(str(DEFAULT_IOC_FOLDER))
        self.hdf1.num_capture.put(0)

        self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
        self.hdf1.stage_sigs["capture"] = 1

    def setup_images(
            self, base_path, name_template, file_number, flyscan=False
    ):

        read_path = base_path / self.name
        _rel = read_path.relative_to(BLUESKY_FILES_ROOT)
        write_path = Path(str(WINDOWS_FILES_ROOT / _rel).replace("/", "\\"))

        self.cam.file_path.set(str(write_path)+"\\").wait(timeout=10)
        self.cam.file_number.set(file_number).wait(timeout=10)
        self.cam.file_name_base.set(name_template).wait(timeout=10)

        self.hdf1.file_path.set(str(write_path)+"\\").wait(timeout=10)
        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.hdf1.file_path.set(str(write_path)+"\\").wait(timeout=10)

        # Changes the stage_sigs to the external trigger mode
        self._flysetup = flyscan

        # _, _, _ = (
        #     self.file.make_write_read_paths(write_path, read_path)
        # )

        self.auto_save_on()

        _, full_path, relative_path = (
            self.hdf1.make_write_read_paths(write_path, read_path)
        )

        return full_path, relative_path


spectrometer = LightFieldDetector("4LF1:", name="spectrometer")
spectrometer.default_settings()
