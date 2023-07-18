# Dumb wrapper to create a submodule in a device with an offset
# base. Used a lot.
# There's probably some simpler way to do this. I have no idea.

class dev_submod:
    def __init__(self, dev, base):
        self.dev = dev
        self.base = base

    def read(self, addr):
        return self.dev.read(addr + self.base)

    def write(self, addr, val):
        return self.dev.write(addr + self.base, val)
    
