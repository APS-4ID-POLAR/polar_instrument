"""
Flyscan using area detector
"""

from bluesky.preprocessors import stage_decorator, run_decorator, subs_decorator
from bluesky.plan_stubs import rd, null, move_per_step, sleep
from bluesky.plan_patterns import outer_product, inner_product
from apstools.utils import (
    validate_experiment_dataDirectory,
    build_run_metadata_dict,
    share_bluesky_metadata_with_dm,
)
from collections import defaultdict
from pathlib import Path
from json import dumps
from warnings import warn
from .local_scans import mv
from ..devices.pva_control import positioner_stream
from ..devices.softgluezynq import sgz
from ..devices.data_management import dm_experiment, dm_workflow
from ..utils import logger
from ..utils.config import iconfig
from ..utils.run_engine import RE
from ..utils.catalog import full_cat
from ..callbacks import nxwriter
from ..utils import dm_get_experiment_data_path
logger.info(__file__)

__all__ = "flyscan_snake flyscan_1d flyscan_cycler".split()

HDF1_NAME_FORMAT = Path(iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"])


def flyscan_snake(
        detector,
        stepping_motor,
        stepping_motor_start,
        stepping_motor_end,
        stepping_motor_number_of_points,
        flying_motor,
        flying_motor_start,
        flying_motor_end,
        flying_motor_speed,
        detector_trigger_period: float = 0.02,
        detector_collection_time: float = 0.01,
        file_name_base: str = "scan",
        master_file_templates: list = [],
        nxwriter_warn_missing: bool = False,
        md: dict = {},
        # DM workflow kwargs -------------------------------------
        wf_run: bool = False,
        wf_analysis_machine: str = "polaris",
        wf_workflow_name: str = "ptychodus",
        wf_detectorName: str = "eiger",
        wf_detectorDistanceInMeters: float = 2.335,
        wf_cropCenterXInPixels: int = 540,
        wf_cropCenterYInPixels: int = 259,
        wf_cropExtentXInPixels: int = 256,
        wf_cropExtentYInPixels: int = 256,
        wf_probeEnergyInElectronVolts: float = 10000,
        wf_numGpus: int = 2,
        wf_settings: str = "/home/beams/POLAR/ptychodusDefaults/default-settings.ini",
        wf_demand: bool = False,
        wf_scanFilePath: str = "fly001_pos.csv",
        wf_name: str = "fly001",
        # internal kwargs ----------------------------------------
        dm_concise: bool = False,
        dm_wait: bool = False,
        dm_reporting_period: float = 10*60,
        dm_reporting_time_limit: float = 10**6,

    ):

    """
    Flyscan using a "snake" trajectory.

    Note the first motor in *args will step and the second will fly (by doing a two
    point step).

    Parameters
    ----------
    eiger : Eiger detector instance
        Currently sort of hardwired for the Eiger, but this will be removed in the
        future to match with the POLAR standard of defaulting to our `counters` class.
    *args :
        The first motor is the outer loop that will step, with the second motor flying
        between the ends. Thus the first motor needs a number of steps.
        .. code-block:: python
            motor1, start1, stop1, number of point, motor2, start2, stop
    speed : float, default to 10
        Velocity of the flying motor. This will be passed to `motor2.velocity` through
        staging.
    trigger_time : float, default to 0.02 seconds
        Time between detector triggers.
    collection_time : float, default to 0.01 seconds
        Time that detector spend collecting the image. It must be smaller or equal to
        the trigger_time otherwise a ValueError is raised.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plan_patterns.outter_product`
    :func:`flyscan_cycler`
    """

    detectors = [detector]
    args = (
        stepping_motor,
        stepping_motor_start,
        stepping_motor_end,
        stepping_motor_number_of_points,
        flying_motor,
        flying_motor_start,
        flying_motor_end,
        2,
        True
    )

    _md = {
        "plan_name": "flyscan_snake",
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "stepping_motor": repr(stepping_motor),
            "stepping_motor_start": stepping_motor_start,
            "stepping_motor_end": stepping_motor_end,
            "stepping_motor_number_of_points": stepping_motor_number_of_points,
            "flying_motor": repr(flying_motor),
            "flying_motor_start": flying_motor_start,
            "flying_motor_end": flying_motor_end,
            "flying_motor_speed": flying_motor_speed,
            "detector_trigger_period": detector_trigger_period,
            "detector_collection_time": detector_collection_time,
            "file_name_base": file_name_base,
            "master_file_templates": master_file_templates,
            "nxwriter_warn_missing": nxwriter_warn_missing,
        }
    }

    _md.update(md)

    cycler = outer_product(args)
    yield from flyscan_cycler(
        detectors,
        cycler,
        speeds=[None, flying_motor_speed],
        detector_trigger_period=detector_trigger_period,
        detector_collection_time=detector_collection_time,
        master_file_templates=master_file_templates,
        file_name_base=file_name_base,
        md=_md,
        # DM workflow kwargs -------------------------------------
        wf_run=wf_run,
        wf_analysis_machine=wf_analysis_machine,
        wf_workflow_name=wf_workflow_name,
        wf_detectorName=wf_detectorName,
        wf_detectorDistanceInMeters=wf_detectorDistanceInMeters,
        wf_cropCenterXInPixels=wf_cropCenterXInPixels,
        wf_cropCenterYInPixels=wf_cropCenterYInPixels,
        wf_cropExtentXInPixels=wf_cropExtentXInPixels,
        wf_cropExtentYInPixels=wf_cropExtentYInPixels,
        wf_probeEnergyInElectronVolts=wf_probeEnergyInElectronVolts,
        wf_numGpus=wf_numGpus,
        wf_settings=wf_settings,
        wf_demand=wf_demand,
        wf_scanFilePath=wf_scanFilePath,
        wf_name=wf_name,
        # internal kwargs ----------------------------------------
        dm_concise=dm_concise,
        dm_wait=dm_wait,
        dm_reporting_period=dm_reporting_period,
        dm_reporting_time_limit=dm_reporting_time_limit,
        nxwriter_warn_missing=nxwriter_warn_missing,
        )

