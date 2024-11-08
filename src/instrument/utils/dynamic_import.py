from importlib import import_module
from time import time as ttime
from .config import iconfig
from .run_engine import sd
from ._logging_setup import logger

TIMEOUT = iconfig.get("PV_CONNECTION_TIMEOUT", 15)


def device_import(module_name, obj_name, baseline):
    t0 = ttime()
    try:
        package = __package__
        module_path = f"{package}.devices.{module_name}"
        module = import_module(module_path)
        obj = getattr(module, obj_name)
        obj.wait_for_connection(timeout=TIMEOUT)
    except (KeyError, NameError, TimeoutError) as exinfo:
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

    return obj
