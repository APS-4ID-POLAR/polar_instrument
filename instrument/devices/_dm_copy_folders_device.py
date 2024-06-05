from apstools.utils import run_in_thread
from shutil import copytree
from ophyd.status import Status
from ophyd import Signal
from ..session_logs import logger
logger.info(__file__)

__all__ = """
    copy_files
""".split()

class CopyFileSignal(Signal):
    # def __init__(
    #         self,
    #         *args,
    #         origin_folder="/home/beams/POLAR/ptychodusDemo/sample1",
    #         **kwargs
    #     ):
    #     super().__init__(*args, **kwargs)
    #     self._origin_folder=origin_folder
    #     self._st = None

    # def set(self, value, **kwargs):
    #     super().set(value, **kwargs)

    #     _st = Status()
    #     @run_in_thread
    #     def _inner_copy():
    #         copytree(self._origin_folder, f"{value}")
    #         _st.set_finished()
    	
    #     _inner_copy()
    #     return _st

    def start_copy(self, origin, destination):
        self._st = Status()
        @run_in_thread
        def _inner_copy():
            copytree(origin, destination)
            self._st.set_finished()
    	
        _inner_copy()
        return self._st

    def set(self, *args, **kwargs):
        return self._st


copy_files = CopyFileSignal(name="copy_files")
