""" Handler for SPE files """

from area_detector_handlers import HandlerBase
from imageio.v3 import imread
from os.path import join


class AreaDetectorSPEHandler(HandlerBase):
    specs = {"AD_SPE_APSPOLAR"} | HandlerBase.specs

    def __init__(self, fpath, template, filename, frame_per_point=1):
        self._path = join(fpath, "")
        self._fpp = frame_per_point
        self._template = template
        self._filename = filename
        self._f_cache = dict()

    def __call__(self, point_number):
        if point_number not in self._f_cache:
            fname = self._template % (self._path, self._filename, point_number)
            imgs = imread(fname)
            self._f_cache[point_number] = imgs

        data = self._f_cache[point_number]

        if data.shape[0] != self._fpp:
            raise ValueError(
                "Expected {} frames, found {} frames".format(self._fpp, data.shape[0])
            )

        return data

    def get_file_list(self, datum_kwarg_gen):
        return [
            self._template % (self._path, self._filename, d["point_number"])
            for d in datum_kwarg_gen
        ]
