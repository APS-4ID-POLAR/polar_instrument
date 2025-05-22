"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

import logging
from pathlib import Path

# from apsbits.core.best_effort_init import init_bec_peaks
# from apsbits.core.catalog_init import init_catalog
from apsbits.core.instrument_init import make_devices
from apsbits.core.instrument_init import oregistry
# from apsbits.core.run_engine_init import init_RE
from apsbits.utils.aps_functions import aps_dm_setup
# from apsbits.utils.aps_functions import host_on_aps_subnet
from apsbits.utils.config_loaders import get_config
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

# Get the path to the instrument package
instrument_path = Path(__file__).parent

# Load configuration to be used by the instrument.
iconfig_path = instrument_path / "configs" / "iconfig.yml"
load_config(iconfig_path)

# Get the configuration
iconfig = get_config()

logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# Discard oregistry items loaded above.
oregistry.clear()

# Configure the session with callbacks, devices, and plans.
aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Initialize core bluesky components
from .utils.run_engine import RE, sd, bec, cat, peaks  # noqa: F401, E402

# Import optional components based on configuration
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    # from .callbacks.nexus_data_file_writer import nxwriter_init
    # nxwriter = nxwriter_init(RE)
    from .callbacks.nexus_data_file_writer import nxwriter  # noqa: F401

if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.spec_data_file_writer import init_specwriter_with_RE
    from .callbacks.spec_data_file_writer import newSpecFile  # noqa: F401
    from .callbacks.spec_data_file_writer import spec_comment  # noqa: F401
    from .callbacks.spec_data_file_writer import specwriter  # noqa: F401

    init_specwriter_with_RE(RE)

# These imports must come after the above setup.
if running_in_queueserver():
    # To make all the standard plans available in QS, import by '*', otherwise
    # import plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403, F401
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F401, F403
    from apstools.utils import *  # noqa: F401, F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

    from .utils.counters_class import counters  # noqa: F401
    from .utils.pr_setup import pr_setup  # noqa: F401
    from .utils.attenuator_utils import atten  # noqa: F401
    from .utils.suspenders import (  # noqa: F401
        run_engine_suspenders,
        suspender_restart,
        suspender_stop,
        suspender_change_sleep
    )
    from .utils.dm_utils import *  # noqa: F401, F403
    from .utils.experiment_utils import *  # noqa: F401, F403
    from .utils.hkl_utils import *  # noqa: F401, F403
    from .utils.polartools_hklpy_imports import *  # noqa: F401, F403
    from .utils.oregistry_auxiliar import get_devices  # noqa: F401
    # TODO: Both DM, hklpy, experiment_utils seems to be changing the
    # logging level. I don't know why.
    logger.setLevel(logging.BSDEV)

    from .plans import *  # noqa: F401, F403


RE(make_devices(clear=True, file="devices.yml"))  # Create the devices.

# Only run .default_setting and add to baseline if belongs to the hutch
# Maybe I can use the device label as a sorting mechanism? - Using oregistry..

STATIONS = ["4ida", "4idb"]

devices = oregistry.findall(STATIONS)  # Not sure oregistry takes a list...
for device in devices:
    try:
        device.default_setting()
        sd.baseline.append(device)
    except TimeoutError:
        logger.warning(
            "TimeoutError encountered while setting default for device: "
            f"{device.name}. Will not add to the baseline."
        )