def flyscan_1d(
        detector,
        motor,
        start,
        end,
        speed,
        detector_trigger_period: float = 0.02,
        detector_collection_time: float = 0.01,
        master_file_templates: list = [],
        file_name_base: str = "scan",
        md: dict = {},
        # DM workflow kwargs -------------------------------------
        wf_run: bool = False,
        wf_analysis_machine: str = "polaris",
        wf_workflow_name: str = "ptychodus",
        wf_detectorName: str = "eiger",
        wf_detectorDistanceInMeters: float = 2.335,
        wf_cropCenterXInPixels: int = 540,
        wf_cropCenterYInPixels: int = 259,
        wf_cropExtentXInPixels: int = 256,
        wf_cropExtentYInPixels: int = 256,
        wf_probeEnergyInElectronVolts: float = 10000,
        wf_numGpus: int = 2,
        wf_settings: str = "/home/beams/POLAR/ptychodusDefaults/default-settings.ini",
        wf_demand: bool = False,
        wf_scanFilePath: str = "fly001_pos.csv",
        wf_name: str = "fly001",
        # internal kwargs ----------------------------------------
        dm_concise: bool = False,
        dm_wait: bool = False,
        dm_reporting_period: float = 10*60,  # TODO: change?
        dm_reporting_time_limit: float = 10**6, # TODO: change?
        nxwriter_warn_missing: bool = False,
    ):
    """
    Flyscan in 1 dimension.

    Parameters
    ----------
    eiger : Eiger detector instance
        Currently sort of hardwired for the Eiger, but this will be removed in the
        future to match with the POLAR standard of defaulting to our `counters` class.
    motor : ophyd motor object
        Ideally it is a motor with a custom unstaging that removes "velocity" from the
        stage_sigs, see ../devices/nanopositioners.py
    start : float
        Initial motor position
    end : float
        Final motor position
    speed : float, default to 10
        Velocity of the flying motor. This will be passed to `motor.velocity` through
        staging.
    trigger_time : float, default to 0.02 seconds
        Time between detector triggers.
    collection_time : float, default to 0.01 seconds
        Time that detector spend collecting the image. It must be smaller or equal to
        the trigger_time otherwise a ValueError is raised.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plan_patterns.inner_product`
    :func:`flyscan_cycler`
    """
    detectors = [detector]
    cycler = inner_product(2, (motor, start, end))

    _md = {
        "plan_name": "flyscan_1d",
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "motor": repr(motor),
            "motor_start": start,
            "motor_end": end,
            "motor_speed": speed,
            "detector_trigger_period": detector_trigger_period,
            "detector_collection_time": detector_collection_time,
            "file_name_base": file_name_base,
            "master_file_templates": master_file_templates,
            "nxwriter_warn_missing": nxwriter_warn_missing,
        }
    }
    _md.update(md)

    yield from flyscan_cycler(
        detectors,
        cycler,
        speeds=[speed],
        detector_trigger_period=detector_trigger_period,
        detector_collection_time=detector_collection_time,
        master_file_templates=master_file_templates,
        file_name_base=file_name_base,
        md=_md,
        # DM workflow kwargs -------------------------------------
        wf_run=wf_run,
        wf_analysis_machine=wf_analysis_machine,
        wf_workflow_name=wf_workflow_name,
        wf_detectorName=wf_detectorName,
        wf_detectorDistanceInMeters=wf_detectorDistanceInMeters,
        wf_cropCenterXInPixels=wf_cropCenterXInPixels,
        wf_cropCenterYInPixels=wf_cropCenterYInPixels,
        wf_cropExtentXInPixels=wf_cropExtentXInPixels,
        wf_cropExtentYInPixels=wf_cropExtentYInPixels,
        wf_probeEnergyInElectronVolts=wf_probeEnergyInElectronVolts,
        wf_numGpus=wf_numGpus,
        wf_settings=wf_settings,
        wf_demand=wf_demand,
        wf_scanFilePath=wf_scanFilePath,
        wf_name=wf_name,
        # internal kwargs ----------------------------------------
        dm_concise=dm_concise,
        dm_wait=dm_wait,
        dm_reporting_period=dm_reporting_period,  # TODO: change?
        dm_reporting_time_limit=dm_reporting_time_limit, # TODO: change?
        nxwriter_warn_missing=nxwriter_warn_missing,
        )

