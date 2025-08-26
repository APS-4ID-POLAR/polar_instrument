from pathlib import Path
import yaml
from pyRestTable import Table
from apsbits.core.instrument_init import oregistry
from apstools.utils import dynamic_import
from logging import getLogger
import sys
from time import sleep
from apsbits.core.instrument_init import make_devices
from ophyd import OphydObject
from .run_engine import sd, RE

logger = getLogger(__name__)

# Default configuration file path for devices
DEFAULT_FILE = Path(__file__).parent / "../configs/devices.yml"
# Main namespace for dynamic imports
MAIN_NAMESPACE = "__main__"


def load_yaml_devices(file=DEFAULT_FILE):
    """
    Load devices from a YAML configuration file.

    Parameters
    ----------
    file : str or pathlib.Path, optional
        The path to the YAML configuration file. Defaults to `DEFAULT_FILE`.

    Returns
    -------
    dict
        A dictionary where keys are device names and values are dictionaries
        containing device parameters, including the class of the device.

    Notes
    -----
    The YAML file is expected to have a structure where each key represents
    a device class, and its value is a list of device parameters. Each device
    must have a 'name' parameter which is used as the key in the returned
    dictionary.
    """
    devices_yaml = yaml.load(open(file, "r").read(), yaml.Loader)

    devices = dict()
    # Iterate through each device class and its parameters
    for key, items in devices_yaml.items():
        for params in items:
            name = params.pop("name")
            devices[name] = {"class": key}
            devices[name].update(params)

    return devices


# Load available devices from the default YAML configuration file
AVAILABLE_DEVICES = load_yaml_devices()


def _exact(a, b):
    """Check if two strings are exactly equal"""
    return a == b


def _partial(a, b):
    """Check if string 'a' is a substring of string 'b'"""
    return a in b


def find_loadable_devices(name=None, label=None, exact_name=False):
    """
    Find devices based on name and label search.

    Parameters
    ----------
    name : str, optional
        The name of the device to search for. If None, all devices are
        considered.
    label : str, optional
        The label to search for within device labels. If None, all labels are
        considered.
    exact_name : bool, optional
        If True, perform an exact match on the device name. If False, perform a
        partial match. Defaults to False.

    Returns
    -------
    None
        Prints a table of devices matching the search criteria in
        reStructuredText format.

    Notes
    -----
    The function filters devices from `AVAILABLE_DEVICES` based on the provided
    `name` and `label`. It uses `_exact` or `_partial` functions for name
    matching based on the `exact_name` parameter. The filtered devices are
    displayed in a table format with columns for Name, Prefix, and Labels.
    """
    func = _exact if exact_name else _partial

    output = AVAILABLE_DEVICES.copy()

    # Find names
    if name is not None:
        for key, item in AVAILABLE_DEVICES.items():
            if not func(name, key):
                del output[key]

    # Find labels
    if label is not None:
        _out = output.copy()
        for key, item in _out.items():
            if label not in item["labels"]:
                del output[key]

    # Create a table to display filtered devices
    table = Table()
    table.labels = ("Name", "Prefix", "Labels")
    for key, items in output.items():
        table.rows.append(
            (
                key,
                items.get("prefix", None) or items.get("PV", "not found"),
                ", ".join(items["labels"]),
            )
        )

    # Print the table in reStructuredText format
    print(table.reST())


