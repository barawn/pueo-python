import numpy as np

# waveform trigger processing
# this is a horrible mess and just hardcoded stuff so of course we have them
# in like 10 different locations

LOWPASS = [ -23, 0, 105, 0, -263, 0, 526, 0, -949, 0, 1672, 0, -3216, 0, 10342,
            16384, 10342, 0, -3216, 0, 1672, 0, -949, 0, 526, 0, -263, 0, 105,
            0, -23 ]

MATCHED1500 = [ -1, 0, 0, 1, 0, -1, 0, 1,
                1, -1, -1, 1, 1, -1, -2, 2,
                0, -4, 4, -2, 1 ]

LEFT_BEAMS = [ [19, 21, 23],
               [9, 9, 9],
               [17, 18, 20],
               [1, 0, 0],
               [0, 2, 5],
               [13,14,15],
               [11,11,12] ]
RIGHT_BEAMS = [ [16,18,20],
                [10,10,10],
                [15,16,18],
                [1,0,0],
                [0,2,5],
                [14,15,16],
                [12,12,13] ]
TOP_BEAMS = [ [0,1],
              [0,0],
              [2,0],
              [0,2],
              [1,0] ]

FULL_BEAMS = [ [1,1,3],
               [1,1,3],
               [1,1,0],
               [1,1,0],
               [1,1,0],
               [1,1,1],
               [1,1,1],
               [6,6,3],
               [6,6,3],
               [6,6,0],
               [6,6,1],
               [6,6,1],
               [6,6,4],
               [6,6,4],
               [5,5,3],
               [5,5,0],
               [5,5,0],
               [5,5,1],
               [5,5,4],
               [5,5,4],
               [2,2,3],
               [2,2,0],
               [2,2,1],
               [2,2,1],
               [2,2,4],
               [2,2,4],
               [2,2,2],
               [0,0,0],
               [0,0,1],
               [0,0,1],
               [0,0,4],
               [0,0,2],
               [0,0,2],
               [3,3,255],
               [3,3,255],
               [3,3,255],
               [3,3,255],
               [3,3,255],
               [3,3,255],
               [3,3,255],
               [4,4,255],
               [4,4,255],
               [4,4,255],
               [4,4,255],
               [4,4,255],
               [4,4,255]]

LEFT_OFFSETS = [
		4,
		5,
		4,
		3,
		3,
		2,
		0,
		4,
		4,
		4,
		3,
		3,
		2,
		0,
		4,
		3,
		4,
		3,
		3,
		2,
		0,
		1,
		2,
		2,
		1,
		2,
		1,
		0,
		0,
		1,
		1,
		1,
		1,
		1,
		0,
		3,
		2,
		1,
		0,
		0,
		0,
		0,
		3,
		2,
		1,
		0,
		0,
		0 ]

RIGHT_OFFSETS = [
    		0,
		2,
		2,
		2,
		3,
		3,
		2,
		0,
		1,
		2,
		2,
		3,
		3,
		2,
		0,
		0,
		2,
		2,
		3,
		3,
		2,
		0,
		2,
		3,
		3,
		5,
		5,
		5,
		0,
		2,
		3,
		4,
		5,
		6,
		6,
		0,
		0,
		0,
		0,
		1,
		2,
		3,
		0,
		0,
		0,
		0,
		1,
		2 ]

BEAM_ELEVATION = [
    -0.618536823,
    -1.431745801,
    -0.816764725,
    0.047434886,
    -0.723349906,
    -1.361324759,
    -0.372703409,
    -4.058857064,
    -3.571098459,
    -4.195939901,
    -4.013145912,
    -4.832213359,
    -4.280256441,
    -3.404280805,
    -7.985148806,
    -6.802217939,
    -8.092925602,
    -7.87915161,
    -8.689908024,
    -8.086296087,
    -7.148243189,
    -10.36460555,
    -11.69136552,
    -12.34856709,
    -11.39508865,
    -13.03243407,
    -12.88484564,
    -12.80331857,
    -13.8650172,
    -15.14933639,
    -15.08687971,
    -14.85797905,
    -15.74080468,
    -16.53589059,
    -16.83824906,
    3.933716425,
    3.933716425,
    3.933716425,
    3.933716425,
    3.933716425,
    3.933716425,
    3.933716425,
    -20.05473896,
    -20.05473896,
    -20.05473896,
    -20.05473896,
    -20.05473896,
    -20.05473896
]

