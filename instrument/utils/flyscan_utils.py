"""
Utility functions for flyscans
"""

from h5py import File
from numpy import array
from ..session_logs import logger
logger.info(__file__)

__all__ = ['read_flyscan_stream']

def read_flyscan_stream(fname, base_key="stream"):
	output = {}
	with File(fname, "r") as f:
		for key in f[base_key].keys():
			output[key] = array(f[f"{base_key}/{key}"])
	return output
