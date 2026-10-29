#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the original cleaned-3.60 Edit and ResourceFiler cohort."""
import hashlib,json,os,shutil,struct,subprocess
from paths import REPO,SRC,HOST
from c_build_support import normalise
from module_image import load_aof
ROOT=REPO/'build/desktop-apps';ROOT.mkdir(exist_ok=True)
for r in json.loads((REPO/'manifests/desktop-app-inputs.json').read_text()):
 b=(SRC/r['component']/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r
CC=REPO/'build/c-toolchain-release/install/bin/gcc'
inc=ROOT/'include';shutil.copytree(REPO/'build/desktop-c-runtime/include',inc,dirs_exist_ok=True)
for p in (SRC/'EditApp/h').iterdir():
 for n in [p.name+'.h','h.'+p.name]:shutil.copy2(p,inc/n)
env=dict(os.environ,HDR_PATH=str(REPO/'build/desktop-c-runtime/Hdr'),MACHINE='A440')
def save(n,v):(ROOT/n).write_text(json.dumps(v,indent=2)+'\n')
def run(cmd,cwd,log,e=env):
 with (ROOT/log).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=cwd,env=e,stdout=f,stderr=subprocess.STDOUT,check=True)
def asm(source,name,cwd,generated=False):
 p=ROOT/(name+'.o');run([HOST/'bin/asasm',*([] if generated else ['-Uppercase']),'-cpu=ARM2','-apcs','3/26bit','-aof',source,p],cwd,name+'.log');return p
objects={}
flags=['-mcpu=arm2','-mapcs-26','-mlibscl','-mmodule','-Os','-fno-builtin','-fno-common','-U__JMP_BUF_SIZE','-nostdinc','-I'+str(inc),'-Dmain=ArcLibre_EditMain']
for name in ['edit','editv','message','slist']:
 raw=ROOT/(name+'.gcc.s');run([CC,*flags,'-S','-x','c',(SRC/'EditApp/c'/name).relative_to(REPO),'-o',raw],REPO,name+'-cc.log')
 gen=ROOT/(name+'.s');gen.write_text(normalise(raw.read_text()));objects[name]=asm(gen,name,REPO,True)
work=ROOT/'EditApp';shutil.copytree(SRC/'EditApp',work,dirs_exist_ok=True)
shutil.copy2(SRC/'RISC_OSLib/s/modulewrap',work/'s/ModuleWrap')
with (work/'s/AppName').open('w') as f:subprocess.run(['awk','-f',str(SRC/'EditApp/awk/AppName'),str(SRC/'EditApp/Resources/UK/Messages')],stdout=f,check=True)
# The original ResourceFile macro uses the RISC OS pathname without its
# host catalogue suffix. Keep the original public Export bytes intact.
shutil.copy2(work/'Resources/Export,ffb',work/'Resources/Export')
objects['wrapper']=asm('s/ModuleWrap','wrapper',work)
objects['romstubs']=REPO/'build/desktop-c-runtime/filer-romstubs.o'
objects['entry']=asm(SRC/'ArcLibre/s/EditCEntry','entry',REPO)
objects['jumps']=asm(SRC/'ArcLibre/s/SCLJump','jumps',REPO)
save('edit-inputs.json',dict(objects={n:str(p.relative_to(REPO)) for n,p in objects.items()}))
for component,entry in [('ResFiler','s/ResFiler'),('BASIC','ModuleAB'),('BASICTrans','TransSrc')]:
 # Independently observed assembly for the original Apps icon provider.
 work=ROOT/component;shutil.copytree(SRC/('BASIC' if component in ['BASIC','BASICTrans'] else component),work,dirs_exist_ok=True)
 out=ROOT/'artifacts/modules'/component;out.mkdir(parents=True,exist_ok=True);hashes=[]
 for attempt in ['normal-1','normal-2','observer']:
  observer=attempt=='observer';e=dict(env)
  if observer:
   for n in ['emissions.tsv','symbols.tsv']:(out/n).unlink(missing_ok=True)
   e.update(ASASM_TRACE=str(out/'emissions.tsv'),ASASM_SYMBOLS=str(out/'symbols.tsv'))
  run([HOST/'bin'/('asasm-observer' if observer else 'asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',entry,out/'module.aof'],work,component+'-'+attempt+'.log',e)
  hashes.append(hashlib.sha256((out/'module.aof').read_bytes()).hexdigest())
 assert len(set(hashes))==1
 (out/'module.bin').write_bytes(load_aof(out/'module.aof')['data'])
run(['python3',REPO/'tools/audit_modules.py'],REPO,'resfiler-audit.log',dict(os.environ,ARCLIBRE_OUTPUT=str(ROOT)))
resources=bytearray();records=[]
for name,path,ft in [('Resources.BASIC.Messages','BASIC/Resources/UK/Messages',0xfff),('Resources.ResFiler.Messages','ResFiler/Resources/UK/Messages',0xfff),('Apps.!Edit.!Boot','EditApp/Resources/!Boot,feb',0xfeb),('Apps.!Edit.!Run','EditApp/Resources/ROM/!Run,feb',0xfeb),('Apps.!Edit.!Help','EditApp/Resources/UK/!Help',0xfff),('Resources.Edit.Messages','EditApp/Resources/UK/Messages',0xfff),('Resources.Edit.Templates','EditApp/Resources/UK/Templates,fec',0xfec)]:
 b=(SRC/path).read_bytes();n=name.encode()+b'\0';n+=bytes(-len(n)%4);length=24+len(n)+((len(b)+3)&~3)
 resources+=struct.pack('<5I',length,0xfff00000|(ft<<8),0,len(b),3)+n+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)
 records.append(dict(name=name,source='src/'+path,sha256=hashlib.sha256(b).hexdigest(),filetype=ft))
(ROOT/'resources.bin').write_bytes(resources+bytes(4))
records.append(dict(name='Resources.Edit.Export',source='src/EditApp/Resources/Export,ffb',filetype=0xffb,embedded_in='Edit module',sha256=hashlib.sha256((SRC/'EditApp/Resources/Export,ffb').read_bytes()).hexdigest()))
save('resources.json',records)
print('Edit objects and ResourceFiler assembled')
