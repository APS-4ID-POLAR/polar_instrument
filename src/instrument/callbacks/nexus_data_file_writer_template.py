"""
Write scan(s) to a NeXus/HDF5 file.
"""

__all__ = ["nxwriter"]

import logging

logger = logging.getLogger(__name__)
logger.info(__file__)

from ..utils.config import iconfig  # noqa
from ..utils.functions import host_on_aps_subnet  # noqa
from ..utils.run_engine import RE  # noqa

if host_on_aps_subnet():
    from apstools.callbacks import NXWriterAPS as NXWriter
else:
    from apstools.callbacks import NXWriter


class MyNXWriter(NXWriter):
    def get_sample_title(self):
        """
        Get the title from the metadata or modify the default.

        default title: S{scan_id}-{plan_name}-{short_uid}
        """
        try:
            title = self.metadata["title"]
        except KeyError:
            # title = super().get_sample_title()  # the default title
            title = f"S{self.scan_id:05d}-{self.plan_name}-{self.uid[:7]}"
        return title


nxwriter = MyNXWriter()  # create the callback instance
"""The NeXus file writer object."""

if "NEXUS_DATA_FILES" in iconfig:
    RE.subscribe(nxwriter.receiver)  # write data to NeXus files

nxwriter.file_extension = iconfig.get("FILE_EXTENSION", "hdf")
warn_missing = iconfig.get("WARN_MISSING", False)
nxwriter.warn_on_missing_content = warn_missing
