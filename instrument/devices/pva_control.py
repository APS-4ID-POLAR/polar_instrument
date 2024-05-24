
__all__ = ["positioner_stream"]

from pvapy import Channel
from ophyd.status import Status
from ophyd import Device


class PositionerStream(Device):
	file_pva = Channel("4idSoftGluePVA:outputFile")
	status_pva = Channel("4idSoftGluePVA:status")
	start_pva = Channel("4idSoftGluePVA:start")
	stop_pva = Channel("4idSoftGluePVA:stop")
	
	_status_obj = None
	_done_signal = None
	
	@property
	def file_path(self):
		return self.file_pva.get().toDict()["filePath"]
		
	@file_path.setter
	def file_path(self, value):
		if not isinstance(value, str):
			raise ValueError(f"file_path needs to be a string, but {type(value)} was entered.")
		self.file_pva.putString(value, "filePath")
	
	@property
	def file_name(self):
		return self.file_pva.get().toDict()["fileName"]

	@file_name.setter
	def file_name(self, value):
		if not isinstance(value, str):
			raise ValueError(f"file_name needs to be a string, but {type(value)} was entered.")
		self.file_pva.putString(value, "fileName")

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

positioner_stream = PositionerStream("", name="positioner_stream")

