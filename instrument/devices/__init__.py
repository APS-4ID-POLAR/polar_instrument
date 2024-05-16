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
from .softgluezynq import sgz

# TODO: this is useful while we are doing pre-commissioning tests
# Remove everything from baseline.
from ..framework import sd
sd.baseline = []