BEAM_AZIMUTH = [
    -21.6666423,
    -11.46061837,
    -1.273150048,
    7.702483132,
    16.20552732,
    26.30672175,
    35.90833494,
    -22.39017937,
    -12.45465574,
    -1.867582083,
    8.50622514,
    17.08951516,
    28.06320353,
    38.12226143,
    -22.95594524,
    -12.22500678,
    -2.489631553,
    7.864538304,
    16.45367149,
    27.39339514,
    37.39931781,
    -24.6893924,
    -12.68605744,
    -1.925715275,
    7.275900201,
    17.38145415,
    26.29699552,
    37.75218894,
    -25.33077606,
    -12.65289961,
    -2.702652354,
    8.200937324,
    17.2125362,
    27.99528818,
    37.19298104,
    -22.46417748,
    -11.92987459,
    -2.048168429,
    7.550071073,
    17.14831057,
    27.03001673,
    37.56431962,
    -24.53980803,
    -13.1922653,
    -2.649826313,
    7.550071073,
    17.74996846,
    28.29240745
]

def downsample(d, both=False):
    """
    Do the downsample step of the trigger. Pass an ndarray or something that can become an ndarray.
    If called with both=True, returns a tuple of (lowpass, decimated). Otherwise just the decimated.
    """
    lowpass = np.round(np.convolve(d, LOWPASS,'same')/32768.)
    decim = lowpass[::2]
    return (lowpass, decim) if both else decim

def match_filter(d):
    """
    Do the match filter step of the trigger. Pass an ndarray or something that can become an ndarray.
    """
    m = np.round(np.convolve(d, MATCHED1500, 'same')/32.)
    return m

def upsample(d):
    """
    Performs the upsample step of the trigger. Pass an ndarray or something that can become an ndarray.
    """
    ups = np.array(d).repeat(2)
    ups[::2] = 0
    ups = np.round(np.convolve(ups, LOWPASS, 'same')/16384.)
    return ups

def full_chain(d, rms=None,real_values=True):
    """
    Performs the full trigger chain on a channel.
    If RMS is provided, use that, otherwise calculate from first 64 samples.
    If real_values=False, returns in representation values, otherwise true values.
    """
    downsampled = downsample(d)
    matched = match_filter(downsampled)
    upsampled = upsample(matched)
    if not rms:
        rms = np.std(upsampled[0:64])
    fivebit = agc(upsampled, rms, real_values=real_values)
    return fivebit

def agc(d, rms, real_values=True):
    """
    Performs the AGC/bit reduction step of the trigger. Pass the scaling (rms).
    If called with real_values=False, returns the integer representations. Otherwise
    returns real values in sigma (RMS) units.
    """
    represent = np.clip(np.floor(d/(rms/4)), a_min=-16, a_max=15)
    true_values = (represent+0.5)/4
    return true_values if real_values else represent

def sub_beams(d, beams, real_values=True, offset=32):
    """
    Calculates the sub-beams from the trigger.
    Offset determines where our new t=0 is. By default 32.
    If real_values=False, if this is a 2-length beam (top sub-beams)
    this adds in the correction. Otherwise it just adds zero because it's already
    in real values.
    """
    bb = []
    this_len = len(d[0])
    new_len = this_len - offset
    third_addend = d[2] if len(beams[0]) > 2 else np.full((new_len),0 if real_values else 4)
    for b in beams:
        start = [offset-b[0], offset-b[1], offset-b[2] if len(b) > 2 else 0]
        bb.append( d[0][start[0]:start[0]+new_len] +
                   d[1][start[1]:start[1]+new_len] +
                   third_addend[start[2]:start[2]+new_len] )
    return bb

def beams(lb, rb, tb, real_values=True, offset=32):
    """
    Calculates the full beams from the sub-beams.
    Offset determines where our new t=0 is. By default 32.
    If real_values=False, adds in the correction for the
    6-channel beams. Otherwise just adds zero.    
    """
    bb = []
    this_len = len(lb[0])
    new_len = this_len - offset
    for i in range(len(FULL_BEAMS)):
        b = FULL_BEAMS[i]
        left_start = offset-LEFT_OFFSETS[i]
        right_start = offset-RIGHT_OFFSETS[i]
        top_start = offset if b[2] < len(tb) else 0
        third_addend = tb[b[2]] if b[2] < len(tb) else np.full((new_len),0 if real_values else 3)
        bb.append( lb[b[0]][left_start:left_start+new_len] +
                   rb[b[1]][right_start:right_start+new_len] +
                   third_addend[top_start:top_start+new_len] )
    return bb

def beamify(channels):
    """
    Pass 8 channels in SURF order and this function returns the trigger beam waveforms.
    Units are always 0.25*rms.
    """
    dd = []
    for c in channels:
        dd.append(full_chain(c,real_values=False))
    lb = sub_beams([dd[5],dd[6],dd[7]], LEFT_BEAMS, real_values=False)
    rb = sub_beams([dd[1],dd[2],dd[3]], RIGHT_BEAMS, real_values=False)
    tb = sub_beams([dd[0],dd[4]], TOP_BEAMS, real_values=False)
    b = beams(lb, rb, tb, real_values=False)
    return b        
    

def envelope(beams):
    e = []
    for b in beams:
        e.append(np.convolve(np.square(b),[1]*8, 'same')[::4])
    return e


