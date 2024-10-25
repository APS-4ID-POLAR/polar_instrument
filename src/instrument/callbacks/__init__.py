"""RunEngine callbacks, mostly."""

from ..utils.config import iconfig

if iconfig.get("NEXUS_DATA_FILES") is not None:
    from .nexus_data_file_writer import *  # noqa

if iconfig.get("SPEC_DATA_FILES") is not None:
    from .spec_data_file_writer import *  # noqa

# from dichro_plot import AutoDichroPlot
# from dichro_stream import dichro, plot_dichro_settings, dichro_bec

del iconfig
