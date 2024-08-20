""" Generate plots """

__all__ = ['start_dichro_plot']

from bluesky_widgets.qt.figures import QtFigures
from bluesky_widgets.utils.streaming import stream_documents_into_runs
from ..framework import RE
from ..callbacks import AutoDichroPlot

from ..session_logs import logger
logger.info(__file__)


# TODO: Is there a better way to do this?
def start_dichro_plot(monitor='Ion Ch 4', detector='Ion Ch 5', fluo=True):
    model = AutoDichroPlot(monitor=monitor, detector=detector, fluo=fluo)
    view = QtFigures(model.figures)
    view.show()
    RE.subscribe(stream_documents_into_runs(model.add_run))
    return model, view
