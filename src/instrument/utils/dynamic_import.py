from importlib import import_module
from time import time as ttime
from ophyd.signal import ConnectionTimeoutError
from apstools.devices import AD_plugin_primed, AD_prime_plugin2
from yaml import load as yload, Loader as yloader
from os.path import dirname, abspath, join
from .config import iconfig
from .run_engine import sd
from .oregistry_setup import oregistry
from ._logging_setup import logger

TIMEOUT = iconfig.get("OPHYD", {}).get("TIMEOUTS", {}).get("PV_CONNECTION", 5)

_current_folder = dirname(abspath(__file__))
DEVICES = yload(
    open(join(_current_folder, "../configs/4ida_devices.yml"), "r").read(),
    yloader
)


def _load_device(
        name,
        module_name,
        class_obj,
        prefix,
        parameters,
        baseline,
        timeout,
        run_defaults
):
    t0 = ttime()
    try:
        # TODO: Change the module path to installed module.
        module = import_module(f"instrument.devices.{module_name}")
        obj = getattr(module, class_obj)
        dev = obj(prefix, **parameters)
        dev.wait_for_connection(timeout=timeout)
    except (
        KeyError, NameError, TimeoutError, ConnectionTimeoutError
    ) as exinfo:
        logger.warning(
            "Error connecting with '%s in %.2fs, %s",
            name,
            ttime() - t0,
            str(exinfo)
        )
        logger.warning(f"Setting {name} to 'None'.")
        dev = None

    if dev is not None and baseline:
        sd.baseline.append(dev)

    cam = getattr(dev, "cam", None)
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

    defaults = getattr(dev, "default_settings", None)
    if defaults is not None and run_defaults:
        defaults()

    oregistry.register(dev)

    return dev


def load_device(name: str, baseline=False, timeout=TIMEOUT):
    config = DEVICES.get(name, None)
    if config is None:
        raise ValueError(
            f"Could not find {name} in the beamline configuration file."
        )

    baseline = config.get("baseline", baseline)
    timeout = config.get("timeout", timeout)
    run_defaults = config.get("run_defaults", False)

    return _load_device(
        name,
        config["module"],
        config["class"],
        config["parameters"],
        baseline,
        timeout,
        run_defaults
    )
