
from pathlib import Path
from ..devices import file_copy_device, dm_experiment
from . import dm_get_experiment_data_path
from ..session_logs import logger
logger.info(__file__)

__all__ = ["copy_previous_files"]

def copy_previous_files(
        origin="/home/beams/POLAR/ptychodusDemo/sample1",
        destination=None
):
    if destination is None:
        destination = Path(dm_get_experiment_data_path(dm_experiment.get())) / "sample1"
    elif isinstance(destination, str):
        destination = Path(destination)

    if destination.is_dir():
        raise FileExistsError("Folder already exists, will not overwrite!")

    file_copy_device.start_copy(origin, destination)
    logger.info(f"Started data copy. Origin: {origin}, destination: {destination}")
