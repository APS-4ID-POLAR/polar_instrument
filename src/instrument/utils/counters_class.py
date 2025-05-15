from pandas import DataFrame
from ophydregistry import ComponentNotFound
from apsbits.core.instrument_init import oregistry
from logging import getLogger

logger = getLogger(__name__)
logger.bsdev(__file__)

__all__ = ['counters']


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

    def __init__(self):
        super().__init__()
        # This will hold the devices instances.
        self._dets = []
        self._mon = None
        self._extra_devices = []
        # self._available_scalers = [scaler_sim, scaler_ctr8]

    def __repr__(self):

        read_names = [
            item.name for item in (self.detectors + self.extra_devices)
        ]

        plot_names = []
        for item in self.detectors:
            plot_names.extend(item.hints['fields'])

        return ("Counters settings\n"
                " Monitor:\n"
                f"  Scaler channel = '{self._mon}'\n"
                # f"  Preset counts = '{self.monitor_counts}'\n"
                " Detectors:\n"
                f"  Read devices = {read_names}\n"
                f"  Plot components = {plot_names}")

    def __str__(self):
        return self.__repr__()

    def __call__(self, detectors, monitor=None):
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
    def available_scalers(self):
        scalers = oregistry.findall("scaler", allow_none=True)
        if scalers is None:
            return None
        else:
            return [device.name for device in scalers]

    @property
    def detectors(self):
        return self._dets

    @property
    def monitor(self):
        return self._mon

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
                raise ValueError("Input has to be a device instance, not a "
                                 f"device name, but {item} was entered.")
            if item not in self.detectors:
                self._extra_devices.append(item)

    @property
    def _available_detectors(self):
        try:
            dets = oregistry.findall("detector")
        except ComponentNotFound:
            logger.warning("WARNING: no detectors were found by oregistry.")
            dets = []

        return dets

    @property
    def detectors_plot_options(self):
        table = dict(detectors=[], channels=[])
        for det in self._available_detectors:
            # det.plot_options will return a list of available
            # plotting options.
            _options = getattr(det, "plot_options", [])
            table["channels"] += _options
            table["detectors"] += [det.name for _ in range(len(_options))]

        # This will be a table with all the options, it will have the advantage
        # that it can be indexed.
        return DataFrame(table)

    def select_plot_channels(self, selection):

        groups = self.detectors_plot_options.iloc[
            list(selection)
        ].groupby("detectors")

        dets = []
        for name, group in groups:
            det = oregistry.find(name)
            # det.select_plot(item) selects that channel to plot.
            getattr(det, "select_plot")(list(group["channels"].values))
            dets.append(det)

        for scaler in self.available_scalers:
            if scaler not in dets:
                dets.append(scaler)
                scaler.select_plot_channels([''])

        self._dets = dets

    def plotselect(self):
        print("Options:")
        print(self.detectors_plot_options)
        print("")

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
                [i in self.detectors_plot_options.index.values for i in dets]
            ):
                print("The index values must be in the table.")
                continue

            self.select_plot_channels(dets)
            break

        selection = self.detectors_plot_options.iloc[dets].detectors.values
        # if any detector is not a scaler, then count agains time!
        if any(["scaler" not in i for i in selection]):
            print(
                "One of the detectors is not a scaler, so 'Time' will be "
                "selected as monitor."
            )
            mon = 0
        else:
            _mon = self.detectors_plot_options[
                self.detectors_plot_options["channels"] == self.monitor
            ].index[0]
            while True:
                mon = input(
                    f"Enter index number of monitor detector [{_mon}]: "
                ) or _mon

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

        self._mon = mon

        print()
        print(self)


counters = CountersClass()
