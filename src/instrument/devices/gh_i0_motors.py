from ophyd import Device, Component, EpicsMotor


class I04idg(Device):
    x = Component(EpicsMotor, "m52", labels=("motor",))
    y = Component(EpicsMotor, "m53", labels=("motor",))


class I04idh(Device):
    x = Component(EpicsMotor, "m20", labels=("motor",))
    y = Component(EpicsMotor, "m21", labels=("motor",))
