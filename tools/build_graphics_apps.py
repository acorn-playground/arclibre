#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the matching original Draw and Paint applications for ARM2."""
import hashlib,json,os,re,shutil,struct,subprocess
from paths import REPO,SRC,HOST
from c_build_support import normalise
ROOT=REPO/'build/graphics-apps';ROOT.mkdir(exist_ok=True)
CC=REPO/'build/c-toolchain-release/install/bin/gcc'
for r in json.loads((REPO/'manifests/graphics-app-inputs.json').read_text()):
 b=(SRC/r['component']/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r
resources=bytearray();records=[]
def templates(b):
 """A Templates file as its header and (name, window block) pairs."""
 font,=struct.unpack_from('<i',b,0);assert font==-1,'font data is not carried over'
 i=16;out=[]
 while struct.unpack_from('<i',b,i)[0]:
  off,size,typ=struct.unpack_from('<3i',b,i);assert typ==1
  out.append((b[i+12:i+24],b[off:off+size]));i+=24
 return out
def with_template(b,donor,name):
 """Add the window `name` from the Templates file `donor` to `b`."""
 entries=templates(b);assert all(n.split(b'\r')[0]!=name for n,_ in entries)
 entries+=[(n,w) for n,w in templates(donor) if n.split(b'\r')[0]==name];assert len(entries)==len(templates(b))+1
 out=bytearray(struct.pack('<4i',-1,0,0,0));data=bytearray();base=16+24*len(entries)+4
 for n,w in entries:
  out+=struct.pack('<3i',base+len(data),len(w),1)+n;data+=w+bytes(-len(w)%4)
 return bytes(out+struct.pack('<i',0)+data)
# Paint 3.60 edits palette entries with RISC_OSLib's dboxtcol, which in an
# Archimedes ROM drives the application's "dboxtcol" window instead of the
# ColourPicker module. Paint's own Templates lost that window when Paint moved
# to ColourPicker, so its copy is taken from Draw's pinned Templates.
DERIVED={'Paint/Resources/UK/Templates,fec':('Draw/Resources/UK/Templates,fec',b'dboxtcol')}
def resource(name,path,ft):
 global resources
 b=(SRC/path).read_bytes();record=dict(name=name,source='src/'+path)
 if path in DERIVED:
  donor,window=DERIVED[path];b=with_template(b,(SRC/donor).read_bytes(),window)
  record.update(source_sha256=hashlib.sha256((SRC/path).read_bytes()).hexdigest(),added_window=window.decode(),added_from='src/'+donor)
 n=name.encode()+b'\0';n+=bytes(-len(n)%4);length=24+len(n)+((len(b)+3)&~3)
 resources+=struct.pack('<5I',length,0xfff00000|(ft<<8),0,len(b),3)+n+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)
 records.append(dict(record,sha256=hashlib.sha256(b).hexdigest(),filetype=ft))
for comp in ['Draw','Paint']:
 work=ROOT/comp;shutil.copytree(SRC/comp,work,dirs_exist_ok=True)
 inc=work/'include';shutil.copytree(REPO/'build/desktop-c-runtime/include',inc,dirs_exist_ok=True)
 for p in (SRC/comp/'h').iterdir():
  for n in [p.name+'.h','h.'+p.name]:shutil.copy2(p,inc/n)
 env=dict(os.environ,HDR_PATH=str(REPO/'build/desktop-c-runtime/Hdr'),MACHINE='A440')
 def run(cmd,log,cwd=REPO):
  with (work/(log+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 def asm(source,name,cwd=REPO,generated=False):
  p=work/(name+'.o');run([HOST/'bin/asasm',*([] if generated else ['-Uppercase']),'-cpu=ARM2','-apcs','3/26bit','-aof',source,p],name,cwd);return p
 flags=['-mcpu=arm2','-mapcs-26','-mlibscl','-mmodule','-Os','-fno-builtin','-fno-common','-U__JMP_BUF_SIZE','-nostdinc','-I'+str(inc),'-Dmain=ArcLibre_'+comp+'Main']
 make=(SRC/comp/'Makefile').read_text();group=re.search(r'^OBJSZ\s*=(.*?)(?=\n[^ \\n])',make,re.M|re.S).group(1)
 names=re.findall(r'\boz?\.(\w+)',group);objects={}
 for name in names:
  sources=[p for p in (SRC/comp/'c').iterdir() if p.name.lower()==name.lower()]
  if sources:
   # __FILE__ must describe the source, not the machine's checkout directory.
   raw=work/(name+'.gcc.s');run([CC,*flags,'-S','-x','c',sources[0].relative_to(REPO),'-o',raw],name+'-cc')
   gen=work/(name+'.s');gen.write_text(normalise(raw.read_text()));objects[name]=asm(gen,name,generated=True)
  else:objects[name]=asm(SRC/comp/'asm'/name,name)
 (work/'s').mkdir(exist_ok=True);shutil.copy2(SRC/'RISC_OSLib/s/modulewrap',work/'s/ModuleWrap');shutil.copy2(work/'asm/ResFiles',work/'s/ResFiles')
 with (work/'s/AppName').open('w') as f:subprocess.run(['awk','-f',str(work/'awk/AppName'),str(work/'Resources/UK/Messages')],stdout=f,check=True)
 for p in (work/'Resources').glob('*,*'):shutil.copy2(p,p.with_name(p.name.split(',')[0]))
 objects['wrapper']=asm('s/ModuleWrap','wrapper',work)
 objects['romstubs']=REPO/'build/desktop-c-runtime/filer-romstubs.o'
 objects['entry']=asm(SRC/'ArcLibre/s'/(comp+'CEntry'),'entry')
 objects['jumps']=asm(SRC/'ArcLibre/s/SCLJump','jumps')
 (work/'inputs.json').write_text(json.dumps(dict(objects={n:str(p.relative_to(REPO)) for n,p in objects.items()}),indent=2)+'\n')
 for name,path,ft in [('!Boot','Resources/ROM/!Boot,feb' if comp=='Draw' else 'Resources/!Boot,feb',0xfeb),('!Run','Resources/ROM/!Run,feb',0xfeb),('!Help','Resources/UK/!Help',0xfff)]:resource('Apps.!'+comp+'.'+name,comp+'/'+path,ft)
 for name,ft in [('Messages',0xfff),('Templates,fec',0xfec)]+([('Sprites,ff9',0xff9)] if comp=='Paint' else []):resource('Resources.'+comp+'.'+name.split(',')[0],comp+'/Resources/UK/'+name,ft)
 print(comp,'assembled',flush=True)
records.append(dict(name='Resources.Draw.Sprites',source='src/Draw/Resources/Sprites,ff9',filetype=0xff9,embedded_in='Draw module',sha256=hashlib.sha256((SRC/'Draw/Resources/Sprites,ff9').read_bytes()).hexdigest()))
(ROOT/'resources.bin').write_bytes(resources+bytes(4));(ROOT/'resources.json').write_text(json.dumps(records,indent=2)+'\n')
