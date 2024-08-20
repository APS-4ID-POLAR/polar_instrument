from apstools.utils import run_in_thread
from shutil import copytree
from ophyd.status import Status
from ophyd import Signal
from datetime import datetime
from ...session_logs import logger
logger.info(__file__)

__all__ = """
    file_copy_device
""".split()

class CopyFileSignal(Signal):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._st = Status()
        self._st.set_finished()
        self._start_time = None
        self._end_time = None

    def start_copy(self, origin, destination):
        self._st = Status()
        @run_in_thread
        def _inner_copy():
            self._start_time = datetime.now()
            copytree(origin, destination)
            self._end_time = datetime.now()
            self._st.set_finished()
    	
        _inner_copy()
        return self._st

    def set(self, *args, **kwargs):
        return self._st


file_copy_device = CopyFileSignal(name="copy_files")
