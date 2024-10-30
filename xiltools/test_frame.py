from xil_process_frame import xil_process_frame

f = open("frame","r")
lines = f.readlines()
fr = []
for line in lines:
    i = int(line,16)
    # swizzle the 32-bit order, it's wrong-endian
    fr.append((i>>24)&0xFF)
    fr.append((i>>16)&0xFF)
    fr.append((i>>8)&0xFF)
    fr.append(i & 0xFF)

r = xil_process_frame(fr)
for b in r:
    print(hex(b))
    
