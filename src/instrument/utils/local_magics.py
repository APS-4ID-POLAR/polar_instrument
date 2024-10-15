from bluesky.magics import BlueskyMagics
from IPython.core.magic import line_magic
from ..plans import mv, mvr
from ..devices.polar_diffractometer import polar
from bluesky import RunEngineInterrupted

try:
    # cytools is a drop-in replacement for toolz, implemented in Cython
    from cytoolz import partition
except ImportError:
    from toolz import partition


class LocalMagics(BlueskyMagics):

    @line_magic
    def uan2(self, line):
        if len(line.split()) != 2:
            raise TypeError("Wrong parameters. Expected: "
                            "uan two_theta theta")
        args = []
        args.append(polar.gamma)
        args.append(eval(line.split()[0], self.shell.user_ns))
        args.append(polar.mu)
        args.append(eval(line.split()[1], self.shell.user_ns))
        plan = mv(*args)
        self.RE.waiting_hook = self.pbar_manager
        try:
            self.RE(plan)
        except RunEngineInterrupted:
            pass
        self.RE.waiting_hook = None
        self._ensure_idle()
        return None

    @line_magic
    def mov(self, line):
        if len(line.split()) % 2 != 0:
            raise TypeError("Wrong parameters. Expected: "
                            "%mov motor position (or several pairs like that)")
        args = []
        for motor, pos in partition(2, line.split()):
            args.append(eval(motor, self.shell.user_ns))
            args.append(eval(pos, self.shell.user_ns))
        plan = mv(*args)
        self.RE.waiting_hook = self.pbar_manager
        try:
            self.RE(plan)
        except RunEngineInterrupted:
            pass
        self.RE.waiting_hook = None
        self._ensure_idle()
        return None

    @line_magic
    def movr(self, line):
        if len(line.split()) % 2 != 0:
            raise TypeError("Wrong parameters. Expected: "
                            "%mov motor position (or several pairs like that)")
        args = []
        for motor, pos in partition(2, line.split()):
            args.append(eval(motor, self.shell.user_ns))
            args.append(eval(pos, self.shell.user_ns))
        plan = mvr(*args)
        self.RE.waiting_hook = self.pbar_manager
        try:
            self.RE(plan)
        except RunEngineInterrupted:
            pass
        self.RE.waiting_hook = None
        self._ensure_idle()
        return None
    

