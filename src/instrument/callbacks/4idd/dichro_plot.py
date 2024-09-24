"""
Processed dichro data for plot.
"""

__all__ = ['AutoDichroPlot']

from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
# Axes and Figure will be renamed to AxesSpec, FigureSpec?
# from bluesky_widgets.models.plot_specs import AxesSpec, FigureSpec
from bluesky_widgets.models.plot_specs import Axes, Figure
from numpy import log, array

from ..session_logs import logger
logger.info(__file__)


def xanes(monitor, detector, fluo):
    if array(detector).size < 4:
        return array(detector).mean()

    rng = 4*(array(detector).size//4)

    if fluo:
        absorption = (
            (array(detector)[:rng] / array(monitor)[:rng]).reshape(-1, 4)
        )
    else:
        absorption = (
            log(array(monitor)[:rng] / array(detector)[:rng]).reshape(-1, 4)
        )

    return absorption.mean(axis=1)


def xmcd(monitor, detector, fluo):
    if array(detector).size < 4:
        return 0

    rng = 4*(array(detector).size//4)

    if fluo:
        absorption = (
            (array(detector)[:rng] / array(monitor)[:rng]).reshape(-1, 4)
        )
    else:
        absorption = (
            log(array(monitor)[:rng] / array(detector)[:rng]).reshape(-1, 4)
        )

    return (absorption[:, [0, 3]].mean(axis=1) -
            absorption[:, [1, 2]].mean(axis=1))


def downsampled(x):
    if array(x).size < 4:
        return array(x).mean()
    rng = 4*(array(x).size//4)
    return array(x[:rng]).reshape(-1, 4).mean(axis=1)


class AutoDichroPlot(AutoPlotter):
    def __init__(self, monitor='Ion Ch 4', detector='Ion Ch 5', fluo=True):
        super().__init__()
        self._x_to_lines = {}  # map x variable to (xanes_lines, xmcd_lines)
        self._monitor = monitor
        self._detector = detector
        self._fluo = fluo

    @property
    def monitor(self):
        return self._monitor

    @property
    def detector(self):
        return self._detector

    @property
    def fluo(self):
        return self._fluo

    @fluo.setter
    def fluo(self, value):
        self._fluo = bool(value)

    def new_plot(self, x_name=None):
        # New plots for all types.
        if x_name is None:
            self._x_to_lines = {}
        else:
            try:
                del self._x_to_lines[x_name]
            except KeyError:
                raise KeyError(f"There is no plot with {x_name}.")

    def handle_new_stream(self, run, stream_name):
        if stream_name != "primary":
            # Nothing to do for this stream.
            return

        # Look for the scan_type='dichro' hint
        scan_type = run.metadata["start"]["hints"].get('scan_type', "")
        if 'dichro' not in scan_type:
            return

        # Detect x variable from hints in metadata.
        first_scan_dimension = run.metadata["start"]["hints"]["dimensions"][0]
        scanning_fields, _ = first_scan_dimension
        x = scanning_fields[0]

        # Collect monitor and detector
        if "monitor" in run.metadata["start"]["hints"].keys():
            self._monitor = run.metadata["start"]["hints"]["monitor"]
        # TODO: This will only use the first detector, but maybe could
        # expand to all detectors.
        if "detectors" in run.metadata["start"]["hints"].keys():
            self._detector = run.metadata["start"]["hints"]["detectors"][0]

        # If we already have a figure for this x, reuse it (over-plot).
        try:
            (xanes_lines, xmcd_lines) = self._x_to_lines[x]
        except KeyError:
            # We don't have a figure for this x. Make one.
            xanes_axes = Axes(x_label=x, title="XANES")
            xmcd_axes = Axes(x_label=x, title="XMCD")
            figure = Figure((xanes_axes, xmcd_axes), title="XANES and XMCD")
            # Set up objects that will select the approriate data and do the
            # desired transformation for plotting.
            xanes_lines = Lines(
                x=lambda primary: downsampled(primary[x]),
                ys=[lambda primary: xanes(primary[self._monitor],
                                          primary[self._detector],
                                          self.fluo)],
                axes=xanes_axes,
            )
            xmcd_lines = Lines(
                x=lambda primary: downsampled(primary[x]),
                ys=[lambda primary: xmcd(primary[self._monitor],
                                         primary[self._detector],
                                         self.fluo)],
                axes=xmcd_axes,
            )
            self._x_to_lines[x] = (xanes_lines, xmcd_lines)
            # Keep track of these plot builders to enable *removing* runs from
            # them.
            self.plot_builders.append(xanes_lines)
            self.plot_builders.append(xmcd_lines)
            # Appending this figures list will trigger to view to show our new
            # figure.
            self.figures.append(figure)
        # Add this Run to the figure.
        xanes_lines.add_run(run)
        xmcd_lines.add_run(run)
