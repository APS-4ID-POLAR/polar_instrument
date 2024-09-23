"""
Setup new user in Bluesky.
"""

from apstools.utils import dm_api_ds, dm_api_proc
from pathlib import Path
from ..devices.data_management import dm_workflow
from .run_engine import RE
from ._logging_setup import logger
logger.info(__file__)

__all__ = """
    dm_get_experiment_data_path
""".split()


def dm_get_experiment_data_path(dm_experiment_name: str):
    return Path(dm_api_ds().getExperimentByName(dm_experiment_name)["dataDirectory"])

def get_processing_job_status(id=None, owner="user4idd"):
    if id is None:
        id = dm_workflow.job_id.get()
    return dm_api_proc().getProcessingJobById(id=id, owner=owner)
