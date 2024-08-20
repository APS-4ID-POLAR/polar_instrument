"""
local, custom Device definitions
"""

import sys
sys.path.append("../../common_setup/devices")

from sample_stage import sx, sy, sz
from ventus_laser import laser
from ad_lightfield import spectrometer
from ge_controller import ge_apply, ge_release
