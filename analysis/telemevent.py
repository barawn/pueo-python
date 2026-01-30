import struct
import numpy as np

class TelemFile:
    """
    Container class to process a telemetry file or set
    of files. Pass a stream-like object (either an open
    file or a BytesIO object).
    """
    def __init__(self, f, verbose=False):
        self.events = {}
        try:
            npkt = 0
            while True:
                if verbose:
                    print(f'Processing packet {npkt}')
                pkt = TelemPacket(f)
                if pkt.packet_type == 0xea7a:
                    # partial event
                    ev = TelemEvent(f)
                    prio = struct.unpack("H", f.read(2))
                    full_evno = f'{ev.run}.{ev.event}'
                    if full_evno not in self.events:
                        ev.priority = prio
                        self.events[full_evno] = ev
                    ch = TelemChannel(f)
                    self.events[full_evno].add_channel(ch.channel_id, f)
                elif pkt.packet_type == 0xda7a:
                    # full event
                    ev = TelemEvent(f)
                    full_evno = f'{ev.run}.{ev.event}'
                    self.events[full_evno] = ev
                    for i in range(224):
                        ch = TelemChannel(f)
                        self.events[full_evno].add_channel(ch.channel_id, f)                        
            npkt = npkt + 1
        except EOFError:
            pass

class TelemChannel:
    HEADER_FORMAT = "BBH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    def __init__(self, f):
        tup = struct.unpack(self.HEADER_FORMAT, f.read(self.HEADER_SIZE))
        self.channel_id = tup[0]
        self.surf_word = tup[1]
        self.length = tup[2]
        
class TelemPacket:
    HEADER_FORMAT = "HHI"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    def __init__(self, f):
        b = f.read(self.HEADER_SIZE)
        if len(b) < self.HEADER_SIZE:
            raise EOFError("end of file")
        tup = struct.unpack(self.HEADER_FORMAT, b)
        self.packet_type = tup[0]
        self.packet_cks = tup[1]
        self.length = tup[2] >> 12        
        
class TelemEvent:
    """
    Container class to hold raw (telemetered) events.
    Got sick of having no easy way to actually view stuff, so
    Jupyter-based event display it is!
    """
    HEADER_FORMAT = "IIIIIIIIIIQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    WAVEFORM_SIZE = 2048
    def __init__(self, f):
        """ Pass a buffer to the *header* for the event to create it. """
        tup = struct.unpack(self.HEADER_FORMAT,
                            f.read(self.HEADER_SIZE))
        self.run = tup[0]
        self.event = tup[1]
        self.event_second = tup[2]
        self.event_time = tup[3]
        self.last_pps = tup[4]
        self.llast_pps = tup[5]
        self.deadtime = tup[6]
        self.deadtime_last = tup[7]
        self.deadtime_llast = tup[8]
        self.trigger_info = tup[9]
        self.readout_sec = (tup[10] & 0xFFFFFFFF)+((tup[10] >> 32) & 0x3)
        self.priority = None
        
        # these are REORDERED into L2 view when added!
        # e.g. self.hdaq[0] = L2[0]
        self.hdaq = {}
        self.vdaq = {}
        self.lf = {}
        self.ramp = {}
        
    def add_channel(self, ch_id, f):
        # MAPPITY MAP MAP
        # 7:0   => hdaq 5
        # 15:8  => hdaq 4
        # 23:16 => hdaq 3
        # 31:24 => hdaq 2
        # 39:32 => hdaq 1
        # 47:40 => hdaq 0
        # 55:48 => lf 0
        # 
        ch = ch_id % 8
        surf = None
        if ch_id < 48:
            surf = 5-int(ch_id/8)
            member_name = 'hdaq'
        elif ch_id < 56:
            surf = 0
            member_name = 'lf'
        elif ch_id < 104:
            surf = 6+int((ch_id-56)/8)
            member_name = 'hdaq'
        elif ch_id < 112:
            surf = 1
            member_name = 'lf'
        elif ch_id < 160:
            surf = 6+int((ch_id-112)/8)
            member_name = 'vdaq'
        elif ch_id < 168:
            surf = 0
            member_name = 'ramp'
        elif ch_id < 216:
            surf = 5-int((ch_id-168)/8)
            member_name = 'vdaq'
        else:
            surf = 1
            member_name = 'ramp'
        if surf not in self.__dict__[member_name]:
            self.__dict__[member_name][surf] = {}
        self.__dict__[member_name][surf][ch] = np.frombuffer(f.read(self.WAVEFORM_SIZE),
                                                             dtype=np.int16)
        
                
                                                       
