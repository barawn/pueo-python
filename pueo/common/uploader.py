from .bf import bf
import struct
import os

pb2 = None
uwidgets = None
make_bar = None
try:
    import progressbar2 as pb2
    uwidgets = [ "Uploading: ",
                 " ", pb2.Percentage(),
                 " ", pb2.GranularBar(),
                 " ", pb2.AdaptiveETA() ]
    make_bar = lambda x, w : pb2.ProgressBar(widgets=w, max_value=x, redirect_stdout=True)
except ImportError:
    pass

if pb2 is None:
    try:
        import progressbar as pb2
        uwidgets = [ "Uploading: ",
                     " ", pb2.Percentage(),
                     " ", pb2.Bar(),
                     " ", pb2.AdaptiveETA() ]
        make_bar = lambda x, w : pb2.ProgressBar(widgets=w, maxval=x)
    except ImportError:
        pass
    

class Uploader:
    BANKLEN = 49152
    
    """
    Handles the upload logic for interacting with SURFs.
    You just need to pass it a function for writing
    fwupd data and a function for setting marks.

    It does NOT do:
    1. bank tracking
    2. putting/exiting SURFs in download mode
    """
    def __init__(self,
                 fwupd_func,
                 mark_func):
        self.fwupd = fwupd_func
        self.mark = mark_func
                 
    @staticmethod
    def fwupdHeader(fn, size):
        """
        generates a header for a PYFW upload.
        there's another header for a PYEX upload.
        will implement that soon.
        """
        hdr = bytearray(b'PYFW')
        flen = size
        hdr += struct.pack(">I", flen)
        hdr += fn.encode()
        hdr += b'\x00'
        hdr += (256 - (sum(hdr) % 256)).to_bytes(1, 'big')
        return (hdr, flen)
            
    def upload(self, surf, fn, destfn=None, bank=0, verbose=False):
        """
        Uploads a file via the commanding path.
        This will ONLY WORK if:
        1. the SURFs are fully set up/enabled
        2. they are in eDownloadMode (pyfwupd running, firmware_loading bit set)
        3. you know what bank you're on. If you've just put them freshly into
           eDownloadMode, it's bank 0. If you're uploading multiple files,
           you need to track which bank this function returns after each file.
        """
        if not isinstance(surf, list):
            surf = [surf]
        # If you don't give me a new destination, it's going
        # in /home/root.
        if not destfn:
            destfn = '/home/root' + os.path.basename(fn)
        # ALL OF THIS could be done ahead of time, like you
        # literally break the entire file up into bank chunks.
        # WHATEVER.
        if not os.path.isfile(fn):
            raise ValueError("%s is not a regular file" % fn)
        hdr, flen = self.fwupdHeader(destfn, os.path.getsize(fn))
        toRead = self.BANKLEN - len(hdr)
        toRead = flen if flen < toRead else toRead
        print("Uploading %s to %s" % (fn, destfn))
        # these are here to make the loop work
        d = hdr
        written = 0

        if pb2:
            uploadbar = make_bar(flen, uwidgets).start()
            update = lambda v, n : uploadbar.update(v)
            finish = uploadbar.finish
        else:
            update = lambda v, n : print("%d/%d" % (v, n))
            finish = lambda : None
            
        with open(fn, "rb") as f:
            while written < flen:
                if verbose:
                    print("%s -> %s : writing %d bytes into bank %d, %d/%d written" %
                          (fn, destfn, toRead, bank, written, flen))
                d += f.read(toRead)
                padBytes = (4-(len(d) % 4)) if (len(d) % 4) else 0
                d += padBytes*b'\x00'
                fmt = ">%dI" % (len(d) // 4)
                il = struct.unpack(fmt, d)
                # check to see if that bank is ready
                testIdx = bank + 14
                for s in surf:
                    rv = bf(s.read(0xC))
                    while not rv[testIdx]:
                        rv = bf(s.read(0xC))
                for val in il:
                    self.fwupd(val)
                self.mark(bank)
                bank = bank ^ 1
                update(written, flen)
                written += toRead
                remain = flen - written
                toRead = remain if remain < self.BANKLEN else self.BANKLEN
                # empty d b/c we add to it above
                d = b''
        finish()
        return bank
    
    
