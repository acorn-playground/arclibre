#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original writable D-format medium for real desktop file operations."""
import hashlib,json,pathlib
from adfs_fixture import pack,u24,directory,entry,oldcheck
root=pathlib.Path(__file__).resolve().parents[1];out=root/'build/filer-action-disc';out.mkdir(exist_ok=True)
disc=bytearray(819200);payload=bytes((i*53+(i>>8)*17+0x31)&255 for i in range(32791))
disc[0x1400:0x1400+len(payload)]=payload
files=[entry('CopyMe',0x14,payload),entry('Dest',12,directory=True)]
disc[0x400:0xc00]=directory('$',4,files,b'Hugo');disc[0xc00:0x1400]=directory('Dest',4,[],b'Hugo')
offset=(0x1400+len(payload)+1023)&~1023;u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
name=b'ACTTEST   '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x41\x29';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(out/'actions.adf').write_bytes(disc);(out/'CopyMe').write_bytes(payload)
(out/'manifest.json').write_text(json.dumps(dict(sha256=hashlib.sha256(disc).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest(),length=len(payload)),indent=2)+'\n')
