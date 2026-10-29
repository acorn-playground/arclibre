"""AOF reader for a single relocatable, fully resolved module area. Apache-2.0.
Derived from the prior independently written inspect_image.py.
"""
import struct
def words(b):return struct.unpack('<'+'I'*(len(b)//4),b)
def load_aof(path):
    b=path.read_bytes();magic,maximum,count=struct.unpack_from('<III',b)
    assert magic==0xc3cbc6c5 and count<=maximum
    chunks={}
    for i in range(maximum):
        name,offset,size=struct.unpack_from('<8sII',b,12+16*i)
        if offset:
            assert offset%4==0 and offset+size<=len(b)
            chunks[name.decode()]=b[offset:offset+size]
    assert len(chunks)==count
    h=words(chunks['OBJ_HEAD']);assert h[0]==0xc5e2d080 and h[1]==310 and h[2]==1
    name,attributes,size,relocs,base=(*h[6:10],0)
    assert attributes & 0x2300==0x2200 and not attributes & (0x10000|0x100000)
    assert relocs==0 and len(chunks['OBJ_AREA'])==size
    strings=chunks['OBJ_STRT']
    def string(n):return strings[n:strings.index(b'\0',n)].decode()
    syms=[]
    assert len(chunks['OBJ_SYMT'])==h[3]*16
    for n,a,v,area in struct.iter_unpack('<IIII',chunks['OBJ_SYMT']):
        assert a&1,'Unresolved external: '+string(n)
        syms.append(dict(name=string(n),attributes=a,value=v,area=area))
    return dict(base=base,size=size,relocations=relocs,symbols=syms,attributes=attributes,data=chunks['OBJ_AREA'])
