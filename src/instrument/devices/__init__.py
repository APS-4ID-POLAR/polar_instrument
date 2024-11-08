"""
local, custom Device definitions
"""

from yaml import load as yload, Loader as yloader
from os.path import dirname, abspath, join
from ..utils.config import iconfig
from ..utils.dynamic_import import device_import
from .counters_class import counters

current_folder = dirname(abspath(__file__))

devs_a = yload(
    open(join(current_folder, "../configs/4ida_devices.yml"), "r").read(),
    yloader
)

devs_b = yload(
    open(join(current_folder, "../configs/4idb_devices.yml"), "r").read(),
    yloader
)

devs_g = yload(
    open(join(current_folder, "../configs/4idg_devices.yml"), "r").read(),
    yloader
)

devs_raman = yload(
    open(join(current_folder, "../configs/4idraman_devices.yml"), "r").read(),
    yloader
)

scaler_name = None
devs = dict()

if iconfig.get("STATION") == "4idb":
    devs = devs_a | devs_b
    scaler_name = "scaler_ctr8"
elif iconfig.get("STATION") == "4idg":
    devs = devs_a | devs_b | devs_g
    scaler_name = "scaler_ctr8"
elif iconfig.get("STATION") == "raman":
    devs = devs_raman

# is there a better way?
for module, items in devs.items():
    devices = (
        [items["device"]]
        if isinstance(items["device"], str) else
        items["device"]
    )
    baselines = (
        [items["baseline"]]
        if isinstance(items["baseline"], bool) else
        items["baseline"]
    )
    for device, baseline in zip(devices, baselines):
        locals()[device] = device_import(module, device, baseline)

if scaler_name is not None:
    counters.default_scaler = locals()[scaler_name]
