"""
local, custom Device definitions
"""

from ..utils.config import iconfig
from ..utils.dynamic_import import device_import
from .counters_class import counters

scaler_name = None
devs = dict()

if iconfig.get("STATION") == "4idb":
    devs = dict(
        scaler_4idCTR8=[["scaler_ctr8", True]],
        jj_slits=[["monoslt", True]],
        ad_vimba=[
            ["flag_camera_4ida_up", False],
            ["flag_camera_4ida_down", False]
        ],
        qxscan_setup=[["qxscan_params", True]],
        hhl_mirror=[["hhl_mirror", True]],
        flags=[["flag_4ida_up", True], ["flag_4ida_down", True]],
        monochromator=[["mono", True]],
        labjacks=[["labjack_4ida", True]],
        phaseplates=[["pr1", True], ["pr2", True], ["pr3", True]],
        s4idundulator=[["undulators", True]],
        energy_device=[["energy", True]],
    )
    scaler_name = "scaler_ctr8"

if iconfig.get("STATION") == "4idg":
    from .simulated_scaler import scaler
    from .scaler_4idtest import scaler_4tst
    from .simulated_fourc_vertical import fourc
    from .simulated_new_diffractometer import diffract
    from .simulated_detector import simdet
    from .polar_diffractometer import polar, polar_psi
    from .xspress import load_vortex
    from .ad_eiger1M import load_eiger1m
    from .nanopositioner import diff_nano
    from .softgluezynq import sgz
    from .pva_control import positioner_stream
    from .data_management import dm_experiment, dm_workflow
elif iconfig.get("STATION") == "raman":
    from .laser_sample_stage import sx, sy, sz
    from .ventus_laser import laser
    from .ad_lightfield import spectrometer
    from .ge_controller import ge_apply, ge_release


# is there a better way?
for module, items in devs.items():
    for obj, baseline in items:
        locals()[obj] = device_import(module, obj, baseline)

counters.default_scaler = locals()[scaler_name]

# from .nanopositioner import diff_nano
# from .interferometers_4IDG import interferometer
# from .magnet_nanopositioner import magnet_nano

# from .preamps import preamp1, preamp2
# preamp1._scaler_channel = scaler_4tst.channels.chan02
# preamp2._scaler_channel = scaler_4tst.channels.chan03

# from .ad_eiger1M import load_eiger1m
# from .softgluezynq import sgz
# from .pva_control import positioner_stream
# from .data_management import dm_experiment, dm_workflow
