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
    tap = tio.cinalign.align_rxclk()
    print(f'TURFIO#{tionum} - tap is {tap}')
    print(f'Aligning CIN on TURFIO#{tionum}...')    
    dev.ctl.tio[tionum].train_enable(True)
    tios[tionum] = tio

tioEyes = [ None, None, None, None ]
for i in range(4):
    if tios[i] is not None:
        try:
            eyes = tios[i].cinalign.find_alignment(do_reset=True)        
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
elif len(commonEye):
    usingEye = list(commonEye)[0]

if usingEye is None:
    print("No common eye found???!?")
    sys.exit(1)

print(f'Using eye: {usingEye}')

aligned_turfios = []
for i in range(4):
    if tioEyes[i] is not None:
        eye = (tioEyes[i][usingEye], usingEye)
        print(f'CIN alignment on TURFIO#{i}: tap {eye[0]} offset {eye[1]}')
        # I HATE YOU XILINX WHY DOESN'T THIS WORK CLEANLY
        trials = 0
        ok = False
        while not ok and trials < 1000:
            try:
                tios[i].cinalign.apply_alignment(eye)
                tios[i].cinalign.enable(True)
                dev.ctl.tio[i].train_enable(False)
                ok = True
            except Exception:
                trials = trials + 1
        if trials == 1000:
            print(f'CIN alignment on TURFIO#{i} failed?!?')
        else:
            print(f'CIN aligned and running on TURFIO#{i} after {trials} attempts')
            aligned_turfios.append(tios[i])
            

for tio in aligned_turfios:    
    tio.syncdelay = 8        
    tio.extsync = True
    
dev.trig.runcmd(dev.trig.RUNCMD_SYNC)
for tio in aligned_turfios:
    tio.extsync = False

print(f'TURFIO sync complete')

