from ..devices.vortex_dante_me4 import VortexDante4
from ..devices.vortex_xmap import VortexXMAP
from ..devices.vortex_xspress3_me4 import VortexXspress34
from ..devices.vortex_xspress3_me7 import VortexXspress37
from .run_engine import sd
from apsbits.core.instrument_init import oregistry
from logging import getLogger

logger = getLogger(__name__)

# TODO: Get this from a YAML file?
DETECTORS = {
    "dante4": (VortexDante4, "dp_dante8_xrd4:"),
    "xmap": (VortexXMAP, "dpxXMAPDP2:"),
    "xspress4": (VortexXspress34, "S4QX4:"),
    "xspress7": (VortexXspress37, "XSP3_7Chan:"),
}


def load_vortex(
    electronic: str,
    pv: str = None,
    name: str = "vortex",
    labels: list = [
        "detector",
    ],
    baseline: bool = False,
    **kwargs,
):
    """
    Load Vortex detector. kwargs are passed to the detector class.

    PARAMETERS
    ----------
        electronic : string
            Name of the electronic. Currently must be one of: dante, xmap,
            xspress4, xspress7
        pv : string, optional
            PV prefix of detector. If None it will use the default.
        name : str, optional
            Bluesky name of the detector. Defaults to 'vortex'.
        labels : list of strings, optional
            Bluesky labels. Defaults to ["detector",]
        baseline : bool, optional
            Flag to add the device to the baseline. Defaults to False.
    RETURNS
    -------
        vortex_detector : Ophyd device
    """

    if electronic not in DETECTORS.keys():
        raise ValueError(
            f"Available electronics are {DETECTORS.keys()}, "
            f"but {electronic} was entered."
        )

    vortexclass, _pv = DETECTORS[electronic]
    pv = _pv if pv is None else pv

    device = vortexclass(pv, name=name, labels=labels, **kwargs)

    try:
        logger.info(f"Connecting to {device.name}...")
        device.wait_for_connection()
        if baseline:
            sd.baseline.append(device)
        if hasattr(device, "default_settings"):
            device.default_settings()
        oregistry.register(device)
    except TimeoutError:
        message = f"Device {device.name} is disconnected."
        if baseline:
            message += " This device was not added to the baseline."
        logger.warning(message)

    return device
