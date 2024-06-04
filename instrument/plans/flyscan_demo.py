"""
Flyscan using area detector
"""

from bluesky.preprocessors import stage_decorator, run_decorator, subs_decorator
from bluesky.plan_stubs import rd, null, move_per_step, sleep
from bluesky.plan_patterns import outer_product, inner_product
from collections import defaultdict
from pathlib import Path
from json import dumps
from .local_scans import mv
from ..devices import sgz, positioner_stream
from ..session_logs import logger
from ..framework import RE
from ..callbacks import nxwriter
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
        detectors,
        cycler,
        speeds,
        trigger_time: float = 0.02,
        collection_time: float = 0.01,
        md: dict = {}
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

    if collection_time > trigger_time:
        raise ValueError(
            f"The collection time ({collection_time}) cannot be larger than the time "
            f"between triggers ({trigger_time})."
        )
    

    #####################
    # Setup files names #
    #####################

    # Collect information to make file names
    _file_name_base = "my_test"
    _scan_id = RE.md["scan_id"] + 1
    _base_path = Path("/home/beams/POLAR/data/2024_2/flyscan_demo_tests/data")
    _fname_format = "%s_%6.6d"

    # Master file
    _master_fullpath = (
        _base_path / ((_fname_format % (_file_name_base, _scan_id)) + ".hdf")
    )

    # Setup area detector
    # TODO: For now we assume the eiger is the first detector
    _eig = detectors[0]
    _eig.hdf1.file_name.set(f"{_file_name_base}").wait()
    _eig.hdf1.file_path.set(str(_base_path / "eiger")).wait()
    _eig.hdf1.file_template.set(f"%s{_fname_format}.h5").wait()
    _eig.hdf1.file_number.set(_scan_id).wait()

    _eiger_paths = detectors[0].hdf1.make_write_read_paths()
    _eiger_fullpath = Path(_eiger_paths[1])
    # Make sure eiger will save image
    detectors[0].auto_save_on()
    # Changes the stage_sigs to the external trigger mode
    detectors[0]._flysetup = True

    _ps_fname = (_fname_format + ".h5") % (_file_name_base, _scan_id)
    _ps_fullpath = _base_path / "positioner_stream" / _ps_fname
    # Setup path and file name in positioner_stream
    positioner_stream.file_path.put(str(_base_path / "positioner_stream"))
    positioner_stream.file_name.put(_ps_fname)

    # Check if any of these files exists
    for _fname in [_master_fullpath, _eiger_fullpath, _ps_fullpath]:
        if _fname.is_file():
            raise FileExistsError(
                f"The file {_fname} already exists! Will not overwrite, quitting."
            )

    ##################
    # nxwriter setup #
    ##################

    _rel_eiger_path = _eiger_fullpath.relative_to(_base_path)
    _rel_ps_path = _ps_fullpath.relative_to(_base_path)

    nxwriter.ad_file_name = str(_rel_eiger_path)
    nxwriter.position_file_name = str(_rel_ps_path)
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(_base_path)

    md.update(dict(master_file=str(nxwriter.file_name)))

    # For now this is here just to show how the templates works.
    templates = [
        ["/entry/detector/eiger/file_path=", str(_rel_eiger_path)],
        ["/entry/instrument/softglue/file_path=", str(_rel_ps_path)],
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
        eiger_file_path = _eiger_paths[1],
        positioner_stream_file_path = str(_ps_fullpath),
        # TODO: a similar scan with a monitor (scaler...)
        hints = dict(monitor=None, detectors=[], scan_type="flyscan")
    )
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])
    
    dimensions = [(motor.hints["fields"], "primary") for motor in motors]
    _md["hints"].setdefault("dimensions", dimensions)

    _md.update(md)

    #################################
    # MOVING DEVICES TO START POINT #
    #################################

    # Setup detectors count time
    for det in detectors:
        yield from mv(det.preset_monitor, collection_time)

    # Stop and reset softglue just in case
    yield from sgz.stop_eiger()
    yield from sgz.stop_softglue()
    yield from sgz.reset_plan()

    # Setup the eiger frequency
    yield from sgz.setup_eiger_trigger_plan(trigger_time)
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
        yield from mv(positioner_stream, 1)
        yield from sgz.start_softglue()

        yield from sgz.start_eiger()
        pos_cache = defaultdict(lambda: None)
        for step in list(cycler):
            yield from move_per_step(step, pos_cache)
        yield from sgz.stop_eiger()

        # This will wait for a full new set of packets.
        # TODO: It's an overkill, maybe Keenan's code can broadcast a signal?
        n = yield from rd(sgz.div_by_n_interf.n)
        _time_per_point = n/1e7
        _number_of_events_per_packet = 1e5/8
        yield from sleep(_time_per_point*_number_of_events_per_packet+ 0.1)

        yield from sgz.stop_softglue()

        print("Stopping the positioner stream, this can take time.")
        yield from mv(positioner_stream, 0)

        return (yield from null()) # Is there something better to do here?

    yield from inner_fly()

    yield from nxwriter.wait_writer_plan_stub()
