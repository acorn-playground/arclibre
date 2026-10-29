#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the pinned Squash SWI implementation, retaining its original wrapper."""
import hashlib,json,os,pathlib,re,shutil,struct,subprocess
from paths import REPO,SRC,HOST
from c_build_support import normalise
ROOT=REPO/'build/squash-runtime';ROOT.mkdir(exist_ok=True)
for row in json.loads((REPO/'manifests/desktop-utility-inputs.json').read_text()):
 if row['component']=='Squash':assert hashlib.sha256((SRC/'Squash'/row['path']).read_bytes()).hexdigest()==row['sha256'],row
CC=REPO/'build/c-toolchain-release/install/bin/gcc'
work=ROOT/'work';shutil.copytree(SRC/'Squash',work,dirs_exist_ok=True)
inc=ROOT/'include';shutil.copytree(REPO/'build/desktop-c-runtime/include',inc,dirs_exist_ok=True)
for p in (SRC/'Squash/h').iterdir():shutil.copy2(p,inc/(p.name+'.h'))
hdr=ROOT/'Hdr';shutil.copytree(REPO/'build/desktop-c-runtime/Hdr',hdr,dirs_exist_ok=True)
env=dict(os.environ,HDR_PATH=str(hdr),MACHINE='A440')
def run(cmd,name,cwd=REPO):
 with (ROOT/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
objects=[];object_proofs=[]
def assemble(name,source,cwd,upper=False):
 hashes=[];obj=ROOT/(name+'.o')
 for attempt in range(2):
  target=obj if attempt==0 else ROOT/(name+'.repeat.o')
  run([HOST/'bin/asasm',*(['-Uppercase'] if upper else []),'-cpu=ARM2','-apcs','3/26bit','-aof',source,target],name+'-'+str(attempt),cwd)
  hashes.append(hashlib.sha256(target.read_bytes()).hexdigest())
 assert hashes[0]==hashes[1]
 objects.append(obj);object_proofs.append(dict(name=name,sha256=hashes[0],identical_assemblies=2))
flags=['-mcpu=arm2','-mapcs-26','-mmodule','-mlibscl','-mno-apcs-stack-check','-Os','-fno-builtin','-fno-common','-funsigned-char','-nostdinc','-I'+str(inc)]
for name in ['compress','cssr','trial','zssr']:
 raw=ROOT/(name+'.gcc.s');run([CC,*flags,'-S','-x','c',pathlib.Path('src/Squash/c')/name,'-o',raw],name+'-cc')
 # GCC's APCS-26 returns need the same ARM2 PSR settling slot as the
 # hand-written sources. Do not alter prologues or emitted calculations.
 generated=ROOT/(name+'.s');code=normalise(raw.read_text())
 code=re.sub(r'(^\t(?:ldm[^\n]*\^|movs\tpc, lr)[^\n]*\n)',r'\1\tmov\tr0, r0 ; ARM2 status settling\n',code,flags=re.M)
 generated.write_text(code)
 assemble(name,generated,REPO)
for name in ['comp_ass','mr_module','statics','zcat_ass12']:
 assemble(name,'s/'+name,work,True)
(ROOT/'inputs.json').write_text(json.dumps(dict(objects=[str(p.relative_to(REPO)) for p in objects],object_proofs=object_proofs,compiler_sha256=hashlib.sha256(CC.read_bytes()).hexdigest(),flags=flags,source_manifest_sha256=hashlib.sha256((REPO/'manifests/desktop-utility-inputs.json').read_bytes()).hexdigest()),indent=2)+'\n')
data=(SRC/'Squash/Resources/UK/Messages').read_bytes();name=b'Resources.Squash.Messages\0';name+=bytes(-len(name)%4)
resource=struct.pack('<5I',24+len(name)+((len(data)+3)&~3),0xffffff00,0,len(data),3)+name+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)+bytes(4)
(ROOT/'resources.bin').write_bytes(resource)
print('Squash objects assembled')
