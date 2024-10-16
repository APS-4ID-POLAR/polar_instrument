"""
Utility functions
=================

.. autosummary::

    ~set_experiment
"""

__all__ = """
    set_experiment
""".split()

from apstools.utils import (
    dm_start_daq,
    validate_experiment_dataDirectory,
    dm_get_experiment_datadir_active_daq,
)

import sys
import fileinput
from pathlib import Path
from ..devices.data_management import dm_experiment
from .config import iconfig
from .dm_utils import dm_get_experiment_data_path
from .run_engine import RE
from ._logging_setup import logger

logger.info(__file__)
path_startup = Path("startup_experiment.py")

def set_experiment(
        user_name: str = None,
        proposal_id: str = None,
        sample: str = None,
        dm_experiment_name: str =  None,
        next_scan_id: int = -1,
        use_vortex: bool = False,
    ):

    _user_name = RE.md.get("user", "test")
    _proposal_id = RE.md.get("proposal_id", "test")
    _sample = RE.md.get("sample", "test")

    name = user_name or input(f"User [{_user_name}]: ") or _user_name
    proposal_id = (
        proposal_id or 
        input(f"Proposal ID [{_proposal_id}]: ") or
        _proposal_id
    )
    sample = sample or input(f"Sample [{_sample}]: ") or _sample

    RE.md["user"] = name
    RE.md["proposal_id"] = proposal_id
    RE.md["sample"] = sample

    if dm_experiment_name is None:
        use_dm = input("Are you using the data management? [no]: ") or "no"
        if use_dm.lower() == "yes":
            dm_experiment_name = input(
                "Enter experiment name (needs to match the DM system): "
            )

    if dm_experiment_name:
        _setup_dm(dm_experiment_name, sample, use_vortex)

    if next_scan_id < 0:
        reset_number =  input(
            "Do you want to reset the scan_id number? [no]: "
        ) or "no"
        if reset_number.lower() == "yes":
            next_scan_id = int(input("Next scan_id [1]: ")) or 1

    if next_scan_id >= 0:
        RE.md["scan_id"] = next_scan_id-1

    if path_startup.exists():
        for line in fileinput.input([path_startup.name], inplace=True):
            if line.strip().startswith("RE.md['user']"):
                line = f"RE.md['user']='{name}'\n"
            if line.strip().startswith("RE.md['proposal_id']"):
                line = f"RE.md['proposal_id']='{proposal_id}'\n"
            if line.strip().startswith("RE.md['sample']"):
                line = f"RE.md['sample']='{sample}'\n"
            sys.stdout.write(line)
    else:
        with open(path_startup.name, "w") as f:
            f.write("from instrument.collection import RE\n")
            f.write(f"RE.md['user']='{name}'\n")
            f.write(f"RE.md['proposal_id']='{proposal_id}'\n")
            f.write(f"RE.md['sample']='{sample}'\n")


def _setup_dm(dm_experiment_name: str, sample_name: str, use_vortex: bool):
    """
    Configure bluesky session for this user.

    PARAMETERS

    dm_experiment_name *str*:
    """

    validate_experiment_dataDirectory(dm_experiment_name)
    dm_experiment.put(dm_experiment_name)

    # Needed when data acquisition (Bluesky, EPICS, ...) writes to Voyager.
    # Full path to directory where new data will be written.
    # Data is written to APS Voyager storage (path
    # starting with ``/gdata/``).  Use "@voyager" in this case.
    # DM sees this and knows not copy from voyager to voyager.
    data_path = dm_get_experiment_data_path(dm_experiment_name)
    data_directory = f"@voyager:{data_path}"

    # Check DM DAQ is running for this experiment, if not then start it.
    if dm_get_experiment_datadir_active_daq(dm_experiment_name, data_directory) is None:
        # Need another DAQ if also writing to a different directory (off voyager).
        # A single DAQ can be used to cover any subdirectories.
        # Anything in them will be uploaded.
        logger.info(
            "Starting DM DAQ: experiment %r in data directory %r",
            dm_experiment_name,
            data_directory,
        )
        dm_start_daq(dm_experiment_name, data_directory)

    # Make sure that the subfolder structure exists, if not creates it.
    sample_path = data_path / sample_name
    if not sample_path.is_dir():
        sample_path.mkdir()

    for subfolder in "eiger positioner_stream".split():
        subpath = sample_path / subfolder
        if not subpath.is_dir():
            subpath.mkdir()
    
    if use_vortex:
        start_vortex_daq(sample_path, sample_name)

def start_vortex_daq(path, sample):

    DM_ROOT_PATH = Path(iconfig["DM_ROOT_PATH"])
    IOC_FILES_ROOT = Path(iconfig["AREA_DETECTOR"]["VORTEX"]["IOC_FILES_ROOT"])

    rel_path = path.relative_to(DM_ROOT_PATH)
    vortex_path = IOC_FILES_ROOT  / rel_path

    full_path = vortex_path / "vortex"
    if not full_path.is_dir():
        full_path.mkdir()

    if dm_get_experiment_datadir_active_daq(dm_experiment.get(), str(full_path)) is None:
        logger.info(
            "Starting DM DAQ for Vortex files: experiment %r in data directory %r",
            dm_experiment.get(),
            str(full_path),
        )
        dm_start_daq(dm_experiment.get(), full_path, destDirectory=f"{sample}/vortex")