def connect_device(device, baseline=None, raise_error=True):
    """
    Connects a device and optionally adds it to the baseline.

    Parameters
    ----------
    device : object
        The device object to be connected. It must have a `name` attribute
        and a `wait_for_connection` method.
    baseline : bool or None, optional
        Determines if the device should be added to the baseline. If None,
        the function checks the device's labels in `AVAILABLE_DEVICES` to
        decide. Defaults to None.
    raise_error : bool, optional
        If raise_error is True, a ValueError is raised if the device is not
        found in `AVAILABLE_DEVICES`.
    Raises
    ------
    ValueError
        If the device is not found in `AVAILABLE_DEVICES` and `baseline` is
        None.

    Notes
    -----
    The function first checks if the device is already registered in
    `oregistry`. If so, it removes the existing entry. It then attempts to
    connect the device and apply default settings if available. The device is
    registered in `oregistry` and added to the baseline if applicable. If a
    `TimeoutError` occurs during connection, the device is removed from
    `oregistry` and the baseline.
    """

    # Work out if we want to add to the baseline or not.
    if baseline is None:
        if device.name not in AVAILABLE_DEVICES.keys():
            if raise_error:
                raise ValueError(
                    f"Could not find the {device.name} in the devices config "
                    "list. You will need to enter True or False to the "
                    "baseline keyword argument."
                )
            else:
                return

        baseline = (
            True
            if "baseline" in AVAILABLE_DEVICES[device.name]["labels"]
            else False
        )

    # Remove device from registry if it already exists
    if oregistry.find(device.name, allow_none=True) is not None:
        oregistry.pop(device)

    try:
        logger.info(f"Connecting to {device.name}...")
        device.wait_for_connection()

        # Apply default settings if available
        if hasattr(device, "default_settings"):
            device.default_settings()

        # Register device if not already registered
        if oregistry.find(device.name, allow_none=True) is None:
            oregistry.register(device)

        # Add device to baseline if applicable
        if baseline:
            for dev in sd.baseline:
                if dev.name == device.name:
                    logger.info(
                        f"Found a duplicated {device.name} name in the "
                        "baseline. Removing the old one."
                    )
                    sd.baseline.remove(dev)

            sd.baseline.append(device)
        
        cam = getattr(device, "cam", None)
        if cam is not None:
            cam.stage_sigs["wait_for_plugins"] = "Yes"
            for nm in device.component_names:
                item = getattr(device, nm)
                if "blocking_callbacks" in dir(item):  # is it a plugin?
                    item.stage_sigs["blocking_callbacks"] = "No"

        hdf1 = getattr(device, "hdf1", None)
        if hdf1 is not None:
            if device.connected:
                if not AD_plugin_primed(hdf1):
                    AD_prime_plugin2(hdf1)

    except TimeoutError:
        message = (
            f"Device {device.name} is disconnected, removing it from oregistry."
        )

        if device in sd.baseline:
            sd.baseline.remove(device)
            message += " This device was removed from the baseline."
        logger.warning(message)


def load_device(name, file=None):
    """
    Load and connect a device by its name from a YAML configuration file.

    Parameters
    ----------
    name : str
        The name of the device to be loaded.
    file : str or None, optional
        The path to the YAML configuration file. If None, the default
        configuration file is used.

    Raises
    ------
    ValueError
        If the device is not found in the configuration file or if the
        device class is not specified in the YAML file.

    Notes
    -----
    The function checks if the device already exists in the registry.
    If not, it loads the device configuration, dynamically imports the
    device class, and connects the device. The device is then added to
    the main namespace and optionally to the baseline if specified in
    the configuration.
    """

    if oregistry.find(name, allow_none=True) is not None:
        logger.warning(
            "The device already exists in the registry. If was not connected, "
            "see `connect_device` function"
        )
        return

    # Load devices from specified file or default file
    _devices = (
        AVAILABLE_DEVICES.copy() if file is None else load_yaml_devices(file)
    )

    # Check if device is available in the loaded configurations
    if name not in _devices:
        raise ValueError(
            "Could not find the device with the specified name."
            "See find_loadable_devices() for available devices."
        )

    params = _devices[name].copy()

    # Get the class path for the device
    class_path = params.pop("class", None)
    if class_path is None:
        raise ValueError(
            "Could not find the class of the device. Please check the .yaml "
            "file."
        )

    baseline = False
    # Check if device should be added to baseline
    if "labels" in params.keys():
        if "baseline" in params["labels"]:
            baseline = True

    # Dynamically import the device class
    device_class = dynamic_import(class_path)
    # Instantiate the device with its parameters
    device = device_class(**params, name=name)

    # Connect and register the device
    connect_device(device, baseline=baseline)

    # Add device to the main namespace
    logger.info("Adding device %r to the main namespace", name)
    namespace = sys.modules[MAIN_NAMESPACE]
    setattr(namespace, name, device)



