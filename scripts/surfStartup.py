from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO
from pueo.surf import PueoSURF
import time
import sys
from itertools import chain

# WHATEVER JUST HARDCODE THIS FOR NOW
surfList = [ (0, 0) ]

dev = PueoTURF(None, 'Ethernet')
tio = {}
masks = {}
for surfAddr in surfList:
    if surfAddr[0] not in tio:
        print(f'Building TURFIO#{surfAddr[0]}')
        tio[surfAddr[0]] = PueoTURFIO((dev, surfAddr[0]), 'TURFGTP')
        print(f'TURFIO#{surfAddr[0]} : {tio[surfAddr[0]]}')
        masks[surfAddr[0]] = 0
    masks[surfAddr[0]] |= (1<<(surfAddr[1]+16))

for m in masks:
    print(f'mask {m} is {hex(masks[m])}')
    
# enable autotrain for the enabled SURFs
for n in tio:
    print(f'Setting TURFIO#{n} autotrain to {hex(masks[n])}')
    tio[n].surfturf.write(0x14, masks[n])

# enable RXCLK for the TURFIOs containing the SURFs
for t in tio.values():
    print(f'Enabling RXCLK on {t}')
    t.enable_rxclk(True)

surfActiveList = []
for surfAddr in surfList:
    tn = surfAddr[0]
    sn = surfAddr[1]
    # wait for train out rdy on each
    print(f'Waiting for train out rdy on SURF#{sn} on TURFIO#{tn}')
    loopno = 0
    while not(tio[tn].surfturf.read(0x18) & (1<<sn)) and loopno < 20:
        time.sleep(0.1)
    if loopno == 20:
        print(f'SURF#{sn} on TURFIO#{tn} did not become ready??')
    else:
        print(f'SURF#{sn} on TURFIO#{tn} is ready for out training')
        tio[tn].dalign[sn].train_enable = 0
        surfActiveList.append(surfAddr)

# dumbass hackery, since sync_offset should be constant
for surfAddr in surfActiveList:
    tn = surfAddr[0]
    sn = surfAddr[1]
    t = tio[tn]
    print(f'Applying sync offset to SURF#{sn} on TURFIO#{tn}')
    s = PueoSURF((t, sn), 'TURFIO')
    s.sync_offset = 7
    
print("Issuing SYNC")
dev.trig.runcmd(dev.trig.RUNCMD_SYNC)

# We should be able to COMPLETELY align the entire
# payload the same, because the only variation should come
# from slot in crate....
# this might be wrong because of left/right issues

# we need a blank starting point
surfEyes = []
for i in range(4):
    stio = []
    for j in range(7):
        stio.append(None)
    surfEyes.append(stio)

# Find ALL the eyes
for surfAddr in surfActiveList:
    tn = surfAddr[0]
    sn = surfAddr[1]
    t = tio[tn]
    print(f'Finding DOUT alignment on SURF#{sn} on TURFIO#{tn}:')
    try:
        eyes = t.dalign[sn].find_alignment(do_reset=True, verbose=True)
    except IOError:
        print(f'DOUT alignment failed on SURF#{sn} on TURFIO#{tn}, skipping')
        continue
    print(f'DOUT alignment found eyes: {eyes}')
    surfEyes[tn][sn] = eyes

print('Eyes found, processing to find a common one.')
commonEye = None
for d in list(chain(*surfEyes)):
    if d is not None:
        commonEye = d.keys() if commonEye is None else commonEye & d.keys()

print(f'Common eye[s]: {commonEye}')
usingEye = None
if len(commonEye) > 1:
    print(f'Multiple common eyes found, choosing the one with smallest delay')
    test_surf = None
    for i in range(4):
        for j in range(7):
            if surfEyes[i][j] is not None:
                test_surf = surfEyes[i][j]
    min = None
    minEye = None
    for eye in commonEye:
        if minEye is None:
            min = test_surf[eye]
            minEye = eye
            print(f'First eye {minEye} has tap {min}')
        else:
            if test_surf[eye] < min:
                min = test_surf[eye]
                minEye = eye
                print(f'New eye {minEye} has smaller tap {min}, using it')
    usingEye = minEye
elif len(commonEye):
    usingEye = list(commonEye)[0]

for i in range(4):
    for j in range(7):
        if surfEyes[i][j] is not None:
            eye = (surfEyes[i][j][commonEye], commonEye)
            tio[i].dalign[j].apply_alignment(eye)
    
print("Issuing NOOP_LIVE")
dev.trig.runcmd(dev.trig.RUNCMD_NOOP_LIVE)

#for surfAddr in trainedSurfs:
#    tn = surfAddr[0]
#    sn = surfAddr[1]
#    t = tio[tn]
#    print(f'Unmasking data from SURF#{sn} on TURFIO#{tn}')
#    t.dalign[sn].enable = 1

