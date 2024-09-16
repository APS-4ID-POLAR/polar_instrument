# Copy of ophyd.mca - needed due to typos

from collections import OrderedDict

from ophyd.signal import (Signal, EpicsSignal, EpicsSignalRO)
from ophyd.device import Device, Component, DynamicDeviceComponent, Kind
from ophyd.areadetector import EpicsSignalWithRBV as SignalWithRBV


class ROI(Device):

    # 'name' is not an allowed attribute
    label = Component(EpicsSignal, 'NM', lazy=True)
    count = Component(EpicsSignalRO, '', lazy=True)
    net_count = Component(EpicsSignalRO, 'N', lazy=True)
    preset_count = Component(EpicsSignal, 'P', lazy=True)
    is_preset = Component(EpicsSignal, 'IP', lazy=True)
    bkgnd_chans = Component(EpicsSignal, 'BG', lazy=True)
    hi_chan = Component(EpicsSignal, 'HI', lazy=True)
    lo_chan = Component(EpicsSignal, 'LO', lazy=True)

    def __init__(self, prefix, *, read_attrs=None, configuration_attrs=None,
                 name=None, parent=None, **kwargs):

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs,
                         name=name, parent=parent, **kwargs)


def add_rois(range_, **kwargs):
    '''Add one or more ROIs to an MCA instance
       Parameters
       ----------
       range_ : sequence of ints
           Must be be in the set [0,31]
       By default, an EpicsMCA is initialized with all 32 rois.
       These provide the following Components as EpicsSignals (N=[0,31]):
       EpicsMCA.rois.roiN.(label,count,net_count,preset_cnt, is_preset,
       bkgnd_chans, hi_chan, lo_chan)
       '''
    defn = OrderedDict()

    for roi in range_:
        if not (0 <= roi < 32):
            raise ValueError('roi must be in the set [0,31]')

        attr = 'roi{}'.format(roi)
        defn[attr] = (ROI, '.R{}'.format(roi), kwargs)

    return defn


