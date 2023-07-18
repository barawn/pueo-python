# General common PUEO utility functions

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
def check_eye(eye_val):
    trainValue = 0xA55A6996
    testVal = int(eye_val)
    def rightRotate(n, d):
        return (n>>d)|(n<<(32-d)) & 0xFFFFFFFF
    for i in range(32):
        if testVal == rightRotate(trainValue, i):
            return i
    return None
