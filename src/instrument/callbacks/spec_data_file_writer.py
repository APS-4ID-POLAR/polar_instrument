"""
custom callbacks
================

.. autosummary::
    ~newSpecFile
    ~spec_comment
    ~specwriter
"""

__all__ = """
    newSpecFile
    spec_comment
    specwriter
""".split()

import datetime
import pathlib

import apstools.callbacks
import apstools.utils
from ..utils._logging_setup import logger

logger.info(__file__)

from ..utils.config import iconfig  # noqa
from ..utils.run_engine import RE  # noqa

from .apstools_spec_file_writer import SpecWriterCallback2


spec_config = iconfig.get("SPEC_DATA_FILES")

DEFAULT_FILE_EXTENSION = "dat"
file_extension = spec_config.get("FILE_EXTENSION", DEFAULT_FILE_EXTENSION)


def spec_comment(comment, doc=None):
    """Make it easy for user to add comments to the data file."""
    apstools.callbacks.spec_comment(comment, doc, specwriter)


def newSpecFile(title, scan_id=None, RE=None):
    """
    User choice of the SPEC file name.

    Cleans up title, prepends month and day and appends file extension.
    If ``RE`` is passed, then resets ``RE.md["scan_id"] = scan_id``.

    If the SPEC file already exists, then ``scan_id`` is ignored and
    ``RE.md["scan_id"]`` is set to the last scan number in the file.
    """
    kwargs = {}
    if RE is not None:
        kwargs["RE"] = RE

    mmdd = str(datetime.datetime.now()).split()[0][5:].replace("-", "_")
    clean = apstools.utils.cleanupText(title)
    fname = pathlib.Path(f"{mmdd}_{clean}.{file_extension}")
    if fname.exists():
        logger.warning(f">>> file already exists: {fname} <<<")
        handled = "appended"
    else:
        kwargs["scan_id"] = scan_id or 1
        handled = "created"

    specwriter.newfile(fname, **kwargs)

    logger.info(f"SPEC file name : {specwriter.spec_filename}")
    logger.info(f"File will be {handled} at end of next bluesky scan.")


# write scans to SPEC data file
try:
    # apstools >=1.6.21
    # _specwriter = apstools.callbacks.SpecWriterCallback2()
    _specwriter = SpecWriterCallback2()
    # _specwriter = apstools.callbacks.SpecWriterCallback()
except AttributeError:
    # apstools <1.6.21
    _specwriter = apstools.callbacks.SpecWriterCallback()

specwriter = _specwriter
"""The SPEC file writer object."""

# make the SPEC file in current working directory (assumes is writable)
_path = pathlib.Path().cwd()
specwriter.newfile(_path / specwriter.spec_filename)

if "SPEC_DATA_FILES" in iconfig:
    RE.subscribe(specwriter.receiver)  # write data to SPEC files

try:
    # feature new in apstools 1.6.14
    from apstools.plans import label_stream_wrapper

    def motor_start_preprocessor(plan):
        return label_stream_wrapper(plan, "motor", when="start")

    RE.preprocessors.append(motor_start_preprocessor)
except Exception:
    logger.warning("Could load support to log motors positions.")
