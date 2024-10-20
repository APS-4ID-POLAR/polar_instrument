"""
Utility functions
=================

.. autosummary::

    ~set_experiment
"""

__all__ = """
    experiment
""".split()

from apstools.utils import (
    dm_start_daq,
    validate_experiment_dataDirectory,
    dm_get_experiment_datadir_active_daq,
)
from dm import ObjectNotFound, DmException
from os import getcwd, chdir
import sys
import fileinput
from pathlib import Path
from ..devices.data_management import dm_experiment
from .config import iconfig
from .dm_utils import (
    dm_get_experiment_data_path, get_esaf_info, get_proposal_info, get_experiment
)
from .run_engine import RE
from ._logging_setup import logger

logger.info(__file__)
path_startup = Path("startup_experiment.py")

# TODO: enforce start and end times so that we don't overwrite experiments?

class ExperimentClass:
    base_experiment_folder = None
    experiment_name = None
    data_management = None
    use_dm = "yes"
    esaf = None
    proposal = None
    sample = None

    def __repr__(self):
        if self.proposal:
            output = f"Proposal #{self.proposal['id']} - {self.proposal['title']}.\n"
        else:
            output = "No proposal entered\n"   
        if self.esaf:
            output += f"ESAF #{self.esaf['esafId']}.\n"
        else:
            output += "No ESAF entered.\n"

        output += f"Sample: {self.sample}.\n"
        output += f"Base experiment folder: {self.base_experiment_folder}.\n"
        output += f"Use data management system: {self.use_dm}.\n"
        if self.use_dm == "yes":
            output += f"DM experiment name: {self.experiment_name}.\n"

        output += f"Next Bluesky scan_id: {RE.md.get('scan_id', 0) + 1}.\n"

        return output

    def __str__(self):
        return self.__repr__()

    def esaf_input(self, esaf_id: int = None):
        while True:
            esaf_id = esaf_id or input(f"Enter ESAF number: ") or None
            if esaf_id == "dev":
                print("No ESAF will be associated to this experiment.")
                self.esaf = esaf_id
            elif esaf_id is None:
                print("An ESAF ID must be provided.")
            else:
                try:
                    esaf_id = int(esaf_id)
                except ValueError:
                    print(f"ESAF must be a number, but {esaf_id} was entered.")
                    continue
                try:
                    self.esaf = get_esaf_info(esaf_id)
                    print(f"ESAF #{self.esaf['esaf_id']} found.")
                    break
                except ObjectNotFound:
                    print(
                        f"The ESAF #{esaf_id} was not found. If this appears to be an "
                        "error, you can cancel this setup and check the `list_esafs` "
                        "function, or use ESAF = dev."
                    )

    def proposal_input(self, proposal_id: int = None):
        while True:
            proposal_id = proposal_id or input(f"Enter proposal number: ") or None
            if proposal_id == "dev":
                print("No proposal will be associated to this experiment.")
                self.proposal = proposal_id
            elif proposal_id is None:
                logger.info("Proposal ID must be provided.")
            else:
                try:
                    proposal_id = int(proposal_id)
                except ValueError:
                    print(
                        f"The proposal number must be a number, but {proposal_id} was "
                        "entered."
                    )
                    continue
                try:
                    self.proposal = get_proposal_info(proposal_id)
                    print(
                        f"Proposal #{self.proposal['id']} found - "
                        f"{self.proposal['title']}."
                    )
                    break
                except DmException:
                    print(
                        f"The proposal_id #{proposal_id} was not found. If this "
                        "appears to be an error, you can cancel this setup and check "
                        "the `list_proposals` function, or use Proposal = dev."
                    )

    def sample_input(self, sample_label: str = None):
        while True:
            self.sample = (
                sample_label or input(f"Enter sample name [sample1]: ") or "sample1"
            )

    def dm_use_input(self, use_dm: str = None):
        while True:
            self.use_dm = (
                use_dm or
                input(
                    "Do you want to use the data management system? "
                    f"[{self.use_dm}]"
                ) or
                self.use_dm
            ).lower().strip()
            if self.use_dm not in "yes no".split():
                print("Answer must be either yes or no.")
            else:
                break

    def dm_experiment_input(self, experiment_name: str = None):
        while True:
            experiment_name = (
                experiment_name or input("\tEnter DM experiment name: ") or None
            )
            if experiment_name is None:
                print("An experiment name must be entered.")
                continue

            try:
                _exp = get_experiment(experiment_name)
            except ObjectNotFound:
                while True:
                    _new_exp = (input(
                        f"\tExperiment {experiment_name} does not exist. Do you want to "
                        "create a new experiment? [yes]: "
                    ) or "yes").lower().strip()
                    if _new_exp not in "yes no".strip():
                        print("\tAnswer must be yes or no.")
                        continue
                if _new_exp == "no":
                    print("\tDM will not be used.")
                    self.data_management = None
                    self.use_dm = "no"
                    break
                else:
                    _esaf_id = self.esaf["esafId"] if self.esaf else None
                    _exp, _ = dm_experiment_setup(
                        experiment_name, esaf_id=_esaf_id
                    )
            
            print(
                f"Using experiment {experiment_name} in folder {_exp['dataDirectory']}."
            )
            self.data_management = _exp
            dm_experiment.put(experiment_name)

    def setup_folder(self):
        """
        Configure bluesky session for this user.

        PARAMETERS

        dm_experiment_name *str*:
        """
        if self.use_dm:
            data_directory = f"@voyager:{self.base_experiment_folder)}"

            # Check DM DAQ is running for this experiment, if not then start it.
            if dm_get_experiment_datadir_active_daq(
                self.experiment_name, data_directory
            ) is None:
                logger.info(
                    "Starting DM voyager DAQ: experiment %r",
                    self.experiment_name
                )
                dm_start_daq(self.experiment_name, "@voyager")

        # Make sure that the subfolder structure exists, if not creates it.
        sample_path = Path(self.base_experiment_folder) / sample_name
        if not sample_path.is_dir():
            sample_path.mkdir()
        
        print(f"Moving to the sample folder: {sample_path}")
        chdir(sample_path)

    def scan_number_input(self, reset_scan_id: int = None):
        while True:
            reset_scan_id = (
                reset_scan_id or input(f"Reset Bluesky scan_id? [yes]: ") or "yes"
            ).strip().lower()
            if reset_scan_id not in "yes no".split():
                print("Answer must be yes or no.")
            else:
                if reset_scan_id == "yes":
                    RE.md["scan_id"] = 0

    def send_params_to_bluesky(self):
        for key in (
            "data_management esaf proposal sample base_experiment_folder"
        ).split():
            RE.md[key] = getattr(self, key)

    def load_params_from_bluesky(self):
        for key in (
            "data_management esaf proposal sample base_experiment_folder"
        ).split():
            getattr(self, key) = RE.md[key]

        self.use_dm = "yes" if self.data_management else "no"
        if self.base_experiment_folder:
            self.setup_folder()

        print(self)
    
    def save_params_to_yaml(self):
        pass

    def load_params_from_yaml(self)

    def new_experiment(
            self,
            esaf_id: int = None,
            proposal_id: int = None,
            sample_label: str = None,
            use_dm: str = None,
            experiment_name: str = None,
            reset_scan_id: int = None
        ):
        self.esaf_input(esaf_id)
        self.proposal_input(proposal_id)
        self.sample_input(sample_label)
        self.dm_use_input(use_dm)
        if self.use_dm == "yes":
            self.dm_experiment_input(experiment_name)
        if self.data_management:
            chdir(self.data_management["dataDirectory"])
        
        print(f"Base experiment folder: {getcwd()}.")
        self.base_experiment_folder = getcwd()
        self.setup_folder()
        self.scan_number_input(reset_scan_id)
        self.send_params_to_bluesky()
        self.save_params_to_yaml()

        print("\nSettings:")
        print(self)

        # TODO: What to do about this?
        # if path_startup.exists():
        #     for line in fileinput.input([path_startup.name], inplace=True):
        #         if line.strip().startswith("RE.md['user']"):
        #             line = f"RE.md['user']='{name}'\n"
        #         if line.strip().startswith("RE.md['proposal_id']"):
        #             line = f"RE.md['proposal_id']='{proposal_id}'\n"
        #         if line.strip().startswith("RE.md['sample']"):
        #             line = f"RE.md['sample']='{sample}'\n"
        #         sys.stdout.write(line)
        # else:
        #     with open(path_startup.name, "w") as f:
        #         f.write("from instrument.collection import RE\n")
        #         f.write(f"RE.md['user']='{name}'\n")
        #         f.write(f"RE.md['proposal_id']='{proposal_id}'\n")
        #         f.write(f"RE.md['sample']='{sample}'\n")

    def __call__(
            self,
            esaf_id: int = None,
            proposal_id: int = None,
            sample_label: str = None,
            use_dm: str = None,
            experiment_name: str = None,
            reset_scan_id: int = None
        ):

        self.new_experiment(
            esaf_id, proposal_id, sample_label, use_dm, experiment_name, reset_scan_id
        )


experiment = ExperimentClass()