def AD_plugin_primed(plugin):
    """
    Determine whether an AreaDetector plugin is primed.

    This variant treats a time stamp of 0 as unprimed.

    Parameters
    ----------
    plugin : object
        The plugin device. Expected to provide:
        - time_stamp: A signal-like object with a .get() method that returns
          a numeric time stamp.

    Returns
    -------
    bool
        True if the plugin appears primed (time stamp != 0), False otherwise.

    Notes
    -----
    This is a modification of the APS AD_plugin_primed heuristic. Using
    time_stamp == 0 to indicate an unprimed state may not be generic across
    all detectors.
    """
    return plugin.time_stamp.get() != 0


def AD_prime_plugin2(plugin):
    """
    Prime (warm up) the HDF5 AreaDetector plugin if it is not already primed.

    This function checks whether the given plugin has been primed using
    AD_plugin_primed. If the plugin is not primed, it attempts to call the
    plugin's warmup method when available. If no warmup method is present,
    a warning is logged to indicate that manual warmup may be required.

    Parameters
    ----------
    plugin : object
        The AreaDetector plugin device to prime. Expected to have:
        - name (str): Plugin name for logging.
        - time_stamp (Signal-like): Used by AD_plugin_primed to determine
          primed state.
        - warmup (callable, optional): Method that performs the warmup.

    Returns
    -------
    None

    Notes
    -----
    - Determination of the primed state is delegated to AD_plugin_primed(plugin).
      For some detectors (e.g., Vortex), a time stamp of 0 is treated as
      "unprimed."
    - If the plugin is already primed, this function logs at debug level and
      returns without performing any action.
    """
    if AD_plugin_primed(plugin):
        logger.debug("'%s' plugin is already primed", plugin.name)
        return

    if getattr(plugin, "warmup", None) is not None:
        plugin.warmup()
    else:
        logger.warning(
            f"Warmup function not found at {plugin.name}.warmup(). The HDF5 "
            "plugin of this area detector may need to be manually warmed up."
        )


def reload_all_devices(file="devices.yml"):
    """
    Reload all devices from a configuration file and connect devices.

    Parameters
    ----------
    file : str, optional
        Path to the YAML devices configuration file. Defaults to "devices.yml".

    Returns
    -------
    None
        Creates devices and add them to the main namespace

    Notes
    -----
    This function:
    1. Invokes the `make_devices` plan with `clear=True` via the RunEngine to
       rebuild and register devices from the specified configuration file.
    2. Searches the registry for devices matching known station identifiers
       ("source", "4ida", "4idb", "4idg", "4idh") and attempts to connect them
       without raising errors on failure.
    """

    RE(make_devices(clear=True, file=file))  # Create the devices.

    stations = ["source", "4ida", "4idb", "4idg", "4idh"]
    for device in oregistry.findall(stations):
        connect_device(device, raise_error=False)


def remove_device(device):
    """
    Remove a device from the registry and the baseline list.

    Parameters
    ----------
    device : OphydObject or str
        The device instance to remove, or the registered name of the device.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If `device` is neither an OphydObject nor a string, or if a device
        name is provided but no matching device is found in the registry.

    Notes
    -----
    If a device name (str) is provided, the function looks up the device in
    `oregistry`. The device is removed from `oregistry` and, if present, from
    `sd.baseline`.
    """
    if isinstance(device, str):
        dev_obj = oregistry.find(device, allow_none=True)
        if dev_obj is None:
            raise ValueError(
                f"Could not find a device named {device!r} in the registry."
            )
        device = dev_obj
    elif not isinstance(device, OphydObject):
        raise ValueError("Input must be an ophyd device or a device name.")
    
    _ = oregistry.pop(device)
    if device in sd.baseline:
        sd.baseline.remove(device)
