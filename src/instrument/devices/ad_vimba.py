"""
Vimba cameras
"""

__all__ = ["flag_camera_4idb"]

from ophyd.areadetector import CamBase, DetectorBase, ADComponent


class VimbaCam(CamBase):
    file_number_sync = None
    file_number_write = None
    fw_clear = None
    link_0 = None
    link_1 = None
    link_2 = None
    link_3 = None
    dcu_buff_free = None
    offset = None


class VimbaDetector(DetectorBase):
    cam = ADComponent(VimbaCam, "cam1:")


flag_camera_4idb = VimbaDetector(
    "4idbPostToroBeam:", name="flag_camera_4idb", labels=("camera",)
)
