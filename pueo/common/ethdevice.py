import socket
import struct
import time
import ipaddress

class EthDevice:
    def __init__(self,
                 remote_ip = "192.168.1.128",
                 remote_rp = 21618,
                 remote_wp = 21623,
                 local_ip = "192.168.1.1",
                 local_port = 21362):

        self.remote_ip = ipaddress.ip_address(remote_ip)
        self.remote_readport = remote_rp
        self.remote_writeport = remote_wp
        self.local_ip = ipaddress.ip_address(local_ip)
        self.local_port = local_port

        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM)
        self.sock.bind( (str(self.local_ip), self.local_port))
        # open by reading ID register with tag 0
        msg = b'\x00'*4
        self.sock.sendto( msg[::-1],
                          (str(self.remote_ip), self.remote_readport))
        data, addr = self.sock.recvfrom(1024)
        resp = data[::-1]
        print("Connected to device: ", resp[0:4].decode())
        self.tag = 1

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
        self.sock.sendto( d, (str(self.remote_ip), self.remote_readport))
        data, addr = self.sock.recvfrom(1024)
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
        self.sock.sendto( d, (str(self.remote_ip), self.remote_writeport))
        data, addr = self.sock.recvfrom(1024)
        resp = data[::-1]
        tag = (resp[4] >> 4)
        if tag != self.tag:
            raise IOError("Incorrect tag received: expected %d got %d:" %
                          (self.tag, tag), data.hex())
        self.tag = (self.tag + 1) & 0xF
        return 4
    
    
        
