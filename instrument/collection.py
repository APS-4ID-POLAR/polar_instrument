
"""
configure for data collection in a console session
"""

from .session_logs import logger

logger.info(__file__)

# conda environment name
import os
_conda_prefix = os.environ.get("CONDA_PREFIX")
if _conda_prefix is not None:
    logger.info("CONDA_PREFIX = %s", _conda_prefix)
del _conda_prefix

from . import iconfig
from IPython import get_ipython

# terse error dumps (Exception tracebacks)
_ip = get_ipython()
if _ip is not None:
    _xmode_level = iconfig.get("XMODE_DEBUG_LEVEL", "Minimal")
    _ip.run_line_magic('xmode', _xmode_level)
    logger.info("xmode exception level: '%s'", _xmode_level)
    del _ip

from . import mpl

logger.info("#### Bluesky Framework ####")
from .framework import *

logger.info("#### Devices ####")
from .devices import *

logger.info("#### Callbacks ####")
from .callbacks import *

logger.info("#### Plans ####")
from .plans import *

logger.info("#### Plotting Tools ####")
from .mpl import *

logger.info("#### Utilities ####")
from .utils import *
from apstools.utils import *

# from hkl.user import (
#     cahkl,
#     cahkl_table,
#     calc_UB,
#     list_samples,
#     new_sample,
#     or_swap,
#     select_diffractometer,
#     set_energy,
#     setor,
#     show_sample,
#     show_selected_diffractometer,
#     update_sample,
#     wh,
#     pa,
# )

# from hkl.util import (
#     list_orientation_runs,
#     restore_constraints,
#     restore_energy,
#     restore_orientation as hkl_restore_orientation,
#     restore_reflections,
#     restore_sample,
#     restore_UB,
#     run_orientation_info,
# )

from polartools.absorption import (
    load_absorption,
    load_dichro,
    load_lockin,
    load_multi_dichro,
    load_multi_lockin,
    load_multi_xas,
    process_xmcd,
    plot_xmcd
)

from polartools.diffraction import (
    fit_peak,
    load_info,
    fit_series,
    load_series,
    get_type,
    load_mesh,
    plot_2d,
    plot_fit,
    load_axes,
    plot_data,
    dbplot,
)

from polartools.load_data import (
    db_query,
    show_meta,
    collect_meta,
    lookup_position,
    load_catalog
)

from polartools.pressure_calibration import (
    xrd_calibrate_pressure
)

from polartools.process_images import (
   load_images,
   get_curvature,
   get_spectrum,
   get_spectra,
)

# from IPython import get_ipython
from .utils.local_magics import LocalMagics
get_ipython().register_magics(LocalMagics)

# qxscan_params.load_from_scan(-1)

from ._iconfig import iconfig
if iconfig.get("WRITE_SPEC_DATA_FILES", False):
    if specwriter is not None:
        RE.subscribe(specwriter.receiver)
        logger.info(f"writing to SPEC file: {specwriter.spec_filename}")
        logger.info("   >>>>   Using default SPEC file name   <<<<")
        logger.info("   file will be created when bluesky ends its next scan")
        logger.info("   to change SPEC file, use command:   newSpecFile('title')")

# last line: ensure we have the console's logger
from .session_logs import logger
logger.info("#### Startup is complete. ####")
