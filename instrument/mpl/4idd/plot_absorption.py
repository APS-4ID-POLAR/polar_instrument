from polartools.absorption import (load_multi_xas, load_multi_dichro,
                                   load_multi_lockin)
from warnings import warn
from ..framework import cat
from ..mpl import plt
from ..utils import counters
from ..session_logs import logger
logger.info(__file__)

__all__ = ['plot_xas', 'plot_dichro', 'plot_lockin']


def plot_xas(scans=-1, positioner=None, detector=None, monitor=None,
             fluo=False, label=None, ax=None):
    """
    Plot the absorption spectrum.

    Parameters
    ----------
    scans : int, uid or iterable of ints, uid, optional
        Scan number or uid. If a list of scans is passed, it will average them.
        Defaults to the last scan.
    positioner : str, optional
        Name of the positioner used. If None, it defaults to the monochromator.
    detector : str, optional
        Name of the detector used. If None, it defaults to the Ion Ch 5.
    monitor : str, optional
        Name of the detector used as monitor. If None, it defaults to the Ion
        Ch 4.
    fluo : bool, optional
        Flag to choose to process as transmission (False) or fluorescence
        (True).
    label : str, optional
        Label for this data. If None, it defaults to `scans`. This is useful
        when comparing multiple samples.
    ax : matplotlib axes, optional
        Axes instance to use in the plot. If None, it will produce one.

    Returns
    -------
    fig, ax : matplotlib figure and axes instances
        Useful to reuse or modify this figure.

    See also
    --------
    :func:`polartools.absorption.load_multi_xas`
    """

    try:
        scans = list(scans)
    except TypeError:
        scans = [scans]

    if detector is None:
        detector = []
        for det in counters.detectors:
            detector.extend(det.hints['fields'])
        if len(detector) > 1:
            warn(f"Found multiple hinted detectors: {detector}, using the "
                 f"first one: {detector[0]}")
            detector = detector[0]

    if monitor is None:
        monitor = counters.monitor

    energy, xas, _ = load_multi_xas(
        scans, cat, positioner=positioner, detector=detector, monitor=monitor,
        transmission=not fluo
        )

    if ax is None:
        fig, ax = plt.subplots()
    else:
        plt.sca(ax)
        fig = ax.figure

    if label is None:
        label = f'{scans}'

    plt.plot(energy, xas, label=label)
    plt.ylabel('XAS')
    plt.xlabel('Energy (keV)')
    plt.tight_layout()

    return fig, ax


def plot_lockin(scans_plus, scans_minus, positioner=None, fluo=False,
                title=''):
    """
    Plot the XMCD signal measured in lockin.

    If either scans input is None, it will skip it.

    Parameters
    ----------
    scans_plus : int, uid or iterable of ints, uid
        Scan number or uid of scans measured with + magnetic field. If a list
        of scans is passed, it will average them.
    scans_minus : int, uid or iterable of ints, uid
        Scan number or uid of scans measured with - magnetic field. If a list
        of scans is passed, it will average them.
    positioner : str, optional
        Name of the positioner used. If None, it defaults to the monochromator.
    fluo : bool, optional
        Flag to choose to process as transmission (False) or fluorescence
        (True).
    title : str, optional
        Title for the plot. By default it will add the scan numbers to it.

    Returns
    -------
    fig, ax : matplotlib figure and axes instances
        Useful to modify this figure.

    See also
    --------
    :func:`polartools.absorption.load_multi_lockin`
    """

    fig, axs = plt.subplots(2, 2, figsize=(8, 6))

    results = []
    for scans, label in zip([scans_plus, scans_minus], ['plus', 'minus']):
        if scans is not None:
            try:
                scans = list(scans)
            except TypeError:
                scans = [scans]

            if title != '':
                title += '\n'
            title += f'{label}: {scans}'

            results.append(load_multi_lockin(
                scans, cat, positioner=positioner, transmission=not fluo
                ))

            _plot_one_xmcd(results[-1], axs[0], label)

    if len(results) > 1:
        combined = (
            results[0][0],  # energy
            (results[0][3] - results[0][3])/2.,  # xmcd
            (results[0][3] + results[0][3])/2.,  # artifact
            )

        _plot_combined_xmcd(combined, axs[1])

    plt.suptitle(title)
    plt.tight_layout()

    return fig, axs


