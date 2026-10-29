#!/usr/bin/env python3
"""Generate original test data in the public FileCore D-format. Apache-2.0."""
import hashlib,json,pathlib,struct
from paths import ROOT,REPO,HOST
out=ROOT/'artifacts/disc';out.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def pack(*w):return struct.pack('<'+'I'*len(w),*w)
# Original ARM2 application: ADR r0,message; SWI OS_Write0; MOV r0,#0;
# SWI OS_Exit. It runs at the catalogue's absolute load/entry address &10000.
program=pack(0xe28f0008,0xef000002,0xe3a00000,0xef000011)+b'ARM2 FLOPPY PROGRAM EXECUTED\r\n\0'
files=[('Hello',program,0x10000,0x10000),
       ('Pattern',bytes((i*73+(i>>8)*19+0x35)&255 for i in range(40973)),0xfffffd00,0),
       ('ReadMe',b'Open Archimedes read-only floppy experiment.\r\nOriginal generated test files; no ROM extracts.\r\n',0xffffff00,0)]
disc=bytearray(819200);directory=bytearray(2048)
def u24(b,p,v):b[p:p+3]=v.to_bytes(3,'little')
directory[1:5]=directory[2043:2047]=b'Hugo'
u24(directory,2010,4);directory[2013]=directory[2032]=ord('$')
offset=0xc00;entries=[]
for i,(name,data,load,execute) in enumerate(files):
 p=5+26*i;directory[p:p+len(name)]=name.encode()
 directory[p+10:p+22]=pack(load,execute,len(data));u24(directory,p+22,offset//256);directory[p+25]=0x11
 disc[offset:offset+len(data)]=data;(out/name).write_bytes(data)
 entries.append(dict(name=name,offset=offset,length=len(data),load=load,execute=execute,attributes=0x11,sha256=sha(data)))
 offset=(offset+len(data)+1023)&~1023
# Check byte: original FileCore/Doc/Dirs, confirmed by its CheckDir routine.
acc=0
def step(value):
 global acc
 acc=value^((acc>>13)|((acc<<19)&0xffffffff))
end=5+26*len(files)
for p in range(0,end&~3,4):step(struct.unpack_from('<I',directory,p)[0])
for p in range(end&~3,end):step(directory[p])
for p in range(2008,2044,4):step(struct.unpack_from('<I',directory,p)[0])
directory[2047]=(acc^(acc>>8)^(acc>>16)^(acc>>24))&255
disc[0x400:0xc00]=directory
u24(disc,0,offset//256);u24(disc,256,(len(disc)-offset)//256);u24(disc,252,len(disc)//256)
name=b'ARM2TEST  '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x02\x26';disc[510]=3
for start in (0,256):
 total=carry=0
 for p in range(start+254,start-1,-1):
  value=total+disc[p]+carry;total=value&255;carry=value>>8
 disc[start+255]=total
(out/'arm2-test.adf').write_bytes(disc)
(out/'manifest.json').write_text(json.dumps(dict(format='D',tracks=80,sides=2,sectors_per_track=5,sector_size=1024,first_sector_id=0,root_offset=1024,bytes=len(disc),sha256=sha(disc),free_start=offset,files=entries),indent=2)+'\n')
print('Generated D-format disc',sha(disc))
