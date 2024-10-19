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
from os import getcwd
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


class ExperimentClass:
    experiment_folder = None
    experiment_name = None
    use_dm = "yes"
    esaf = None

    def __repr__(self):
        output = f"User: {RE.md.get("user", None)}\n"
        output += f"Proposal ID: {RE.md.get("proposal_id", None)}\n"
        output += f"Sample: {RE.md.get("sample", None)}\n"
        output += f"Next scan_id: {RE.md.get("scan_id", 0) + 1}\n"
        output += f"Experiment folder: {self.experiment_folder}\n"
        output += f"Use data management system: {self.use_dm}\n"
        if self.use_dm == "yes":
            output += f"DM experiment name: {self.experiment_name}\n"
        
        return output

    def __str__(self):
        return self.__repr__()

    def __call__(
        self,
        user_name: str = None,
        proposal_id: str = None,
        sample: str = None,
        dm_experiment_name: str =  None,
        next_scan_id: int = -1,
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
            while True:
                self.use_dm = input(
                    f"Are you using the data management? [{self.use_dm}]: "
                ) or self.use_dm
                if use_dm.strip().lower() in "yes no".split():
                    if use_dm.strip().lower() == "yes":
                        dm_experiment_name = input(
                            "Enter experiment name (needs to match the DM system): "
                        )
                    break
                else:
                    print(f"{self.use_dm} is not a valid answer. Please use yes or no.")

        if dm_experiment_name:
            self.use_dm = "yes"
            while True:
                _custom_folder = input(
                    "Do you want to use the same folder naming as in data management? "
                    "[yes]: "
                ).strip().lower() or "yes"
                if _custom_folder == "no":
                    _folder = (
                        self.experiment_dserv_folder if self.experiment_dserv_folder is 
                        None else getcwd()
                    )
                    self.dserv_folder = (
                        input(f"Enter experiment folder [{_folder}]: ") or _folder
                    )

            _setup_dm(dm_experiment_name, sample, dserv = self.dserv_folder)
            self.experiment_dm_folder = dm_get_experiment_data_path(dm_experiment_name)

        if next_scan_id < 0:
            while True:
                reset_number =  input(
                    "Do you want to reset the scan_id number? [no]: "
                ) or "no"
                if reset_number.strip().lower() in "yes no".split():
                    if reset_number.strip().lower() == "yes":
                        while True:
                            try:
                                next_scan_id = int(input("Next scan_id [1]: ")) or 1
                                break
                            except ValueError:
                                print("Needs to be an integer number.")
                    break
                else:
                    print(
                        f"{reset_number} is not a valid answer. Please use yes or no."
                    )

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


def _setup_dm(dm_experiment_name: str, sample_name: str):
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
    data_directory = f"@voyager:{dm_get_experiment_data_path(dm_experiment_name)}"

    # Check DM DAQ is running for this experiment, if not then start it.
    if dm_get_experiment_datadir_active_daq(dm_experiment_name, data_directory) is None:
        # Need another DAQ if also writing to a different directory (off voyager).
        # A single DAQ can be used to cover any subdirectories.
        # Anything in them will be uploaded.
        logger.info(
            "Starting DM voyager DAQ: experiment %r",
            dm_experiment_name
        )
        dm_start_daq(dm_experiment_name, "@voyager")

    # Make sure that the subfolder structure exists, if not creates it.
    sample_path = dm_get_experiment_data_path(dm_experiment_name) / sample_name
    if not sample_path.is_dir():
        sample_path.mkdir()

set_experiment = SetExperiment()

