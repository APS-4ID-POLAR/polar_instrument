""" Loads a new lambda device """

from ..devices.ad_lambda import Lambda250kDetector
from ..session_logs import logger
logger.info(__file__)

__all__ = ['load_lambda']


def load_lambda(pv="DP_LAMBDA250K_1:"):

    logger.info("-- Loading Lambda 250k detector --")
    lambda250k = Lambda250kDetector(pv, name="lambda250k")

    lambda250k.wait_for_connection(timeout=10)

    # logger.info("Setting up ROI and STATS defaults ...", end=" ")
    logger.info("Setting up ROI and STATS defaults ...")
    for name in lambda250k.component_names:
        if "roi" in name:
            roi = getattr(lambda250k, name)
            roi.wait_for_connection(timeout=10)
            roi.nd_array_port.put("PROC1")
        if "stats" in name:
            stat = getattr(lambda250k, name)
            stat.wait_for_connection(timeout=10)
            stat.nd_array_port.put(f"ROI{stat.port_name.get()[-1]}")
    logger.info("Done!")

    # logger.info("Setting up defaults kinds ...", end=" ")
    logger.info("Setting up defaults kinds ...")
    lambda250k.default_kinds()
    logger.info("Done!")
    # logger.info("Setting up default settings ...", end=" ")
    logger.info("Setting up default settings ...")
    lambda250k.default_settings()
    logger.info("Done!")
    logger.info("All done!")
    return lambda250k
