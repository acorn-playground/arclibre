# SPDX-License-Identifier: Apache-2.0
"""Shared construction of original ADFS test directories and old-map checksums."""
import struct
def pack(*v):return struct.pack('<'+'I'*len(v),*v)
def u24(b,p,v):b[p:p+3]=v.to_bytes(3,'little')
def directory(name,parent,entries,signature):
 b=bytearray(2048);b[1:5]=b[2043:2047]=signature
 u24(b,2010,parent);b[2013:2013+len(name)]=name.encode();b[2032:2032+len(name)]=name.encode()
 for i,e in enumerate(sorted(entries,key=lambda e:e['name'].upper())):
  p=5+i*26;n=e['name'].encode();assert 0<len(n)<=10;b[p:p+len(n)]=n
  b[p+10:p+22]=pack(e['load'],e['execute'],e['length']);u24(b,p+22,e['address']);b[p+25]=e['attributes']
 end=5+len(entries)*26;acc=0
 def step(v,a):return v^((a>>13)|((a<<19)&0xffffffff))
 for p in range(0,end&~3,4):acc=step(struct.unpack_from('<I',b,p)[0],acc)
 for p in range(end&~3,end):acc=step(b[p],acc)
 for p in range(2008,2044,4):acc=step(struct.unpack_from('<I',b,p)[0],acc)
 b[-1]=(acc^(acc>>8)^(acc>>16)^(acc>>24))&255
 return b
def entry(name,address,data=None,directory=False,load=0xffffff00,execute=0):
 return dict(name=name,address=address,length=2048 if directory else len(data),load=load,execute=execute,attributes=0x19 if directory else 0x11)
def oldcheck(b):
 s=c=0
 for v in reversed(b):t=s+v+c;s=t&255;c=t>>8
 return s
