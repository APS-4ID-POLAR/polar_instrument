"""
Databroker catalog, provides ``cat``.
=====================================

.. autosummary::
    ~cat
"""

import logging
from polartools.load_data import load_catalog
import databroker
from .config import iconfig
from .spe_handler import SPEHandler

logger = logging.getLogger(__name__)
logger.info(__file__)

TEMPORARY_CATALOG_NAME = "temp"

catalog_name = iconfig.get("DATABROKER_CATALOG", TEMPORARY_CATALOG_NAME)
if catalog_name == TEMPORARY_CATALOG_NAME:
    _cat = databroker.temp().v2
else:
    _cat = load_catalog(catalog_name)
    _cat.register_handler("AD_SPE_APSPolar", SPEHandler, overwrite=True)

cat = _cat
"""Databroker catalog object, receives new data from ``RE``."""

logger.info("Databroker catalog: %s", cat.name)