def flyscan_cycler(
        detectors: list,
        cycler,
        speeds: list,
        detector_trigger_period: float = 0.02,
        detector_collection_time: float = 0.01,
        master_file_templates: list = [],
        file_name_base: str = "scan",
        md: dict = {},
        # DM workflow kwargs -------------------------------------
        wf_run: bool = False,
        wf_analysis_machine: str = "polaris",
        wf_workflow_name: str = "ptychodus",
        wf_detectorName: str = "eiger",
        wf_detectorDistanceInMeters: float = 2.335,
        wf_cropCenterXInPixels: int = 540,
        wf_cropCenterYInPixels: int = 259,
        wf_cropExtentXInPixels: int = 256,
        wf_cropExtentYInPixels: int = 256,
        wf_probeEnergyInElectronVolts: float = 10000,
        wf_numGpus: int = 2,
        wf_settings: str = "/home/beams/POLAR/ptychodusDefaults/default-settings.ini",
        # patternsFile (from area detector) --> ?
        wf_demand: bool = False,
        wf_scanFilePath: str = "fly001_pos.csv",
        wf_name: str = "fly001",
        # internal kwargs ----------------------------------------
        dm_concise: bool = False,
        dm_wait: bool = False,
        dm_reporting_period: float = 10*60,
        dm_reporting_time_limit: float = 10**6,
        nxwriter_warn_missing: bool = False,
    ):

    """
    Flyscan using a generic path.

    Note that only the last motor will fly (by doing a two point step).

    Parameters
    ----------
    detectors : list of ophyd detectors
        Currently sort of hardwired for the Eiger, which must be the first item in the
        list. But this will be removed in the future to match with the POLAR standard of
        defaulting to our `counters` class.
    cycler : Cycler
        cycler.Cycler object mapping movable interfaces to positions.
    speeds : list
        Velocity of the motors, this is particularly useful for the flying motor. If
        `None`, then the speed will not be changed. The speed will be passed to
        `motor.velocity` through staging (see ../devices/nanopositioners.py).
    trigger_time : float, default to 0.02 seconds
        Time between detector triggers.
    collection_time : float, default to 0.01 seconds
        Time that detector spend collecting the image. It must be smaller or equal to
        the trigger_time otherwise a ValueError is raised.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plan_patterns.outter_product`
    :func:`bluesky.plan_patterns.inner_product`
    """

    ############################
    # Check potential problems #
    ############################

    try:
        validate_experiment_dataDirectory(dm_experiment.get())
    except:
        raise ValueError(
            f"Cannot find an experiment named: {dm_experiment.get()} in DM. Please see"
            "and run the setup_user function."
        )

    if detector_collection_time > detector_trigger_period:
        raise ValueError(
            f"The collection time ({detector_collection_time}) cannot be larger than the time "
            f"between triggers ({detector_trigger_period})."
        )
    
    # Sample metadata will be used to sort data
    if "sample" not in RE.md.keys():
        RE.md["sample"] = "sample01"
        warn(f"'sample' metadata not found! Using {RE.md['sample']}")

    #####################
    # Setup files names #
    #####################

    # Collect information to make file names
    _base_path = (
        Path(dm_get_experiment_data_path(dm_experiment.get())) / RE.md["sample"]
    )
    if not _base_path.is_dir():
        _base_path.mkdir()

    _scan_id = RE.md["scan_id"] + 1

    # TODO: simplify
    # Master file
    _master_fullpath = HDF1_NAME_FORMAT % (str(_base_path), file_name_base, _scan_id)
    _master_fullpath += "_master.hdf"

    # Setup area detectors
    _dets_file_paths = {}
    for det in list(detectors) + [positioner_stream]:
        _setup_images = getattr(det, "setup_images", None)
        if _setup_images:
            _dets_file_paths[det.name] = _setup_images(
                file_name_base, _scan_id, flyscan=True
            )

    # Check if any of these files exists
    # for _fname in [_master_fullpath, _ps_fullpath] + list(_dets_file_paths.values()):
    for _fname in [_master_fullpath] + list(_dets_file_paths.values()):
        if _fname.is_file():
            raise FileExistsError(
                f"The file {_fname} already exists! Will not overwrite, quitting."
            )

    #################################################
    # nxwriter - creates and setup the master file  #
    #################################################

    # Relative paths are used in the master file so that data can be copied.
    _rel_dets_paths = {}
    for _name, _path in _dets_file_paths.items():
        _rel_dets_paths[_name] = _path.relative_to(_base_path)

    # Sets the file names
    nxwriter.externals = _rel_dets_paths
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(_base_path)

    md.update(dict(master_file=str(nxwriter.file_name)))

    # For now this is here just to show how the templates works.
    # master_file_templates += [
    #     ["/entry/eiger_file_path=", str(_rel_eiger_path)],
    #     ["/entry/softglue_file_path=", str(_rel_ps_path)],
    # ]
    md[nxwriter.template_key] = dumps(master_file_templates)  # <-- adds the templates

    nxwriter.warn_on_missing_content = nxwriter_warn_missing

    ############
    # METADATA #
    ############

    motors = list(cycler.keys)  # the cycler inverts the list.

    _md = dict(
        detectors = [det.name for det in detectors],
        motors = [motor.name for motor in motors], 
        plan_name = "flyscan_cycler",
        plan_args = {
            "detectors": list(map(repr, detectors)),
            "motors": repr(motors),
            "cycler": repr(cycler),
            "detector_trigger_period": detector_trigger_period,
            "detector_collection_time": detector_collection_time,
            "file_name_base": file_name_base,
            "master_file_templates": master_file_templates,
            "nxwriter_warn_missing": nxwriter_warn_missing,
        },
        master_file_path = str(_master_fullpath),
        # This assumes the first detector is the eiger.
        # eiger_relative_file_path = str(_rel_eiger_path),
        # eiger_full_file_path = str(_eiger_fullpath),
        # positioner_stream_full_file_path = str(_ps_fullpath),
        # positioner_stream_relative_file_path = str(_rel_ps_path),
        # TODO: a similar scan with a monitor (scaler...)
        hints = dict(monitor=None, detectors=[], scan_type="flyscan")
    )

    for _name, _fpath in _dets_file_paths.items():
        _md[f"{_name}_full_file_path"] = str(_fpath)

    for _name, _fpath in _rel_dets_paths.items():
        _md[f"{_name}_relative_file_path"] = str(_fpath)

    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])
    
    dimensions = [(motor.hints["fields"], "primary") for motor in motors]
    _md["hints"].setdefault("dimensions", dimensions)


    if wf_run:
        _md = build_run_metadata_dict(
            _md,  # TODO: maybe it needs **_md?
            workflow=wf_workflow_name,
            wait=dm_wait,
            timeout=dm_reporting_time_limit,
            filePath=_master_fullpath.name,
            sampleName = RE.md["sample"],
            experimentName=dm_experiment.get(),
            analysisMachine=wf_analysis_machine,
            # TODO: What all can we switch to PV.gets?
            detectorName = wf_detectorName,
            detectorDistanceInMeters = wf_detectorDistanceInMeters,
            cropCenterXInPixels = wf_cropCenterXInPixels,
            cropCenterYInPixels = wf_cropCenterYInPixels,
            cropExtentXInPixels = wf_cropExtentXInPixels,
            cropExtentYInPixels = wf_cropExtentYInPixels,
            probeEnergyInElectronVolts = wf_probeEnergyInElectronVolts,
            numGpus = wf_numGpus,
            settings = wf_settings,
            demand = wf_demand,
            name=wf_name,
            scanFilePath=wf_scanFilePath,
        )

    _md.update(md)

    #################################
    # MOVING DEVICES TO START POINT #
    #################################

    logger.info("Setting up devices.")

    # Setup detectors count time --> detector is now gated.
    # for det in detectors:
    #     yield from mv(det.preset_monitor, detector_collection_time)

    # Stop and reset softglue just in case
    yield from sgz.stop_detectors()
    yield from sgz.stop_softglue()
    yield from sgz.reset_plan()

    # Stop positioner stream just in case
    yield from mv(positioner_stream, 0)

    # Setup the eiger frequency
    yield from sgz.setup_trigger_plan(
        detector_trigger_period, detector_collection_time
    )

    logger.info("Moving motors to the start position.")

    # Move motor to start position using "normal speed"
    args = ()
    for motor, position in list(cycler)[0].items():
        args += (motor, position)
    yield from mv(*args)

    # Setup the motors stage signals
    speeds = speeds[::-1]  # The cycler inverts the motor list.
    for motor, speed in zip(motors, speeds):
        if speed is not None:
            motor.stage_sigs["velocity"] = speed

    ################
    # RUNNING SCAN #
    ################

    @subs_decorator(nxwriter.receiver)
    @stage_decorator(list(detectors) + motors)
    @run_decorator(md=_md)
    def inner_fly():
        yield from mv(positioner_stream, 1)
        yield from sgz.start_softglue()

        yield from sgz.start_detectors()
        pos_cache = defaultdict(lambda: None)
        for step in list(cycler):
            yield from move_per_step(step, pos_cache)
        yield from sgz.stop_detectors()

        # This will wait for a full new set of packets.
        # TODO: It's an overkill, maybe Keenan's code can broadcast a signal?
        n = yield from rd(sgz.div_by_n_interf.n)
        _time_per_point = n/1e7
        _number_of_events_per_packet = 1e5/8
        yield from sleep(_time_per_point*_number_of_events_per_packet+ 0.1)

        yield from sgz.stop_softglue()

        logger.info("Stopping the positioner stream, this can take time.")
        yield from mv(positioner_stream, 0)

        return (yield from null()) # Is there something better to do here?

    uid = yield from inner_fly()

    # Get the bluesky run
    run = full_cat[uid]

    # Wait for the master file to finish writing.
    yield from nxwriter.wait_writer_plan_stub()

    #############################
    # START THE APS DM WORKFLOW #
    #############################

    if wf_run:
        yield from mv(
            dm_workflow.concise_reporting, dm_concise,
            dm_workflow.reporting_period, dm_reporting_period,
        )

        logger.info(
            "DM workflow %r, filePath=%r",
            wf_workflow_name,
            _master_fullpath.name,
        )

        yield from dm_workflow.run_as_plan(
            workflow=wf_workflow_name,
            wait=dm_wait,
            timeout=dm_reporting_time_limit,
            # all kwargs after this line are DM argsDict content
            filePath=_master_fullpath.name,
            sampleName = RE.md["sample"],
            experimentName=dm_experiment.get(),
            scanFilePath=wf_scanFilePath,
            analysisMachine=wf_analysis_machine,
            # TODO: What all can we switch to PV.gets?
            detectorName = wf_detectorName,
            detectorDistanceInMeters = wf_detectorDistanceInMeters,
            cropCenterXInPixels = wf_cropCenterXInPixels,
            cropCenterYInPixels = wf_cropCenterYInPixels,
            cropExtentXInPixels = wf_cropExtentXInPixels,
            cropExtentYInPixels = wf_cropExtentYInPixels,
            probeEnergyInElectronVolts = wf_probeEnergyInElectronVolts,
            numGpus = wf_numGpus,
            settings = wf_settings,
            demand = wf_demand,
            name=wf_name,
        )

        yield from sleep(0.1)
        logger.info(f"dm_workflow id: {dm_workflow.job_id.get()}")

        # upload bluesky run metadata to APS DM
        share_bluesky_metadata_with_dm(dm_experiment.get(), wf_workflow_name, run)

    logger.info("Finished!")
