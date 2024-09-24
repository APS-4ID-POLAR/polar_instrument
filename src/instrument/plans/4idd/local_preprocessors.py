""" Local decorators """

from bluesky.utils import make_decorator
from bluesky.preprocessors import finalize_wrapper
from bluesky.plan_stubs import (
    mv, sleep, abs_set, rd, null, subscribe, unsubscribe
)
from ophyd import Signal, Kind
from ophyd.status import SubscriptionStatus
from ..devices import scalerd, pr_setup, mag6t
from ..callbacks.dichro_stream import plot_dichro_settings, dichro_bec
from ..framework import bec

from ..session_logs import logger
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


# TODO: This is a workaround. Maybe the best fix would be to turn
# ramp_button and switch_heater into PVPositioners.
class SetSignal(Signal):

    """ Signal that only matters for the set function """

    def __init__(self, *args, timeout=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeout = timeout

    def set(self, device, function):
        return SubscriptionStatus(device, function, timeout=self._timeout)


def _difference_check(target, tolerance):
    """
    Returns a callback function that checks the distance from target.

    Parameters
    ----------
    target : float
        Final position.
    tolerance : float
        Maximum accepted tolerance.

    Returns
    -------
    check_pos : function
        Function that can be used as a callback of SubscriptionStatus.
    """
    def check_pos(value=None, **kwargs):
        return abs(value-target) <= tolerance

    return check_pos


def _status_check(target):
    """
    Returns a callback function that checks the positioner status.

    Parameters
    ----------
    target : list
        List of acceptable status.

    Returns
    -------
    check_pos : function
        Function that can be used as a callback of SubscriptionStatus.
    """
    def check_pos(value=None, **kwargs):
        return value in target

    return check_pos


def stage_ami_wrapper(plan, magnet, turn_off=True):
    """
    Stage the AMI magnet.

    Turns on/off the persistence switch heater before/after the magnetic field
    scan or move.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects
    magnet : boolean
        Flag that triggers the stage/unstage.

    Yields
    ------
    msg : Msg
        messages from plan, with 'subscribe' and 'unsubscribe' messages
        inserted and appended
    """

    # This just needs to be set once here.
    signal = SetSignal(name='tmp')

    def _stage():

        _update_rate = yield from rd(mag6t.field.update_rate)
        if _update_rate <= 5:
            yield from mv(mag6t.field.update_rate, 6)

        _heater_status = yield from rd(mag6t.field.switch_heater)

        if _heater_status != 'On':
            # Click current ramp button
            yield from mv(mag6t.field.ramp_button, 1)

            # Wait for the supply current to match the magnet.
            target = yield from rd(mag6t.field.current)
            function = _difference_check(target, tolerance=0.01)
            yield from abs_set(signal, mag6t.field.supply_current, function,
                               wait=True)

            # Turn on persistance switch heater.
            yield from mv(mag6t.field.switch_heater, 'On')
            yield from sleep(2)

            # Wait for the heater to be on.
            function = _status_check(target=[3])
            yield from abs_set(signal, mag6t.field.magnet_status, function,
                               wait=True)

            # Click current ramp button
            yield from mv(mag6t.field.ramp_button, 1)

    def _unstage():

        # Wait for the voltage to be zero.
        function = _difference_check(target=0.0, tolerance=0.02)
        yield from abs_set(signal, mag6t.field.voltage, function,
                           wait=True)

        # Turn off persistance switch heater
        yield from mv(mag6t.field.switch_heater, 'Off')
        yield from sleep(2)

        # Wait for the heater to be off.
        function = _status_check(target=[2, 3])
        yield from abs_set(signal, mag6t.field.magnet_status, function,
                           wait=True)

        # Wait for the current to go to zero.
        yield from mv(mag6t.field.zero_button, 1)
        function = _status_check(target=[8])
        yield from abs_set(
            signal, mag6t.field.magnet_status, function, wait=True
        )
        yield from sleep(1)

    def _inner_plan():
        yield from _stage()
        return (yield from plan)

    if magnet:
        return (
            (yield from finalize_wrapper(_inner_plan(), _unstage()))
            if turn_off else
            (yield from _inner_plan())
        )
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
            if detectors != [scalerd]:
                raise ValueError('count_time can be < 0 only if the scalerd '
                                 'is only detector used.')
            else:
                if scalerd.monitor == 'Time':
                    raise ValueError('count_time can be < 0 only if '
                                     'scalerd.monitor is not "Time".')
                original_times[scalerd] = yield from rd(scalerd.preset_monitor)
                yield from mv(scalerd.preset_monitor, abs(count_time))

        elif count_time > 0:
            for det in detectors:
                if det == scalerd:
                    original_monitor.append(scalerd.monitor)
                    det.monitor = 'Time'
                original_times[det] = yield from rd(det.preset_monitor)
                yield from mv(det.preset_monitor, count_time)
        else:
            raise ValueError('count_time cannot be zero.')

    def reset():
        for det, time in original_times.items():
            yield from mv(det.preset_monitor, time)
            if det == scalerd and len(original_monitor) == 1:
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
            for chan in scalerd.channels.component_names:
                scaler_channel = getattr(scalerd.channels, chan)
                if scaler_channel.kind.value >= 5:
                    _current_scaler_plot.append(scaler_channel.s.name)

            scalerd.select_plot_channels(['Lock DC', 'Lock AC'])

            if pr_setup.positioner is None:
                raise ValueError('Phase retarder was not selected.')

            if 'th' in pr_setup.positioner.name:
                raise TypeError('Theta motor cannot be used in lock in! \
                                Please run pr_setup.config() and choose \
                                pzt.')

            yield from mv(pr_setup.positioner.parent.selectAC, 1)

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
                yield from mv(pr_setup.positioner,
                              pr_setup.positioner.parent.center.get())

    def _unstage():

        if lockin:
            scalerd.select_plot_channels(_current_scaler_plot)
            yield from mv(pr_setup.positioner.parent.selectDC, 1)

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
stage_ami_decorator = make_decorator(stage_ami_wrapper)
