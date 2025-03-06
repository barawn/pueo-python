import socket
import time
import struct
import ipaddress

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
        
    def ctrl_identify(self):
        msg = b'\x00'*6+b'ID'
        self.cs.sendto( msg[::-1], (str(self.turf_ip), self.turf_csp))
        data, addr = self.cs.recvfrom(1024)
        resp = data[::-1]
        return resp[2:].hex(sep=':')
        
    def read(self, addr):
        
