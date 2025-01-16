"""
ophyd-related setup
===================

.. autosummary::
    ~set_control_layer
    ~set_timeouts
"""

import ophyd
from ophyd.signal import EpicsSignalBase
from .config import iconfig
from ._logging_setup import logger
logger.info(__file__)

DEFAULT_CONTROL_LAYER = "PyEpics"
DEFAULT_TIMEOUT = 2  # default used next...
ophyd_config = iconfig.get("OPHYD", {})


def set_control_layer(control_layer: str = DEFAULT_CONTROL_LAYER):
    """
    Communications library between ophyd and EPICS Channel Access.

    Choices are: PyEpics (default) or caproto.

    OPHYD_CONTROL_LAYER is an application of "lessons learned."

    Only used in a couple rare cases where PyEpics code was failing.
    It's defined here since it was difficult to find how to do this
    in the ophyd documentation.
    """

    control_layer = ophyd_config.get("CONTROL_LAYER", control_layer)
    ophyd.set_cl(control_layer.lower())

    logger.info("using ophyd control layer: %r", ophyd.cl.name)


def set_timeouts():
    """Set default timeout for all EpicsSignal connections & communications."""
    if not EpicsSignalBase._EpicsSignalBase__any_instantiated:
        # Only BEFORE any EpicsSignalBase (or subclass) are created!
        timeouts = ophyd_config.get("TIMEOUTS", {})
        print(timeouts)
        EpicsSignalBase.set_defaults(
            auto_monitor=True,
            timeout=timeouts.get("PV_READ", DEFAULT_TIMEOUT),
            write_timeout=timeouts.get("PV_WRITE", DEFAULT_TIMEOUT),
            connection_timeout=iconfig.get("PV_CONNECTION", DEFAULT_TIMEOUT),
        )
    else:
        logger.warning("Not setting up the timeouts.")
