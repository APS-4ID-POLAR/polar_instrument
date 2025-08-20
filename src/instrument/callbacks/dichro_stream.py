"""
Create new stream with processed XMCD data
"""

__all__ = ["dichro", "plot_dichro_settings", "dichro_bec"]


from bluesky.callbacks.stream import LiveDispatcher
from bluesky.callbacks.mpl_plotting import LivePlot
from bluesky.callbacks.best_effort import BestEffortCallback
from streamz import Source
from numpy import mean, log, array, nan
from ophyd import Signal, Device, Component
from logging import getLogger

logger = getLogger(__name__)


class DichroDevice(Device):
    positioner1 = Component(Signal, value=0)
    positioner2 = Component(Signal, value=0)
    xas = Component(Signal, value=0)
    xmcd = Component(Signal, value=0)

    def subscribe(self, callback, event_type=None, run=False):
        super().subscribe(callback, event_type="acq_done", run=run)

    def put(self, dev_t, **kwargs):
        super().put(dev_t, **kwargs)
        self._run_subs(sub_type=self.SUB_ACQ_DONE, success=True)


class Settings:
    positioner1 = "energy"
    positioner2 = None
    monitor = "4idhI0"
    detector = "4idhI1"
    transmission = True
    pattern = [1, -1, -1, 1]

    def get_keys(self):
        return {
            item: getattr(self, item)
            for item in ["positioner1", "positioner2", "monitor", "detector"]
            if getattr(self, item) is not None
        }


# TODO: Should this go in the pr_setup?
class DichroStream(LiveDispatcher):
    """Stream that processes XMCD and XANES"""

    def __init__(self):
        self.n = 4
        self.in_node = None
        self.out_node = None
        self.processor = None
        self.data_keys = None
        self.settings = Settings()
        self._trigger = False
        super().__init__()

    def start(self, doc):
        """
        Create the stream after seeing the start document

        The callback looks for the 'average' key in the start document to
        configure itself.
        """

        def process_xmcd(cache):
            processed_evt = dict()
            desc_id = cache[0]["descriptor"]

            # Check that all of our events came from the same configuration
            if not all([desc_id == evt["descriptor"] for evt in cache]):
                raise Exception(
                    "The events in this bundle are from different"
                    "configurations!"
                )

            # Use the last descriptor to avoid strings and objects
            if all(
                [
                    key in self.raw_descriptors[desc_id]["data_keys"]
                    for key in self.data_keys.values()
                ]
            ):

                for key, value in self.data_keys.items():
                    if "positioner1" in key:
                        processed_evt[value] = mean(
                            [evt["data"][value] for evt in cache], axis=0
                        )
                    elif "positioner2" in key:
                        processed_evt[value] = mean(
                            [evt["data"][value] for evt in cache], axis=0
                        )
                    elif "monitor" in key:
                        _mon = array([evt["data"][value] for evt in cache])
                    elif "detector" in key:
                        _det = array([evt["data"][value] for evt in cache])

                _xas = (
                    log(_mon / _det)
                    if self.settings.transmission
                    else _det / _mon
                )

                processed_evt["xas"] = mean(_xas)

                # This assumes that there is two polarization states
                processed_evt["xmcd"] = (
                    mean(_xas * array(self.settings.pattern)) * 2
                )
            else:
                logger.warning(
                    "The input data keys do not match entries in the database. "
                    "Data is being recorded, but the plot will not be "
                    "generated."
                )

                for key, value in self.data_keys.items():
                    if "positioner" in key:
                        processed_evt[value] = 0
                processed_evt["xas"] = 0
                processed_evt["xmcd"] = 0

            dichro_out = ()

            for key in ["positioner1", "positioner2"]:
                pos = getattr(self.settings, key)
                if pos is not None:
                    dichro_out += (processed_evt[pos],)
                else:
                    dichro_out += (nan,)

            dichro_out += (processed_evt["xas"], processed_evt["xmcd"])

            dichro.put(dichro_out)

            return {"data": processed_evt, "descriptor": desc_id}

        # Define our nodes
        self.in_node = Source(stream_name="dichro_xmcd")

        self.n = len(self.settings.pattern)
        self.processor = self.in_node.partition(self.n)

        self.data_keys = self.settings.get_keys()

        self.out_node = self.processor.map(process_xmcd)
        self.out_node.sink(self.process_event)

        _start_doc = doc
        _start_doc["motors"] = []
        for pos in (self.settings.positioner1, self.settings.positioner2):
            if pos is not None:
                _start_doc["motors"].append(pos)
        super().start(_start_doc)

    def event(self, doc):
        """Send an Event through the stream"""
        descriptor = self.raw_descriptors[doc["descriptor"]]
        if descriptor.get("name") == "primary":
            self.in_node.emit(doc)

    def stop(self, doc):
        """Delete the stream when run stops"""
        self.in_node = None
        self.out_node = None
        self.processor = None
        self.data_keys = None
        self.settings.positioner1 = None
        self.settings.positioner2 = None
        self._trigger = False
        super().stop(doc)


class DichroLivePlot(LivePlot):
    def __init__(self, y, stream, **kwargs):
        self.stream = stream
        super().__init__(y, x=stream.settings.positioner1, **kwargs)

    def start(self, doc):
        self.x = self.stream.settings.positioner1
        super().start(doc)


dichro = DichroDevice("", name="dichro")
dichro.xmcd.kind = "normal"
dichro.xas.kind = "normal"

plot_dichro_settings = DichroStream()
dichro_bec = BestEffortCallback()
dichro_bec.disable_heading()
dichro_bec.disable_table()
plot_dichro_settings.subscribe(dichro_bec)
