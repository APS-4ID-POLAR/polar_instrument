
"""
Configure matplotlib in interactive mode for IPython console
"""

__all__ = ['plt']

import matplotlib.pyplot as plt
from ..session_logs import logger
logger.info(__file__)

plt.ion()
