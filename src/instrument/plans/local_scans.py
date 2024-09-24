"""
Modifed bluesky scans
"""

__all__ = [
    'lup',
    'ascan',
    'mv',
    'mvr',
    'grid_scan',
    'rel_grid_scan',
    'count',
    'abs_set'
]

from bluesky.plans import (
    scan, grid_scan as bp_grid_scan, count as bp_count
)
from bluesky.plan_stubs import mv as bps_mv, abs_set as bps_abs_set
from bluesky.preprocessors import (
    reset_positions_decorator, relative_set_decorator
)
from bluesky.plan_patterns import chunk_outer_product_args
from .local_preprocessors import (
    configure_counts_decorator,
    extra_devices_decorator
)
from ..devices import counters

from toolz import partition

from ..utils import logger
logger.info(__file__)


def _collect_extras():
    """Collect all detectors that need to be read during a scan."""
    return counters.extra_devices.copy()


def count(detectors=None, num=1, time=None, delay=None, md=None, per_shot=None):
    """
    Take one or more readings from detectors.
    This is a local version of `bluesky.plans.count`. Note that the `per_shot`
    cannot be set here, as it is used for dichro scans.
    Parameters
    ----------
    detectors : list, optional
        List of 'readable' objects. If None, will use the detectors defined in
        `counters.detectors`.
    num : integer, optional
        number of readings to take; default is 1
        If None, capture data until canceled
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    delay : iterable or scalar, optional
        Time delay in seconds between successive readings; default is 0.
    md : dict, optional
        metadata
    Notes
    -----
    If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
    the plan will raise a ``ValueError`` during iteration.
    """

    if detectors is None:
        detectors = counters.detectors

    extras = _collect_extras()

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = {'hints': {'monitor': counters.monitor, 'detectors': []}}
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md.update(md or {})

    @configure_counts_decorator(detectors, time)
    @extra_devices_decorator(extras)
    def _inner_count():
        yield from bp_count(
            detectors + extras,
            num=num,
            delay=delay,
            per_shot=per_shot,
            delay=delay,
            md=_md
            )

    return (yield from _inner_count())


def ascan(*args, time=None, detectors=None, per_step=None, md=None):
    """
    Scan over one multi-motor trajectory.

    This is a local version of `bluesky.plans.scan`. Note that the `per_step`
    cannot be set here, as it is used for dichro scans.

    Parameters
    ----------
    *args :
        For one dimension, ``motor, start, stop, number of points``.
        In general:
        .. code-block:: python
            motor1, start1, stop1,
            motor2, start2, start2,
            ...,
            motorN, startN, stopN,
            number of points
        Motors can be any 'settable' object (motor, temp controller, etc.)
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.scan`
    :func:`lup`
    """

    # This allows passing "time" without using the keyword.
    if len(args) % 3 == 2 and time is None:
        time = args[-1]
        args = args[:-1]

    if detectors is None:
        detectors = counters.detectors

    # TODO: why yield from!?
    # extras = yield from _collect_extras(energy in args, "fourc" in str(args))
    extras = _collect_extras()

    # for det in detectors + extras:
    #     if isinstance(det, EIGER_DETECTORS):
    #         det.file.base_name = f"scan{RE.md['scan_id'] + 1}"

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = {'hints': {'monitor': counters.monitor, 'detectors': []}}
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md["hints"]["scan_type"] = "ascan"

    _md.update(md or {})

    @configure_counts_decorator(detectors, time)
    @extra_devices_decorator(extras)
    def _inner_ascan():
        yield from scan(
            detectors + extras,
            *args,
            per_step=per_step,
            md=_md
            )

    return (yield from _inner_ascan())


def lup(*args, time=None, detectors=None, per_step=None, md=None):
    """
    Scan over one multi-motor trajectory relative to current position.

    This is a local version of `bluesky.plans.rel_scan`. Note that the
    `per_step` cannot be set here, as it is used for dichro scans.

    Parameters
    ----------
    *args :
        For one dimension, ``motor, start, stop, number of points``.
        In general:
        .. code-block:: python
            motor1, start1, stop1,
            motor2, start2, start2,
            ...,
            motorN, startN, stopN,
            number of points
        Motors can be any 'settable' object (motor, temp controller, etc.)
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan.
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    fixq : boolean, optional
        Flag for fixQ scans. If True, it will fix the diffractometer hkl
        position during the scan. This is particularly useful for energy scan.
        Note that hkl is moved ~after~ the other motors!
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.rel_scan`
    :func:`ascan`
    """

    _md = {'plan_name': 'rel_scan'}
    md = md or {}
    _md.update(md)
    motors = [motor for motor, _, _ in partition(3, args)]

    @reset_positions_decorator(motors)
    @relative_set_decorator(motors)
    def inner_lup():
        return (yield from ascan(
            *args,
            time=time,
            detectors=detectors,
            per_step=per_step,
            md=_md
        ))

    return (yield from inner_lup())


