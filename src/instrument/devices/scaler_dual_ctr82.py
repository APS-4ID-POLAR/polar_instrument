from collections import OrderedDict
from math import floor

from ophyd import Device, Component, FormattedComponent, Kind
from ophyd.scaler import ScalerChannel, ScalerCH

from .scaler import PresetMonitorSignal
from ..utils.formatted_dynamic_component import InstanceFormattedComponent

NUMCHANNELS = 8


class LocalScalerChannel(ScalerChannel):
    def __init__(self, *args, ch_num=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._scaler_number = floor((ch_num - 1) / NUMCHANNELS) + 1


class LocalScalerCHNoTrigger(ScalerCH):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channels.kind = Kind.omitted


class DualCTR8Scaler(Device):
    def __init__(self, prefix1, prefix2, **kwargs):
        self.prefix1 = prefix1
        self.prefix2 = prefix2
        super().__init__("", **kwargs)

        self._monitor = self.channels.chan01  # Default monitor
        self.scaler1.channels.kind = Kind.omitted
        self.scaler2.channels.kind = Kind.omitted

    @staticmethod
    def make_channels(instance):
        defn = OrderedDict()
        for i in range(1, NUMCHANNELS + 1):
            defn[f"chan{i:02d}"] = (
                ScalerChannel,
                "{prefix1}",
                {"ch_num": i, "kind": Kind.normal},
            )
        for i in range(1, NUMCHANNELS + 1):
            defn[f"chan{i + NUMCHANNELS:02d}"] = (
                ScalerChannel,
                "{prefix2}",
                {"ch_num": i, "kind": Kind.normal},
            )
        return defn

    channels = InstanceFormattedComponent(make_channels)

    scaler1 = FormattedComponent(ScalerCH, "{prefix1}")
    scaler2 = FormattedComponent(ScalerCH, "{prefix2}")

    preset_time = None
    preset_monitor = Component(PresetMonitorSignal, kind=Kind.config)

    def match_names(self):
        for s in self.channels.component_names:
            getattr(self.channels, s).match_name()

    def select_channels(self, chan_names=None):
        self.match_names()
        name_map = {}
        for s in self.channels.component_names:
            scaler_channel = getattr(self.channels, s)
            nm = scaler_channel.s.name
            if len(nm) > 0:
                name_map[nm] = s

        if chan_names is None:
            chan_names = name_map.keys()

        read_attrs = []
        for ch in chan_names:
            try:
                read_attrs.append(name_map[ch])
            except KeyError:
                raise RuntimeError(
                    f"The channel {ch} is not configured on the scaler. "
                    f"Named channels: {tuple(name_map)}"
                )

        self.channels.kind = Kind.normal
        self.channels.read_attrs = list(read_attrs)
        self.channels.configuration_attrs = list(read_attrs)
        for ch in read_attrs[1:]:
            getattr(self.channels, ch).s.kind = Kind.hinted

    @property
    def trigger_scaler(self):
        channel = self.channels_name_map[self.monitor]
        scaler_num = 1 if int(channel.replace("chan", "")) <= NUMCHANNELS else 2
        return getattr(self, f"scaler{scaler_num}")

    def trigger(self):
        return self.trigger_scaler.trigger()

    @property
    def channels_name_map(self):
        name_map = {}
        for channel in self.channels.component_names:
            name = getattr(self.channels, channel).s.name
            if len(name) > 0:
                name_map[name] = channel
        return name_map

    def select_plot_channels(self, chan_names=None):
        self.match_names()
        name_map = self.channels_name_map

        if not chan_names:
            chan_names = name_map.keys()

        for ch in name_map.keys():
            try:
                channel = getattr(self.channels, name_map[ch])
            except KeyError:
                raise RuntimeError(
                    f"The channel {ch} is not configured on the scaler. "
                    f"Named channels: {tuple(name_map)}"
                )
            if ch in chan_names:
                channel.s.kind = Kind.hinted
            else:
                if channel.kind.value != 0:
                    channel.s.kind = Kind.normal

    def select_read_channels(self, chan_names=None):
        self.match_names()
        name_map = self.channels_name_map

        if chan_names is None:
            chan_names = name_map.keys()

        read_attrs = ['chan01']  # always include time
        for ch in chan_names:
            try:
                read_attrs.append(name_map[ch])
            except KeyError:
                raise RuntimeError(
                    f"The channel {ch} is not configured on the scaler. "
                    f"Named channels: {tuple(name_map)}"
                )

        self.channels.kind = Kind.normal
        self.channels.read_attrs = list(read_attrs)
        self.channels.configuration_attrs = list(read_attrs)
        if len(self.hints['fields']) == 0:
            self.select_plot_channels(chan_names)

    @property
    def monitor(self):
        return self._monitor.s.name

    @monitor.setter
    def monitor(self, value):
        name_map = self.channels_name_map
        if value not in (set(name_map.keys()) | set(name_map.values())):
            raise ValueError(
                "Monitor must be either a channel name or component name. "
                f"Valid names: {name_map.keys()}, {name_map.values()}"
            )

        if value in name_map.keys():
            value = name_map[value]

        channel = getattr(self.channels, value)
        if channel.kind == Kind.omitted:
            channel.kind = Kind.normal

        for channel_name in self.channels.component_names:
            chan = getattr(self.channels, channel_name)
            target = 'Y' if chan == channel else 'N'
            chan.gate.put(target, use_complete=True)

        self._monitor = channel

    @property
    def plot_options(self):
        return list(self.channels_name_map.keys())

    def select_plot(self, channels):
        self.select_plot_channels(chan_names=channels)

    def default_settings(self):
        self.monitor = 'chan01'
        self.select_read_channels()
        self.select_plot_channels()
