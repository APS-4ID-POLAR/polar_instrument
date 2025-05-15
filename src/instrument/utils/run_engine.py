"""
Setup the Bluesky RunEngine, provides ``RE`` and ``sd``.
========================================================

.. autosummary::
    ~RE
    ~sd
    ~bec
    ~peaks
"""

from apsbits.core.run_engine_init import init_RE
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.utils.config_loaders import get_config
from apsbits.core.catalog_init import init_catalog


iconfig = get_config()
cat = init_catalog(iconfig)
bec, peaks = init_bec_peaks(iconfig)
RE, sd = init_RE(iconfig, bec_instance=bec, cat_instance=cat)