def grid_scan(*args, time=None, detectors=None, snake_axes=None, per_step=None, md=None):
    """
    Scan over a mesh; each motor is on an independent trajectory.
    Parameters
    ----------
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)
        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md: dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """

    # This allows passing "time" without using the keyword.
    if len(args) % 4 == 1 and time is None:
        time = args[-1]
        args = args[:-1]

    if detectors is None:
        detectors = counters.detectors

    # extras = yield from _collect_extras(energy in args, "fourc" in str(args))
    extras = _collect_extras()

    # for det in detectors + extras:
    #     if isinstance(det, EIGER_DETECTORS):
    #         det.file.base_name = f"scan{RE.md['scan_id'] + 1}"

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = {'hints': {'monitor': counters.monitor, 'detectors': []}}
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md["hints"]["scan_type"] = "gridscan"

    _md.update(md or {})

    @configure_counts_decorator(detectors, time)
    @extra_devices_decorator(extras)
    def _inner_grid_scan():
        yield from bp_grid_scan(
            detectors + extras,
            *args,
            snake_axes=snake_axes,
            per_step=per_step,
            md=_md
        )
    return (yield from _inner_grid_scan())


def rel_grid_scan(*args, time=None, detectors=None, snake_axes=None,
                  per_step=None, md=None):
    """
    Scan over a mesh relative to current position.

    Each motor is on an independent trajectory.

    Parameters
    ----------
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)
        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    fixq : boolean, optional
        Flag for fixQ scans. If True, it will fix the diffractometer hkl
        position during the scan. This is particularly useful for energy scan.
        Note that hkl is moved ~after~ the other motors!
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md: dict, optional
        metadata

    See Also
    --------
    :func:`grid_scan`
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """

    _md = {'plan_name': 'rel_grid_scan'}
    _md.update(md or {})
    motors = [m[0] for m in chunk_outer_product_args(args)]

    @reset_positions_decorator(motors)
    @relative_set_decorator(motors)
    def inner_rel_grid_scan():
        return (yield from grid_scan(
            *args,
            time=time,
            detectors=detectors,
            snake_axes=snake_axes,
            per_step=per_step,
            md=_md
        ))

    return (yield from inner_rel_grid_scan())


def mv(*args, **kwargs):
    """
    Move one or more devices to a setpoint, and wait for all to complete.

    This is a local version of `bluesky.plan_stubs.mv`. If more than one device
    is specifed, the movements are done in parallel.

    Parameters
    ----------
    args :
        device1, value1, device2, value2, ...
    kwargs :
        passed to bluesky.plan_stubs.mv

    Yields
    ------
    msg : Msg

    See Also
    --------
    :func:`bluesky.plan_stubs.mv`
    """

    def _inner_mv():
        yield from bps_mv(*args, **kwargs)

    return (yield from _inner_mv())


def mvr(*args, **kwargs):
    """
    Move one or more devices to a relative setpoint. Wait for all to complete.
    If more than one device is specified, the movements are done in parallel.

    This is a local version of `bluesky.plan_stubs.mvr`.

    Parameters
    ----------
    args :
        device1, value1, device2, value2, ...
    kwargs :
        passed to bluesky.plan_stub.mvr
    Yields
    ------
    msg : Msg
    See Also
    --------
    :func:`bluesky.plan_stubs.rel_set`
    :func:`bluesky.plan_stubs.mv`
    """
    objs = []
    for obj, _ in partition(2, args):
        objs.append(obj)

    @relative_set_decorator(objs)
    def _inner_mvr():
        return (yield from mv(*args, **kwargs))

    return (yield from _inner_mvr())


def abs_set(*args, **kwargs):
    """
    Set a value. Optionally, wait for it to complete before continuing.
    This is a local version of `bluesky.plan_stubs.abs_set`. If more than one
    device is specifed, the movements are done in parallel.

    Parameters
    ----------
    obj : Device
    group : string (or any hashable object), optional
        identifier used by 'wait'
    wait : boolean, optional
        If True, wait for completion before processing any more messages.
        False by default.
    args :
        passed to obj.set()
    kwargs :
        passed to obj.set()

    Yields
    ------
    msg : Msg

    See Also
    --------
    :func:`bluesky.plan_stubs.rel_set`
    :func:`bluesky.plan_stubs.wait`
    :func:`bluesky.plan_stubs.mv`
    """

    def _inner_abs_set():
        yield from bps_abs_set(*args, **kwargs)

    return (yield from _inner_abs_set())
