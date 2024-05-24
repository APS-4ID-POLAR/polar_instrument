
__all__ = ["positioner_stream"]

from pvapy import Channel


class PositionerStream():
	file_pva = Channel("4idSoftGluePVA:outputFile")
	status_pva = Channel("4idSoftGluePVA:status")
	start_pva = Channel("4idSoftGluePVA:start")
	stop_pva = Channel("4idSoftGluePVA:stop")
	
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

	@property
	def start(self):
		self.start_pva.putInt(1)

	@property
	def stop(self):
		self.stop_pva.putInt(1)

positioner_stream = PositionerStream()

