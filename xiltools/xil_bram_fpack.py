# we print out things in bytes, starting
# from byte 30 in the frame
def xil_bram_fpack( r ):
    # bits 240-247
    print(hex(r[0]+(r[64]<<2)+(r[32]<<3)+(r[96]<<5)+(r[16]<<6)))
    # bits 248-255
    print(hex(r[80]+(r[48]<<1)+(r[112]<<3)+(r[2]<<4)+(r[66]<<6)+(r[34]<<7)))
    # bits 256-263
    print(hex((r[98]<<1)+(r[18]<<2)+(r[82]<<4)+(r[50]<<5)+(r[114]<<7)))


# f is an array of 372 bytes
def xil_bram_funpack( f ):
    # idx is what's listed in the ll file    
    def access( in_idx, out_idx, f , s ):
        byte = f[int(in_idx/8)]
        bit = (byte >> (idx % 8)) & 0x1
        return bit
q
    # bit 0 240
    # bit 1 372
    # bit 2 252
    # bit 3 384
    # bit 4 264
    # bit 5 396
    # bit 6 276
    # bit 7 408
    r = access(f,240)
    r |= access(f,372)<<1
    r |= access(f,252)<<2
    r |= access(f,384)<<3
    r |= access(f,264)<<4
    r |= access(f,396)<<5
    r |= access(f,276)<<6
    r |= access(f,408)<<7

    
