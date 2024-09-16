
"""
custom callbacks
"""

from apstools.callbacks import (
    SpecWriterCallback, spec_comment as aps_spec_comment
)
from apstools.utils import cleanupText
from datetime import datetime
from os import getcwd
from os.path import join, exists
from .initialize import RE
from ..session_logs import logger
logger.info(__file__)

__all__ = [
    'specwriter',
    'spec_comment',
    'newSpecFile',
]


# write scans to SPEC data file
specwriter = SpecWriterCallback()
# make the SPEC file in /tmp (assumes OS is Linux)
# _path = "/tmp"
# make the SPEC file in current working directory (assumes is writable)
_path = getcwd()
specwriter.newfile(join(_path, specwriter.spec_filename))
# callback_db['specwriter'] = RE.subscribe(specwriter.receiver)
RE.subscribe(specwriter.receiver)

logger.info(f"writing to SPEC file: {specwriter.spec_filename}")
logger.info("   >>>>   Using default SPEC file name   <<<<")
logger.info("   file will be created when bluesky ends its next scan")
logger.info("   to change SPEC file, use command:   newSpecFile('title')")


def spec_comment(comment, doc=None):
    # supply our specwriter to the standard routine
    aps_spec_comment(comment, doc, specwriter)


def newSpecFile(title, scan_id=1):
    """
    user choice of the SPEC file name

    cleans up title, prepends month and day and appends file extension
    """
    global specwriter
    mmdd = str(datetime.now()).split()[0][5:].replace("-", "_")
    clean = cleanupText(title)
    fname = "%s_%s.dat" % (mmdd, clean)
    if exists(fname):
        logger.warning(f">>> file already exists: {fname} <<<")
        specwriter.newfile(fname, RE=RE)
        handled = "appended"

    else:
        specwriter.newfile(fname, scan_id=scan_id, RE=RE)
        handled = "created"

    logger.info(f"SPEC file name : {specwriter.spec_filename}")
    logger.info(f"File will be {handled} at end of next bluesky scan.")
