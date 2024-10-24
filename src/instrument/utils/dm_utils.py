"""
Setup new user in Bluesky.
"""

from apstools.utils import dm_api_ds, dm_api_proc, dm_api_daq
from apstools.utils.aps_data_management import (
    DEFAULT_UPLOAD_TIMEOUT, DEFAULT_UPLOAD_POLL_PERIOD
)
from pathlib import Path
from time import time, sleep
from bluesky.plan_stubs import null
from ..devices.data_management import dm_workflow
from ._logging_setup import logger
logger.info(__file__)

__all__ = """
    dm_get_experiment_data_path
    dm_upload
    dm_upload_info
""".split()


def dm_get_experiment_data_path(dm_experiment_name: str):
    return Path(dm_api_ds().getExperimentByName(dm_experiment_name)["dataDirectory"])


def get_processing_job_status(id=None, owner="user4idd"):
    if id is None:
        id = dm_workflow.job_id.get()
    return dm_api_proc().getProcessingJobById(id=id, owner=owner)


def dm_upload(experiment_name, folder_path, **daqInfo):
    return dm_api_daq().upload(
        experiment_name, folder_path, daqInfo
    )


def dm_upload_info(id):
    return dm_api_daq().getUploadInfo(id)


def dm_upload_wait(
    id,
    timeout: float = DEFAULT_UPLOAD_TIMEOUT,
    poll_period: float = DEFAULT_UPLOAD_POLL_PERIOD,
):
    """
    (bluesky plan) Wait for APS DM data acquisition to upload a file.

    PARAMETERS

    - Experiment id
    - timeout *float*: Number of seconds to wait before raising a 'TimeoutError'.
    - poll_period *float*: Number of seconds to wait before check DM again.

    RAISES

    - TimeoutError: if DM does not identify file within 'timeout' (seconds).

    """
    t0 = time()
    deadline = t0 + timeout
    yield from null()  # now, it's a bluesky plan

    while time() <= deadline:
        if dm_upload_info(id)["status"].lower() != "done":
            yield from sleep(poll_period)
        else:
            return

    raise TimeoutError(
        f"DM upload in DM timed out after {time()-t0 :.1f} s."
    )
