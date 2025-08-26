from ophyd import Component, Device, EpicsSignalRO, EpicsMotor

# TODO: Will add some as read only for now, but
# may be able to run as motors


class Vertical(Device):
    piezo_ds = Component(EpicsMotor, "m4", labels=("motor",))
    pico_ds = Component(EpicsMotor, "m11")

    piezo_us = Component(EpicsMotor, "m5", labels=("motor",))
    pico_us = Component(EpicsMotor, "m7", labels=("motor",))

    capsensor_ds = Component(EpicsSignalRO, "m16.RBV")
    capsensor_us = Component(EpicsSignalRO, "m15.RBV")

    y = Component(EpicsSignalRO, "vert:t2.D")
    thx = Component(EpicsSignalRO, "vert:t2.C")

    stripe = Component(EpicsMotor, "m20", labels=("motor",))


class Horizontal(Device):
    # Pitch angle
    thy_piezo = Component(EpicsMotor, "m4", labels=("motor",))
    thy_pico = Component(EpicsMotor, "m11", labels=("motor",))
    thy = Component(EpicsSignalRO, "SM1.RBV")

    # Roll
    thz_pico = Component(EpicsMotor, "m10", labels=("motor",))
    thy = Component(EpicsSignalRO, "SM2.RBV")

    # Normal
    x_piezo = Component(EpicsMotor, "m3", labels=("motor",))
    x_pico = Component(EpicsMotor, "m12", labels=("motor",))
    x = Component(EpicsSignalRO, "m18.RBV")

    # Along beam
    z_piezo = Component(EpicsMotor, "m2", labels=("motor",))
    z_pico = Component(EpicsMotor, "m8", labels=("motor",))
    z = Component(EpicsSignalRO, "m17.RBV")

    # Stripe
    stripe = Component(EpicsMotor, "m22", labels=("motor",))


class KBDevice(Device):
    vert = Component(Vertical, "")
    hor = Component(Horizontal, "")
