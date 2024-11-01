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
from numpy import array
from datetime import datetime
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

        for name, path in self.external_files.items():
            link_path = (
                "/stream"
                if name == "positioner_stream" else
                "/entry/instrument"
            )
            h5addr = f"/entry/externals/{name}"
            self.root[h5addr] = h5py.ExternalLink(
                str(path),
                link_path,  # link to the image dataset
            )

        # TODO: Do they need to be reset!?
        self.external_files = {}

    # This is a tweak of the parent class because we do not want to write the
    # external files
    def write_streams(self, parent):
        """
        group: /entry/instrument/bluesky/streams:NXnote

        data from all the bluesky streams
        """
        bluesky = self.create_NX_group(parent, "streams:NXnote")
        for stream_name, uids in self.streams.items():
            if len(uids) != 1:
                # fmt: off
                raise ValueError(
                    f"stream {len(uids)} has descriptors, expecting only 1"
                )
                # fmt: on
            group = self.create_NX_group(bluesky, stream_name + ":NXnote")
            uid0 = uids[0]  # just get the one descriptor uid
            group.attrs["uid"] = uid0
            # just get the one descriptor
            acquisition = self.acquisitions[uid0]
            for k, v in acquisition["data"].items():
                d = v["data"]
                # NXlog is for time series data but NXdata makes an automatic "
                # plot
                subgroup = self.create_NX_group(group, k + ":NXdata")

                if v["external"]:
                    # We will link external images directly.
                    # self.write_stream_external(
                    #     parent, d, subgroup, stream_name, k, v
                    # )
                    pass
                else:
                    self.write_stream_internal(
                        parent, d, subgroup, stream_name, k, v
                    )

                t = array(v["time"])
                ds = subgroup.create_dataset("EPOCH", data=t)
                ds.attrs["units"] = "s"
                ds.attrs["long_name"] = "epoch time (s)"
                ds.attrs["target"] = ds.name

                t_start = t[0]
                iso = datetime.fromtimestamp(t_start).isoformat()
                ds = subgroup.create_dataset("time", data=t - t_start)
                ds.attrs["units"] = "s"
                ds.attrs["long_name"] = "time since first data (s)"
                ds.attrs["target"] = ds.name
                ds.attrs["start_time"] = t_start
                ds.attrs["start_time_iso"] = iso

            # link images to parent names
            for k in group:
                if k.endswith("_image") and k[:-6] not in group:
                    group[k[:-6]] = group[k]

        return bluesky


nxwriter = MyNXWriter()  # create the callback instance
_nx_config = iconfig.get("NEXUS_DATA_FILE", None)
if _nx_config is not None:
    nxwriter.warn_on_missing_content = _nx_config.get(
        "NEXUS_WARN_MISSING_CONTENT", False
    )
