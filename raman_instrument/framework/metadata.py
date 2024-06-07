
"""
"""

import apstools
import bluesky
import databroker
# from datetime import datetime
import epics
import getpass
import h5py
import matplotlib
import numpy
import ophyd
import os
import pyRestTable
import socket
import spec2nexus

# required before hkl is imported
import gi
gi.require_version('Hkl', '5.0')
import hkl

from .initialize import RE

from ..session_logs import logger
logger.info(__file__)



# Set up default metadata

RE.md['beamline_id'] = '4-ID-Polar'
RE.md['proposal_id'] = 'testing'
RE.md['pid'] = os.getpid()

HOSTNAME = socket.gethostname() or 'localhost'
USERNAME = getpass.getuser() or 'APS 4-ID-Polar user'
RE.md['login_id'] = USERNAME + '@' + HOSTNAME

# useful diagnostic to record with all data
versions = dict(
    apstools=apstools.__version__,
    bluesky=bluesky.__version__,
    databroker=databroker.__version__,
    epics=epics.__version__,
    h5py=h5py.__version__,
    hklpy=hkl.__version__,
    matplotlib=matplotlib.__version__,
    numpy=numpy.__version__,
    ophyd=ophyd.__version__,
    pyRestTable=pyRestTable.__version__,
    spec2nexus=spec2nexus.__version__,
)
RE.md['versions'] = versions
