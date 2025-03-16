"""
Huber filters
"""

from ophyd import Component, FormattedComponent, Device, EpicsSignal
from ..utils._logging_setup import logger
logger.info(__file__)


class SlotDevice(Device):
    label = FormattedComponent(
        EpicsSignal,
        "text{i}_in",
        write_pv="text{i}_out", 
        string=True,
        kind="config"
    )
    thickness = FormattedComponent(
        EpicsSignal,
        "thickness{i}_in",
        write_pv="thickness{i}_out",
        string=True,
        kind="config"
    )
    status = FormattedComponent(
        EpicsSignal, "a{i}_in", write_pv="a{i}_out"
    )

    def __init__(self, *args, slot=1, **kwargs):
        self.i = slot
        super().__init__(*args, **kwargs)


class HuberFilter(Device):
    slot1 = Component(SlotDevice, "", i=1)
    slot2 = Component(SlotDevice, "", i=2)
    slot3 = Component(SlotDevice, "", i=3)
    slot4 = Component(SlotDevice, "", i=4)
    slot5 = Component(SlotDevice, "", i=5)
    slot6 = Component(SlotDevice, "", i=6)
