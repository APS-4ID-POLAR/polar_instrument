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
    'qxscan',
    'count',
    'abs_set'
]

from bluesky.plans import (
    scan, grid_scan as bp_grid_scan, count as bp_count, list_scan
)
from bluesky.plan_stubs import (
    mv as bps_mv, abs_set as bps_abs_set, rd, trigger_and_read, move_per_step
)
from bluesky.preprocessors import (
    reset_positions_decorator, relative_set_decorator, subs_decorator
)
from bluesky.plan_patterns import chunk_outer_product_args
from .local_preprocessors import (
    configure_counts_decorator,
    extra_devices_decorator,
    stage_dichro_decorator
)

from toolz import partition
from pathlib import Path
from numpy import array

from ..callbacks.nexus_data_file_writer import nxwriter
from ..devices import counters
from ..devices.qxscan_setup import qxscan_params
from ..devices.energy_device import energy
from ..devices.aps_undulator import undulators
from ..devices.phaseplates import pr1, pr2, pr3, pr_setup
from ..devices.polar_diffractometer import huber_euler
from ..utils._logging_setup import logger
from ..utils.experiment_setup import experiment
from ..utils.run_engine import RE
from ..utils.config import iconfig

logger.info(__file__)

HDF1_NAME_FORMAT = Path(iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"])


class LocalFlag:
    """Stores flags that are used to select and run local scans."""
    dichro = False
    fixq = False
    hkl_pos = {}
    dichro_steps = None


flag = LocalFlag()


def _collect_extras(escan_flag, huber_flag):
    """Collect all detectors that need to be read during a scan."""

    # TODO: most or all of this can be removed if we add these to the energy
    # device directly.

    # Initialize the list of extra devices with the standard set from counters
    extras = counters.extra_devices.copy()

    if escan_flag:
        for und in (undulators.ds, undulators.us):
            und_track = yield from rd(und.tracking)
            if und_track:
                extras.append(und.energy)

        # Do the same for phase plates
        for pr in [pr1, pr2, pr3]:
            # Fetch tracking status asynchronously
            pr_track = yield from rd(pr.tracking)
            if pr_track:
                extras.append(pr.th)

    if huber_flag:
        # extras.append(huber)
        pass

    return extras


def dichro_steps(devices_to_read, take_reading):
    """
    Switch the x-ray polarization for each scan point.
    This will increase the number of points in a scan by a factor that is equal
    to the length of the `pr_setup.dichro_steps` list.
    """
    devices_to_read += [pr_setup.positioner]
    for pos in flag.dichro_steps:
        yield from mv(pr_setup.positioner, pos)
        yield from take_reading(devices_to_read)


def one_local_step(detectors, step, pos_cache, take_reading=trigger_and_read):
    """
    Inner loop for fixQ and dichro scans.

    It is always called in the local plans defined here. It is used as a
    `per_step` kwarg in Bluesky scan plans, such as `bluesky.plans.scan`. But
    note that it requires the `LocalFlag` class.

    Parameters
    ----------
    detectors : iterable
        devices to read
    step : dict
        mapping motors to positions in this step
    pos_cache : dict
        mapping motors to their last-set positions
    take_reading : plan, optional
        function to do the actual acquisition ::
           def take_reading(dets, name='primary'):
                yield from ...
        Callable[List[OphydObj], Optional[str]] -> Generator[Msg], optional
        Defaults to `trigger_and_read`
    """

    devices_to_read = list(step.keys()) + list(detectors)
    yield from move_per_step(step, pos_cache)

    if flag.fixq:
        devices_to_read += [huber_euler]
        args = (huber_euler.h, flag.hkl_pos[huber_euler.h],
                huber_euler.k, flag.hkl_pos[huber_euler.k],
                huber_euler.l, flag.hkl_pos[huber_euler.l])
        yield from bps_mv(*args)

    if flag.dichro:
        yield from dichro_steps(devices_to_read, take_reading)
    else:
        yield from take_reading(devices_to_read)


def one_local_shot(detectors, take_reading=trigger_and_read):
    """
    Inner loop for fixQ and dichro scans.
    To be used as a `per_shot` kwarg in the Bluesky `bluesky.plans.count`.
    It is always called in the local `count` plan defined here. It is used as a
    `per_shot` kwarg in the Bluesky `bluesky.plans.count`. But note that it
    requires the `LocalFlag` class.
    Parameters
    ----------
    detectors : iterable
        devices to read
    take_reading : plan, optional
        function to do the actual acquisition ::
           def take_reading(dets, name='primary'):
                yield from ...
        Callable[List[OphydObj], Optional[str]] -> Generator[Msg], optional
        Defaults to `trigger_and_read`
    """

    devices_to_read = list(detectors)
    if flag.dichro:
        yield from dichro_steps(devices_to_read, take_reading)
    else:
        yield from take_reading(devices_to_read)


def _setup_paths(detectors):

    if None in (experiment.base_experiment_path, experiment.file_base_name):
        raise ValueError(
            "The experiment needs to be setup, please run setup_experiment()"
        )

    _scan_id = RE.md["scan_id"] + 1

    # Master file
    _master_fullpath = str(HDF1_NAME_FORMAT) % (
        str(experiment.experiment_path), experiment.file_base_name, _scan_id
    )
    _master_fullpath += "_master.hdf"

    # Setup area detectors
    _dets_file_paths = {}
    # Relative paths are used in the master file so that data can be copied.
    _rel_dets_paths = {}
    for det in list(detectors):
        # Check if we can and want to get images from this detector
        _setup_images = getattr(det, "setup_images", None)
        _flag = getattr(det, "save_image_flag", False)
        if _setup_images and _flag:
            _fp, _rp = _setup_images(
                experiment.experiment_path,
                experiment.file_base_name,
                _scan_id,
                flyscan=False
            )
            _dets_file_paths[det.name] = str(_fp)
            _rel_dets_paths[det.name] = str(_rp)

    # Check if any of these files exists
    for _fname in [_master_fullpath] + list(_dets_file_paths.values()):
        if Path(_fname).is_file():
            raise FileExistsError(
                f"The file {_fname} already exists! Will not overwrite, "
                "quitting."
            )

    return _master_fullpath, _dets_file_paths, _rel_dets_paths


def setup_nxwritter(_base_path, _master_fullpath, _rel_dets_paths):
    nxwriter.external_files = _rel_dets_paths
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(_base_path)


def count(
        num=1,
        time=None,
        detectors=None,
        delay=None,
        md=None,
        per_shot=None,
        dichro=False,
        lockin=False
):
    """
    Take one or more readings from detectors.
    This is a local version of `bluesky.plans.count`. Note that the `per_shot`
    cannot be set here, as it is used for dichro scans.
    Parameters
    ----------
    num : integer, optional
        number of readings to take; default is 1
        If None, capture data until canceled
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of 'readable' objects. If None, will use the detectors defined in
        `counters.detectors`.
    delay : iterable or scalar, optional
        Time delay in seconds between successive readings; default is 0.
    md : dict, optional
        metadata
    Notes
    -----
    If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
    the plan will raise a ``ValueError`` during iteration.
    """
    fixq = False
    if detectors is None:
        detectors = counters.detectors

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step*_offset for step in _steps]

    flag.fixq = fixq
    per_shot = one_local_shot if fixq or dichro else None

    extras = yield from _collect_extras(False, False)

    _master_fullpath, _dets_file_paths, _rel_dets_paths = (
        _setup_paths(detectors)
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(False, False)

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = dict(
        hints={'monitor': counters.monitor, 'detectors': []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md.update(md or {})

    @subs_decorator(nxwriter.receiver)
    @stage_dichro_decorator(dichro, lockin, None)
    @configure_counts_decorator(detectors, time)
    @extra_devices_decorator(extras)
    def _inner_count():
        yield from bp_count(
            detectors + extras,
            num=num,
            per_shot=per_shot,
            delay=delay,
            md=_md
        )
        # Wait for the master file to finish writing.
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_count())


def ascan(
    *args,
    time=None,
    detectors=None,
    per_step=None,
    fixq=False,
    dichro=False,
    lockin=False,
    md=None
):
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

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step*_offset for step in _steps]

    flag.fixq = fixq
    if per_step is None:
        per_step = one_local_step if fixq or dichro else None
    if fixq:
        flag.hkl_pos = {
            huber_euler.h: huber_euler.h.get().setpoint,
            huber_euler.k: huber_euler.k.get().setpoint,
            huber_euler.l: huber_euler.l.get().setpoint,
        }

    # This allows passing "time" without using the keyword.
    if len(args) % 3 == 2 and time is None:
        time = args[-1]
        args = args[:-1]

    if detectors is None:
        detectors = counters.detectors

    _master_fullpath, _dets_file_paths, _rel_dets_paths = (
        _setup_paths(detectors)
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(energy in args, "huber" in str(args))

    _md = dict(
        hints={'monitor': counters.monitor, 'detectors': []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md["hints"]["scan_type"] = "ascan"

    _md.update(md or {})

    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, args)
    @extra_devices_decorator(extras)
    def _inner_ascan():
        yield from scan(
            detectors + extras,
            *args,
            per_step=per_step,
            md=_md
        )

        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_ascan())


def lup(
    *args,
    time=None,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    per_step=None,
    md=None
):
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
            lockin=lockin,
            dichro=dichro,
            fixq=fixq,
            per_step=per_step,
            md=_md
        ))

    return (yield from inner_lup())


