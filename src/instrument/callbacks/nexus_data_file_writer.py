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

# LAYOUT_VERSION = "APS-POLAR-2024-06"
LAYOUT_VERSION = "APS-POLAR-2024-10"
NEXUS_RELEASE = "v2022.07"  # NeXus release to which this file is written


class MyNXWriter(NXWriterAPS):
    """
    Modify the default behavior of NXWriter for XPCS.
    """

    external_files = {}

    def write_root(self, filename):
        super().write_root(filename)
        self.root.attrs["NeXus_version"] = NEXUS_RELEASE
        self.root.attrs["layout_version"] = LAYOUT_VERSION

    def write_entry(self):
        """Called after stop document has been received."""
    
        nxentry = super().write_entry()
        ds = nxentry.create_dataset("layout_version", data=LAYOUT_VERSION)
        ds.attrs["target"] = ds.name
        nxentry["instrument/layout_version"] = ds
        # nxentry = super().write_entry()
        # print(f"{nxentry=!r}")

        for name, path in self.external_files.items():
            link_path = (
                "/stream" if name == "positioner_stream" else "/entry/instrument"
            )
            h5addr = f"/entry/externals/{name}"
            self.root[h5addr] = h5py.ExternalLink(
                str(path),
                link_path,  # link to the image dataset
            )
        
        # TODO: Do they need to be reset!?
        self.external_files = {}


nxwriter = MyNXWriter()  # create the callback instance
_nx_config = iconfig.get("NEXUS_DATA_FILE", None)
if _nx_config is not None:
    nxwriter.warn_on_missing_content = _nx_config.get(
        "NEXUS_WARN_MISSING_CONTENT", False
    )
