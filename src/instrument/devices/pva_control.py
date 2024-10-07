
"""
Device to control the PositionerStream
"""

__all__ = ["positioner_stream"]

from pvapy import Channel
from ophyd import Device, Signal, Component
from ophyd.status import Status
from pathlib import Path
from .data_management import dm_experiment
from ..utils.dm_utils import dm_get_experiment_data_path
from ..utils.run_engine import sd, RE
from ..utils.config import iconfig
from ..utils import logger
logger.info(__file__)

HDF1_NAME_TEMPLATE = iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"]
HDF1_FILE_EXTENSION = iconfig["AREA_DETECTOR"]["HDF5_FILE_EXTENSION"]
HDF1_NAME = Path(HDF1_NAME_TEMPLATE + "." + HDF1_FILE_EXTENSION)


class PVASignal(Signal):
	def __init__(self, *args, pva_channel="", pva_label="", **kwargs):
		super().__init__(*args, **kwargs)
		self._pva = Channel(pva_channel)
		self._pva_label = pva_label

	def get(self, **kwargs):
		return self._pva.get().toDict()[self._pva_label]
	
	def put(self, value, **kwargs):
		if not isinstance(value, str):
			raise ValueError(
				f"file_path needs to be a string, but {type(value)} was entered."
			)
		self._pva.putString(value, self._pva_label)

	def set(self, value, **kwargs):
		self.set(value, **kwargs)
		# Do not check completion.
		st = Status()
		st.set_finished()
		return st


class PositionerStream(Device):
	file_pva = Channel("4idSoftGluePVA:outputFile")
	status_pva = Channel("4idSoftGluePVA:status")
	start_pva = Channel("4idSoftGluePVA:start")
	stop_pva = Channel("4idSoftGluePVA:stop")

	# These will be signals that Bluesky can read and save in the catalog.
	file_path = Component(
		PVASignal,
		pva_channel="4idSoftGluePVA:outputFile",
		pva_label="filePath",
		kind="normal"
	)

	file_name = Component(
		PVASignal,
		pva_channel="4idSoftGluePVA:outputFile",
		pva_label="fileName",
		kind="normal"
	)

	_status_obj = None
	_done_signal = None

	@property
	def status(self):
		return self.status_pva.get().toDict()["value"]

	def start_signal(self):
		self.start_pva.putInt(1)

	def stop_signal(self):
		self.stop_pva.putInt(1)
		
	def start_stream(self):
		def _status_sub(inp):
			if inp["value"] == "Acquiring":
				self._status_obj.set_finished()
				self.status_pva.stopMonitor()

		self._done_signal = False
		self.start_pva.stopMonitor()
		self._status_obj = Status()

		self.start_signal()

		self.status_pva.monitor(_status_sub, "field(value, alarm, timeStamp)")
		
		return self._status_obj

	def stop_stream(self):
		def _status_sub(inp):
			if inp["value"] == "Idle":
				self._status_obj.set_finished()
				self.status_pva.stopMonitor()

		self._done_signal = False
		self.start_pva.stopMonitor()
		self._status_obj = Status()

		self.stop_signal()

		self.status_pva.monitor(_status_sub, "field(value, alarm, timeStamp)")
		
		return self._status_obj

	def set(self, value, **kwargs):
		if value not in [1, 0]:
			raise ValueError ("Value must be 1 or 0.")
		
		return self.start_stream() if value == 1 else self.stop_stream()
	
	def stop(self, **kwargs):
		super().stop(**kwargs)
		self.stop_signal()

	def setup_file_path_name(self, name_base, file_number):
		path = Path(dm_get_experiment_data_path(dm_experiment.get()))
		# Add the sample name from metadata to the folder.
		path /= RE.md["sample"]
		# Add the name of the device
		path /= self.name

		full_path = str(HDF1_NAME) % (
			str(path), name_base, file_number
		)

		return path, full_path


	def setup_images(
            self, name_base, file_number, flyscan=False
        ):

		folder, full_path = self.setup_file_path_name(name_base, file_number)

		# Setup positioner stream
		if not folder.is_dir():
			folder.mkdir()

		_ps_fname = full_path.relative_to(folder)

		# Setup path and file name in positioner_stream
		self.file_path.put(str(folder))
		self.file_name.put(str(_ps_fname))

		return full_path


positioner_stream = PositionerStream("", name="positioner_stream")
sd.baseline.append(positioner_stream)
