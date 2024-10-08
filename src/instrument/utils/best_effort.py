"""
BestEffortCallback: simple real-time visualizations, provides ``bec``.
======================================================================

.. autosummary::
    ~bec
    ~peaks
"""

import logging

from bluesky.callbacks.best_effort import BestEffortCallback

logger = logging.getLogger(__name__)
logger.info(__file__)

from .config import iconfig  # noqa
from .functions import running_in_queueserver  # noqa

bec = BestEffortCallback()
"""BestEffortCallback object, creates live tables and plots."""

bec_config = iconfig.get("BEC", {})

if not bec_config.get("BASELINE", True):
    bec.disable_baseline()

if not bec_config.get("HEADING", True):
    bec.disable_heading()

if not bec_config.get("PLOTS", True) or running_in_queueserver():
    bec.disable_plots()

if not bec_config.get("TABLE", True):
    bec.disable_table()

peaks = bec.peaks
"""Dictionary with statistical analysis of LivePlots."""