def grid_scan(
    *args,
    time=None,
    detectors=None,
    snake_axes=None,
    lockin=False,
    dichro=False,
    fixq=False,
    per_step=None,
    md=None
):
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

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step*_offset for step in _steps]

    flag.fixq = fixq
    if per_step is None:
        per_step = one_local_step if fixq or dichro else None

    if fixq:
        flag.hkl_pos = {
            huber_euler.h: huber_euler.h.get().setpoint,
            huber_euler.k: huber_euler.k.get().setpoint,
            huber_euler.l: huber_euler.l.get().setpoint,
        }

    # This allows passing "time" without using the keyword.
    if len(args) % 4 == 1 and time is None:
        time = args[-1]
        args = args[:-1]

    if detectors is None:
        detectors = counters.detectors

    _master_fullpath, _dets_file_paths, _rel_dets_paths = (
        _setup_paths(detectors)
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(energy in args, "huber" in str(args))

    _md = dict(
        hints={'monitor': counters.monitor, 'detectors': []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md["hints"]["scan_type"] = "gridscan"

    _md.update(md or {})

    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, args)
    @extra_devices_decorator(extras)
    def _inner_grid_scan():
        yield from bp_grid_scan(
            detectors + extras,
            *args,
            snake_axes=snake_axes,
            per_step=per_step,
            md=_md
        )

        yield from nxwriter.wait_writer_plan_stub()

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


def qxscan(
    edge_energy,
    time=None,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    md=None
):
    """
    Energy scan with fixed delta_K steps.

    WARNING: please run qxscan_params.setup() before using this plan! It will
    use the parameters set in qxscan_params to determine the energy points.

    Parameters
    ----------
    edge_energy : float
        Absorption edge energy. The parameters in qxscan_params offset by this
        energy.
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
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
        position during the scan. Note that hkl is moved ~after~ the other
        motors!
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.scan`
    :func:`lup`
    """

    if detectors is None:
        detectors = counters.detectors

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step*_offset for step in _steps]

    flag.fixq = fixq
    per_step = one_local_step if fixq or dichro else None
    if fixq:
        flag.hkl_pos = {
            huber_euler.h: huber_euler.h.get().setpoint,
            huber_euler.k: huber_euler.k.get().setpoint,
            huber_euler.l: huber_euler.l.get().setpoint,
        }

    # Get energy argument and extras
    energy_list = yield from rd(qxscan_params.energy_list)
    args = (energy, array(energy_list) + edge_energy)

    extras = yield from _collect_extras(energy in args, "huber" in str(args))

    # Setup count time
    factor_list = yield from rd(qxscan_params.factor_list)

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = {'hints': {'monitor': counters.monitor, 'detectors': []}}
    for item in detectors:
        _md['hints']['detectors'].extend(item.hints['fields'])

    _md["hints"]["scan_type"] = "qxscan"
    if dichro:
        _md['hints']['scan_type'] += " dichro"
    if lockin:
        _md['hints']['scan_type'] += " lockin"

    _md.update(md or {})

    _ct = {}
    if time:
        if time < 0 and detectors != [counters.default_scaler]:
            raise TypeError('time < 0 can only be used with scaler.')
        else:
            for det in detectors:
                _ct[det] = abs(time)
                args += (det.preset_monitor, abs(time)*array(factor_list))
    else:
        for det in detectors:
            _ct[det] = yield from rd(det.preset_monitor)
            args += (det.preset_monitor, _ct[det]*array(factor_list))

    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, args)
    @extra_devices_decorator(extras)
    def _inner_qxscan():
        yield from list_scan(
            detectors + extras, *args, per_step=per_step, md=_md
            )

        # put original times back.
        for det, preset in _ct.items():
            yield from mv(det.preset_monitor, preset)

        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_qxscan())


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
