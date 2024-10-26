"""
Vimba cameras
"""

__all__ = ["flag_camera_4idb"]

from ophyd.areadetector import CamBase, DetectorBase, ADComponent


class VimbaCam(CamBase):
    pass


class VimbaDetector(DetectorBase):
    cam = ADComponent(VimbaCam, "cam1")


flag_camera_4idb = VimbaDetector(
    "4idbPostToroBeam:", name="flag_camera_4idb", labels=("camera",)
)
