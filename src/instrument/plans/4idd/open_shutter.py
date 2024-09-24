"""
Plan to open shutters
"""

from ..devices import ashutter, bshutter, dshutter, status4id
from .local_preprocessors import _difference_check, SetSignal
from .local_scans import mv
from bluesky.plan_stubs import abs_set, rd
from toolz import partition

__all__ = [
    'shopen',
    'shclose'
]
# 30 sec timeout.
signal = SetSignal(name='tmp', timeout=30)


def shopen(hutch="d"):

    for component in status4id.component_names:
        value = yield from rd(getattr(status4id, component))
        if value == "OFF":
            raise ValueError(
                f"Cannot open shutter, {component.upper()} is not enabled!"
            )

    if hutch.lower() == "a":
        args = (ashutter, "open")
    elif hutch.lower() == "b":
        args = (ashutter, "open", bshutter, "open")
    elif hutch.lower() == "d":
        args = (ashutter, "open", bshutter, "open", dshutter, "open")
    else:
        raise ValueError("Input must be 'a', 'b', or 'd'.")

    for shutter, _ in partition(2, args):
        # Checking if all permits are good.
        for permit in ["user_enable", "aps_enable", "bleps"]:

            good = (
                0 if (shutter == ashutter) and (permit == "bleps") else 1
            )
            status = yield from rd(getattr(shutter, permit))

            if status != good:
                raise ValueError(
                    f"{getattr(shutter, permit).name} is not enabled!"
                )

        # Wait for search to end. Timeout is defined above.
        function = _difference_check(1, tolerance=0.1)
        yield from abs_set(
            signal, getattr(shutter, "searched"), function, wait=True,
        )

    yield from mv(*args)


def shclose(hutch="d"):
    if hutch.lower() == "a":
        args = (ashutter, "close")
    elif hutch.lower() == "b":
        args = (bshutter, "close")
    elif hutch.lower() == "d":
        args = (dshutter, "close")
    elif hutch.lower() == "all":
        args = (ashutter, "close", bshutter, "close", dshutter, "close")
    else:
        raise ValueError("Input must be 'a', 'b', 'd', or 'all'.")

    yield from mv(*args)
