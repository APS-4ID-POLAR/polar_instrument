"""
Run DM workflow
"""

from bluesky.plan_stubs import sleep
from pathlib import Path
from .local_scans import mv
from ..framework import RE, cat
from ..devices import dm_workflow, dm_experiment
from ..session_logs import logger
logger.info(__file__)


def run_workflow(
        scan = -1,
        # DM workflow kwargs -------------------------------------
        wf_analysis_machine: str = "polaris",
        wf_workflow_name: str = "ptychodus",
        wf_detectorName: str = "eiger",
        wf_detectorDistanceInMeters: float = 2.335,
        wf_cropCenterXInPixels: int = 540,
        wf_cropCenterYInPixels: int = 259,
        wf_cropExtentXInPixels: int = 256,
        wf_cropExtentYInPixels: int = 256,
        wf_probeEnergyInElectronVolts: float = 10000,
        wf_numGpus: int = 2,
        wf_settings: str = "/home/beams/POLAR/ptychodusDefaults/default-settings.ini",
        wf_demand: bool = False,
        wf_scanFilePath: str = "fly001_pos.csv",
        wf_name: str = "fly001",
        wf_sample_name: str = RE.md["sample"],
        wf_master_file_name: str = "",
        # internal kwargs ----------------------------------------
        dm_concise: bool = False,
        dm_wait: bool = False,
        dm_reporting_period: float = 10*60,
        dm_reporting_time_limit: float = 10**6,
    ):

    if wf_master_file_name == "":
        start_doc = cat[scan].metadata["start"]
        _path = start_doc.get("master_file", None)
        if not _path:
            raise ValueError(
                "could not find master_file_name in the scan metadata and no value was"
                "provided."
            )
        wf_master_file_name = Path(_path).name
    
    yield from mv(
        dm_workflow.concise_reporting, dm_concise,
        dm_workflow.reporting_period, dm_reporting_period,
    )

    logger.info(
        "DM workflow %r, filePath=%r",
        wf_workflow_name,
        wf_master_file_name,
    )

    yield from dm_workflow.run_as_plan(
        workflow=wf_workflow_name,
        wait=dm_wait,
        timeout=dm_reporting_time_limit,
        # all kwargs after this line are DM argsDict content
        filePath=wf_master_file_name,
        sampleName = wf_sample_name,
        experimentName=dm_experiment.get(),
        scanFilePath=wf_scanFilePath,
        analysisMachine=wf_analysis_machine,
        # TODO: What all can we switch to PV.gets?
        detectorName=wf_detectorName,
        detectorDistanceInMeters=wf_detectorDistanceInMeters,
        cropCenterXInPixels=wf_cropCenterXInPixels,
        cropCenterYInPixels=wf_cropCenterYInPixels,
        cropExtentXInPixels=wf_cropExtentXInPixels,
        cropExtentYInPixels=wf_cropExtentYInPixels,
        probeEnergyInElectronVolts=wf_probeEnergyInElectronVolts,
        numGpus=wf_numGpus,
        settings=wf_settings,
        demand=wf_demand,
        name=wf_name,
    )

    yield from sleep(0.1)
    logger.info(f"dm_workflow id: {dm_workflow.job_id.get()}")
