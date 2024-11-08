"""
local, custom Device definitions
"""

from yaml import load as yload, Loader as yloader
from ..utils.config import iconfig
from ..utils.dynamic_import import device_import
from .counters_class import counters

# devs_a = dict(
#     s4idundulator=[["undulators", True]],
#     hhl_mirror=[["hhl_mirror", True]],
#     wb_slit=[["wbslt", True]],
#     monochromator=[["mono", True]],
#     labjacks=[["labjack_4ida", True]],
#     ad_vimba=[
#         ["flag_camera_4ida_up", False],
#         ["flag_camera_4ida_down", False]
#     ],
#     flags=[["flag_4ida_up", True], ["flag_4ida_down", True]],
#     jj_slits=[["monoslt", True]],
#     phaseplates=[["pr1", True], ["pr2", True], ["pr3", True]],
#     energy_device=[["energy", True]],
#     qxscan_setup=[["qxscan_params", True]],
#     data_management=[["dm_experiment", True], ["dm_workflow", True]]
# )

devs_a = yload(open("../configs/4ida_devices.yml", "r").read(), yloader)

devs_b = dict(
    scaler_4idCTR8=[["scaler_ctr8", True]],
    ad_vimba=[["flag_camera_4idb", False]],
)

devs_g = dict(
    polar_diffractometer=[["polar", True], ["polar_psi", True]],
    simulated_fourc_vertical=[["fourc", True]],
    pva_control=["positioner_stream", True],
    softgluezynq=[["sgz", True]],
    nanopositioner=[["diff_nano", True]],
    xspress=[["load_vortex", True]],  # TODO: Replace by import device?
    ad_eiger1M=[["load_eiger1m", True]],  # TODO: Replace by import device?
)

devs_raman = dict(
    laser_sample_stage=[["sx", True], ["sy", True], ["sz", True]],
    ventus_laser=[["laser", True]],
    ad_lightfield=[["spectrometer", True]],
    ge_controller=[["ge_apply", True], ["ge_release", True]]
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
    for obj, baseline in items:
        locals()[obj] = device_import(module, obj, baseline)

counters.default_scaler = locals()[scaler_name]
