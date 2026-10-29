# SPDX-License-Identifier: Apache-2.0
"""Strict little-endian AOF 3.10 reader for C/assembler link verification."""
import struct

def read(path):
 b=path.read_bytes();magic,maximum,count=struct.unpack_from('<III',b)
 assert magic==0xc3cbc6c5 and count<=maximum
 chunks={}
 for i in range(maximum):
  name,offset,size=struct.unpack_from('<8sII',b,12+16*i)
  if offset:
   assert offset%4==0 and offset+size<=len(b)
   chunks[name.decode()]=b[offset:offset+size]
 assert len(chunks)==count
 h=struct.unpack('<'+'I'*(len(chunks['OBJ_HEAD'])//4),chunks['OBJ_HEAD']);assert h[:2]==(0xc5e2d080,310) and len(h)==6+5*h[2]
 strings=chunks['OBJ_STRT']
 def string(n):return strings[n:strings.index(0,n)].decode()
 areas=[];pos=0
 for i in range(h[2]):
  n,attributes,size,nrelocs,base=h[6+i*5:11+i*5]
  data=b'\0'*size if attributes&0x1000 else chunks['OBJ_AREA'][pos:pos+size]
  assert len(data)==size
  if not attributes&0x1000:pos+=size
  relocs=[dict(offset=o,flags=f) for o,f in struct.iter_unpack('<II',chunks['OBJ_AREA'][pos:pos+nrelocs*8])];assert len(relocs)==nrelocs;pos+=nrelocs*8
  areas.append(dict(name=string(n),attributes=attributes,size=size,base=base,data=data,relocations=relocs))
 assert pos==len(chunks['OBJ_AREA'])
 syms=[dict(name=string(n),attributes=a,value=v,area=string(ar) if ar else '') for n,a,v,ar in struct.iter_unpack('<IIII',chunks.get('OBJ_SYMT',b''))];assert len(syms)==h[3]
 return dict(areas=areas,symbols=syms)
