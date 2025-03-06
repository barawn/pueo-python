import socket
import time
import struct
import ipaddress

class TURFEth:
    """ helper class for TURF ethernet testing """

    # these ports are fixed
    UDP_CTRL = 21603
    
    def __init__(self,
                 turf = "192.168.1.128",
                 cs_ip = "192.168.1.1",
                 cs_port = 21347):
        """ no event path right now """
        self.cs_ip = ipaddress.ip_address(cs_ip)
        self.cs_port = cs_port
        self.turf_ip = ipaddress.ip_address(turf)
        self.turf_port = self.UDP_CTRL
        
        self.cs = socket.socket(socket.AF_INET,
                                socket.SOCK_DGRAM)
        self.cs.bind( (str(cs_ip), cs_port) )

    def ctrl_identify(self):
        msg = b'\x00'*6+b'ID'
        self.cs.sendto( msg, (str(self.turf_ip), self.turf_port))
        data, addr = self.cs.recvfrom(1024)
        resp = bytearray(data).reverse()
        print("Response: ", resp.hex())
        
