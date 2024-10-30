# This contains BOTH the main cratebridge AND the individual link bridges.
# We might want to add crap to allow this module to configure the bridges
# specifically.

from ..common.bf import bf
from ..common.dev_submod import dev_submod

from enum import Enum

class PueoLinkBridge(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)

# TURFIOs get accessed as submodules from here.
class PueoCrateBridge(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.link = [ PueoLinkBridge(self.dev, self.base+(0<<25)),
                      PueoLinkBridge(self.dev, self.base+(1<<25)),
                      PueoLinkBridge(self.dev, self.base+(2<<25)),
                      PueoLinkBridge(self.dev, self.base+(3<<25)) ]
        
        
