# this script assumes you're talking to the TURF via Ethernet
# ONLY DO THIS SCRIPT IF THE TURF STARTUP STATE MACHINE IS NOT DOING IT
#
# These commands CANNOT be repeated!! They're once-and-done!

from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--turfio", type=str, default="0,1,2,3",
                    help="comma-separated list of TURFIOs to initialize")

args = parser.parse_args()
validTios = [0,1,2,3]
tioList = list(map(int,args.turfio.split(',')))
for tio in tioList:
    if tio not in validTios:
        print("TURFIOs can only be one of", validTios)
        sys.exit(1)

dev = PueoTURF(None, 'Ethernet')

tios = [ None, None, None, None ]
for tionum in tioList:
    print(f'Trying to initialize TURFIO#{tionum}')
    if not (dev.aurora.linkstat(tionum) & 0x1):
        print(f'Lane not up, skipping??')
        continue
    tio = PueoTURFIO((dev, tionum), 'TURFGTP')
    tio.program_sysclk(tio.ClockSource.TURF)
    while not ((tio.read(0xC) & 0x1)):
        print(f'Waiting for clock on TURFIO#{tionum}...')
    print(f'Aligning RXCLK->SYSCLK transition on TURFIO#{tionum}...')
    tap = tio.calign[0].align_rxclk()
    print(f'TURFIO#{tionum} - tap is {tap}')
    print(f'Aligning CIN on TURFIO#{tionum}...')    
    dev.ctl.tio[tionum].train_enable(True)
    tios[tionum] = tio

tioEyes = [ None, None, None, None ]
for i in range(4):
    if tios[i] is not None:
        try:
            eyes = tios[i].calign[0].find_alignment(doReset=True)        
        except IOError:
            print(f'Alignment failed on TURFIO#{i}, skipping')
            continue
        print(f'CIN alignment found eyes: {eyes}')
        tioEyes[i] = eyes

print("Eyes found, processing to find a common one:")
commonEye = None
for d in tioEyes:
    if d is not None:
        commonEye = d.keys() if commonEye is None else commonEye & d.keys() 
print(f'Common eye[s]: {commonEye}')
usingEye = None
if len(commonEye) > 1:
    print(f'Multiple common eyes found, choosing the one with smallest delay')
    test_turfio = None
    for i in range(4):
        if tioEyes[i] is not None:
            test_turfio = tioEyes[i]
            break
    min = None
    minEye = None
    for eye in commonEye:
        if minEye is None:
            min = test_turfio[eye]
            minEye = eye
            print(f'First eye {minEye} has tap {min}')
        else:
            if test_turfio[eye] < min:
                min = test_turfio[eye]
                minEye = eye
                print(f'New eye {minEye} has smaller tap {min}, using it')
    usingEye = minEye
else:
    usingEye = list(commonEye)[0]
    
print(f'Using eye: {usingEye}')

enabled_turfios = []
for i in range(4):
    if tioEyes[i] is not None:
        eye = (tioEyes[i][usingEye], usingEye)
        print(f'CIN alignment on TURFIO#{i}: tap {eye[0]} offset {eye[1]}')
        tios[i].calign[0].apply_alignment(eye)
        dev.ctl.tio[i].train_enable(False)
        tios[i].syncdelay = 9 if usingEye == 0 else 8
        tios[i].extsync = True
        enabled_turfios.append(tios[i])
        print(f'CIN is running on TURFIO#{i}')
    
dev.trig.runcmd(dev.trig.RUNCMD_SYNC)
for tio in enabled_turfios:
    tio.extsync = False

print(f'TURFIO sync complete')

