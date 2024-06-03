"""
Setup new user in Bluesky.
"""

from apstools.utils import (
    dm_start_daq,
    validate_experiment_dataDirectory,
    dm_get_experiment_datadir_active_daq,
    dm_get_experiment_path
)
from ..devices import dm_experiment
from ..plans import mv
from ..framework import RE
from ..session_logs import logger
logger.info(__file__)

__all__ = """
    setup_user
""".split()


def setup_user(dm_experiment_name: str, index: int = -1):
    """
    Configure bluesky session for this user.

    PARAMETERS

    dm_experiment_name *str*:

    .. note:: Set ``index=-1`` to continue with current 'scan_id' value.
    """

    validate_experiment_dataDirectory(dm_experiment_name)
    dm_experiment.put(dm_experiment_name)

    if index >= 0:
        RE.md["scan_id"] = index

    # Needed when data acquisition (Bluesky, EPICS, ...) writes to Voyager.
    # Full path to directory where new data will be written.
    # XPCS new data is written to APS Voyager storage (path
    # starting with ``/gdata/``).  Use "@voyager" in this case.
    # DM sees this and knows not copy from voyager to voyager.
    data_directory = "@voyager"

    # Check DM DAQ is running for this experiment, if not then start it.
    if dm_get_experiment_datadir_active_daq(dm_experiment_name) is None:
        # Need another DAQ if also writing to a different directory (off voyager).
        # A single DAQ can be used to cover any subdirectories.
        # Anything in them will be uploaded.
        logger.info(
            "Starting DM DAQ: experiment %r in data directory %r",
            dm_experiment_name,
            data_directory,
        )
        dm_start_daq(dm_experiment_name, data_directory)

    # Make sure that the subfolders are created.
    path = dm_get_experiment_path(dm_experiment_name)
    for subfolder in "eiger positioner_stream".split():
        subpath = path / subfolder
        if not subpath.is_dir():
            subpath.mkdir()

    # TODO: Add other setup things here.