"""
local, custom Device definitions
"""

from ..utils.config import iconfig

if iconfig.get("STATION") == "4idb":
    from .scaler_4idtest import scaler_4tst
    from .hhl_mirror import hhl_mirror
    from .flags import flag_4ida_up, flag_4ida_down
    from .monochromator import mono
    from .jj_slits import monoslt
    from .phaseplates import pr1, pr2, pr3
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


from .counters_class import counters

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
