"""
For development and testing only, provides plans.
=================================================

.. autosummary::
    ~sim_count_plan
    ~sim_print_plan
    ~sim_rel_scan_plan
"""

__all__ = """
    sim_count_plan
    sim_print_plan
    sim_rel_scan_plan
""".split()

import logging

from bluesky import plan_stubs as bps
from bluesky import plans as bp
from ophyd.sim import motor
from ophyd.sim import noisy_det

logger = logging.getLogger(__name__)
logger.info(__file__)

DEFAULT_MD = {"title": "test run with simulator(s)"}


def sim_count_plan(num: int = 1, imax: float = 10_000, md: dict = DEFAULT_MD):
    """Demonstrate the count() plan."""
    logger.info("(%s) %s()", __name__, "sim_count_plan")
    yield from bps.mv(noisy_det.Imax, imax)
    yield from bp.count([noisy_det], num=num, md=md)


def sim_print_plan():
    """Demonstrate a print() plan stub (no data streams)."""
    logger.info("(%s) %s()", __name__, "sim_print_plan")
    yield from bps.null()
    print(f"({__name__}) This is a test.")
    print(f"({__name__})  {motor.position=}  {noisy_det.read()=}.")


def sim_rel_scan_plan(
    span: float = 5,
    num: int = 11,
    imax: float = 10_000,
    center: float = 0,
    sigma: float = 1,
    noise: str = "uniform",  # none poisson uniform
    md: dict = DEFAULT_MD,
):
    """Demonstrate the rel_scan() plan."""
    logger.info("(%s) %s()", __name__, "sim_rel_scan_plan")
    # fmt: off
    yield from bps.mv(
        noisy_det.Imax, imax,
        noisy_det.center, center,
        noisy_det.sigma, sigma,
        noisy_det.noise, noise,
    )
    # fmt: on
    print(f"({__name__})  {motor.position=}  {noisy_det.read()=}.")
    print(f"({__name__})  {noisy_det.read_configuration()=}.")
    print(f"({__name__})  {noisy_det.noise._enum_strs=}.")
    yield from bp.rel_scan([noisy_det], motor, -span / 2, span / 2, num=num, md=md)
