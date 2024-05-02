from ..framework import cat
from ..mpl import plt
from ..session_logs import logger
from pathlib import Path
from numpy import array, s_, single, mean, nan
from xml.dom.minidom import parseString
from imageio import imopen
from scipy.interpolate import interp1d

logger.info(__file__)

__all__ = ['plot_raman']


def _read_exposure_time(dom):
    """
    Reads exposure time and returns it in seconds.
    """
    return (
        single(dom.getElementsByTagName('ExposureTime')[0].childNodes[0].toxml())/1000.
    )


def _read_calibration(dom):
    """
    Reads the x calibration of the image from the xml footer and saves 
    it in the x_calibration field

    Function adapted from T-Rax:
    https://github.com/CPrescher/T-rax/blob/develop/t_rax/model/SpeFile.py
    """

    spe_format = dom.childNodes[0]
    calibrations = spe_format.getElementsByTagName('Calibrations')[0]
    wavelengthmapping = calibrations.getElementsByTagName('WavelengthMapping')[0]
    wavelengths = wavelengthmapping.getElementsByTagName('Wavelength')[0]
    wavelength_values = wavelengths.childNodes[0]

    return array([float(i) for i in wavelength_values.toxml().split(',')])


def plot_raman(scans=-1, roi=None, label=None, ax=None, time_norm=False):
    """
    Plot the Raman spectrum.

    This assumes that the energy calibration did not change 

    Parameters
    ----------
    scans : int, uid or iterable of ints, uid, optional
        Scan number or uid. If a list of scans is passed, it will average them.
        Defaults to the last scan.
    roi: list of int
        Index of boundaries of roi to be applied to images. First two numbers are the
        low/high range of the first axis, and last two of the second axis, i.e. it will
        be converted to numpy.s_[roi[0]:roi[1], roi[2]:roi[3]].
    label : str, optional
        Label for this data. If None, it defaults to `scans`. This is useful
        when comparing multiple samples.
    ax : matplotlib axes, optional
        Axes instance to use in the plot. If None, it will produce one.

    Returns
    -------
    fig, ax : matplotlib figure and axes instances
        Useful to reuse or modify this figure.
    """

    try:
        scans = list(scans)
    except TypeError:
        scans = [scans]

    if roi is None:
        index = s_[:, :]
    else:
        index = s_[roi[0]:roi[1], roi[2]:roi[3]]

    xs = []
    ys = []
    for scan in scans:
        for _res in cat[scan].primary._resources:
            if _res["spec"] == "AD_SPE_APSPolar":
                resources = _res
                break

        path = Path(resources["root"]) / Path(resources["resource_path"])
        fnames = cat[-1].primary.read()["spectrometer_cam_file_name"].values

        xi = []
        yi = []
        for fname in fnames:
            imgfile = imopen(path / fname, "r")
            dom = parseString(imgfile.metadata()["__xml"])
            calibration = _read_calibration(dom)
            norm = _read_exposure_time(dom) if time_norm else 1.
            xi.append(calibration[index[0]])
            yi.append(imgfile.read().mean(axis=0)[index].mean(axis=0)/norm)

        # Assumes that the energy calibration is the same within a single Bluesky scan.
        xs.append(mean(xi, axis=0))
        ys.append(mean(yi, axis=0))

    if len(scans) == 1:
        x = xs[0]
        y = ys[0]
    else:
        x = xs[0]
        y = [ys[0]]
        for i in range(1, len(scans)):
            y.append(
                interp1d(xs[i], ys[i], "linear", bounds_error=False, fill_value=nan)(x)
            )
        y = mean(y, axis=0)
        
    if ax is None:
        fig, ax = plt.subplots()
    else:
        plt.sca(ax)
        fig = ax.figure

    if label is None:
        label = f'{scans}'

    plt.plot(x, y, label=label)
    plt.ylabel('Intensity')
    plt.xlabel('Wavelength (nm)')
    plt.tight_layout()

    return fig, ax
