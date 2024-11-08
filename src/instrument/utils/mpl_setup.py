"""
MatPlotLib setup.
=================

.. autosummary::

    ~is_notebook
"""

__all__ = ["is_notebook", "plt"]

import logging

from .functions import running_in_queueserver

logger = logging.getLogger(__name__)
logger.info(__file__)


def is_notebook():
    """
    Detect if running in a notebook.

    see: https://stackoverflow.com/a/39662359/1046449
    """
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)

    except NameError:
        return False  # Probably standard Python interpreter


if not running_in_queueserver():
    import matplotlib.pyplot as plt

    if not is_notebook():
        plt.ion()
else:
    plt = None
