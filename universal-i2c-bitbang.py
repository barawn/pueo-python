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
        self.__sda = sda
        self.__scl = scl

        self.__sda.hiz()
        self.__scl.hiz()
    
    def wait(self):
        "Delay for reliable I2C operation. May be too small for Pi type 2"
        return

    def start(self):
        self.__sda.hiz()
        self.__scl.hiz()
        self.wait()
        self.__sda.lo()
        self.wait()
        self.__scl.lo()
        self.wait()
        self.wait()
        return

    def clock(self):
        self.wait()
        self.__scl.hiz()
        self.wait()
        self.__scl.lo()
        return

    def rxAck(self):        
        self.__scl.lo()
        self.__sda.hiz()
        self.__scl.hiz()
        self.wait()
        return self.__sda.value() == 1 ? False : True

    def txAck(self):
        self.__sda.lo()
        self.wait()
        self.clock()
        self.__sda.hiz()
        return

    def stop(self):
        self.__sda.lo()
        self.__scl.hiz()
        self.wait()
        self.__sda.hiz()
        return

    def rxBit(self):
        bit = 0
        self.wait()
        self.__scl.hiz()
        self.wait()
        bit = self.__sda.value()
        self.wait()
        self.__scl.lo()
        self.wait()
        return bit

    def rxByte(self):
        byte = 0
        self.__scl.lo()
        self.wait()
        self.__sda.hiz()
        for i in range(0, 8):
            byte = (byte << 1) + self.rxBit()
        return byte
                   
    def txByte(self, byte):
        self.__byte = byte
        self.__count = 0
        self.__scl.lo()
        self.__sda.lo()
        self.wait()
        for self.__count in range(0, 8):
            if (self.__byte & 0x80) == 0:
                self.__sda.lo()
            else:
                self.__sda.hiz()
            self.__byte = self.__byte << 1
            self.clock()
        self.__sda.hiz()
        return self.rxAck()

    # returns True on error, False if not
    def write(self, address, txd = None):
        self.start()
        addr = address << 1
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at addr")
            return True
        i = 0
        if txd is None or len(txd) == 0:
            return False
        for byte in txd:
            ack = self.txByte(byte)
            if not ack:
                print("no acknowledge at byte %d" % i)
                return True
            i = i + 1
        self.stop()
        return False

    def read(self, address, nbytes=1):
        self.start()
        addr = (address << 1) | 1
        ack = self.txByte(addr)
        if not ack:
            print("no acknowledge at addr")
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
