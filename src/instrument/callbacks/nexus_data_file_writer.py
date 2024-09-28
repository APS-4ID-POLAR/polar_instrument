"""
Write each run to a NeXus/HDF5 file.

Based on implementation from Sector 8
https://github.com/aps-8id-dys/bluesky/blob/d2481c7a865ecd2e6306378e405c2814c26a79d8/instrument/callbacks/nexus_data_file_writer.py

IMPORTANT
See the note about waiting for the nxwriter to finish AFTER EACH ACQUISITION!
https://bcda-aps.github.io/apstools/dev/api/_filewriters.html#apstools.callbacks.nexus_writer.NXWriter
"""

__all__ = ["nxwriter"]

import h5py
from apstools.callbacks import NXWriterAPS
from ..utils import iconfig, logger

# from ..framework.initialize import RE
logger.info(__file__)

LAYOUT_VERSION = "APS-POLAR-2024-06"
NEXUS_RELEASE = "v2022.07"  # NeXus release to which this file is written


class MyNXWriter(NXWriterAPS):
    """
    Modify the default behavior of NXWriter for XPCS.
    """

    ad_file_names = {}
    position_file_name = None

    def write_root(self, filename):
        super().write_root(filename)
        self.root.attrs["NeXus_version"] = NEXUS_RELEASE
        self.root.attrs["layout_version"] = LAYOUT_VERSION

    def write_entry(self):
        nxentry = super().write_entry()
        ds = nxentry.create_dataset("layout_version", data=LAYOUT_VERSION)
        ds.attrs["target"] = ds.name
        nxentry["instrument/layout_version"] = ds

    def write_entry(self):
        """Called after stop document has been received."""
        # nxentry = super().write_entry()
        # print(f"{nxentry=!r}")
        super().write_entry()

        for name, path in self.ad_file_names.items():
            h5addr = f"/entry/detectors/{name}"
            self.root[h5addr] = h5py.ExternalLink(
                str(path),
                "/entry/instrument",  # link to the image dataset
            )
      
        if self.position_file_name is not None:
            h5addr = "/entry/instrument/softglue"  # TODO: final location to be decided
            self.root[h5addr] = h5py.ExternalLink(
                str(self.position_file_name),
                "/stream",  # link to the root of the file
            )
        
        # TODO: Do they need to be reset!?
        self.ad_file_names = {}
        self.position_file_name = None


nxwriter = MyNXWriter()  # create the callback instance
nxwriter.warn_on_missing_content = iconfig.get("NEXUS_WARN_MISSING_CONTENT", False)