class EpicsMCARecord(Device):
    '''SynApps MCA Record interface'''
    stop_signal = Component(EpicsSignal, '.STOP', kind='omitted')
    preset_real_time = Component(
        EpicsSignal, '.PRTM', kind=Kind.config | Kind.normal
    )
    preset_live_time = Component(EpicsSignal, '.PLTM', kind='omitted')
    elapsed_real_time = Component(EpicsSignalRO, '.ERTM')
    elapsed_live_time = Component(EpicsSignalRO, '.ELTM', kind='omitted')

    spectrum = Component(EpicsSignalRO, '.VAL')
    background = Component(EpicsSignalRO, '.BG', kind='omitted')
    mode = Component(EpicsSignal, '.MODE', string=True, kind='omitted')

    rois = DynamicDeviceComponent(
        add_rois(range(0, 32), kind='omitted'), kind='omitted'
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # could arguably be made a configuration_attr instead...
        self.stage_sigs['mode'] = 'PHA'

    def stop(self, *, success=False):
        self.stop_signal.put(1)


class EpicsMCA(EpicsMCARecord):
    '''mca records with extras from mca.db'''
    start = Component(EpicsSignal, '.Start', kind='omitted')
    stop_signal = Component(EpicsSignal, '.Stop', kind='omitted')
    erase = Component(EpicsSignal, '.Erase', kind='omitted')
    erase_start = Component(
        EpicsSignal, '.EraseStart', trigger_value=1, kind='omitted'
    )

    check_acquiring = Component(EpicsSignal, '.CheckACQG', kind='omitted')
    client_wait = Component(EpicsSignal, '.ClientWait', kind='omitted')
    enable_wait = Component(EpicsSignal, '.EnableWait', kind='omitted')
    force_read = Component(EpicsSignal, '.Read', kind='omitted')
    set_client_wait = Component(EpicsSignal, 'SetClientWait', kind='omitted')
    status = Component(EpicsSignal, '.Status', kind='omitted')
    when_acq_stops = Component(EpicsSignal, 'WhenAcqStops', kind='omitted')
    why1 = Component(EpicsSignal, '.Why1', kind='omitted')
    why2 = Component(EpicsSignal, '.Why2', kind='omitted')
    why3 = Component(EpicsSignal, '.Why3', kind='omitted')
    why4 = Component(EpicsSignal, '.Why4', kind='omitted')


class EpicsMCAReadNotify(EpicsMCARecord):
    '''mca record with extras from mcaReadNotify.db'''
    start = Component(EpicsSignal, 'Start', kind='omitted')
    stop_signal = Component(EpicsSignal, 'Stop', kind='omitted')
    erase = Component(EpicsSignal, 'Erase', kind='omitted')
    erase_start = Component(
        EpicsSignal, 'EraseStart', trigger_value=1, kind='omitted'
    )

    check_acquiring = Component(EpicsSignal, 'CheckACQG', kind='omitted')
    client_wait = Component(EpicsSignal, 'ClientWait', kind='omitted')
    enable_wait = Component(EpicsSignal, 'EnableWait', kind='omitted')
    force_read = Component(EpicsSignal, 'Read', kind='omitted')
    set_client_wait = Component(EpicsSignal, 'SetClientWait', kind='omitted')
    status = Component(EpicsSignal, 'Status', kind='omitted')


class EpicsMCACallback(Device):
    '''Callback-related signals for MCA devices'''
    read_callback = Component(EpicsSignal, '.ReadCallback')
    read_data_once = Component(EpicsSignal, '.ReadDataOnce')
    read_status_once = Component(EpicsSignal, '.ReadStatusOnce')
    collect_data = Component(EpicsSignal, '.CollectData')


class EpicsDXP(Device):
    '''All high-level DXP parameters for each channel'''

    live_time_output = Component(SignalWithRBV, 'LiveTimeOutput', string=True)
    elapsed_live_time = Component(EpicsSignal, 'ElapsedLiveTime')
    elapsed_real_time = Component(EpicsSignal, 'ElapsedRealTime')
    elapsed_trigger_live_time = Component(
        EpicsSignal, 'ElapsedTriggerLiveTime'
    )

    # Trigger Filter PVs
    trigger_peaking_time = Component(SignalWithRBV, 'TriggerPeakingTime')
    trigger_threshold = Component(SignalWithRBV, 'TriggerThreshold')
    trigger_gap_time = Component(SignalWithRBV, 'TriggerGapTime')
    trigger_output = Component(SignalWithRBV, 'TriggerOutput', string=True)
    max_width = Component(SignalWithRBV, 'MaxWidth')

    # Energy Filter PVs
    peaking_time = Component(SignalWithRBV, 'PeakingTime')
    energy_threshold = Component(SignalWithRBV, 'EnergyThreshold')
    gap_time = Component(SignalWithRBV, 'GapTime')

    # Baseline PVs
    baseline_cut_percent = Component(SignalWithRBV, 'BaselineCutPercent')
    baseline_cut_enable = Component(SignalWithRBV, 'BaselineCutEnable')
    baseline_filter_length = Component(SignalWithRBV, 'BaselineFilterLength')
    baseline_threshold = Component(SignalWithRBV, 'BaselineThreshold')
    baseline_energy_array = Component(EpicsSignal, 'BaselineEnergyArray')
    baseline_histogram = Component(EpicsSignal, 'BaselineHistogram')

    # Misc PVs
    preamp_gain = Component(SignalWithRBV, 'PreampGain')
    detector_polarity = Component(SignalWithRBV, 'DetectorPolarity')
    reset_delay = Component(SignalWithRBV, 'ResetDelay')
    decay_time = Component(SignalWithRBV, 'DecayTime')
    max_energy = Component(SignalWithRBV, 'MaxEnergy')
    adc_percent_rule = Component(SignalWithRBV, 'ADCPercentRule')

    # read-only diagnostics
    triggers = Component(EpicsSignalRO, 'Triggers', lazy=True)
    events = Component(EpicsSignalRO, 'Events', lazy=True)
    overflows = Component(EpicsSignalRO, 'Overflows', lazy=True)
    underflows = Component(EpicsSignalRO, 'Underflows', lazy=True)
    input_count_rate = Component(EpicsSignalRO, 'InputCountRate', lazy=True)
    output_count_rate = Component(EpicsSignalRO, 'OutputCountRate', lazy=True)

    mca_bin_width = Component(EpicsSignalRO, 'MCABinWidth_RBV')
    calibration_energy = Component(EpicsSignalRO, 'CalibrationEnergy_RBV')
    current_pixel = Component(EpicsSignal, 'CurrentPixel')
    dynamic_range = Component(EpicsSignalRO, 'DynamicRange_RBV')

    # Preset options
    preset_events = Component(SignalWithRBV, 'PresetEvents')
    preset_mode = Component(SignalWithRBV, 'PresetMode', string=True)
    preset_triggers = Component(SignalWithRBV, 'PresetTriggers')

    # Trace options
    trace_data = Component(EpicsSignal, 'TraceData')
    trace_mode = Component(SignalWithRBV, 'TraceMode', string=True)
    trace_time_array = Component(EpicsSignal, 'TraceTimeArray')
    trace_time = Component(SignalWithRBV, 'TraceTime')


class EpicsDXPLowLevelParameter(Device):
    param_name = Component(EpicsSignal, 'Name')
    value = Component(SignalWithRBV, 'Val')


class EpicsDXPLowLevel(Device):
    num_low_level_params = Component(EpicsSignal, 'NumLLParams')
    read_low_level_params = Component(EpicsSignal, 'ReadLLParams')

    parameter_prefix = 'LL{}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parameter_cache = {}

    def get_low_level_parameter(self, index):
        '''Get a DXP low level parameter
        Parameters
        ----------
        index : int
            In the range of [0, 229]
        Returns
        -------
        param : EpicsDXPLowLevelParameter
        '''
        try:
            return self._parameter_cache[index]
        except KeyError:
            pass

        prefix = '{}{}'.format(self.prefix, self.parameter_prefix)
        name = '{}_param{}'.format(self.name, index)
        param = EpicsDXPLowLevelParameter(prefix, name=name)
        self._parameter_cache[index] = param
        return param


class EpicsDXPMapping(Device):
    apply = Component(EpicsSignal, 'Apply')
    auto_apply = Component(SignalWithRBV, 'AutoApply')
    auto_pixels_per_buffer = Component(SignalWithRBV, 'AutoPixelsPerBuffer')
    buffer_size = Component(EpicsSignalRO, 'BufferSize_RBV')
    collect_mode = Component(SignalWithRBV, 'CollectMode')
    ignore_gate = Component(SignalWithRBV, 'IgnoreGate')
    input_logic_polarity = Component(SignalWithRBV, 'InputLogicPolarity')
    list_mode = Component(SignalWithRBV, 'ListMode')
    mbytes_read = Component(EpicsSignalRO, 'MBytesRead_RBV')
    next_pixel = Component(EpicsSignal, 'NextPixel')
    pixel_advance_mode = Component(SignalWithRBV, 'PixelAdvanceMode')
    pixels_per_buffer = Component(SignalWithRBV, 'PixelsPerBuffer')
    pixels_per_run = Component(SignalWithRBV, 'PixelsPerRun')
    read_rate = Component(EpicsSignalRO, 'ReadRate_RBV')
    sync_count = Component(SignalWithRBV, 'SyncCount')


class EpicsDXPBaseSystem(Device):
    channel_advance = Component(EpicsSignal, 'ChannelAdvance')
    client_wait = Component(EpicsSignal, 'ClientWait')
    dwell = Component(EpicsSignal, 'Dwell')
    max_scas = Component(EpicsSignal, 'MaxSCAs')
    num_scas = Component(SignalWithRBV, 'NumSCAs')
    poll_time = Component(SignalWithRBV, 'PollTime')
    prescale = Component(EpicsSignal, 'Prescale')
    save_system = Component(SignalWithRBV, 'SaveSystem')
    save_system_file = Component(EpicsSignal, 'SaveSystemFile')
    set_client_wait = Component(EpicsSignal, 'SetClientWait')


class EpicsDXPMultiElementSystem(EpicsDXPBaseSystem):
    # Preset info
    preset_events = Component(EpicsSignal, 'PresetEvents')
    preset_live_time = Component(EpicsSignal, 'PresetLive')
    preset_real_time = Component(EpicsSignal, 'PresetReal')
    preset_mode = Component(EpicsSignal, 'PresetMode', string=True)
    preset_triggers = Component(EpicsSignal, 'PresetTriggers')

    # Acquisition
    erase_all = Component(EpicsSignal, 'EraseAll')
    erase_start = Component(EpicsSignal, 'EraseStart', trigger_value=1)
    start_all = Component(EpicsSignal, 'StartAll')
    stop_all = Component(EpicsSignal, 'StopAll')

    # Status
    set_acquire_busy = Component(EpicsSignal, 'SetAcquireBusy')
    acquire_busy = Component(EpicsSignal, 'AcquireBusy')
    status_all = Component(EpicsSignal, 'StatusAll')
    status_all_once = Component(EpicsSignal, 'StatusAllOnce')
    acquiring = Component(EpicsSignal, 'Acquiring')

    # Reading
    read_baseline_histograms = Component(EpicsSignal, 'ReadBaselineHistograms')
    read_all = Component(EpicsSignal, 'ReadAll')
    read_all_once = Component(EpicsSignal, 'ReadAllOnce')

    # As a debugging note, if snl_connected is not '1', your IOC is
    # misconfigured:
    snl_connected = Component(EpicsSignal, 'SNL_Connected')

    # Copying to individual elements
    copy_adcp_ercent_rule = Component(EpicsSignal, 'CopyADCPercentRule')
    copy_baseline_cut_enable = Component(EpicsSignal, 'CopyBaselineCutEnable')
    copy_baseline_cut_percent = Component(
        EpicsSignal, 'CopyBaselineCutPercent'
    )
    copy_baseline_filter_length = Component(
        EpicsSignal, 'CopyBaselineFilterLength'
    )
    copy_baseline_threshold = Component(EpicsSignal, 'CopyBaselineThreshold')
    copy_decay_time = Component(EpicsSignal, 'CopyDecayTime')
    copy_detector_polarity = Component(EpicsSignal, 'CopyDetectorPolarity')
    copy_energy_threshold = Component(EpicsSignal, 'CopyEnergyThreshold')
    copy_gap_time = Component(EpicsSignal, 'CopyGapTime')
    copy_max_energy = Component(EpicsSignal, 'CopyMaxEnergy')
    copy_max_width = Component(EpicsSignal, 'CopyMaxWidth')
    copy_peaking_time = Component(EpicsSignal, 'CopyPeakingTime')
    copy_preamp_gain = Component(EpicsSignal, 'CopyPreampGain')
    copy_roic_hannel = Component(EpicsSignal, 'CopyROIChannel')
    copy_roie_nergy = Component(EpicsSignal, 'CopyROIEnergy')
    copy_roi_sca = Component(EpicsSignal, 'CopyROI_SCA')
    copy_reset_delay = Component(EpicsSignal, 'CopyResetDelay')
    copy_trigger_gap_time = Component(EpicsSignal, 'CopyTriggerGapTime')
    copy_trigger_peaking_time = Component(
        EpicsSignal, 'CopyTriggerPeakingTime'
    )
    copy_trigger_threshold = Component(EpicsSignal, 'CopyTriggerThreshold')

    # do_* executes the process:
    do_read_all = Component(EpicsSignal, 'DoReadAll')
    do_read_baseline_histograms = Component(
        EpicsSignal, 'DoReadBaselineHistograms'
    )
    do_read_traces = Component(EpicsSignal, 'DoReadTraces')
    do_status_all = Component(EpicsSignal, 'DoStatusAll')

    # Time
    dead_time = Component(EpicsSignal, 'DeadTime')
    elapsed_live = Component(EpicsSignal, 'ElapsedLive')
    elapsed_real = Component(EpicsSignal, 'ElapsedReal')
    idead_time = Component(EpicsSignal, 'IDeadTime')

    # low-level
    read_low_level_params = Component(EpicsSignal, 'ReadLLParams')

    # Traces
    read_traces = Component(EpicsSignal, 'ReadTraces')
    trace_modes = Component(EpicsSignal, 'TraceModes', string=True)
    trace_times = Component(EpicsSignal, 'TraceTimes')


class SaturnMCA(EpicsMCA, EpicsMCACallback):
    pass


class SaturnDXP(EpicsDXP, EpicsDXPLowLevel):
    pass


class Saturn(EpicsDXPBaseSystem):
    '''DXP Saturn with 1 channel example'''
    dxp = Component(SaturnDXP, 'dxp1:')
    mca = Component(SaturnMCA, 'mca1')


class MercuryDXP(EpicsDXP, EpicsDXPLowLevel):
    pass


class Mercury1(EpicsDXPMultiElementSystem):
    '''DXP Mercury with 1 channel example'''
    dxp = Component(MercuryDXP, 'dxp1:')
    mca = Component(EpicsMCARecord, 'mca1')


class SoftDXPTrigger(Device):
    '''Simple soft trigger for DXP devices
    Parameters
    ----------
    count_signal : str, optional
        Signal to set acquisition time (default: 'preset_real_time')
    preset_mode : str, optional
        Default preset mode for the stage signals (default: 'Real time')
    mode_signal : str, optional
        Preset mode signal attribute (default 'preset_mode')
    stop_signal : str, optional
        Stop signal attribute (default 'stop_all')
    '''

    count_time = Component(Signal, value=None, doc='bluesky count time')

    def __init__(self, *args, count_signal='preset_real_time',
                 stop_signal='stop_all', mode_signal='preset_mode',
                 preset_mode='Real time',
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._status = None
        self._count_signal = getattr(self, count_signal)

        stop_signal = getattr(self, stop_signal)
        self.stage_sigs[stop_signal] = 1

        mode_signal = getattr(self, mode_signal)
        self.stage_sigs[mode_signal] = preset_mode

    def stage(self):
        if self.count_time.get() is None:
            # remove count_time from the stage signals if count_time unset
            try:
                del self.stage_sigs[self._count_signal]
            except KeyError:
                pass
        else:
            self.stage_sigs[self._count_signal] = self.count_time.get()

        super().stage()
