from importlib import import_module
from time import time as ttime
from ophyd.signal import ConnectionTimeoutError
from apstools.devices import AD_plugin_primed, AD_prime_plugin2
from .config import iconfig
from .run_engine import sd
from .oregistry_setup import oregistry
from ._logging_setup import logger

TIMEOUT = iconfig.get("PV_CONNECTION_TIMEOUT", 15)


def device_import(module_name, obj_name, baseline, timeout=TIMEOUT):
    t0 = ttime()
    try:
        module_path = f"instrument.devices.{module_name}"
        module = import_module(module_path)
        obj = getattr(module, obj_name)
        print(f"{module_name}: ", timeout)
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
