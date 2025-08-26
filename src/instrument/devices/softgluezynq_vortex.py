from ophyd import (
    Device,
    DynamicDeviceComponent,
    Component,
    DeviceStatus,
    Staged,
    Signal,
)
from bluesky.plan_stubs import mv, sleep
from .softgluezynq_parts import (
    _buffer_fields,
    _io_fields,
    SGZUpCounter,
    SGZDownCounter,
    SGZClocks,
    SGZDevideByN,
    SGZGateDly,
    SGZGates,
    SGZDFF,
    SGZHistScal,
    SGZhistScalerDma,
)


# class TimeSettingSignal(Signal):
#     def get()


class SGZVortex(Device):

    # TODO: This is a dummy that will do nothing for now,
    # but can be used to setup the time at some point.
    preset_monitor = Component(Signal, value=0, kind="omitted")

    # Buffer 1 --> enable
    # Buffer 2 --> reset
    buffers = DynamicDeviceComponent(_buffer_fields(num=2))

    # I/O fields
    io = DynamicDeviceComponent(_io_fields(num=3))

    # If counts goes +1 then it's done.
    up_counter_status = Component(SGZUpCounter, "SG:UpCntr-2_", kind="config")

    # Pulses control
    down_counter_pulse = Component(
        SGZDownCounter, "SG:DnCntr-1_", kind="config"
    )

    # Setup the frequency of the count and trigger based on 10 MHz clock.
    div_by_n = Component(SGZDevideByN, "SG:DivByN-2_", kind="config")

    # Digitize the sync
    gate_sync = Component(SGZGateDly, "SG:GateDly-1_", kind="config")

    # Create a gate pulse
    gate_trigger = Component(SGZGateDly, "SG:GateDly-2_", kind="config")

    # Gates
    and_1 = Component(SGZGates, "SG:AND-1_", kind="config")
    and_3 = Component(SGZGates, "SG:AND-3_", kind="config")
    or_1 = Component(SGZGates, "SG:OR-1_", kind="config")

    # DFFs
    dff_2 = Component(SGZDFF, "SG:DFF-2_", kind="config")
    dff_3 = Component(SGZDFF, "SG:DFF-3_", kind="config")

    # Histogram
    histscal = Component(SGZHistScal, "SG:HistScal-1_", kind="config")
    histdma = Component(SGZhistScalerDma, "1histScalerDma")

    # Clocks
    clocks = Component(SGZClocks, "SG:", kind="config")

    # Dummy for now
    preset_monitor = Component(Signal, value=0, kind="omitted")

    def __init__(
        self, *args, reset_sleep_time=0.1, reference_clock=1e7, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._reset_sleep_time = reset_sleep_time
        self._reference_clock = reference_clock
        self._status = None
        self._frequency = 13

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        if isinstance(value, (int, float)):
            self._frequency = value
        else:
            raise ValueError("Frequency must be a number.")

    def start_softglue(self):
        yield from mv(self.buffers.in1.signal, "1")

    def stop_softglue(self):
        yield from mv(self.buffers.in1.signal, "0")

    def reset(self):
        yield from mv(
            self.buffers.in2.signal, "1!", self.histscal.clear.signal, "1!"
        )
        yield from sleep(self._reset_sleep_time)

    # TODO: Add a function that setups the times?
    # @property
    # def preset_monitor(self):
    #     return self.connected

    def stage(self):
        # Make sure the sgz is not running and clear it.
        self.buffers.in1.signal.set("0").wait()
        self.buffers.in2.signal.set("1!").wait()
        self.histscal.clear.signal.set("1!").wait()
        self.up_counter_status.counts.subscribe(self._acquire_changed)
        super().stage()

    def unstage(self):
        # Make sure the sgz is not running and clear it.
        self.buffers.in1.signal.set("0").wait()
        self.buffers.in2.signal.set("1!").wait()
        self.histscal.clear.signal.set("1!").wait()
        self.up_counter_status.counts.clear_sub(self._acquire_changed)
        super().unstage()

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger. "
                "Call the stage() method before triggering."
            )
        self._status = DeviceStatus(self)
        self.buffers.in1.signal.put("1", use_complete=True)
        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        if self._status is not None:
            if value == old_value + 1:
                # Turn off the enable
                # Not sure .set is the best thing to do here.
                self.buffers.in1.signal.set("0").wait()

                self._status.set_finished()
                self._status = None

    def default_settings(self, timeout=10):
        pass

        # logger.info("Setting up clocks.")

        # self.clocks.clock_10MHz.signal.set("ck10").wait(timeout)

        # self.div_by_n_count.enable.signal.set("enable").wait(timeout)
        # self.div_by_n_count.clock.signal.set("ck10").wait(timeout)
        # self.div_by_n_count.reset.signal.set("1").wait(timeout)
        # self.div_by_n_count.reset.signal.set("0").wait(timeout)
        # self.div_by_n_count.out.signal.set("ckUser").wait(timeout)
        # self.div_by_n_count.n.set(10000).wait(timeout)

        # self.div_by_n_trigger.enable.signal.set("enableDet").wait(timeout)
        # self.div_by_n_trigger.clock.signal.set("ck10").wait(timeout)
        # self.div_by_n_trigger.reset.signal.set("1").wait(timeout)
        # self.div_by_n_trigger.reset.signal.set("0").wait(timeout)
        # self.div_by_n_trigger.out.signal.set("ckDet").wait(timeout)
        # self.div_by_n_trigger.n.set(1000000).wait(timeout)

        # self.div_by_n_interrupt.enable.signal.set("enable").wait(timeout)
        # self.div_by_n_interrupt.clock.signal.set("ck10").wait(timeout)
        # self.div_by_n_interrupt.reset.signal.set("1").wait(timeout)
        # self.div_by_n_interrupt.reset.signal.set("0").wait(timeout)
        # self.div_by_n_interrupt.out.signal.set("ckInt").wait(timeout)
        # self.div_by_n_interrupt.n.set(100000).wait(timeout)

        # logger.info("Setting up buffers.")

        # for i in range(1, 5):
        #     getattr(self.buffers, f"in{i}").signal.set("1!").wait(timeout)

        # self.buffers.out1.signal.set("enable").wait(timeout)
        # self.buffers.out2.signal.set("enableDet").wait(timeout)
        # self.buffers.out3.signal.set("resetCnters").wait(timeout)
        # self.buffers.out4.signal.set("reset").wait(timeout)

        # logger.info("Setting up counters.")

        # self.up_counter_count.enable.signal.set("enable").wait(timeout)
        # self.up_counter_count.clock.signal.set("ckUser").wait(timeout)
        # self.up_counter_count.reset.signal.set("resetCnters").wait(timeout)

        # self.up_counter_trigger.enable.signal.set("enable").wait(timeout)
        # self.up_counter_trigger.clock.signal.set("ckDet").wait(timeout)
        # self.up_counter_trigger.reset.signal.set("resetCnters").wait(timeout)

        # self.up_counter_gate_on.enable.signal.set("enable").wait(timeout)
        # self.up_counter_gate_on.clock.signal.set("gateTrigger").wait(timeout)
        # self.up_counter_gate_on.reset.signal.set("resetCnters").wait(timeout)

        # self.up_counter_gate_on.enable.signal.set("enable").wait(timeout)
        # self.up_counter_gate_on.clock.signal.set("gateTrigger*").wait(timeout)
        # self.up_counter_gate_on.reset.signal.set("resetCnters").wait(timeout)

        # logger.info("Setting up outputs.")

        # self.io.fo1.signal.set("gateTrigger").wait(timeout)
        # self.io.fo15.signal.set("ckInt").wait(timeout)
        # self.io.fo16.signal.set("reset").wait(timeout)

        # logger.info("Setting up DMA transfer.")

        # self.scaltostream.reset.signal.set("reset*").wait(timeout)
        # self.scaltostream.chadv.signal.set("ckUser").wait(timeout)
        # self.scaltostream.dmawords.set(16384).wait(timeout)
        # self.dma.scan.set(6).wait(timeout)

        # logger.info("Setting up trigger transfer.")

        # self.gate_trigger.input.signal.set("ckDet").wait(timeout)
        # self.gate_trigger.clock.signal.set("ck10").wait(timeout)
        # self.gate_trigger.out.signal.set("gateTrigger").wait(timeout)
        # self.gate_trigger.delay.set(0).wait(timeout)
        # self.gate_trigger.width.set(500000).wait(timeout)
