"""
Flyscan using area detector
"""

from bluesky.preprocessors import stage_decorator, run_decorator
from bluesky.plan_stubs import rd, null
from ..devices import sgz
from .local_scans import mv


def flyscan_linear(
        detectors,
        motor,
        start,
        end,
        speed,
        trigger_time,
        collection_time,
        md: dict = {}
    ):

    if collection_time > trigger_time:
        raise ValueError(
            f"The collection time ({collection_time}) cannot be larger than the time "
            f"between triggers ({trigger_time})."
        )

    ### Setup ###

    # Metadata
    _md = dict(
        # This assumes the first detector is the eiger.
        eiger_file_path = detectors[0].hdf1.make_write_read_paths()[1]
    )
    _md.update(md)

    # Setup detectors
    for det in detectors:
        yield from mv(det.preset_monitor, collection_time)
    
    # This again assumes the eiger is the first (and only detector)
    # Changes the stage_sigs to the external trigger mode
    # Staging already clicks the acquire button.
    yield from detectors[0].setup_external_trigger()

    # Stop softglue just in case
    yield from sgz.stop_plan()

    # Setup the frequency
    yield from sgz.setup_trigger_time_plan(trigger_time)

    # Move motor to start position using "normal speed"
    yield from mv(motor, start)

    # Change motor speed
    _motor_speed_stash = yield from rd(motor.velocity)
    yield from mv(motor.velocity, speed)

    @stage_decorator(list(detectors) + list(motor))
    @run_decorator(md=_md)
    def inner_fly():
        yield from sgz.start_plan()
        yield from mv(motor, end)
        yield from sgz.stop_plan()
        return (yield from null()) # Is there something better to do here?

    yield from inner_fly()

    # Put speed back
    yield from mv(motor.velocity, _motor_speed_stash)  

    # Returns to manual trigger
    yield from detectors[0].setup_manual_trigger()
