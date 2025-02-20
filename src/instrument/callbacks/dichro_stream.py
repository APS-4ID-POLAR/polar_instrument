"""
Create new stream with processed XMCD data
"""

__all__ = ["dichro", "plot_dichro_settings", "dichro_bec"]


from bluesky.callbacks.stream import LiveDispatcher
from bluesky.callbacks.mpl_plotting import LivePlot
from bluesky.callbacks.best_effort import BestEffortCallback
from streamz import Source
from numpy import mean, log, array
from ophyd import Signal, Device, Component
from ..utils.run_engine import sd


class DichroDevice(Device):
    positioner = Component(Signal, value=0)
    xas = Component(Signal, value=0)
    xmcd = Component(Signal, value=0)

    def subscribe(self, callback, event_type=None, run=True):
        super().subscribe(callback, event_type="acq_done", run=run)

    def put(self, dev_t, **kwargs):
        super().put(dev_t, **kwargs)
        self._run_subs(sub_type=self.SUB_ACQ_DONE, success=True)


class Settings():
    positioner = "energy"
    monitor = "4idbI0"
    detector = "4idbI"
    transmission = True


# TODO: Should this go in the pr_setup?
class DichroStream(LiveDispatcher):
    """Stream that processes XMCD and XANES"""
    def __init__(self, n=4):
        self.n = n
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

        # Define our nodes
        if not self.in_node:
            self.in_node = Source(stream_name='dichro_xmcd')

        self.processor = self.in_node.partition(self.n)

        self.data_keys = [
            self.settings.positioner,
            self.settings.monitor,
            self.settings.detector,
        ]

        def process_xmcd(cache):
            processed_evt = dict()
            desc_id = cache[0]['descriptor']

            # Check that all of our events came from the same configuration
            if not all([desc_id == evt['descriptor'] for evt in cache]):
                raise Exception(
                    'The events in this bundle are from different'
                    'configurations!'
                )

            # Use the last descriptor to avoid strings and objects
            if all([key in self.raw_descriptors[desc_id]['data_keys'] for key
                    in self.data_keys]):
                processed_evt[self.data_keys[0]] = mean(
                    [evt['data'][self.data_keys[0]] for evt in cache], axis=0
                )

                _mon = array(
                    [evt['data'][self.data_keys[1]] for evt in cache]
                )

                _det = array(
                    [evt['data'][self.data_keys[2]] for evt in cache]
                )

                _xas = (
                    log(_mon/_det) if self.settings.transmission else _det/_mon
                )

                processed_evt["xas"] = mean(_xas)
                processed_evt["xmcd"] = (
                    (_xas[0] + _xas[3])/2 - (_xas[1] + _xas[2])/2
                )
            else:
                raise Exception(
                    'The input data keys do not match entries in the database.'
                )

            dichro.put((
                processed_evt[self.data_keys[0]],
                processed_evt["xas"],
                processed_evt["xmcd"]
            ))

            return {'data': processed_evt, 'descriptor': desc_id}

        self.out_node = self.processor.map(process_xmcd)
        self.out_node.sink(self.process_event)

        _start_doc = doc
        _start_doc["motors"] = [self.settings.positioner]
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
        self._trigger = False
        super().stop(doc)


class DichroLivePlot(LivePlot):
    def __init__(self, y, stream, **kwargs):
        self.stream = stream
        super().__init__(y, x=stream.settings.positioner, **kwargs)

    def start(self, doc):
        self.x = self.stream.settings.positioner
        super().start(doc)


dichro = DichroDevice("", name="dichro")
sd.monitors.append(dichro)
# dichro.xmcd.kind = "hinted"
# dichro.xas.kind = "hinted"
dichro.xmcd.kind = "normal"
dichro.xas.kind = "normal"

plot_dichro_settings = DichroStream()
dichro_bec = BestEffortCallback()
dichro_bec.disable_heading()
dichro_bec.disable_table()
plot_dichro_settings.subscribe(dichro_bec)
