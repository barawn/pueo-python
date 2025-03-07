import socket
import time
import struct
import ipaddress

# NOTE:
#
# The Ethernet UDP stuff presents 64-bit data in a
# LITTLE-ENDIAN fashion. As in, the first byte we
# receive is [7:0], the next is [15:8], etc.
#
# This means when you send stuff you need to make sure
# it's little endian, rather than network byte order.
#
# In Python we just get bytes from the socket
# functions, so we can slice & dice them ourselves.
#
class TURFEth:
    """ helper class for TURF ethernet testing """

    # these ports are fixed
    UDP_CTRL = 21603
    UDP_RD = 21618
    UDP_WR = 21623
    
    def __init__(self,
                 turf = "192.168.1.128",
                 cs_ip = "192.168.1.1",
                 cs_port = 21347):
        """ no event path right now """
        self.cs_ip = ipaddress.ip_address(cs_ip)
        self.cs_port = cs_port
        self.turf_ip = ipaddress.ip_address(turf)
        self.turf_csp = self.UDP_CTRL
        self.turf_rdp = self.UDP_RD
        self.turf_wrp = self.UDP_WR
        
        self.cs = socket.socket(socket.AF_INET,
                                socket.SOCK_DGRAM)
        self.cs.bind( (str(cs_ip), cs_port) )
        # open the read/write interface to set tag to 0
        msg = b'\x00'*4
        self.cs.sendto( msg[::-1], (str(self.turf_ip), self.turf_rdp))
        data, addr = self.cs.recvfrom(1024)
        resp = data[::-1]
        print("Connected to device: ", resp[0:4].decode())
        self.tag = 1

    # MOVE THIS TO A DIFFERENT CLASS - NETWORKING IS COOL
    def ctrl_identify(self):
        msg = b'\x00'*6+b'ID'
        self.cs.sendto( msg[::-1], (str(self.turf_ip), self.turf_csp))
        data, addr = self.cs.recvfrom(1024)
        resp = data[::-1]
        return resp[2:].hex(sep=':')
        
    def read(self, addr):
        addr = (addr & 0xFFFFFFF) | (self.tag << 28)
        d = addr.to_bytes(4, 'little')

        # this is the Be Bold method
        # the "correct" method here is to create a separate process/thread
        # which handles the send/receive/repeat request if lost method.
        # We DO NOT have to use the cs port here, the read/write guys
        # respond to whatever port sent them data.
        # So it probably makes sense to completely farm off the event
        # stuff too.

        # we do NOT need to reverse bytes here
        self.cs.sendto( d, (str(self.turf_ip), self.turf_rdp))
        data, addr = self.cs.recvfrom(1024)
        resp = data[::-1]
        tag = (resp[4] >> 4)
        if tag != self.tag:
            raise IOError("Incorrect tag received: expected %d got %d:" %
                          (self.tag, tag), data.hex())
        self.tag = (self.tag + 1) & 0xF
        return struct.unpack(">I", resp[0:4])[0]
        
    def write(self, addr, value):
        addr = (addr & 0xFFFFFFF) | (self.tag << 28)
        d = addr.to_bytes(4, 'little') + value.to_bytes(4, 'little')
        self.cs.sendto( d, (str(self.turf_ip), self.turf_wrp))
        data, addr = self.cs.recvfrom(1024)
        resp = data[::-1]
        tag = (resp[4] >> 4)
        if tag != self.tag:
            raise IOError("Incorrect tag received: expected %d got %d:" %
                          (self.tag, tag), data.hex())
        self.tag = (self.tag + 1) & 0xF
        return 4
    
        
