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
    dm_get_experiment_datadir_active_daq,
)
from dm import ObjectNotFound, DmException
from os import chdir
from pathlib import Path
from ..devices.data_management import dm_experiment
from .dm_utils import (
    get_esaf_info,
    get_proposal_info,
    get_experiment,
    dm_experiment_setup,
    get_current_run
)
from .run_engine import RE
from ._logging_setup import logger

logger.info(__file__)

SERVERS = {
    "dserv": Path("/net/s4data/export/sector4/4idd/"),
    # "dserv_windows": Path(r"Z:\4idd"),
    "data management": Path("/gdata/dm/4IDD/")
}

path_startup = Path("startup_experiment.py")

# TODO: enforce start and end times so that we don't overwrite experiments?


class ExperimentClass:
    esaf = None
    proposal = None

    server = None

    # By default will be the server + run + experiment_name
    base_experiment_path = None
    windows_base_experiment_path = None

    experiment_name = None
    data_management = None

    sample = None
    file_base_name = None

    # The experiment folder is the base_experiment_path / sample.
    @property
    def experiment_path(self, windows=False):
        if None in (self.base_experiment_path, self.sample):
            raise ValueError(
                "The base folder or sample name are not defined. Please run "
                "setup_experiment()"
            )
        return (
            Path(self.base_experiment_path) / self.sample
            if not windows else
            Path(self.windows_base_experiment_path) / self.sample
        )

    @experiment_path.setter
    def experiment_path(self, *args):
        raise AttributeError(
            "The experiment folder is automatically generated by combining the "
            "base folder and sample name."
        )

    def __repr__(self):
        print("\n-- Experiment setup --")
        if isinstance(self.proposal, dict):
            output = (
                f"Proposal #{self.proposal['id']} - {self.proposal['title']}."
                "\n"
            )
        else:
            output = "No proposal entered.\n"
        if isinstance(self.esaf, dict):
            output += f"ESAF #{self.esaf['esafId']}.\n"
        else:
            output += "No ESAF entered.\n"

        output += f"Data server: {self.server}\n"
        output += f"Sample: {self.sample}.\n"
        output += f"Experiment name: {self.experiment_name}\n"
        output += f"Base experiment folder: {self.base_experiment_path}\n"
        output += f"Experiment folder: {self.base_experiment_path}\n"

        _id = RE.md.get('scan_id', None)
        _id = _id + 1 if isinstance(_id, int) else None
        output += f"Next Bluesky scan_id: {_id}\n"

        return output

    def __str__(self):
        return self.__repr__()

    def esaf_input(self, esaf_id: int = None):
        while True:
            esaf_id = esaf_id or input("Enter ESAF number: ") or None
            if esaf_id == "dev":
                print("No ESAF will be associated to this experiment.")
                self.esaf = esaf_id
                break
            elif esaf_id is None:
                print("An ESAF ID must be provided.")
            else:
                try:
                    esaf_id = int(esaf_id)
                except ValueError:
                    print(f"ESAF must be a number, but {esaf_id} was entered.")
                    esaf_id = None
                    continue
                try:
                    self.esaf = dict(get_esaf_info(esaf_id))
                    print(f"ESAF #{self.esaf['esafId']} found.")
                    break
                except ObjectNotFound:
                    print(
                        f"The ESAF #{esaf_id} was not found. If this appears "
                        "to be an error, you can cancel this setup and check "
                        "the `list_esafs` function, or use ESAF = dev."
                    )
                    esaf_id = None

    def proposal_input(self, proposal_id: int = None):
        while True:
            proposal_id = (
                proposal_id or input("Enter proposal number: ") or None
            )
            if proposal_id == "dev":
                print("No proposal will be associated to this experiment.")
                self.proposal = proposal_id
                break
            elif proposal_id is None:
                print("Proposal ID must be provided.")
            else:
                try:
                    proposal_id = int(proposal_id)
                except ValueError:
                    print(
                        "The proposal number must be a number, but "
                        f"{proposal_id} was entered."
                    )
                    proposal_id = None
                    continue
                try:
                    self.proposal = dict(get_proposal_info(proposal_id))
                    print(
                        f"Proposal #{self.proposal['id']} found - "
                        f"{self.proposal['title']}."
                    )
                    break
                except DmException:
                    print(
                        f"The proposal_id #{proposal_id} was not found. If "
                        "this appears to be an error, you can cancel this "
                        "setup and check the `list_proposals` function, or use "
                        "Proposal = dev."
                    )
                    proposal_id = None

    def sample_input(self, sample_label: str = None):
        self.sample = (
            sample_label
            or input("Enter sample name [DefaultSample]: ")
            or "DefaultSample"
        )
        RE.md["sample"] = self.sample

    def base_name_input(self, base_name: str = None):
        self.file_base_name = (
            base_name or input("Enter files base name [scan_]: ") or "scan_"
        )

    def server_input(self, server: str = None):
        _server_options = str(tuple(SERVERS.keys()))
        while True:
            self.server = (server or input(
                    "Which data server will be used? options - "
                    f"{_server_options} [{list(SERVERS.keys())[0]}]: "
                ) or list(SERVERS.keys())[0]
            )

            if self.server.strip().lower() not in _server_options:
                print(f"Answer must be one of {_server_options}")
            else:
                break

    def experiment_name_input(self, experiment_name: str = None):
        while True:
            self.experiment_name = experiment_name = (
                experiment_name or input("Enter experiment name: ") or None
            )
            if experiment_name is None:
                print("An experiment name must be entered.")
            else:
                break

    def dm_experiment_setup(self, experiment_name):
        try:
            _exp = get_experiment(experiment_name)
            while True:
                _reuse = input(
                    "This experiment name already exist. Do you want to "
                    "re-use this experiment? [no]: "
                ).lower().strip() or "no"
                if _reuse not in "yes no".split():
                    print("Answer must be yes or no.")
                else:
                    break
            if _reuse == "no":
                experiment_name = None
                return False
        except ObjectNotFound:
            while True:
                _new_exp = (input(
                    f"\tExperiment {experiment_name} does not exist in DM. "
                    "Do you want to create a new experiment? [yes]: "
                ) or "yes").lower().strip()
                if _new_exp not in "yes no".strip():
                    print("\tAnswer must be yes or no.")
                else:
                    break
            if _new_exp == "no":
                print("\tData management will not be used. Switching to dserv.")
                self.data_management = None
                self.server = "dserv"
            else:
                _esaf_id = (
                    self.esaf["esafId"] if isinstance(self.esaf, dict) else
                    None
                )
                _exp, _ = dm_experiment_setup(
                    experiment_name, esaf_id=_esaf_id
                )

        if self.server == "data management":
            self.data_management = dict(_exp)
            dm_experiment.put(self.experiment_name)
        return True

    def setup_dm_daq(self):
        """
        Configure bluesky session for this user.

        PARAMETERS

        dm_experiment_name *str*:
        """
        data_directory = f"@voyager:{self.base_experiment_path}"

        # Check DM DAQ is running for this experiment, if not then start it.
        if dm_get_experiment_datadir_active_daq(
            self.experiment_name, data_directory
        ) is None:
            logger.info(
                "Starting DM voyager DAQ: experiment %r",
                self.experiment_name
            )
            dm_start_daq(self.experiment_name, "@voyager")

    def setup_path(self):
        # Make sure that the subfolder structure exists, if not creates it.
        if not self.experiment_path.is_dir():
            self.experiment_path.mkdir(parents=True)

        print(f"Moving to the sample folder: {self.experiment_path}")
        chdir(self.experiment_path)

    def scan_number_input(self, reset_scan_id: int = None):
        if not isinstance(reset_scan_id, (int, type(None))):
            print(
                f"WARNING: {reset_scan_id = } is not valid. Must be an integer."
            )

        while True:
            reset_scan_id = (
                reset_scan_id or input("Reset Bluesky scan_id to 1? [yes]: ") or
                "yes"
            ).strip().lower()
            if reset_scan_id not in "yes no".split():
                print("Answer must be yes or no.")
                reset_scan_id = None
            else:
                if reset_scan_id == "yes":
                    RE.md["scan_id"] = 0
                break

    def load_params_from_bluesky(self):
        # TODO!!!!
        # for key in (
        #     "data_management esaf proposal sample base_experiment_path"
        # ).split():
        #     setattr(self, key, RE.md[key])

        # self.use_dm = "yes" if self.data_management else "no"

        # if isinstance(self.data_management, dict):
        #     self.experiment_name = self.data_management["name"]
        #     chdir(self.data_management["dataDirectory"])

        # self.base_experiment_path = getcwd()
        # self.setup_folder()

        # print(self.__repr__)
        pass

    def save_params_to_yaml(self):
        pass

    def load_params_from_yaml(self):
        pass

    def new_experiment(
            self,
            esaf_id: int = None,
            proposal_id: int = None,
            base_name: str = None,
            sample_label: str = None,
            server: str = None,
            experiment_name: str = None,
            reset_scan_id: int = None
    ):
        # ESAF and proposal ID info first. Will get data from APS databases.
        self.esaf_input(esaf_id)
        self.proposal_input(proposal_id)

        # Selects where to save the data. Long term, this probably this will be
        # mostly the DM.
        self.server_input(server)
        # This is needed because if using the DM, the experiment name may need
        # to be changed.
        while True:
            self.experiment_name_input(experiment_name)
            if self.server == "data management":
                _done = self.dm_experiment_setup()
                if not _done:
                    continue
            break

        # This is a very opinionated folder setup.
        # NOTE: you can still change base_experiment_path by hand!!
        if self.data_management:
            self.base_experiment_path = self.data_management["dataDirectory"]
            self.setup_dm_daq()
            self.windows_experiment_path = None  # windows cannot see DM?
        else:
            self.base_experiment_path = (
                SERVERS[self.server] /
                get_current_run()["name"] /
                self.experiment_name
            )
            self.windows_base_experiment_path = (
                rf"{SERVERS[self.server + '_windows']}"
                rf"\{get_current_run()['name']}\{self.experiment_name}"
            )

        # Sample name. In practice this is used to create another folder layer.
        self.sample_input(sample_label)

        self.setup_path()

        self.base_name_input(base_name)
        self.scan_number_input(reset_scan_id)

        self.save_params_to_yaml()

        print(self.__repr__())

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

    def new_sample(
            self,
            sample_name: str = None,
            base_name: str = None,
            reset_scan_id: int = None
    ):
        self.sample_input(sample_name)
        self.setup_path()
        self.scan_number_input(reset_scan_id)
        self.base_name_input(base_name)

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
            esaf_id,
            proposal_id,
            sample_label,
            use_dm,
            experiment_name,
            reset_scan_id
        )


experiment = ExperimentClass()
