from cobs import cobs
import serial
from time import sleep

# This is updated now to allow for wider address spaces and address-mode
class SerialCOBSDevice:
    # searches for FT2232H-based devices only!!
    @classmethod
    def find_serial_devices(cls, board = -1, name=None, verbose=False):
        try:
            import usb
        except ImportError:
            print("find_serial_devices() needs pyusb")
            return
        import os
        if os.uname().sysname != 'Linux':
            print("find_serial_devices() only works on Linux right now (need sysfs)")
            return
        
        # pathlib is super fantastic for traversing sysfs
        from pathlib import Path

        # find FT2232 devices
        devs = []
        for dev in usb.core.find(find_all=True,
                                 idVendor=0x0403,
                                 idProduct=0x6010):
            # check their serial number
            # if for some reason it's not there, pyusb throws
            # ValueError
            try:
                sn = dev.serial_number
                # we know where we stored stuff
                typeboard = sn[-6:]
                typeStr = typeboard[:-2]
                boardStr = typeboard[-2:]
                thisType = chr(int(typeStr[0:2],16))+chr(int(typeStr[2:],16))
                thisBoard = int(boardStr, 16)
                if name is None or thisType == name:
                    if board == -1 or board == thisBoard:
                        devs.append((dev, thisBoard, thisType))
                        if verbose:
                            if name is None:
                                print("found FTDI device (%s #%d) at bus %d dev %d" % (thisType, thisBoard, dev.bus, dev.address))
                            else:
                                print("found %s #%d at bus %d dev %d" % (thisType, thisBoard, dev.bus, dev.address))
            except ValueError:
                pass
            
        # now we can zip through the ftdi_sio devices
        # and find All The Guys
        matchedDevices = []
        for p in Path('/sys/bus/usb/drivers/ftdi_sio').glob('*'):
            if (not os.path.isdir(p)) or os.path.basename(p) == 'module':
                continue
            bus = int(( p / '..' / 'busnum').read_text().rstrip('\x00\n'))
            address = int(( p / '..' / 'devnum').read_text().rstrip('\x00\n'))
            ttyPath = '/dev/' + os.path.basename( (p.glob('tty*')).__next__() )
            if verbose:
                print("path %s (tty %s) has bus %d/addr %d" % (p, ttyPath, bus, address))
            for devt in devs:
                thisDev = devt[0]
                thisBoard = devt[1]
                thisType = devt[2]
                if thisDev.bus == bus and thisDev.address == address:
                    if name is None:
                        matchedDevices.append( (ttyPath, thisBoard, thisType) )
                    else:
                        matchedDevices.append( (ttyPath, thisBoard) )
        return matchedDevices    
    
    def __init__(self, port, baudrate, addrbytes=3, devAddress=None):
            self.dev = serial.Serial(port, baudrate)
            self.addrbytes = addrbytes
            self.address = devAddress
            self.reset()

    def reset(self):                
            # flushy-flushy
            self.dev.write([0x00,0x00,0x00,0x00])
            sleep(0.1)
            rx = self.dev.in_waiting
            # and dump
            if rx:
                    self.dev.read(rx)

    # this is used if we have a multidrop bus and are using addressing
    def setAddress(self, addr):
            self.address = addr

    def __setBaud(self, bd):
            tx = bytearray('\x00B\x00\x00\x00\x00', encoding='utf-8');
            tx[0] = 0xFF
            tx[2] = bd & 0xFF;
            tx[3] = (bd >> 8) & 0xFF
            tx[4] = (bd >> 16) & 0xFF
            tx[5] = (bd >> 24) & 0xFF
            self.writecobs(tx)
            self.dev.flush()
            sleep(0.1)
            self.dev.baudrate = bd
            sleep(0.1)
            c = self.dev.read(1)
            print("Out of baudrate change: %2.2x" % c[0])


    def __buildaddr(self, tx, addr):
            for i in range(self.addrbytes):
                    tx[i] = (addr >> (self.addrbytes-i-1)*8) & 0xFF

    # these are private methods because they only work for devices that implement the Secret FS methods
    # so the idea is that for devices that do implement it, they can just promote this guy however they want
    def __listfiles(self):
            # sigh, there should be a better way to do this
            tx = bytearray('\x00L\x00\x00\x00',encoding='utf-8')
            tx[0] = 0xFF
            self.writecobs(tx)
            rv = self.dev.read_until()
            # now process it
            rv = rv.strip(b' \r\n')
            files = []
            lof = rv.split(b',')
            for f in lof:
                    files.append(f.split(b' '))
            return files

    def __delfile(self, fname):
            if len(fname)>12:
                    print("Filename must be 12 max")
                    return
            tx = bytearray('\x00D\x00\x00\x00', encoding='utf-8')
            tx[0] = 0xFF
            tx[2] = len(fname)
            tx.extend(fname.encode('utf-8'))
            self.writecobs(tx)
            c = self.dev.read(1)
            if c[0] != 0x00:
                    print("File delete failed.")

    def __readfile(self, fname, readlen, offset = 0):
            if len(fname) > 12:
                    print("Filename must be 12 max")
                    return
            if readlen == 0:
                    # special case 0
                    tx = bytearray('\x00R\x00\x00\x00', encoding='utf-8')
                    tx[0] = 0xFF
                    tx[2] = len(fname)
                    tx[3] = 0
                    tx[4] = 0x2
                    tx.extend(fname.encode('utf-8'))
                    self.writecobs(tx)
                    c = self.dev.read(1)
                    if c[0] != 0x00:
                            return None
                    return []
            else:
                    bytesRemain = readlen
                    rb = bytearray()
                    iter = 0
                    while bytesRemain > 0:
                            thisBytes = bytesRemain
                            if thisBytes > 256:
                                    thisBytes = 256
                            tx = bytearray('\x00R\x00\x00\x00', encoding='utf-8')
                            tx[0] = 0xFF
                            tx[2] = len(fname)
                            tx[3] = thisBytes-1
                            tx[4] = 0x1
                            tx.extend(fname.encode('utf-8'))
                            thisOffset = offset + iter*256
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            self.writecobs(tx)
                            # read status
                            st = self.dev.read(1)
                            if st[0] != 0x00:
                                    print("File read failed.")
                                    return
                            # read bytes
                            r = self.dev.read(2)
                            nb = r[0] + (r[1] << 8)
                            d = self.dev.read(nb)
                            rb.extend(d)
                            if nb != thisBytes:
                                    print("EOF reached.")
                                    return rb
                            iter = iter + 1
                            bytesRemain -= thisBytes
                            if iter % 64 == 0:
                                    print(bytesRemain, "/", readlen)
                    return rb                                                        

    # The writefile process has a fair amount of error-checking to allow it to recover
    # from an error. This is because BOOT.BIN files are big, of course, so generally
    # we want to actually run data faster than the FPGA can actually run at easily.
    def __writefile(self, fname, data, offset=0):
            if len(fname) > 12:
                    print("Filename must be 12 max")
                    return
            bytesRemain = len(data)
            totalBytes = bytesRemain
            # special case 0
            if bytesRemain == 0:
                    tx = bytearray('\x00W\x00\x00\x00', encoding='utf-8')
                    tx[0] = 0xFF
                    tx[2] = len(fname)
                    tx[3] = 0
                    tx[4] = 0x2
                    tx.extend(fname.encode('utf-8'))
                    self.writecobs(tx)
                    c = self.dev.read(1)
                    if c[0] != 0x00:
                            print("File create failed.")
                            return
            else:
                    # if offset is 0, we create the file too
                    if offset == 0:
                            tx = bytearray('\x00W\x00\x00\x00', encoding='utf-8')
                            tx[0] = 0xFF
                            tx[2] = len(fname)
                            tx[3] = 0
                            tx[4] = 0x2
                            tx.extend(fname.encode('utf-8'))
                            self.writecobs(tx)
                            c = self.dev.read(1)
                            if c[0] != 0x00:
                                    print("File create failed.")
                                    return
                    iter = 0
                    retryCount = 0
                    # and we need to set timeout too...
                    originalTimeout = self.dev.timeout
                    print("Beginning file upload")
                    self.dev.timeout = 0.1
                    while bytesRemain > 0 and retryCount < 16:
                            thisBytes = bytesRemain
                            if thisBytes > 256:
                                    thisBytes = 256

                            start = 256*iter
                            stop = start + thisBytes

                            tx = bytearray('\x00W\x00\x00\x00',encoding='utf-8')
                            tx[0] = 0xFF
                            tx[2] = len(fname)
                            tx[3] = thisBytes-1
                            tx[4] = 0x5
                            tx.extend(fname.encode('utf-8'))
                            thisOffset = offset + iter*256
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            thisOffset >>= 8
                            tx.append(thisOffset & 0xFF)
                            # re-store
                            thisOffset = offset + iter*256
                            # now checksum...
                            s = sum(data[start:stop]) % 256
                            tx.append(s)
                            tx.extend(data[start:stop])
                            self.writecobs(tx)
                            # wait for ack, which is a single byte
                            c = self.dev.read(1)
                            if c is None or len(c) == 0:
                                    print("Timeout:", bytesRemain, "/", totalBytes)
                                    sleep(0.25)
                                    self.reset()                                        
                                    print("Retrying block", iter)
                                    retryCount = retryCount + 1
                                    continue
                            if c[0] != 0x00:
                                    print("Write failed:", bytesRemain, "/", totalBytes)
                                    sleep(0.25)
                                    self.reset()
                                    print("Retrying block", iter)
                                    retryCount = retryCount + 1
                                    continue
                            else:
                                    b = self.dev.read(4)
                                    if b is None or len(b) < 4:
                                            print("Timeout:", bytesRemain, "/", totalBytes)
                                            sleep(0.25)
                                            self.reset()
                                            print("Retrying block", iter)
                                            retryCount = retryCount + 1
                                            continue
                                    ofs = b[0]
                                    ofs += (b[1] << 8)
                                    ofs += (b[2] << 16)
                                    ofs += (b[3] << 24)
                                    if ofs != thisOffset:
                                            # something went wrong
                                            print("Something went wrong: flushing buffer and retrying")
                                            sleep(0.25)
                                            self.reset()
                                            print("Retrying block", iter)
                                            retryCount = retryCount + 1
                                            continue
                                    # success
                                    retryCount = 0
                            iter = iter + 1
                            bytesRemain -= thisBytes
                            if (iter % 64 == 0):
                                    print(bytesRemain, "/", totalBytes)
                    print("Write complete, restoring timeout")
                    originalTimeout = self.dev.timeout



    # Use to write random cobs-encoded data. For special purposes.
    def writecobs(self, data):
            toWrite = cobs.encode(data)
            self.dev.write(toWrite)
            self.dev.write(b'\x00')                

    # Multiread isn't necessarily supported for all addresses, be careful!
    def multiread(self, addr, num):
            tx = bytearray(self.addrbytes + 1)
            self.__buildaddr(tx, addr)
            # kill the top bit
            tx[0] = tx[0] & 0x7F
            tx[self.addrbytes] = num - 1
            # are we using addressing?
            if self.address is not None:
                    tx.insert(0, self.address)
            toWrite = cobs.encode(tx)
            # print(toWrite)
            self.dev.write(toWrite)
            self.dev.write(b'\x00')
            # expect num+addr bytes back + 1 overhead + 1 framing
            rx = self.dev.read(num + self.addrbytes + 2)
            pk = cobs.decode(rx[:(num+self.addrbytes+2-1)])
            return pk[self.addrbytes:]

    def read(self, addr):
            pk = self.multiread(addr, 4)
            val = pk[0]
            val |= (pk[1] << 8)
            val |= (pk[2] << 16)
            val |= (pk[3] << 24)
            return val

    def multiwrite(self, addr, data):
            self.writeto(addr, data)
            # expect addrbytes + 1 num + 1 overhead + 1 framing
            rx = self.dev.read(self.addrbytes+3)
            pk = cobs.decode(rx[:self.addrbytes+3-1])
            return pk[self.addrbytes]

    def write(self, addr, val):
            tx = bytearray(4)
            tx[0] = val & 0xFF
            tx[1] = (val & 0xFF00)>>8
            tx[2] = (val & 0xFF0000)>>16
            tx[3] = (val & 0xFF000000)>>24
            return self.multiwrite(addr, tx)

    # supes-dangerous, only do this if you KNOW there won't be a response
    def writeto(self, addr, data):
            tx = bytearray(self.addrbytes)
            self.__buildaddr(tx, addr)
            # set top bit in addr for write
            tx[0] |= 0x80
            tx.extend(data)
            # are we using addressing?
            if self.address is not None:
                    tx.insert(0, self.address)
            self.dev.write(cobs.encode(tx))
            self.dev.write(b'\x00')


