"""
Eiger area detector
"""

from pathlib import PurePath
from time import time as ttime
from ophyd import (Component, ADComponent, EigerDetectorCam, DetectorBase,
                   Staged, EpicsSignal, Signal, Kind, Device)
from ophyd.areadetector.base import EpicsSignalWithRBV
from ophyd.signal import EpicsSignalRO
from ophyd.status import wait as status_wait, SubscriptionStatus
from ophyd.areadetector.plugins import ROIPlugin_V34, StatsPlugin_V34
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
from ophyd.areadetector.filestore_mixins import FileStoreBase
from apstools.utils import run_in_thread
from time import sleep
from os.path import join, isdir
from ..session_logs import logger
logger.info(__file__)


# EigerDetectorCam inherits FileBase, which contains a few PVs that were
# removed from AD after V22: file_number_sync, file_number_write,
# pool_max_buffers.
class LocalEigerCam(EigerDetectorCam):
    file_number_sync = None
    file_number_write = None
    pool_max_buffers = None

    wait_for_plugins = ADComponent(EpicsSignal, 'WaitForPlugins', string=True)
    file_path = ADComponent(EpicsSignal, 'FilePath', string=True)
    create_directory = ADComponent(EpicsSignal, "CreateDirectory")


class TriggerNewImage(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name
        self._image_count = self.cam.array_counter
        self._acquisition_signal = self.cam.special_trigger_button

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Internal Enable"
        self.cam.stage_sigs["manual_trigger"] = "Enable"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["num_exposures"] = 1
        self.cam.stage_sigs["num_triggers"] = int(1e5)

    def stage(self):
        # Make sure that detector is not armed.
        self.cam.acquire.set(0).wait(timeout=10)
        super().stage()
        # The trigger button does not track that the detector is done, so
        # the image_count is used. Not clear it's the best choice.
        self._image_count.subscribe(self._acquire_changed)
        self.cam.acquire.set(1).wait(timeout=10)

    def unstage(self):
        super().unstage()
        self._image_count.clear_sub(self._acquire_changed)
        self.cam.acquire.set(0).wait(timeout=10)

        def check_value(*, old_value, value, **kwargs):
            "Return True when detector is done"
            return (value == "Ready" or value == "Acquisition aborted")

        # When stopping the detector, it may take some time processing the
        # images. This will block until it's done.
        status_wait(
            SubscriptionStatus(
                self.cam.status_message, check_value, timeout=10
            )
        )
        # This has to be here to ensure it happens after stopping the
        # acquisition.
        self.save_images_off()

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        self.dispatch(self._image_name, ttime())
        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if value > old_value:  # There is a new image!
            self._status.set_finished()
            self._status = None


class TriggerTime(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, delay=0.1, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name
        self._acquisition_signal = self.cam.special_trigger_button
        self._delay = delay

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, value):
        try:
            self._delay = float(value)
        except ValueError:
            raise ValueError("delay must be a number.")

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Internal Enable"
        self.cam.stage_sigs["manual_trigger"] = "Enable"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["num_exposures"] = 1
        self.cam.stage_sigs["num_triggers"] = int(1e5)

    def stage(self):
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

        # When stopping the detector, it may take some time processing the
        # images. This will block until it's done.
        status_wait(
            SubscriptionStatus(
                self.cam.status_message, check_value, timeout=10
            )
        )
        # This has to be here to ensure it happens after stopping the
        # acquisition.
        self.save_images_off()

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        @run_in_thread
        def add_delay(status_obj, delay):
            total_sleep = self.cam.trigger_exposure.get() + delay
            sleep(total_sleep)
            status_obj.set_finished()

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        self.dispatch(self._image_name, ttime())
        add_delay(self._status, self._delay)
        return self._status


# Based on NSLS2-CHX
class EigerSimulatedFilePlugin(Device, FileStoreBase):
    """
    Using the filename from EPICS.
    """
    seq_id = ADComponent(EpicsSignalRO, "SequenceId")
    file_path = ADComponent(EpicsSignalWithRBV, 'FilePath', string=True,
                            put_complete=True)
    file_write_name_pattern = ADComponent(EpicsSignalWithRBV, 'FWNamePattern',
                                          string=True, put_complete=True)
    file_write_images_per_file = ADComponent(EpicsSignalWithRBV,
                                             'FWNImagesPerFile')
    current_run_start_uid = Component(Signal, value='', add_prefix=())
    num_images_counter = ADComponent(EpicsSignalRO, 'NumImagesCounter_RBV')
    enable = Component(Signal, value=False, kind="omitted")

    def __init__(self, *args, **kwargs):
        self.filestore_spec = "AD_EIGER_APSPolar"
        super().__init__(*args, **kwargs)
        self.enable.subscribe(self._set_kind)
        self._base_name = None

        # This is a workaround to enable setting these values in the detector
        # startup. Needed because we don't have a stable solution on where
        # these images would be.
        self.write_path_template = self.parent._write_path_template
        self.read_path_template = self.parent._read_path_template

    def _set_kind(self, value, **kwargs):
        if value in (True, 1, "on", "enable"):
            self.kind = "normal"
        else:
            self.kind = "omitted"

    @property
    def base_name(self):
        return 'seqid_{}' if self._base_name is None else self._base_name

    @base_name.setter
    def base_name(self, value):
        self._base_name = value.replace("$id", "{}")

    # This is the part to change if a different file scheme is chosen.
    def make_write_read_paths(self):
        _base_name = self.base_name.format(self.seq_id.get() + 1)
        write_path = join(self.write_path_template, _base_name + "/")
        read_path = join(
            self.read_path_template, self.base_name, _base_name
        )
        return _base_name, write_path, read_path

    def stage(self):
        # Only save images if the enable is on...
        if self.enable.get() in (True, 1, "on", "enable"):
            _base_name, write_path, read_path = self.make_write_read_paths()
            if isdir(write_path):
                raise OSError(f"{write_path} exists! Please be sure that"
                              f"{self.base_name} has not been used!")
            self.file_write_name_pattern.put(_base_name)
            self.file_path.put(write_path)
            self._fn = PurePath(read_path)

            self.parent.save_images_on()
            super().stage()

            ipf = int(self.file_write_images_per_file.get())
            res_kwargs = {'images_per_file': ipf}
            self._generate_resource(res_kwargs)

    def generate_datum(self, key, timestamp, datum_kwargs):
        """Using the num_images_counter to pick image from scan."""
        datum_kwargs.update({'image_num': self.num_images_counter.get()})
        return super().generate_datum(key, timestamp, datum_kwargs)


class LocalEigerDetectorBase(DetectorBase):

    _default_configuration_attrs = ('roi1', 'roi2', 'roi3', 'roi4')
    _default_read_attrs = ('cam', 'file', 'stats1', 'stats2', 'stats3',
                           'stats4')

    _html_docs = ['EigerDoc.html']
    cam = Component(LocalEigerCam, 'cam1:', kind="normal")

    file = Component(
        EigerSimulatedFilePlugin, suffix='cam1:',
        # Paths are changed in the EigerSimulatedFilePlugin __init__
        write_path_template="",
        read_path_template=""
    )

    # ROIs
    roi1 = Component(ROIPlugin_V34, 'ROI1:')
    roi2 = Component(ROIPlugin_V34, 'ROI2:')
    roi3 = Component(ROIPlugin_V34, 'ROI3:')
    roi4 = Component(ROIPlugin_V34, 'ROI4:')

    # ROIs stats
    stats1 = Component(StatsPlugin_V34, "Stats1:")
    stats2 = Component(StatsPlugin_V34, "Stats2:")
    stats3 = Component(StatsPlugin_V34, "Stats3:")
    stats4 = Component(StatsPlugin_V34, "Stats4:")

    def __init__(
        self, *args, write_path_template="", read_path_template="", **kwargs
    ):
        self._write_path_template = write_path_template
        self._read_path_template = read_path_template
        super().__init__(*args, **kwargs)

    # Make this compatible with other detectors
    @property
    def preset_monitor(self):
        return self.cam.trigger_exposure

    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.manual_trigger.set("Disable").wait(timeout=10)
        self.cam.num_triggers.set(int(1e6)).wait(timeout=10)
        self.cam.trigger_mode.set("Internal Enable").wait(timeout=10)
        self.cam.trigger_exposure.set(time).wait(timeout=10)
        self.cam.acquire.set(1).wait(timeout=10)

    def align_off(self):
        """Stop detector"""
        self.cam.acquire.set(0).wait(timeout=10)

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
            item for item in EigerDetectorCam.component_names if item not in
            _remove_from_config
        ]

        self.cam.read_attrs += ["num_images_counter"]

        for name in self.component_names:
            comp = getattr(self, name)
            if isinstance(comp, (ROIPlugin_V34, StatsPlugin_V34)):
                comp.configuration_attrs += [
                    item for item in comp.component_names if item not in
                    _remove_from_config
                ]
            if isinstance(comp, StatsPlugin_V34):
                comp.total.kind = Kind.hinted
                comp.read_attrs += ["max_value", "min_value"]

    def save_images_on(self):
        def check_value(*, old_value, value, **kwargs):
            "Return True when file writter is enabled"
            return value == "ready"

        self.cam.fw_enable.put("Enable")
        status_wait(
            SubscriptionStatus(self.cam.fw_state, check_value, timeout=10)
        )

    def save_images_off(self):
        def check_value(*, old_value, value, **kwargs):
            "Return True when file writter is enabled"
            return value == "disabled"

        self.cam.fw_enable.put("Disable")
        status_wait(
            SubscriptionStatus(self.cam.fw_state, check_value, timeout=10)
        )

    def default_settings(self):
        self.cam.num_triggers.put(1)
        self.cam.manual_trigger.put("Disable")
        self.cam.trigger_mode.put("Internal Enable")
        self.cam.acquire.put(0)
        self.cam.wait_for_plugins.put("Yes")
        self.cam.create_directory.put(-1)
        self.cam.fw_compression.put("Enable")
        self.cam.fw_num_images_per_file.put(1)
        self.file.enable.put(True)
        self.setup_manual_trigger()
        self.save_images_off()


class EigerDetectorTimeTrigger(TriggerTime, LocalEigerDetectorBase):
    pass


class EigerDetectorImageTrigger(TriggerNewImage, LocalEigerDetectorBase):
    pass
