# Dumb wrapper to create a submodule in a device with an offset
# base. Used a lot.
# There's probably some simpler way to do this. I have no idea.
# This entire file should probably be named something else.

# property helper
def _property_base(address, bf_params, doc="", signed=False, conversion=None, readonly=False):
    """ Base helper for bitfield/bitfield_ro/register/register_ro. Factored out for less screwups. """
    # we handle conversions in the creation to avoid runtime access costs
    if bf_params is None:
        twid = 0x80000000 if signed else 0
        if conversion is None:
            fget = lambda self : (self.read(address) ^ twid) - twid
            fset = lambda self, v : self.write(address, int(v))
        else:
            fget = lambda self : conversion((self.read(address) ^ twid) - twid, True)
            fset = lambda self, v : self.write(address, conversion(v,False))
    else:
        start = bf_params[0]
        mask = bf_params[1]
        twid = ((mask+1)>>1)*int(signed)        
        if conversion is None:
            fget = lambda self : (((self.read(address) >> start) & mask) ^ twid) - twid
            fset = lambda self, v : (self.write(address, (self.read(address) & (~(mask<<start))) | ((int(v)&mask)<<start)))
        else:
            fget = lambda self : conversion((((self.read(address) >> start) & mask) ^ twid) - twid, True)
            fset = lambda self, v : (self.write(address, (self.read(address) & (~(mask<<start))) | ((conversion(v,False)&mask) << start)))

    if readonly:
        return property(fget=fget,
                        doc=doc)
    else:
        return property(fget=fget,
                        fset=fset,
                        doc=doc)
    

def bitfield(address, start, mask, doc="", signed=False, conversion=None):
    """ Creates a bitfield property: a value at 'address' starting at bit 'start' with bits marked in 'mask' """
    return _property_base(address, (start, mask), doc, signed, conversion, readonly=False)
    
def bitfield_ro(address, start, mask, doc="", signed=False, conversion=None):
    """ Read-only bitfield property: a value at 'address' starting at bit 'start' with bits marked in 'mask' """
    return _property_base(address, (start, mask), doc, signed, conversion, readonly=True)

def register(address, doc="", signed=False, conversion=None):
    """ Creates a register property: a 32-bit value at 'address' """
    return _property_base(address, None, doc, signed, conversion, readonly=False)

def register_ro(address, doc="", signed=False, conversion=None):
    """ Read only register property: a 32-bit value at 'address' """
    return _property_base(address, None, doc, signed, conversion, readonly=True)

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
    
