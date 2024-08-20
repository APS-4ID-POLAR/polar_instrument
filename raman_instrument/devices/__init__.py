"""
local, custom Device definitions
"""

import sys
from pathlib import Path
# sys.path.append("../../common_setup/devices")
sys.path.append(str(Path(__file__).absolute().parent.parent / Path("common_setup/devices")))

from .sample_stage import sx, sy, sz
from .ventus_laser import laser
#from .ad_lightfield import spectrometer
#from .ge_controller import ge_apply, ge_release
