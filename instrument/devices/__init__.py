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
