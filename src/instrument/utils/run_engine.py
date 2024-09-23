"""
Setup the Bluesky RunEngine, provides ``RE`` and ``sd``.
========================================================

.. autosummary::
    ~RE
    ~sd
"""

import logging

import bluesky
from bluesky.utils import ProgressBarManager

from .config import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)

from .best_effort import bec  # noqa
from .catalog import cat  # noqa
from .epics_setup import connect_scan_id_pv  # noqa
from .metadata import MD_PATH  # noqa
from .metadata import re_metadata  # noqa

re_config = iconfig.get("RUN_ENGINE", {})

RE = bluesky.RunEngine()
"""The bluesky RunEngine object."""

# Save/restore RE.md dictionary, in this precise order.
if MD_PATH is not None:
    RE.md = bluesky.utils.PersistentDict(MD_PATH)
RE.md.update(re_metadata(cat))  # programmatic metadata
RE.md.update(re_config.get("DEFAULT_METADATA", {}))
RE.md["station"] = iconfig.get("STATION")

sd = bluesky.SupplementalData()
"""Baselines & monitors for ``RE``."""

RE.subscribe(cat.v1.insert)
RE.subscribe(bec)
RE.preprocessors.append(sd)

connect_scan_id_pv(RE)  # if configured

if re_config.get("USE_PROGRESS_BAR", True):
    # Add a progress bar.
    pbar_manager = ProgressBarManager()
    RE.waiting_hook = pbar_manager
