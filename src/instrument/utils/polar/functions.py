"""
Utility functions
=================

.. autosummary::

    ~host_on_aps_subnet
    ~running_in_queueserver
"""

__all__ = """
    host_on_aps_subnet
    running_in_queueserver
""".split()

import logging
import socket

logger = logging.getLogger(__name__)
logger.info(__file__)


def host_on_aps_subnet():
    """Detect if this host is on an APS subnet."""
    LOOPBACK_IP4 = "127.0.0.1"
    PUBLIC_IP4_PREFIX = "164.54."
    PRIVATE_IP4_PREFIX = "10.54."
    TEST_IP = "10.254.254.254"  # does not have to be reachable
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0)
        try:
            sock.connect((TEST_IP, 1))
            ip4 = sock.getsockname()[0]
        except Exception:
            ip4 = LOOPBACK_IP4
    return True in [
        ip4.startswith(PUBLIC_IP4_PREFIX),
        ip4.startswith(PRIVATE_IP4_PREFIX),
    ]


def running_in_queueserver():
    """Detect if running in the bluesky queueserver."""
    try:
        from bluesky_queueserver import is_re_worker_active

        active = is_re_worker_active()
        # print(f"{active=!r}")
        return active
    except Exception as cause:  # noqa
        # print(f"{cause=}")
        return False
