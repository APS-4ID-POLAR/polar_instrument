""" Loads a new vortex device """

from ..devices.xspress import Xspress3Vortex1Ch, Xspress3Vortex4Ch
from ..devices.vortex_dxp import MySaturn
from ..session_logs import logger
logger.info(__file__)

__all__ = ['load_vortex']


def load_vortex(electronic, num_channels, num_rois=2):
    """
    Load the vortex detector.

    Parameters
    ----------
    electronic : str
        Type of electronics being used. Only accepts 'xspress3'
    num_channels : int
        Number of channels. Only accepts 1 or 4.
    num_rois : int
        Number of ROIs to be enabled during startup.

    Returns
    -------
    vortex : ophyd device
        Vortex device.
    """

    if electronic == 'xspress3':
        if num_channels == 1:
            vortex = Xspress3Vortex1Ch('XSP3_1Chan:', name='vortex')
        elif num_channels == 4:
            vortex = Xspress3Vortex4Ch('S4QX4:', name='vortex')
        else:
            raise ValueError('num_channels for xspress3 must be 1 or 4.')
        # Disable all but ROI 1 and 2
        vortex.enable_roi([i+1 for i in range(num_rois+1)])
        total_rois = vortex.Ch1.rois.num_rois.get()
        vortex.disable_roi([i for i in range(num_rois+1, total_rois+1)])
    elif electronic == 'dxp':
        if num_channels == 1:
            vortex = MySaturn("4idd:", name='vortex')
            vortex.default_kinds()
            vortex.default_settings()
        else:
            raise ValueError('num_channels for dxp must be 1.')
    else:
        raise ValueError('electronic must be "xspress3" or "dxp"')

    return vortex
