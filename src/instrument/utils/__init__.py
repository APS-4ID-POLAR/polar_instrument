"""
Utility support to start bluesky sessions.

Also contains setup code that MUST run before other code in this directory.
"""

from ._logging_setup import logger  # noqa
from .aps_dm_setup import *  # noqa
from .debug_setup import *  # noqa
from .mpl_setup import *  # noqa

# from .dm_utils import (
#   setup_user, dm_get_experiment_data_path, get_processing_job_status
# )
# from .local_magics import LocalMagics

from .config import iconfig

if iconfig.get("STATION") == "4idg":
    from .hkl_utils import *
    # from .transfocator_calculation import *
    from .flyscan_utils import read_flyscan_stream, find_eiger_triggers
    from .attenuator_utils import atten 
elif iconfig.get("STATION") == "raman":
    pass
