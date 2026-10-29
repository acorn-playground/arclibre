#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Public sprite command fixture; no commercial game bytes or ROM resources."""
import hashlib,json,pathlib,struct,subprocess
from paths import REPO,HOST
from adfs_fixture import pack,u24,directory,entry,oldcheck
from module_image import load_aof
import inspect_image
out=REPO/'build/sprite-command-app';out.mkdir(parents=True,exist_ok=True)
obj=out/'client.aof'
subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',str(REPO/'tests/fixtures/SpriteCommandClient.s'),str(obj)],check=True)
o=load_aof(obj);program=o['data'];end=min(s['value'] for s in o['symbols'] if s['name']=='$d')
for p in range(0,end,4):
 d=inspect_image.decode(struct.unpack_from('<I',program,p)[0],p);assert d['branch'] is None or 0<=d['branch']<end
files={'!Run':(b'WimpSlot -min 64k -max 64k\nRun <Obey$Dir>.!RunImage\n',0xffffeb00,0),'!RunImage':(program,0x10000,0x10000)}
sprite=struct.pack('<I12s7I2I',52,b'fixture',0,1,0,31,44,44,12,0xFEDCBA98,0x76543210)
files['Input']=(struct.pack('<3I',1,16,68)+sprite,0xfffff900,0)
(out/'input.sprite').write_bytes(files['Input'][0])
disc=bytearray(819200);offset=0x1400;entries=[]
for name,(data,load,execute) in files.items():
 disc[offset:offset+len(data)]=data;entries.append(entry(name,offset//256,data,load=load,execute=execute));entries[-1]['attributes']=3;offset+=(len(data)+1023)&~1023
disc[0x400:0xc00]=directory('$',4,[entry('!SprTest',12,directory=True)],b'Hugo')
disc[0xc00:0x1400]=directory('!SprTest',4,entries,b'Hugo')
u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
name=b'ARCSPRITE '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x53\x4e';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(out/'application.adf').write_bytes(disc)
(out/'manifest.json').write_text(json.dumps(dict(sha256=hashlib.sha256(disc).hexdigest(),program_sha256=hashlib.sha256(program).hexdigest(),arm2_instructions=end//4),indent=2)+'\n')
