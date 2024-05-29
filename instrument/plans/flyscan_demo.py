"""
Flyscan using area detector
"""

from bluesky.preprocessors import stage_decorator, run_decorator
from bluesky.plan_stubs import rd, null, move_per_step, sleep
from bluesky.plan_patterns import outer_product, inner_product
from collections import defaultdict
from .local_scans import mv
from ..devices import sgz, positioner_stream
from ..session_logs import logger
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

    # TODO: For now we assume the eiger is the first detector
    eiger_paths = detectors[0].hdf1.make_write_read_paths()
    # Make sure eiger will save image
    detectors[0].auto_save_on()
    # Changes the stage_sigs to the external trigger mode
    detectors[0]._flysetup = True

    # Metadata
    # TODO: More mds?
    motors = list(cycler.keys)  # the cycler inverts the list.
    _md = dict(
        detectors = [det.name for det in detectors],
        motors = [motor.name for motor in motors], 
        plan_name = "flyscan_1d",
        # This assumes the first detector is the eiger.
        eiger_file_path = eiger_paths[1],
        # TODO: a similar scan with a monitor (scaler...)
        hints = dict(monitor=None, detectors=[], scan_type="flyscan")
    )
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])
    
    dimensions = [(motor.hints["fields"], "primary") for motor in motors]
    _md["hints"].setdefault("dimensions", dimensions)

    _md.update(md)

    # Setup detectors
    for det in detectors:
        yield from mv(det.preset_monitor, collection_time)

    # Stop and reset softglue just in case
    yield from sgz.stop_eiger()
    yield from sgz.stop_softglue()
    yield from sgz.reset_plan()

    # Setup the frequency
    yield from sgz.setup_eiger_trigger_plan(trigger_time)
    # TODO: Should we change the speed of the interferometer?
    # yield from sgz.setup_interf_trigger_plan(trigger_time/1000)

    # Move motor to start position using "normal speed"
    args = ()
    for motor, position in list(cycler)[0].items():
        args += (motor, position)
    yield from mv(*args)

    # Change motor speed
    speeds = speeds[::-1]  # The cycler inverts the motor list.
    for motor, speed in zip(motors, speeds):
        if speed is not None:
            motor.stage_sigs["velocity"] = speed

    # Setup names in positioner_stream
    positioner_stream.file_path = eiger_paths[0]
    # TODO: Need a better way to handle this file name....
    positioner_stream.file_name = "positionstream_" + eiger_paths[1].split("/")[-1]

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
