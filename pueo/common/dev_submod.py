# Dumb wrapper to create a submodule in a device with an offset
# base. Used a lot.
# There's probably some simpler way to do this. I have no idea.
# This entire file should probably be named something else.

# property helper
def bitfield(address, start, mask, doc=""): 
    """ Creates a bitfield property: a value at 'address' starting at bit 'start' with bits marked in 'mask' """
    return property(fget=lambda self : (self.read(address) >> start) & mask,
                    fset=lambda self, v : (self.write(address, (self.read(address) & (~(mask<<start))) | ((int(v)&mask)<<start))),
                    doc=doc)

def bitfield_ro(address, start, mask, doc=""):
    """ Read-only bitfield property: a value at 'address' starting at bit 'start' with bits marked in 'mask' """
    return property(fget=lambda self : (self.read(address) >> start) & mask,
                    doc=doc)
    
def register(address, doc=""):
    """ Creates a register property: a 32-bit value at 'address' """
    return property(fget=lambda self : self.read(address),
                    fset=lambda self, v : self.write(address, int(v)),
                    doc=doc)

def register_ro(address, doc=""):
    """ Read only register property: a 32-bit value at 'address' """
    return property(fget=lambda self : self.read(address),
                    doc=doc)

class dev_submod:
    def __init__(self, dev, base):
        self.dev = dev
        self.base = base

    def read(self, addr):
#        print("dev_submod: addr", hex(addr+self.base))
        return self.dev.read(addr + self.base)

    def write(self, addr, val):
        return self.dev.write(addr + self.base, val)
    
    def writeto(self, addr, val):
        return self.dev.writeto(addr + self.base, val)
    
