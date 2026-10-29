#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build public parent/filter/CPU-bound child fixtures for task-service gates."""
import hashlib,json,os,pathlib,struct,subprocess
from paths import REPO,HOST,SRC
from c_build_support import normalise
from adfs_fixture import pack,u24,directory,entry,oldcheck
out=REPO/'build/task-service-app';out.mkdir(exist_ok=True);lib=REPO/'build/desktop-c-runtime';cc=REPO/'build/c-toolchain-release/install/bin/gcc'
env=dict(os.environ,HDR_PATH=str(lib/'Hdr'),MACHINE='A440')
def run(cmd,name,cwd=REPO):
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([cc,'-mcpu=arm2','-mapcs-26','-mlibscl','-O2','-fno-builtin','-fno-common','-U__JMP_BUF_SIZE','-nostdinc','-I'+str(lib/'include'),'-S',REPO/'tests/fixtures/TaskServiceClient.c','-o',out/'client.gcc.s'],'compiler')
(out/'client.s').write_text(normalise((out/'client.gcc.s').read_text()))
(out/'entry.s').write_text('        AREA |C$$code|, CODE, READONLY\n        IMPORT ArcLibre_TaskMain\n        EXPORT main\nmain\n        B ArcLibre_TaskMain\n        END\n')
for name,source,cwd in [('filters',REPO/'tests/fixtures/TaskServiceFilters.s',REPO),('client',out/'client.s',REPO),('entry',out/'entry.s',REPO),('jumps',SRC/'ArcLibre/s/SCLJump',REPO),('stubs','clib/s/cl_stub_r',SRC/'RISC_OSLib')]:
 run([HOST/'bin/asasm',*(['-Uppercase','-PreDefine=Apps_Only SETL {TRUE}'] if name=='stubs' else []),'-cpu=ARM2','-apcs','3/26bit','-aof',source,out/(name+'.o')],name,cwd)
run([cc.parent/'drlink','-aif','-map','-symbols',out/'client.symbols','-output',out/'client.aif',out/'stubs.o',out/'filters.o',out/'client.o',out/'entry.o',out/'jumps.o',lib/'gcc-div.o'],'link')
program=(out/'client.aif').read_bytes()
files={'!Run':(b'WimpSlot -min 128k -max 128k\nRun <Obey$Dir>.!RunImage\n',0xffffeb00,0),'!RunImage':(program,0x8000,0x8000)}
from module_image import load_aof
run([HOST/'bin/asasm','-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',REPO/'tests/fixtures/TaskServiceChild.s',out/'child.aof'],'child')
child=load_aof(out/'child.aof')['data'];(out/'child.bin').write_bytes(child)
files['Child']=(child,0x10000,0x10000)
disc=bytearray(819200);offset=0x1400;entries=[]
for name,(data,load,execute) in files.items():
 disc[offset:offset+len(data)]=data;entries.append(entry(name,offset//256,data,load=load,execute=execute));offset+=(len(data)+1023)&~1023
disc[0x400:0xc00]=directory('$',4,[entry('!TaskTest',12,directory=True)],b'Hugo');disc[0xc00:0x1400]=directory('!TaskTest',4,entries,b'Hugo')
u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
name=b'ARCTASK   '
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x41\x42';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511]);(out/'application.adf').write_bytes(disc)
(out/'manifest.json').write_text(json.dumps(dict(sha256=hashlib.sha256(disc).hexdigest(),program_sha256=hashlib.sha256(program).hexdigest(),source='tests/fixtures/TaskServiceClient.c'),indent=2)+'\n')
# Audit the final AIF code, including the host-generated AIF entry sequence.
import re
from aof import read
import inspect_image
code={};veneers=[]
for address,size,area,path in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+R/O code\s+(\S+) from (.+)$',(out/'link.log').read_text(),re.M):
 address,size=int(address,16),int(size,16);o=read(pathlib.Path(path));markers=sorted((s['value'],s['name']) for s in o['symbols'] if s['area']==area and s['name'] in ['$a','$d','$t'])
 for i,(start,tag) in enumerate(markers):
  assert tag!='$t';end=markers[i+1][0] if i+1<len(markers) else size
  if tag=='$a':
   for off in range(start,end,4):code[address+off]=struct.unpack_from('<I',program,address+off-0x8000)[0]
 if area=='Stub$$Entries':veneers=list(range(address,address+size,4))
for pc in range(0x8000,0x8014,4):code[pc]=struct.unpack_from('<I',program,pc-0x8000)[0]
integer=[];fp=[]
for pc,w in sorted(code.items()):
 row=dict(offset=pc-0x8000,source=dict(word=w))
 try:d=inspect_image.decode(w,pc)
 except AssertionError as e:
  assert 'coprocessor instruction' in str(e) and (w>>8)&15 in [1,2] and w>>28!=15
  fp.append(row);continue
 if d['branch'] is not None:assert d['branch'] in code,(hex(pc),hex(w),hex(d['branch']))
 if d['psr'] or d.get('user_bank') and d['kind']=='LDM':assert code[pc+4]==0xe1a00000
 integer.append(dict(row,decoded=d))
(out/'instructions.json').write_text(json.dumps(integer,indent=2)+'\n');(out/'fpa-dependency.json').write_text(json.dumps(fp,indent=2)+'\n')
(out/'runtime-veneers.json').write_text(json.dumps(veneers)+'\n')
# The separate child makes no SWIs inside its busy loop. Audit its code as well
# as the linked parent; it executes in a different Wimp slot at &10000.
o=load_aof(out/'child.aof');end=min(s['value'] for s in o['symbols'] if s['name']=='$d')
decoded=[];child_fp=[]
for off in range(0,end,4):
 w=struct.unpack_from('<I',child,off)[0]
 try:d=inspect_image.decode(w,0x10000+off)
 except AssertionError as e:
  assert 'coprocessor instruction' in str(e) and (w>>8)&15==1 and w>>28==14
  child_fp.append(dict(offset=off,source=dict(word=w)));continue
 assert d['branch'] is None or 0x10000<=d['branch']<0x10000+end
 decoded.append(dict(offset=off,source=dict(word=w),decoded=d))
(out/'child-instructions.json').write_text(json.dumps(decoded,indent=2)+'\n')
(out/'child-fpa-dependency.json').write_text(json.dumps(child_fp,indent=2)+'\n')
assert len(child_fp)==16
