
from pathlib import Path
from ..devices import copy_files, dm_experiment
from ..utils import dm_get_experiment_data_path
from ..session_logs import logger
logger.info(__file__)

__all__ = ["copy_previous_files"]

def copy_previous_files(
        origin="/home/beams/POLAR/ptychodusDemo/sample1",
        destination=None
):
    if destination is None:
        destination = Path(dm_get_experiment_data_path(dm_experiment.get())) / "sample1"

    copy_files.start_copy(origin, destination)
