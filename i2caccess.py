#! /usr/bin/python3

# Author Richard Hinckley - April 2015
# Modified by PSA - 5/15/24

# We don't want to use a specific class here.
# Instead we want to be passed two pin *objects*
# which have functions
# pin.hiz()
# pin.lo()
# pin.value()
#import RPi.GPIO as GPIO

class I2cAccess(object):
    def __init__(self, scl, sda):
        self.sda = sda
        self.scl = scl

        self.sda.hiz()
        self.scl.hiz()
    
    def wait(self):
        "Delay for reliable I2C operation. May be too small for Pi type 2"
        return

    def start(self):
        self.sda.hiz()
        self.scl.hiz()
        self.wait()
        self.sda.lo()
        self.wait()
        self.scl.lo()
        self.wait()
        self.wait()
        return

    def clock(self):
        self.wait()
        self.scl.hiz()
        self.wait()
        self.scl.lo()
        return

    def rxAck(self):        
        self.scl.lo()
        self.sda.hiz()
        self.scl.hiz()
        self.wait()
        return False if self.sda.value() == 1 else True
    
    def txAck(self):
        self.sda.lo()
        self.wait()
        self.clock()
        self.sda.hiz()
        return
    
    def stop(self):
        self.scl.lo()
        self.sda.lo()
        self.scl.hiz()
        self.wait()
        self.sda.hiz()
        return

    def rxBit(self):
        bit = 0
        self.wait()
        self.scl.hiz()
        self.wait()
        bit = self.sda.value()
        self.wait()
        self.scl.lo()
        self.wait()
        return bit

    def rxByte(self):
        byte = 0
        self.scl.lo()
        self.wait()
        self.sda.hiz()
        for i in range(0, 8):
            byte = (byte << 1) + self.rxBit()
        return byte
                   
    def txByte(self, byte):
        self.__byte = byte
        self.__count = 0
        self.scl.lo()
        self.sda.lo()
        self.wait()
        for self.__count in range(0, 8):
            if (self.__byte & 0x80) == 0:
                self.sda.lo()
            else:
                self.sda.hiz()
            self.__byte = self.__byte << 1
            self.clock()
        self.sda.hiz()
        return self.rxAck()

    # returns True on error, False if not
    def write(self, address, txd = None):
        self.start()
        addr = address << 1
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at addr")
            self.stop()
            return True
        i = 0
        if txd is None or len(txd) == 0:
            self.stop()
            return False
        for byte in txd:
            ack = self.txByte(byte)
            if not ack:
                print("no acknowledge at byte %d" % i)
                self.stop()
                return True
            i = i + 1
        self.stop()
        return False

    # read using a restart
    def readFrom(self, address, regAddr, nbytes=1):
        self.start()
        addr = (address << 1) 
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at addr")
            self.stop()
            return (True, None)
        ack = self.txByte(regAddr)
        if not ack:
            print("no acknowledge at regAddr")
            self.stop()
            return (True, None)
        # repeated start
        self.scl.lo()
        self.scl.hiz()
        self.sda.lo()
        addr = (address << 1) | 1
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at read addr")
            self.stop()
            return (True, None)
        rxd = []
        if nbytes == 0:
            self.stop()
            return (False, None)
        while nbytes > 0:
            rxd.append(self.rxByte())
            nbytes = nbytes - 1
            if nbytes:
                self.txAck()
            else:
                self.clock()
        self.stop()
        return (False, rxd)
    
    def read(self, address, nbytes=1):
        self.start()
        addr = (address << 1) | 1
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at addr")
            self.stop()
            return (True, None)
        rxd = []
        if nbytes == 0:
            self.stop()
            return (False, None)
        while nbytes > 0:
            rxd.append(self.rxByte())
            nbytes = nbytes - 1
            if nbytes:
                self.txAck()
            else:
                self.clock()
        self.stop()
        return (False, rxd)
