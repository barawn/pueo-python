# General common PUEO utility functions
from .bf import bf

train32 = 0xA55A6996
train8 = 0x6A

# This returns either None (incorrect eye value)
# or the number of bit-slips required to match up.
# Training pattern is 0xA55A6996. The bit-slipped
# versions of that are:
# 0xA55A6996 (0 bitslips needed)
# 0x52AD34CB (1 bitslip  needed)
# 0xA9569A65 (2 bitslips needed)
# 0xD4AB4D32 (3 bitslips needed)
# Note that we ALSO need to check all the nybble-rotated
# versions of this
def check_eye(eye_val, bw=32, trainValue=train32):
    testVal = int(eye_val)
    def rightRotate(n, d):
        return (n>>d)|(n<<(bw-d)) & (2 ** bw - 1)
    for i in range(bw):
        if testVal == rightRotate(trainValue, i):
            return i
    return None

