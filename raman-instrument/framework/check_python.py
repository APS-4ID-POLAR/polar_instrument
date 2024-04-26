
"""
make sure we have the software packages we need
"""

import sys
from ..session_logs import logger
logger.info(__file__)

__all__ = []


# ensure Python 3.6+
req_version = (3, 6)
cur_version = sys.version_info
if cur_version < req_version:
    ver_str = '.'.join((map(str, req_version)))
    raise RuntimeError(
        f"Requires Python {ver_str}+ with the Bluesky framework.\n"
        f"You have Python {sys.version} from {sys.prefix}\n"
        "\n"
        "You should exit now and start ipython"
        " with the Bluesky framework."
        )
