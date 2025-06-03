"""
Setup for two CTR8 devices used together
"""

from collections import OrderedDict
from ophyd import (
    FormattedComponent, DynamicDeviceComponent, Component, Device, Kind
)
from ophyd.scaler import ScalerChannel, ScalerCH
from math import floor
from .scaler import PresetMonitorSignal

# TODO: This has the PVs hardcoded in the make_channel function. Need to find a
# way to create have a DynamicDeviceComponent that also uses FormattedComponent.

NUMCHANNELS = 8  # Hardcoded number of channels... Is it needed?
PREFIX1 = "4idCTR8_1:scaler1"
PREFIX2 = "4idCTR8_1:scaler2"


class LocalScalerChannel(ScalerChannel):
    def __init__(self, *args, ch_num=0, **kwargs):
        super().__init__(*args, **kwargs)

        # This stores info on which scaler this belongs to
        self._scaler_number = floor((ch_num-1)/NUMCHANNELS) + 1


def make_channels():
    defn = OrderedDict()

    # First scaler
    for i in range(1, NUMCHANNELS + 1):
        defn[f"chan{i :02d}"] = (
            ScalerChannel,
            PREFIX1,
            {"ch_num": i, "kind": "normal"}
        )

    # Second scaler
    for i in range(1, NUMCHANNELS + 1):
        defn[f"chan{i + NUMCHANNELS :02d}"] = (
            ScalerChannel,
            PREFIX2,
            {"ch_num": i, "kind": "normal"}
        )

    return defn


class DualCTR8Scaler(Device):

    def __init__(self, prefix1, prefix2, **kwargs):
        self.prefix1 = prefix1
        self.prefix2 = prefix2
        super().__init__("", **kwargs)
        self._monitor = self.channels.chan01  # Time is the default monitor.
        self.scaler1.channels.kind = Kind.omitted
        self.scaler2.channels.kind = Kind.omitted

    channels = DynamicDeviceComponent(make_channels())

    scaler1 = FormattedComponent(ScalerCH, "{prefix1}")
    scaler2 = FormattedComponent(ScalerCH, "{prefix2}")

    preset_time = None
    preset_monitor = Component(PresetMonitorSignal, kind=Kind.config)

    def match_names(self):
        for s in self.channels.component_names:
            getattr(self.channels, s).match_name()

    def select_channels(self, chan_names=None):
        """Select channels based on the EPICS name PV

        Parameters
        ----------
        chan_names : Iterable[str] or None

            The names (as reported by the ``channel.chname`` signal)
            of the channels to select.
            If ``None``, select **all** channels named in the EPICS scaler.
        """
        self.match_names()
        name_map = {}
        for s in self.channels.component_names:
            scaler_channel = getattr(self.channels, s)
            nm = scaler_channel.s.name  # as defined in self.match_names()
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
                    "The channel {} is not configured "
                    "on the scaler.  The named channels are "
                    "{}".format(ch, tuple(name_map))
                )

        self.channels.kind = Kind.normal
        self.channels.read_attrs = list(read_attrs)
        self.channels.configuration_attrs = list(read_attrs)
        for ch in read_attrs[1:]:
            getattr(self.channels, ch).s.kind = Kind.hinted

    @property
    def trigger_scaler(self):
        channel = self.channels_name_map[self.monitor]
        scaler_num = 1 if int(channel.replace("chan", "")) <= 8 else 2
        return getattr(self, f"scaler{scaler_num}")

    def trigger(self):
        # Only click trigger in the scaler of the monitor, the other
        # will follow because they are hardwired together.
        return self.trigger_scaler.trigger()

    @property
    def channels_name_map(self):
        name_map = {}
        for channel in self.channels.component_names:
            # as defined in self.match_names()
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
                    f"The channel {ch} is not configured on the scaler. The "
                    f"named channels are {tuple(name_map)}"
                )
            if ch in chan_names:
                channel.s.kind = Kind.hinted
            else:
                if channel.kind.value != 0:
                    channel.s.kind = Kind.normal

    def select_read_channels(self, chan_names=None):
        """Select channels based on the EPICS name PV.

        Parameters
        ----------
        chan_names : Iterable[str] or None

            The names (as reported by the channel.chname signal)
            of the channels to select.
            If *None*, select all channels named in the EPICS scaler.
        """
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
                    f"The channel {ch} is not configured on the scaler. The "
                    f"named channels are {tuple(name_map)}"
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
        """
        Selects the monitor channel.

        Parameters
        ----------
        value : str
            Can be either the name of the component channel (like 'chan01'),
            or the name of that channel (like 'Ion Ch 1').
        """

        # Check that value is a valid name.
        name_map = self.channels_name_map
        if value not in (set(name_map.keys()) | set(name_map.values())):
            raise ValueError(
                "Monitor must be either a channel name or the channel "
                f"component. Valid entries are one of these: {name_map.keys()},"
                f" or these: {name_map.keys()}."
            )

        # Changes value to the channel number if needed. From here on,
        # value will always be something like 'chan01'.
        if value in name_map.keys():
            value = name_map[value]

        # Checks/modifies the channel Kind.
        channel = getattr(self.channels, value)
        if channel.kind == Kind.omitted:
            channel.kind = Kind.normal

        # Adjust gates
        for channel_name in self.channels.component_names:
            chan = getattr(self.channels, channel_name)
            target = 'Y' if chan == channel else 'N'
            chan.gate.put(target, use_complete=True)

        self._monitor = channel

    @property
    def plot_options(self):
        # Return all named scaler channels
        return list(self.channels_name_map.keys())

    def select_plot(self, channels):
        self.select_plot_channels(chan_names=channels)

    def default_settings(self):
        self.monitor = 'chan01'
        self.select_read_channels()
        self.select_plot_channels()
