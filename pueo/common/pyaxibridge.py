from ctypes import cdll, Structure, c_int, c_uint, c_uint64, CFUNCTYPE, POINTER
# we use atexit because this guy can be multiply opened and it doesn't matter
import atexit

class struct_axi_bridge_t(Structure):
    pass

struct_axi_bridge_t.__slots__ = [
    'fd',
    'vptr',
    'length',
]

struct_axi_bridge_t._fields_ = [
    ('fd', c_int),
    ('vptr', POINTER(c_uint)),
    ('length', c_uint),
]

class PyAXIBridge:
    def __init__( self, base, size, libPath="libaxibridge32.so" ):
        # build the interface
        self.lib = cdll.LoadLibrary(libPath)
        # define the stuff
        self.lib.libaxibridge32_open.argtypes = [c_uint64]
        self.lib.libaxibridge32_open.restype = POINTER(struct_axi_bridge_t)
        self.lib.libaxibridge32_read.argtypes = [POINTER(struct_axi_bridge_t),
                                                 c_uint]
        self.lib.libaxibridge32_read.restype = c_uint
        self.lib.libaxibridge32_write.argtypes = [POINTER(struct_axi_bridge_t),
                                                  c_uint,
                                                  c_uint]
        self.lib.libaxibridge32_write.restype = None
        self.lib.libaxibridge32_close.argtypes = [POINTER(struct_axi_bridge_t)]
        self.lib.libaxibridge32_close.restype = None

        self.handle = self.lib.libaxibridge32_open(base, size)
        if not bool(self.handle):
            raise IOError("error calling libaxibridge32_open()")
        # ok we now know handle is valid, so we can register the exit
        # we use a lambda here because we don't want this exposed
        close = lambda : self.lib.libaxibridge32_close(self.handle)
        atexit.register(close)
        self.read = lambda x : self.lib.libaxibridge32_read(self.handle, x)
        self.write = lambda x, y : self.lib.libaxibridge32_write(self.handle, x, y)
