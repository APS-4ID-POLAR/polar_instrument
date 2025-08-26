from pandas import DataFrame
from ophydregistry import ComponentNotFound
from apsbits.core.instrument_init import oregistry
from logging import getLogger
from collections.abc import Iterable

logger = getLogger(__name__)
logger.bsdev(__file__)

__all__ = ["counters"]

IDEAL_ORDER = [
    "scaler1",
    "scaler2",
    "eiger",
    "vortex",
    "flagcam_hhl",
    "flagcam_mono",
    "flagcam_toro",
]


class CountersClass:
    """
    Holds monitor and detectors for scans. Our scans read these by default.

    Attributes
    ----------
    detectors : list of devices
        Detectors that will be read.
    extra_devices : list of devices
        Extra devices that will be read but explicitly not plottedd during
        scan. Keep in mind that it will "trigger and read", so if this takes a
        long time to trigger, it will slow down the scan.
    monitor : str
        Name of the scaler channel that is used as monitor.
    """

    def __init__(self, order=IDEAL_ORDER):
        super().__init__()
        # This will hold the devices instances.
        self._dets = []
        self._mon = "Time"
        self._extra_devices = []
        self._order = order

    def __repr__(self):

        read_names = [
            item.name for item in (self.detectors + self.extra_devices)
        ]

        return (
            "Counters settings\n"
            " Monitor:\n"
            f"  Scaler channel = '{self._mon}'\n"
            " Detectors:\n"
            f"  Read devices = {read_names}\n"
            f"  Plot components = {self.plot_names}"
        )

    def __str__(self):
        return self.__repr__()

    def __call__(self):
        """
        Selects the plotting detector and monitor.

        For now both monitor and detector has to be in scaler.

        Parameters
        ----------
        detectors : str or iterable
            Name(s) of the scaler channels, or the detector instance to plot,
            if None it will not be changedd.
        monitor : str or int, optional
            Name or number of the scaler channel to use as monitor, uses the
            same number convention as in SPEC. If None, it will not be changed.
        counts : int or float, optional
            Counts in the monitor to be used. If monitor = 'Time', then this is
            the time per point. If None, it will read the preset count for the
            monitor in the EPICS scaler.
        Example
        -------
        This selects the "Ion Ch 4" as detector, and "Ion Ch 1" as monitor:

        .. code-block:: python
            In[1]: counters('Ion Ch 4')

        Changes monitor to 'Ion Ch 3':

        .. code-block:: python
            In[2]: counters('Ion Ch 4', 'Ion Ch 3')

        Both 'Ion Ch 5' and 'Ion Ch 4' as detectors, and 'Ion Ch 3' as monitor:

        .. code-block:: python
            In[3]: counters(['Ion Ch 4', 'Ion Ch 5'], 'Ion Ch 3')

        Vortex as detector:

        .. code-block:: python
            In[4]: vortex = load_votex('xspress', 4)
            In[5]: counters(vortex)

        But you can mix scaler and other detectors:

        .. code-block:: python
            In[6]: counters([vortex, 'Ion Ch 5'])

        """

        # self.detectors = detectors
        # self.monitor = monitor
        self.plotselect()

    @property
    def plot_names(self):
        plot_names = []
        for item in self.detectors:
            plot_names.extend(item.hints["fields"])
        return plot_names

    @property
    def _available_scalers(self):
        return oregistry.findall("scaler", allow_none=True)

    @property
    def detectors(self):
        return self._dets

    @property
    def selected_plot_detectors(self):
        _selected = []
        for det in self.detectors:
            if len(det.hints["fields"]) > 0:
                _selected.append(det.name)
        return _selected

    @property
    def monitor(self):
        return self._mon

    @property
    def monitor_detector(self):
        if self.monitor == "Time":
            return self._available_scalers
        else:
            name = self.detectors_plot_options[
                self.detectors_plot_options["channels"] == self.monitor
            ].iloc[0]["detectors"]
            return oregistry.find(name)

    @property
    def extra_devices(self):
        return self._extra_devices

    @extra_devices.setter
    def extra_devices(self, value):
        # Ensures value is iterable.
        try:
            value = list(value)
        except TypeError:
            value = [value]

        self._extra_devices = []
        for item in value:
            if isinstance(item, str):
                raise ValueError(
                    "Input has to be a device instance, not a "
                    f"device name, but {item} was entered."
                )
            if item not in self.detectors:
                self._extra_devices.append(item)

    @property
    def _available_detectors(self):
        try:
            _dets = oregistry.findall("detector")
        except ComponentNotFound:
            logger.warning("WARNING: no detectors were found by oregistry.")
            _dets = []

        dets = []
        for name in self._order:
            dev = oregistry.find(name, allow_none=True)
            if dev in _dets:
                _dets.remove(dev)
            if dev is not None:
                dets.append(dev)

        return dets + _dets

    @property
    def detectors_plot_options(self):
        table = dict(detectors=[], channels=[])

        # If there is any scaler, then we will have a first row with Time
        if len(self._available_scalers) > 0:
            table["detectors"].append("scalers")
            table["channels"].append("Time")

        for det in self._available_detectors:
            # det.plot_options will return a list of available
            # plotting options.
            _options = getattr(det, "plot_options", [])

            # We are taking "Time" for all scalers together, so need to remove
            # it here.
            if det in self._available_scalers:
                _options = _options[1:]

            table["channels"] += _options
            table["detectors"] += [det.name for _ in range(len(_options))]

        # This will be a table with all the options, it will have the advantage
        # that it can be indexed.
        return DataFrame(table)

    def select_plot_channels(self, selection):

        plot_options = self.detectors_plot_options

        # If "Time" is selected, then selects the "Time" of every scaler.
        if 0 in selection:
            selection.remove(0)
            for scaler in self._available_scalers:
                selection.append(len(plot_options))
                plot_options.loc[len(plot_options)] = [
                    scaler.name,
                    scaler.channels.chan01.chname.get(),
                ]

        groups = plot_options.iloc[list(selection)].groupby("detectors")

        dets = []
        for name, group in groups:
            det = oregistry.find(name)
            # det.select_plot(item) selects that channel to plot.
            getattr(det, "select_plot")(list(group["channels"].values))
            dets.append(det)

        for scaler in self._available_scalers:
            if scaler not in dets:
                dets.append(scaler)
                scaler.select_plot_channels([""])

        self._dets = dets

    def plotselect(self, dets=None, mon=None):

        _valid_dets = False
        _valid_mon = False

        # Checks if input is valid
        if dets is not None:
            if not isinstance(dets, Iterable):
                dets = [dets]

            number_of_options = self.detectors_plot_options.shape[0]
            if all([isinstance(i, int) for i in dets]) and all(
                [i < number_of_options for i in dets]
            ):
                _valid_dets = True
            else:
                logger.warning(f"The detectors option {dets} is invalid!")

        if mon is not None:
            if isinstance(mon, int):
                _valid_mon = True
            else:
                logger.warning(f"The monitor option {mon} is invalid!")

        if not (_valid_dets and _valid_mon):
            print("Options:")
            print(self.detectors_plot_options)
            print("")

        if not _valid_dets:
            while True:
                dets = input("Enter the indexes of plotting channels: ") or None

                if dets is None:
                    print("A value must be entered.")
                    continue

                # Check these are all numbers
                try:
                    dets = [int(i) for i in dets.split()]
                except ValueError:
                    print("Please enter the index numbers only.")
                    continue

                # Check that the numbers are valid.
                if not all(
                    [
                        i in self.detectors_plot_options.index.values
                        for i in dets
                    ]
                ):
                    print("The index values must be in the table.")
                    continue

                break

        self.select_plot_channels(dets)

        if not _valid_mon:
            _mon = self.detectors_plot_options[
                self.detectors_plot_options["channels"] == self.monitor
            ].index[0]
            while True:
                mon = (
                    input(f"Enter index number of monitor detector. [{_mon}]: ")
                    or _mon
                )

                try:
                    mon = int(mon)
                except ValueError:
                    print("Please enter the index number only.")
                    continue

                if mon in dets:
                    print(
                        f"Monitor {mon} is invalid because this is being used "
                        "as detector."
                    )
                    continue

                break

        self._mon = self.detectors_plot_options.loc[mon]["channels"]

        print()
        print(self)


counters = CountersClass()