def plot_dichro(scans_plus, scans_minus, positioner=None, detector=None,
                monitor=None, fluo=False, title=''):

    """
    Plot the XMCD signal measured in lockin.

    If either scans input is None, it will skip it.s

    Parameters
    ----------
    scans_plus : int, uid or iterable of ints, uid
        Scan number or uid of scans measured with + magnetic field. If a list
        of scans is passed, it will average them.
    scans_minus : int, uid or iterable of ints, uid
        Scan number or uid of scans measured with - magnetic field. If a list
        of scans is passed, it will average them.
    positioner : str, optional
        Name of the positioner used. If None, it defaults to the monochromator.
    detector : str, optional
        Name of the detector used. If None, it defaults to the Ion Ch 5.
    monitor : str, optional
        Name of the detector used as monitor. If None, it defaults to the Ion
        Ch 4.
    fluo : bool, optional
        Flag to choose to process as transmission (False) or fluorescence
        (True).
    title : str, optional
        Title for the plot. By default it will add the scan numbers to it.

    Returns
    -------
    fig, ax : matplotlib figure and axes instances
        Useful to modify this figure.

    See also
    --------
    :func:`polartools.absorption.load_multi_dichro`
    """

    if detector is None:
        detector = []
        for det in counters.detectors:
            detector.extend(det.hints['fields'])
        if len(detector) > 1:
            warn(f"Found multiple hinted detectors: {detector}, using the "
                 f"first one: {detector[0]}")
            detector = detector[0]

    if monitor is None:
        monitor = counters.monitor

    fig, axs = plt.subplots(2, 2, figsize=(8, 6))

    results = []
    for scans, label in zip([scans_plus, scans_minus], ['plus', 'minus']):
        if scans is not None:
            try:
                scans = list(scans)
            except TypeError:
                scans = [scans]

            if title != '':
                title += '\n'
            title += f'{label}: {scans}\n'

            results.append(load_multi_dichro(
                scans, cat, positioner=positioner, detector=detector,
                monitor=monitor, transmission=not fluo
                ))

            _plot_one_xmcd(results[-1], axs[0], label)

    if len(results) > 1:
        combined = (
            results[0][0],  # energy
            (results[0][3] - results[0][3])/2.,  # xmcd
            (results[0][3] + results[0][3])/2.,  # artifact
            )

        _plot_combined_xmcd(combined, axs[1])

    plt.suptitle(title)
    plt.tight_layout()

    return fig, axs


def _plot_one_xmcd(data, axs, label=''):

    plt.sca(axs[0])
    plt.plot(data[0], data[1], label=label)
    plt.ylabel('XANES')
    plt.xlabel('Energy (keV)')
    plt.legend()

    plt.sca(axs[1])
    plt.plot(data[0], data[3], label=label)
    plt.tick_params(labelleft=False, labelright=True, right=True, left=False)
    axs[1].yaxis.set_label_position('right')
    plt.ylabel('XMCD', rotation=270, labelpad=15)
    plt.xlabel('Energy (keV)')


def _plot_combined_xmcd(data, axs):

    plt.sca(axs[0])
    plt.plot(data[0], data[1])
    plt.ylabel('XMCD')
    plt.xlabel('Energy (keV)')
    plt.legend()

    plt.sca(axs[1])
    plt.plot(data[0], data[2])
    plt.tick_params(labelleft=False, labelright=True)
    axs[1].yaxis.set_label_position('right')
    plt.ylabel('Artifact', rotation=270, labelpad=15)
    plt.xlabel('Energy (keV)')
