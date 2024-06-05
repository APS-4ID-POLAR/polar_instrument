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
from ..devices import sgz, positioner_stream, dm_experiment, dm_workflow
from ..session_logs import logger
from ..framework import RE, cat
from ..callbacks import nxwriter
from ..utils import dm_get_experiment_data_path
logger.info(__file__)


__all__ = "flyscan_snake flyscan_1d flyscan_cycler".split()


def flyscan_snake(
        eiger,
        *args,
        speed: float = 10,
        trigger_time: float = 0.02,
        collection_time: float = 0.01,
        md: dict = {}
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

    detectors = [eiger]
    cycler = outer_product(args + (2, True))
    yield from flyscan_cycler(
        detectors,
        cycler,
        speeds=[None, speed],
        trigger_time=trigger_time,
        collection_time=collection_time,
        md=md
        )

def flyscan_1d(
        eiger,
        motor,
        start,
        end,
        speed: float = 10,
        trigger_time: float = 0.02,
        collection_time: float = 0.01,
        md: dict = {},
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
    detectors = [eiger]
    cycler = inner_product(2, (motor, start, end))
    yield from flyscan_cycler(
        detectors,
        cycler,
        speeds=[speed],
        trigger_time=trigger_time,
        collection_time=collection_time,
        md=md
        )

def flyscan_cycler(
        detectors: list,
        cycler,
        speeds: list,
        trigger_time: float = 0.02,
        collection_time: float = 0.01,
        md: dict = {},
        templates: list = [],
        file_name_base: str = "scan",
        # DM workflow kwargs ----------------------------------------
        # wf_smooth: str = "sqmap",
        # wf_gpuID: int = -1,
        # wf_beginFrame: int = 1,
        # wf_endFrame: int = -1,
        # wf_strideFrame: int = 1,
        # wf_avgFrame: int = 1,
        # wf_type: str = "Multitau",
        # wf_dq: str = "all",
        # wf_verbose: bool = False,
        # wf_saveG2: bool = False,
        # wf_overwrite: bool = False,
        analysis_machine: str = "polaris",
        workflow_name: str = "ptychodus",
        # internal kwargs ----------------------------------------
        dm_concise: bool = False,
        dm_wait: bool = False,
        dm_reporting_period: float = 10*60,  # TODO: change?
        dm_reporting_time_limit: float = 10**6, # TODO: change?
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

    if collection_time > trigger_time:
        raise ValueError(
            f"The collection time ({collection_time}) cannot be larger than the time "
            f"between triggers ({trigger_time})."
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
    _fname_format = "%s_%6.6d"

    # Master file
    _master_fullpath = (
        _base_path / ((_fname_format % (file_name_base, _scan_id)) + ".hdf")
    )

    # Setup area detector
    _eiger_folder = _base_path / "eiger"

    # TODO: For now we assume the eiger is the first detector
    _eig = detectors[0]
    _eig.hdf1.file_name.set(f"{file_name_base}").wait()
    _eig.hdf1.file_path.set(_eiger_folder).wait()
    _eig.hdf1.file_template.set(f"%s{_fname_format}.h5").wait()
    _eig.hdf1.file_number.set(_scan_id).wait()

    _eiger_fullpath = Path(detectors[0].hdf1.make_write_read_paths()[1])

    # Make sure eiger will save image
    detectors[0].auto_save_on()
    # Changes the stage_sigs to the external trigger mode
    detectors[0]._flysetup = True
    
    # Setup positioner stream
    _ps_folder = _base_path / "positioner_stream"
    if not _ps_folder.is_dir():
        _ps_folder.mkdir()

    _ps_fname = (_fname_format + ".h5") % (file_name_base, _scan_id)
    _ps_fullpath = _ps_folder / _ps_fname

    # Setup path and file name in positioner_stream
    # SOFTGLUE_PROBLEM
    # positioner_stream.file_path.put(str(_ps_folder))
    # positioner_stream.file_name.put(_ps_fname)

    # Check if any of these files exists
    for _fname in [_master_fullpath, _eiger_fullpath, _ps_fullpath]:
        if _fname.is_file():
            raise FileExistsError(
                f"The file {_fname} already exists! Will not overwrite, quitting."
            )

    #################################################
    # nxwriter - creates and setup the master file  #
    #################################################

    # Relative paths are used in the master file so that data can be copied.
    _rel_eiger_path = _eiger_fullpath.relative_to(_base_path)
    _rel_ps_path = _ps_fullpath.relative_to(_base_path)

    # Sets the file names
    nxwriter.ad_file_name = str(_rel_eiger_path)
    nxwriter.position_file_name = str(_rel_ps_path)
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(_base_path)

    md.update(dict(master_file=str(nxwriter.file_name)))

    # For now this is here just to show how the templates works.
    templates += [
        ["/entry/eiger_file_path=", str(_rel_eiger_path)],
        ["/entry/softglue_file_path=", str(_rel_ps_path)],
    ]

    md[nxwriter.template_key] = dumps(templates)  # <-- adds the templates

    ############
    # METADATA #
    ############

    motors = list(cycler.keys)  # the cycler inverts the list.
    _md = dict(
        detectors = [det.name for det in detectors],
        motors = [motor.name for motor in motors], 
        plan_name = "flyscan_cycler",
        # This assumes the first detector is the eiger.
        eiger_relative_file_path = str(_rel_eiger_path),
        eiger_full_file_path = str(_eiger_fullpath),
        positioner_stream_full_file_path = str(_ps_fullpath),
        positioner_stream_relative_file_path = str(_rel_ps_path),
        # TODO: a similar scan with a monitor (scaler...)
        hints = dict(monitor=None, detectors=[], scan_type="flyscan")
    )
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])
    
    dimensions = [(motor.hints["fields"], "primary") for motor in motors]
    _md["hints"].setdefault("dimensions", dimensions)

    _md = build_run_metadata_dict(
        _md,
        # ALL following kwargs are stored under RE.md["data_management"]
        smooth=wf_smooth,
        gpuID=wf_gpuID,
        beginFrame=wf_beginFrame,
        endFrame=wf_endFrame,
        strideFrame=wf_strideFrame,
        avgFrame=wf_avgFrame,
        type=wf_type,
        dq=wf_dq,
        verbose=wf_verbose,
        saveG2=wf_saveG2,
        overwrite=wf_overwrite,
        analysisMachine=analysis_machine,
    )

    _md.update(md)

    #################################
    # MOVING DEVICES TO START POINT #
    #################################

    # DM workflow
    yield from mv(
        dm_workflow.concise_reporting, dm_concise,
        dm_workflow.reporting_period, dm_reporting_period,
    )

    # Setup detectors count time
    for det in detectors:
        yield from mv(det.preset_monitor, collection_time)

    # Stop and reset softglue just in case
    # SOFTGLUE_PROBLEM
    # yield from sgz.stop_eiger()
    # yield from sgz.stop_softglue()
    # yield from sgz.reset_plan()

    # Stop positioner stream just in case
    # SOFTGLUE_PROBLEM
    # yield from mv(positioner_stream, 0)

    # Setup the eiger frequency
    # SOFTGLUE_PROBLEM
    # yield from sgz.setup_eiger_trigger_plan(trigger_time)
    # TODO: Should we change the speed of the interferometer?
    # yield from sgz.setup_interf_trigger_plan(trigger_time/1000)

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
        # SOFTGLUE_PROBLEM
        # yield from mv(positioner_stream, 1)
        # yield from sgz.start_softglue()

        # yield from sgz.start_eiger()
        yield from mv(detectors[0].cam.acquire, 1)
        pos_cache = defaultdict(lambda: None)
        for step in list(cycler):
            yield from move_per_step(step, pos_cache)
        yield from mv(detectors[0].cam.acquire, 0)
        # yield from sgz.stop_eiger()

        # This will wait for a full new set of packets.
        # TODO: It's an overkill, maybe Keenan's code can broadcast a signal?
        # n = yield from rd(sgz.div_by_n_interf.n)
        # _time_per_point = n/1e7
        # _number_of_events_per_packet = 1e5/8
        # yield from sleep(_time_per_point*_number_of_events_per_packet+ 0.1)
        yield from sleep(0.1)

        # yield from sgz.stop_softglue()

        # print("Stopping the positioner stream, this can take time.")
        # yield from mv(positioner_stream, 0)

        return (yield from null()) # Is there something better to do here?

    uid = yield from inner_fly()

    # Get the bluesky run
    run = cat[uid]

    # Wait for the master file to finish writing.
    yield from nxwriter.wait_writer_plan_stub()

    #############################
    # START THE APS DM WORKFLOW #
    #############################
    logger.info(
        "DM workflow %r, filePath=%r",
        workflow_name,
        _eiger_fullpath.name,
    )
    yield from dm_workflow.run_as_plan(
        workflow=workflow_name,
        wait=dm_wait,
        timeout=dm_reporting_time_limit,
        # all kwargs after this line are DM argsDict content
        filePath=_eiger_fullpath.name,
        experimentName=dm_experiment.get(),
        analysisMachine=analysis_machine,
        # from the plan's API
        # smooth=wf_smooth,
        # gpuID=wf_gpuID,
        # beginFrame=wf_beginFrame,
        # endFrame=wf_endFrame,
        # strideFrame=wf_strideFrame,
        # avgFrame=wf_avgFrame,
        # type=wf_type,
        # dq=wf_dq,
        # verbose=wf_verbose,
        # saveG2=wf_saveG2,
        # overwrite=wf_overwrite,
        detectorDistanceInMeters = 2.335,
        cropCenterXInPixels = 540,
        cropCenterYInPixels = 259,
        cropExtentXInPixels = 256,
        cropExtentYInPixels = 256,
        probeEnergyInElectronVolts = 10000,
        defocusDistanceInMeters = 0.000800,
        numGpus = 2,
        settings = "/home/beams/POLAR/ptychodusDefaults/default-settings.ini",
        # patternsFile (from area detector) --> ?
        demand = False
    )

    # upload bluesky run metadata to APS DM
    share_bluesky_metadata_with_dm(dm_experiment.get(), workflow_name, run)

    logger.info("Finished!")
