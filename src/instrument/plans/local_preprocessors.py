""" Local decorators """

from bluesky.utils import make_decorator
from bluesky.preprocessors import finalize_wrapper
from bluesky.plan_stubs import mv, null, subscribe, unsubscribe
from ophyd import Kind
from ..callbacks.dichro_stream import plot_dichro_settings, dichro_bec
from ..devices import counters
from ..devices.phaseplates import pr_setup
from ..utils.run_engine import bec
from ..utils._logging_setup import logger
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
    original_monitor = []

    def setup():
        if count_time < 0:
            raise ValueError('count_time cannot be < 0.')
        elif count_time > 0:
            for det in detectors:
                yield from mv(det.preset_monitor, count_time)
        else:
            raise ValueError('count_time cannot be zero.')

    # def reset():
    #     for det, time in original_times.items():
    #         yield from mv(det.preset_monitor, time)
    def reset():
        for det, time in original_times.items():
            yield from mv(det.preset_monitor, time)
            if det == counters.default_scaler and len(original_monitor) == 1:
                det.monitor = original_monitor[0]

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
    _current_scaler_plot = []
    _dichro_token = [None, None]

    def _stage():

        if dichro and lockin:
            raise ValueError('Cannot have both dichro and lockin = True.')

        if lockin:
            for chan in counters.default_scaler.channels.component_names:
                scaler_channel = getattr(counters.default_scaler.channels, chan)
                if scaler_channel.kind.value >= 5:
                    _current_scaler_plot.append(scaler_channel.s.name)

            counters.default_scaler.select_plot_channels(['LockDC', 'LockAC'])

            if pr_setup.positioner is None:
                raise ValueError('Phase retarder was not selected.')

            if 'th' in pr_setup.positioner.name:
                raise TypeError('Theta motor cannot be used in lock in! \
                                Please run pr_setup.config() and choose \
                                pzt.')

            yield from mv(pr_setup.positioner.parent.selectAC, 1)
            # yield from mv(pr_setup.positioner.parent.ACstatus, 2)

        if dichro:

            # TODO: This will only work for 1 motor and 1 detector!
            plot_dichro_settings.settings.positioner = (
                "None" if positioner is None else positioner[0].name
            )

            dichro_bec.enable_plots()
            bec.disable_plots()

            _dichro_token[0] = yield from subscribe(
                "all", plot_dichro_settings
            )
            # move PZT to center.
            if 'pzt' in pr_setup.positioner.name:
                yield from mv(
                    pr_setup.positioner, pr_setup.positioner.parent.center.get()
                )

    def _unstage():

        if lockin:
            counters.default_scaler.select_plot_channels(_current_scaler_plot)
            yield from mv(pr_setup.positioner.parent.selectDC, 1)
            # yield from mv(pr_setup.positioner.parent.ACstatus, 0)

        if dichro:
            # move PZT to off center.
            if 'pzt' in pr_setup.positioner.name:
                yield from mv(pr_setup.positioner,
                              pr_setup.positioner.parent.center.get() +
                              pr_setup.offset.get())

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
