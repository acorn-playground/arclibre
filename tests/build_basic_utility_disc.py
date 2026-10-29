#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Public floppy wrappers which run the ROM's BASIC applications (Chars, Help, Alarm, Calc, Configure)."""
import hashlib,json,pathlib
from adfs_fixture import directory,entry,u24,oldcheck
R=pathlib.Path(__file__).resolve().parents[1];out=R/'build/basic-utility-app';out.mkdir(exist_ok=True)
disc=bytearray(819200);offset=0x3400;roots=[]
for name,address in [('Chars',12),('Help',20),('Alarm',28),('Calc',36),('Configure',44)]:
 data=('Run Resources:$.Apps.!'+name+'.!Run\n').encode();disc[offset:offset+len(data)]=data
 disc[address*256:address*256+2048]=directory('!'+name,4,[entry('!Run',offset//256,data,load=0xffffeb00)],b'Hugo')
 roots.append(entry('!'+name,address,directory=True));offset+=1024
# Files start after the five 2 KiB application directories.
disc[0x400:0xc00]=directory('$',4,roots,b'Hugo')
u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
name=b'ARCBASIC  '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x41\x42';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(out/'applications.adf').write_bytes(disc)
print(hashlib.sha256(disc).hexdigest())
