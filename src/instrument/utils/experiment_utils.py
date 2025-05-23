"""
Utility functions
=================

.. autosummary::

    ~set_experiment
"""

__all__ = """
    change_experiment_sample
    setup_experiment
    load_experiment_from_bluesky
    experiment
""".split()

from apstools.utils import (
    dm_start_daq,
    dm_get_experiment_datadir_active_daq,
)
from dm import ObjectNotFound, DmException
from os import chdir
from pathlib import Path
from ..callbacks.spec_data_file_writer import specwriter
from ..devices.data_management import dm_experiment
from .dm_utils import (
    get_esaf_info,
    get_proposal_info,
    get_experiment,
    dm_experiment_setup,
    get_current_run_name
)
from .run_engine import RE
from ._logging_setup import logger
from .config import iconfig

logger.info(__file__)

SERVERS = {
    "dserv": Path(iconfig["DSERV_ROOT_PATH"]),
    "data management": Path(iconfig["DM_ROOT_PATH"])
}

path_startup = Path("startup_experiment.py")


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

    spec_file = None

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
                f"Proposal #{self.proposal['id']} - {self.proposal['title']}"
                "\n"
            )
        else:
            output = "No proposal entered\n"
        if isinstance(self.esaf, dict):
            output += f"ESAF #{self.esaf['esafId']}\n"
        else:
            output += "No ESAF entered\n"

        output += f"Data server: {self.server}\n"
        output += f"Sample: {self.sample}\n"
        output += f"Experiment name: {self.experiment_name}\n"
        output += f"Base experiment folder: {self.base_experiment_path}\n"
        output += f"Current experiment folder: {self.experiment_path}\n"
        output += f"Spec file name: {self.spec_file}\n"

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

        RE.md["esaf_id"] = str(esaf_id)

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

        RE.md["proposal_id"] = str(proposal_id)

    def sample_input(self, sample: str = None):
        self.sample = (
            sample
            or input("Enter sample name [DefaultSample]: ")
            or "DefaultSample"
        )
        RE.md["sample"] = self.sample

    def base_name_input(self, base_name: str = None):
        guess = self.file_base_name or "scan"
        self.file_base_name = (
            base_name or input(f"Enter files base name [{guess}]: ") or guess
        )
        RE.md["base_name"] = self.file_base_name

    def server_input(self, server: str = None):
        _server_options = str(tuple(SERVERS.keys()))
        guess = self.server or list(SERVERS.keys())[0]
        while True:
            self.server = (server or input(
                    "Which data server will be used? options - "
                    f"{_server_options} [{guess}]: "
                ) or guess
            )

            if self.server.strip().lower() not in _server_options:
                print(f"Answer must be one of {_server_options}")
            else:
                break
        RE.md["server"] = self.server

    def experiment_name_input(self, experiment_name: str = None):
        guess = self.experiment_name or None
        while True:
            self.experiment_name = experiment_name = (
                experiment_name or input(f"Enter experiment name ({guess}): ")
                or guess
            )
            if experiment_name is None:
                print("An experiment name must be entered.")
            else:
                break
        RE.md["experiment_name"] = self.experiment_name

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

        # print(f"Moving to the sample folder: {self.experiment_path}")
        # chdir(self.experiment_path)
        print(f"Moving to the sample folder: {self.base_experiment_path}")
        chdir(self.base_experiment_path)

    def scan_number_input(self, reset_scan_id: int = None):
        if isinstance(reset_scan_id, type(None)):
            while True:
                reset_scan_id = (
                    reset_scan_id
                    or input("Reset Bluesky scan_id to 1? [yes]: ")
                    or "yes"
                ).strip().lower()
                if reset_scan_id not in "yes no".split():
                    print("Answer must be yes or no.")
                    reset_scan_id = None
                else:
                    if reset_scan_id == "yes":
                        RE.md["scan_id"] = 0
                    break
        elif isinstance(reset_scan_id, int):
            if reset_scan_id >= 0:
                RE.md["scan_id"] = reset_scan_id - 1
        else:
            print(
                f"WARNING: {reset_scan_id = } is not valid. It must be an "
                "integer. Will not reset it. Next scan_id = "
                f"{RE.md['scan_id'] + 1}."
            )

    def start_specwriter(self):
        suffix = specwriter.make_default_filename()
        fname = self.experiment_path / f"{self.sample}_{suffix}"
        specwriter.newfile(fname)
        self.spec_file = specwriter.spec_filename.name

    def load_from_bluesky(
            self,
            reset_scan_id: int = -1,
            skip_DM: bool = False
    ):
        kwargs = {}
        for key in (
            "esaf_id",
            "proposal_id",
            "base_name",
            "sample",
            "server",
            "experiment_name"
        ):
            kwargs[key] = RE.md[key]

        self.setup(
            reset_scan_id=reset_scan_id,
            skip_DM=skip_DM,
            **kwargs
        )

    def save_params_to_yaml(self):
        pass

    def load_params_from_yaml(self):
        pass

    def setup(
            self,
            esaf_id: int = None,
            proposal_id: int = None,
            base_name: str = None,
            sample: str = None,
            server: str = None,
            experiment_name: str = None,
            reset_scan_id: int = None,
            skip_DM: bool = False
    ):
        if not skip_DM:
            # ESAF and proposal ID info first. Will get data from APS databases.
            self.esaf_input(esaf_id)
            self.proposal_input(proposal_id)

            # Selects where to save the data. Long term, this probably this will
            # be mostly the DM.
            self.server_input(server)

        else:
            self.server = "dserv"

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
                get_current_run_name() /
                self.experiment_name
            )
            # self.windows_base_experiment_path = (
            #     rf"{SERVERS[self.server + '_windows']}"
            #     rf"\{get_current_run()['name']}\{self.experiment_name}"
            # )

        # Sample name. In practice this is used to create another folder layer.
        self.sample_input(sample)

        self.setup_path()
        self.base_name_input(base_name)
        self.scan_number_input(reset_scan_id)

        self.start_specwriter()

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

    def change_sample(
            self,
            sample_name: str = None,
            base_name: str = None,
            reset_scan_id: int = None
    ):
        self.sample_input(sample_name)
        self.setup_path()
        self.scan_number_input(reset_scan_id)
        self.base_name_input(base_name)
        self.start_specwriter()

    def __call__(
            self,
            esaf_id: int = None,
            proposal_id: int = None,
            base_name: str = None,
            sample: str = None,
            server: str = None,
            experiment_name: str = None,
            reset_scan_id: int = None,
            skip_DM: bool = False
    ):

        self.setup(
            esaf_id,
            proposal_id,
            base_name,
            sample,
            server,
            experiment_name,
            reset_scan_id,
            skip_DM
        )


experiment = ExperimentClass()


def experiment_setup(
        esaf_id: int = None,
        proposal_id: int = None,
        base_name: str = None,
        sample: str = None,
        server: str = None,
        experiment_name: str = None,
        reset_scan_id: int = None,
        skip_DM: bool = False
):
    experiment.setup(
        esaf_id,
        proposal_id,
        base_name,
        sample,
        server,
        experiment_name,
        reset_scan_id,
        skip_DM
    )


def experiment_change_sample(
    sample_name: str = None,
    base_name: str = None,
    reset_scan_id: int = None
):
    experiment.sample_input(sample_name)
    experiment.setup_path()
    experiment.scan_number_input(reset_scan_id)
    experiment.base_name_input(base_name)


def experiment_load_from_bluesky(
    reset_scan_id: int = -1,
    skip_DM: bool = False,
):
    experiment.load_from_bluesky(
        reset_scan_id, skip_DM
    )
