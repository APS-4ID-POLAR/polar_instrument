from importlib import import_module
from time import time as ttime, sleep
from ophyd.signal import ConnectionTimeoutError
from collections import OrderedDict
from .config import iconfig
from .run_engine import sd
from .oregistry_setup import oregistry
from ._logging_setup import logger

TIMEOUT = iconfig.get("OPHYD", {}).get("TIMEOUTS", {}).get("PV_CONNECTION", 5)


def AD_plugin_primed(plugin):
    """
    Modification of the APS AD_plugin_primed for Vortex.

    Uses the timestamp = 0 as a sign of an unprimed plugin. Not sure this is
    generic.
    """

    return plugin.time_stamp.get() != 0


def AD_prime_plugin2(plugin):
    """
    Modification of the APS AD_plugin_primed for Vortex.

    Some area detectors PVs are not setup in the Vortex.
    """
    if AD_plugin_primed(plugin):
        logger.debug("'%s' plugin is already primed", plugin.name)
        return

    if getattr(plugin, "warmup", None) is not None:
        plugin.warmup()
    else:
        sigs = OrderedDict(
            [
                (plugin.enable, 1),
                (plugin.parent.cam.array_callbacks, 1),  # set by number
                (plugin.parent.cam.image_mode, 0),  # Single, set by number
                # Trigger mode names are not identical for every camera.
                # Assume here that the first item in the list is
                # the best default choice to prime the plugin.
                (plugin.parent.cam.trigger_mode, 1),  # set by number
                # just in case the acquisition time is set very long...
                (plugin.parent.cam.acquire_time, 1),
                (plugin.parent.cam.acquire, 1),  # set by number
            ]
        )

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            sleep(0.1)  # abundance of caution
            sig.set(val).wait()

        sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            sleep(0.1)
            sig.set(val).wait()


def device_import(module_name, obj_name, baseline, timeout=TIMEOUT):
    t0 = ttime()
    try:
        module_path = f"instrument.devices.{module_name}"
        module = import_module(module_path)
        obj = getattr(module, obj_name)
        obj.wait_for_connection(timeout=timeout)
    except (
        KeyError, NameError, TimeoutError, ConnectionTimeoutError
    ) as exinfo:
        logger.warning(
            "Error connecting with '%s in %.2fs, %s",
            obj_name,
            ttime() - t0,
            str(exinfo)
        )
        logger.warning(f"Setting {obj_name} to 'None'.")
        obj = None

    if obj is not None and baseline:
        sd.baseline.append(obj)

    cam = getattr(obj, "cam", None)
    if cam is not None:
        cam.stage_sigs["wait_for_plugins"] = "Yes"
        for nm in obj.component_names:
            item = getattr(obj, nm)
            if "blocking_callbacks" in dir(item):  # is it a plugin?
                item.stage_sigs["blocking_callbacks"] = "No"

    hdf1 = getattr(obj, "hdf1", None)
    if hdf1 is not None:
        if obj.connected:
            if not AD_plugin_primed(hdf1):
                AD_prime_plugin2(hdf1)

    defaults = getattr(obj, "default_settings", None)
    if defaults is not None:
        defaults()

    oregistry.register(obj)

    return obj
