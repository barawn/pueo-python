import struct
import sys
import time
import hexfile
from .bf import * 

# let's prettify this
try:
    import progressbar2 as pb2
except ImportError:
    pb2 = None

# This pulls out the SPI flash stuff from the old spi.py.
class SPIFlash:
    
    cmd = { 'RES'        : 0xAB ,
            'RDID'       : 0x9F ,
            'WREN'       : 0x06 ,
            'WRDI'       : 0x04 ,
            'RDSR'       : 0x05 ,
            'WRSR'       : 0x01 ,
            '4READ'      : 0x13 , 
	    '3READ'      : 0x03 ,   
            'FASTREAD'   : 0x0B ,
            '4PP'        : 0x12 , 
	    '3PP'        : 0x02 , 
            '4SE'        : 0xDC , 
            '3SE'        : 0xD8 ,
            'BRRD'       : 0x16 , 
            'BRWR'       : 0x17 , 
            'BE'         : 0xC7 }
    
    bits = { 'SPIF'      : 0x80,
             'WCOL'      : 0x40,
             'WFFULL'    : 0x08,
             'WFEMPTY'   : 0x04,
             'RFFULL'    : 0x02,
             'RFEMPTY'   : 0x01 }

    # This needs to take a "dev" that has a "command"
    # function which takes
    # command( val, num_dummy_bytes, num_read_bytes, data_in_bytes )
    # 'val' is a byte which begins the command
    # data_in_bytes is data that gets written after val
    # num_dummy_bytes a number of 0x00 bytes appended after data_in_list
    #   - the return value of these will be dropped
    # num_read_bytes is the number of 0x00 bytes appended after dummy bytes
    #   - the return value of these will be returned
    
    def __init__(self, dev):
        self.dev = dev
        res = self.dev.command(self.cmd['RES'], 3, 1)
        self.electronic_signature = res[0]
        res = self.dev.command(self.cmd['RDID'], 0, 3)
        self.manufacturer_id = res[0]
        self.memory_type = res[1]
        self.memory_capacity = 2**res[2]        
        
    def status(self):
        res = self.dev.command(self.cmd['RDSR'], 0, 1)
        return res[0]
    

    def identify(self):
        print("Electronic Signature: 0x%x" % self.electronic_signature)
        print("Manufacturer ID: 0x%x" % self.manufacturer_id)
        print("Memory Type: 0x%x Memory Capacity: %d bytes" % (self.memory_type, self.memory_capacity))


    def read(self, address, length):
        if self.memory_capacity > 2**24:
            data_in = bytearray()
            data_in.append((address >> 24) & 0xFF)
            data_in.append((address >> 16) & 0xFF)
            data_in.append((address >> 8) & 0xFF)
            data_in.append(address & 0xFF)
            result = self.dev.command(self.cmd['4READ'], 0, length, data_in)
        else:
            data_in = bytearray()
            data_in.append((address >> 16) & 0xFF)
            data_in.append((address >> 8) & 0xFF)
            data_in.append(address & 0xFF)
            result = self.dev.command(self.cmd['3READ'], 0, length, data_in)
        return result 

    # sometimes write enable takes an extra tick
    def write_enable(self):
        enable = self.dev.command(self.cmd["WREN"], 0, 0)
        trials = 0
        while trials < 10:
            res = self.status()
            if not res & 0x2:
                trials = trials + 1
            else:
                return
        raise IOError("Write enable latch did not go high (%d)!" % res)    

    # never seen write disable fail to be immediate
    def write_disable(self):
        disable = self.dev.command(self.cmd["WRDI"], 0, 0)
        res = self.status()
        if res & 0x2:
            raise IOError("Write disable failed (%d)!" % res)

    def program_mcs(self, filename):
        f = hexfile.load(filename)
        # Figure out what sectors we need to erase.
        sector_size = 0
        total_size = 0
        page_size = 256
        if self.memory_capacity == 2**24:
            # this SHOULD be discoverable but eff it
            if self.manufacturer_id == 0x20 and self.memory_type == 0xba:
                sector_size = 64*1024
            else:
                sector_size = 256*1024
            total_size = self.memory_capacity
        elif self.memory_capacity == 2**25:
            sector_size = 256*1024
            total_size = self.memory_capacity
        elif self.memory_capacity == 2**20:
            sector_size = 64*1024
            total_size = self.memory_capacity
        elif self.memory_capacity == 2**22:            
            sector_size = 64*1024
            total_size = self.memory_capacity
        else:
            print("Unknown flash. Add sector size to program_mcs()")
            print("Capacity %d" % self.memory_capacity)
            print("Manufacturer ID %2.2x type %2.2x" %
                  (self.manufacturer_id, self.memory_type))
            return
        erase_sectors = [0]*int(total_size/sector_size)
        sector_list = []
        for seg in f.segments:
            print("Segment %s starts at %d" % (seg, seg.start_address))
            start_sector = int(seg.start_address/sector_size)
            print("This is sector %d" % start_sector)
            if erase_sectors[start_sector] == 0:
                erase_sectors[start_sector] = 1
                sector_list.append(start_sector)
            end_address = seg.end_address
            end_sector = start_sector + 1
            while end_sector*sector_size < seg.end_address:
                if erase_sectors[end_sector] == 0:
                    erase_sectors[end_sector] = 1
                    sector_list.append(end_sector)
                end_sector = end_sector + 1
        # prep the erasebar
        if pb2:
            widgets = [ "Erasing: ",
                        " ", pb2.Percentage(),
                        " ", pb2.GranularBar(),
                        " ", pb2.AdaptiveETA() ]
            erasebar = pb2.ProgressBar( widgets=widgets,
                                        max_value=len(sector_list),
                                        redirect_stdout=True ).start()
            update = lambda v, n : erasebar.update(v)
            finish = erasebar.finish
        else:
            update = lambda v, n : print("Erasing sector %d" % n)
            finish = lambda : None
            
        idx=0
        for erase in sector_list:
            update(idx, erase)
            self.erase(erase*sector_size)
            idx = idx + 1
        finish()

        idx = 1
        maxIdx = len(f.segments)
        for seg in f.segments:
            print("Segment %d/%d" % (idx, maxIdx))
            start = seg.start_address
            end = 0
            tot = 0
            if pb2:
                widgets = [ "Programming: ",
                            " ", pb2.Percentage(),
                            " ", pb2.GranularBar(),
                            " ", pb2.AdaptiveETA() ]
                progbar = pb2.ProgressBar( widgets = widgets,
                                           max_value=seg.size,
                                           redirect_stdout=True).start()
                update = lambda s, e, t : pb2.update(t)
                finish = pb2.finish
            else:
                update = lambda s, e, t : print("Programming %d-%d" % (s, e))
                finish = lambda : None

            while start < seg.start_address + seg.size:
                end = start + page_size
                if end > seg.end_address:
                    end = seg.end_address
                data = seg[start:end].data
                update(start, end, tot)
                self.page_program(start, bytes(data))
                tot += page_size
                start = end
            finish()
            
        self.write_disable()
        print("Complete!")

    def page_program(self, address, data_write = bytearray()):
        # if we're passed a bytes object, this will work
        towrite = bytearray(data_write)
        self.write_enable()
        towrite.insert(0,(address & 0xFF))
        towrite.insert(0,((address>>8) & 0xFF))
        towrite.insert(0,((address>>16) & 0xFF))
        if self.memory_capacity > 2**24:
            towrite.insert(0,((address>>24) & 0xFF))
            self.dev.command(self.cmd["4PP"],0,0,towrite)
        else:
            self.dev.command(self.cmd["3PP"],0,0,towrite)
        trials = 0
        while trials < 10:
            res = self.status()
            # same deal as before
            if not (res & 0x2):
                break
            if res & 0x1:
                break
            trials = trials + 1
        if trials == 10:
            print("START TIMED OUT!!")
            self.write_disable()
            return
        trials = 0
        while res & 0x1:
            res = self.status()
            trials = trials + 1

    def erase(self, address):
        self.write_enable()
        if self.memory_capacity > 2**24:
            data = bytearray()
            data.append((address >> 24) & 0xFF)
            data.append((address >> 16) & 0xFF)
            data.append((address >> 8) & 0xFF)
            data.append((address & 0xFF))
            erase = self.dev.command(self.cmd["4SE"], 0, 0, data)
        else:
            data = bytearray()
            data.append((address>>16) & 0xFF)
            data.append((address>>8) & 0xFF)
            data.append((address & 0xFF))
            erase = self.dev.command(self.cmd["3SE"], 0, 0, data)
        res = self.status()
        print("Checking for erase start...")
        trials = 0
        while trials < 10:
            res = self.status()
            trials = trials + 1
            # Before the erase command, we know that the bottom 2 bits
            # are 0b10.
            # After the erase command is issued, we can have:
            # -> 00   (sector erase completed)
            # -> 11   (sector erase in progress)
            # So we look for EITHER bit 2 NOT set or bit 1 set
            # If both of them are clear, it'll jump through the
            # erase complete right away.
            if not (res & 0x2):
                break
            if res & 0x1:
                break
        if trials == 10:
            print("START TIMED OUT!!")
            self.write_disable()
            return
        print("Erase started. Waiting for erase complete...")
        trials = 0
        while res & 0x1:
            res = self.status()
            trials = trials + 1
        print("Erase complete after %d trials." % trials)

    def write_bank_address(self, bank):
        if self.memory_capacity > 2**24:
            return
        bank_write = self.dev.command(self.cmd["BRWR"], 0, 0, bytes([ bank ]))
        return bank_write 	
	

    def read_bank_address(self):
        if self.memory_capacity > 2**24:
            res = []
            res.append(0)
            return res
        bank_read = self.dev.command(self.cmd["BRRD"], 0, 1)
        return bank_read
	
	
	
	
	
