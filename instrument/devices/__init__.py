"""
local, custom Device definitions
"""

from .simulated_scaler import scaler
from .scaler_4idtest import scaler_4tst
from .simulated_fourc_vertical import fourc
from .simulated_new_diffractometer import diffract
from .simulated_detector import simdet
from .nanopositioner import diff_nano
from .interferometers_4IDG import interferometer
from .magnet_nanopositioner import magnet_nano

from .preamps import preamp1, preamp2
preamp1._scaler_channel = scaler_4tst.channels.chan02
preamp2._scaler_channel = scaler_4tst.channels.chan03

from .ad_eiger1M import load_eiger1m
from .softgluezynq import sgz
from .pva_control import positioner_stream
from .data_management import dm_experiment, dm_workflow

# TODO: this is useful while we are doing pre-commissioning tests
# Remove everything from baseline.
from ..framework import sd
sd.baseline = []
