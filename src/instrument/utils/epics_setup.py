"""
EPICS-related setup
===================

.. autosummary::
    ~epics_scan_id_source
    ~connect_scan_id_pv
"""

import logging

from .config import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)

from .ophyd_setup import *  # noqa  Ensure oregistry & timeouts are setup first.

re_config = iconfig.get("RUN_ENGINE", {})


def epics_scan_id_source(scan_id_epics, _md):
    """
    Callback function for RunEngine.  Returns *next* scan_id to be used.

    * Ignore metadata dictionary passed as argument.
    * Get current scan_id from PV.
    * Apply lower limit of zero.
    * Increment (so that scan_id numbering starts from 1).
    * Set PV with new value.
    * Return new value.

    Exception will be raised if PV is not connected when next
    ``bps.open_run()`` is called.
    """
    new_scan_id = max(scan_id_epics.get(), 0) + 1
    scan_id_epics.put(new_scan_id)
    return new_scan_id


def connect_scan_id_pv(RE, pv: str = None):
    """
    Define a PV to use for the RunEngine's `scan_id`.
    """
    from ophyd import EpicsSignal  # TODO: MUST set timeouts first!

    pv = pv or re_config.get("SCAN_ID_PV")
    if pv is None:
        return

    logger.info("Using EPICS PV %r for RunEngine 'scan_id'", pv)

    scan_id_epics = EpicsSignal(pv, name="scan_id_epics")

    # Setup the RunEngine to use the EPICS PV to provide the scan_id.
    RE.scan_id_source = epics_scan_id_source(scan_id_epics)

    scan_id_epics.wait_for_connection()
    RE.md["scan_id_pv"] = scan_id_epics.pvname
    RE.md["scan_id"] = scan_id_epics.get()  # set scan_id from EPICS
