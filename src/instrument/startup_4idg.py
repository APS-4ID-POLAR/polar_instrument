"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

from os import environ
if not environ.get("POLAR_INSTRUMENT"):
    environ["POLAR_INSTRUMENT"] = "4idg"

# logging setup first
from .utils import logger

logger.info(__file__)

# Bluesky data acquisition setup
from .utils.best_effort import bec  # noqa
from .utils.best_effort import peaks  # noqa
from .utils.catalog import full_cat  # noqa
from .utils.functions import running_in_queueserver  # noqa
from .utils.oregistry_auxiliar import oregistry, get_devices  # noqa
from .utils.run_engine import RE, sd  # noqa

# Configure the session with callbacks, devices, and plans.
# These imports must come after the above setup.
if running_in_queueserver():
    from apstools.plans import lineup2  # noqa
    from bluesky.plans import *  # noqa
else:
    from apstools.plans import *  # noqa
    from apstools.utils import *  # noqa
    from bluesky import plan_stubs as bps  # noqa
    from bluesky import plans as bp  # noqa

    # Sessions in the queueserver do not need the devices & signals.
    # Their plans can find the devices & signals they need in the oregistry.
    from .devices import *  # noqa

from .callbacks import *  # noqa
from .plans import *  # noqa
from .utils.polartools_hklpy_imports import *  # noqa
from .utils import *  # noqa: E402, F403

# TODO: Loads plans for development, remove for production.
# from .utils.tests.common import *  # noqa

from IPython import get_ipython  # noqa: E402
from .utils.local_magics import LocalMagics  # noqa: E402
get_ipython().register_magics(LocalMagics)

cat = db_query(full_cat, dict(instrument_name = f'polar-{environ["POLAR_INSTRUMENT"]}'))
