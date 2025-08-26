"""Local decorators"""

from bluesky.utils import make_decorator
from bluesky.preprocessors import finalize_wrapper
from bluesky.plan_stubs import mv, null, subscribe, unsubscribe, rd
from ophyd import Kind
from logging import getLogger
from apsbits.core.instrument_init import oregistry

from ..callbacks.dichro_stream import plot_dichro_settings, dichro_bec
from ..utils.counters_class import counters
from ..utils.pr_setup import pr_setup
from ..utils.run_engine import bec

logger = getLogger(__name__)
logger.info(__file__)


def extra_devices_wrapper(plan, extras):

    hinted_stash = []

    def _stage():
        for device in extras:
            for _, component in device._get_components_of_kind(Kind.normal):
                if component.kind == Kind.hinted:
                    component.kind = Kind.normal
                    hinted_stash.append(component)
        yield from null()

    def _unstage():
        for component in hinted_stash:
            component.kind = Kind.hinted
        yield from null()

    def _inner_plan():
        yield from _stage()
        return (yield from plan)

    if len(extras) != 0:
        return (yield from finalize_wrapper(_inner_plan(), _unstage()))
    else:
        return (yield from plan)


def configure_counts_wrapper(plan, detectors, count_time):
    """
    Set all devices with a `preset_monitor` to the same value.

    The original setting is stashed and restored at the end.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects
    monitor : float or None
        If None, the plan passes through unchanged.

    Yields
    ------
    msg : Msg
        messages from plan, with 'set' messages inserted
    """
    original_times = {}

    def setup():
        if count_time < 0:
            if counters.monitor == "Time":
                raise ValueError(
                    'count_time cannot be < 0 because "Time" is the monitor.'
                    "Run counters.plotselect() to change the monitor to a"
                    "scaler channel."
                )

            scaler = counters.monitor_detector

            scaler_channel = getattr(
                scaler.channels, scaler.channels_name_map[counters.monitor]
            )

            # Changing the preset already forces the gate to the "Y"
            yield from mv(scaler_channel.preset, abs(count_time))

        elif count_time > 0:
            args = ()
            for det in detectors:
                original_times[det.preset_monitor] = yield from rd(
                    det.preset_monitor
                )
                args += (det.preset_monitor, count_time)
            yield from mv(*args)

        else:
            raise ValueError("count_time cannot be zero.")

    def reset():
        if count_time < 0:
            scaler = counters.monitor_detector
            scaler_channel = getattr(
                scaler.channels, scaler.channels_name_map[counters.monitor]
            )
            yield from mv(scaler_channel.gate, "N")
        else:
            for mon, time in original_times.items():
                yield from mv(mon, time)

    def _inner_plan():
        yield from setup()
        return (yield from plan)

    if count_time is None:
        return (yield from plan)
    else:
        return (yield from finalize_wrapper(_inner_plan(), reset()))


def stage_dichro_wrapper(plan, dichro, lockin, positioner):
    """
    Stage dichoic scans.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects
    dichro : boolean
        Flag that triggers the stage/unstage process of dichro scans.
    lockin : boolean
        Flag that triggers the stage/unstage process of lockin scans.

    Yields
    ------
    msg : Msg
        messages from plan, with 'subscribe' and 'unsubscribe' messages
        inserted and appended
    """
    _hinted_devices = []
    _lockin_devices = []
    _dichro_token = [None, None]

    def _stage():
        if dichro and lockin:
            raise ValueError("Cannot have both dichro and lockin = True.")

        if lockin:
            for det in counters.detectors:
                hints = det.hints["fields"]
                for name in hints:
                    dev = oregistry.find(name.replace("_", "."))
                    _hinted_devices.append(dev)
                    dev.kind = "normal"

            for scaler in counters._available_scalers:
                for ch in ["LockDC", "LockAC"]:
                    if ch in scaler.channels_name_map.keys():
                        device = getattr(
                            scaler.channels, scaler.channels_name_map[ch]
                        ).s
                        device.kind = "hinted"
                        _lockin_devices.append(device)

            if pr_setup.positioner is None:
                raise ValueError("Phase retarder was not selected.")

            if "th" in pr_setup.positioner.name:
                raise TypeError(
                    "Theta motor cannot be used in lock in!"
                    "Please run pr_setup.config() and choose pzt."
                )

            yield from mv(pr_setup.positioner.parent.selectAC, 1)

        if dichro:
            for i in range(len(positioner)):
                setattr(
                    plot_dichro_settings.settings,
                    f"positioner{i+1}",
                    None if positioner[i] is None else positioner[i].name,
                )

            if len(counters.plot_names) != 0:
                if len(counters.plot_names) > 1:
                    msg = (
                        "There is more than one plotting detector selected, "
                        "but only one can be used. Will use the first one: "
                        f"{counters.plot_names[0]}."
                    )
                    logger.warning(msg)
                    print(f"\n=== Warning: {msg} ===")

                plot_dichro_settings.settings.detector = counters.plot_names[0]

            plot_dichro_settings.settings.monitor = counters.monitor

            dichro_bec.enable_plots()
            bec.disable_plots()

            _dichro_token[0] = yield from subscribe("all", plot_dichro_settings)
            # move PZT to center.
            if "pzt" in pr_setup.positioner.name:
                yield from mv(
                    pr_setup.positioner, pr_setup.positioner.parent.center.get()
                )

    def _unstage():

        if lockin:
            for dev in _lockin_devices:
                dev.kind = "normal"

            for dev in _hinted_devices:
                dev.kind = "hinted"

            yield from mv(pr_setup.positioner.parent.selectDC, 1)

        if dichro:
            # move PZT to off center.
            if "pzt" in pr_setup.positioner.name:
                yield from mv(
                    pr_setup.positioner,
                    pr_setup.positioner.parent.center.get()
                    + pr_setup.offset.get(),
                )

            yield from unsubscribe(_dichro_token[0])
            dichro_bec.disable_plots()
            bec.enable_plots()

    def _inner_plan():
        yield from _stage()
        return (yield from plan)

    return (yield from finalize_wrapper(_inner_plan(), _unstage()))


extra_devices_decorator = make_decorator(extra_devices_wrapper)
configure_counts_decorator = make_decorator(configure_counts_wrapper)
stage_dichro_decorator = make_decorator(stage_dichro_wrapper)
