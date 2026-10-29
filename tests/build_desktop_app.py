#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original application-directory floppy: !Boot, nested Obey and a real ARM2 app."""
import hashlib,json,pathlib,struct
from paths import REPO
from adfs_fixture import pack,u24,directory,entry,oldcheck
out=REPO/'build/desktop-app';out.mkdir(parents=True,exist_ok=True)
disc=bytearray(819200)
# Four actual ARM2 instructions: print the PC-relative message, then OS_Exit.
program=pack(0xe28f0008,0xef000002,0xe3a00000,0xef000011)+b'ARCLIBRE DOUBLE CLICK APPLICATION EXECUTED\r\n\0'
files={
 '!Boot':(b'Set ArcLibre$AppSeen Yes\n',0xffffeb00,0),
 '!Run':(b'WimpSlot -min 64k -max 64k\nObey <Obey$Dir>.Inner\n',0xffffeb00,0),
 'Inner':(b'Run <Obey$Dir>.!RunImage\n',0xffffeb00,0),
 '!RunImage':(program,0x10000,0x10000),
}
offset=0x1400;entries=[];rows=[]
for name,(data,load,execute) in files.items():
 disc[offset:offset+len(data)]=data
 entries.append(entry(name,offset//256,data,load=load,execute=execute))
 rows.append(dict(name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),offset=offset,load=load,execute=execute))
 offset+=(len(data)+1023)&~1023
disc[0x400:0xc00]=directory('$',4,[entry('!ArcTest',12,directory=True)],b'Hugo')
disc[0xc00:0x1400]=directory('!ArcTest',4,entries,b'Hugo')
u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
name=b'ARCLIBRE  '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x41\x29';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(out/'application.adf').write_bytes(disc)
(out/'manifest.json').write_text(json.dumps(dict(sha256=hashlib.sha256(disc).hexdigest(),files=rows),indent=2)+'\n')
print(out/'application.adf')
