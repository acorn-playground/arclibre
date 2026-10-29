#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build four pinned original-machine rendering providers, without ROM joining."""
import hashlib,json,os,pathlib,shutil,struct,subprocess
from paths import REPO,SRC,HOST
from module_image import load_aof
from generate_super_tables import generate
import inspect_image
ROOT=REPO/'build/render-components';ROOT.mkdir(exist_ok=True);(ROOT/'result.json').unlink(missing_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
components=[('Colours','MakeNew',0x40740),('DrawMod','s/Draw',0x40700),('Hourglass','NewOS',0x406c0),('Super','s/Super',0x40d80)]
inputs=json.loads((REPO/'manifests/desktop-inputs.json').read_text())
for row in inputs:
 if row['component'] in [c[0] for c in components]:assert sha((SRC/row['component']/row['path']).read_bytes())==row['sha256']
work=ROOT/'work';headers=ROOT/'Hdr';modules=ROOT/'modules'
for p in [work,headers,modules]:
 if p.exists():shutil.rmtree(p)
 p.mkdir()
h=json.loads((REPO/'manifests/header-exports.json').read_text());mapping=dict(h['kernel']);mapping.update(h['module_overrides']);mapping.update(json.loads((REPO/'manifests/desktop-header-exports.json').read_text()))
for n,s in mapping.items():
 p=headers/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/s,p)
save(ROOT/'headers.json',{n:dict(source=s,sha256=sha((SRC/s).read_bytes())) for n,s in mapping.items()})
env=dict(os.environ,HDR_PATH=str(headers),MACHINE='A440',LOCALE='UK',IMAGESIZE='2048K');reports=[]
for c,entry,base in components:
 shutil.copytree(SRC/c,work/c);d=modules/c;d.mkdir();hashes=[]
 if c=='Super':save(ROOT/'generated-tables.json',generate(work/c/'s'))
 for attempt in ['normal-1','normal-2','observer']:
  observer=attempt=='observer';e=dict(env)
  if observer:e.update(ASASM_TRACE=str(d/'emissions.tsv'),ASASM_SYMBOLS=str(d/'symbols.tsv'))
  cmd=[HOST/'bin'/('asasm-observer' if observer else 'asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',entry,d/(attempt+'.aof')]
  with (d/(attempt+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=work/c,env=e,stdout=f,stderr=subprocess.STDOUT,check=True)
  hashes.append(sha((d/(attempt+'.aof')).read_bytes()))
 assert len(set(hashes))==1
 o=load_aof(d/'normal-1.aof');data=o['data'];(d/'module.bin').write_bytes(data);assert struct.unpack_from('<I',data,28)[0]==base
 symbols={line.split('\t')[0]:int(line.split('\t')[2]) for line in (d/'symbols.tsv').read_text().splitlines()};save(d/'symbols.json',symbols)
 ins={}
 for line in (d/'emissions.tsv').read_text().splitlines():
  k,offset,size,value,times,file,ln,caller,cl=line.split('\t');offset,size,value,times=map(int,[offset,size,value,times])
  for i in range(times):
   for j in range(size):assert data[offset+i*size+j]==(value>>(8*j))&255
  if k=='I':ins[offset]=dict(word=value,file=str(pathlib.Path(file).relative_to(ROOT)),line=int(ln))
 ms=sorted((s['value'],s['name']) for s in o['symbols'] if s['name'] in ['$a','$d','$t']);code=set()
 for i,(start,kind) in enumerate(ms):
  end=ms[i+1][0] if i+1<len(ms) else len(data);assert kind!='$t'
  if kind=='$a':code.update(range(start,end,4))
 assert code==set(ins),(c,'code/data mismatch',code-set(ins),set(ins)-code)
 decoded=[]
 for offset,row in ins.items():
  info=inspect_image.decode(row['word'],offset)
  if info['branch'] is not None:assert info['branch'] in ins,(c,offset,'branch into data')
  if info['psr'] or info.get('user_bank') and info['kind']=='LDM':assert ins.get(offset+4,{}).get('word')==0xe1a00000,(c,offset,'settling')
  if info['kind'] in ['MOV','MVN'] and 'immediate' in info:
   line=(ROOT/row['file']).read_text(encoding='latin1').splitlines()[row['line']-1];assert 'ADR' not in line,(c,offset,'absolute ADR')
  decoded.append(dict(offset=offset,source=row,decoded=info))
 save(d/'instructions.json',decoded)
 report=dict(component=c,status='STATIC_ARM2_PASS',bytes=len(data),sha256=sha(data),aof_sha256=hashes[0],integer_instructions=len(ins),relocations=0,unresolved_symbols=0,swi_base=base)
 reports.append(report);print(c,len(data),'bytes',flush=True)
resources=b'';assetrows=[]
for c in ['Colours','DrawMod']:
 path='Resources/UK/Messages';b=(SRC/c/path).read_bytes();name='Resources.'+c+'.Messages';n=name.encode()+b'\0';n+=bytes(-len(n)%4);length=24+len(n)+((len(b)+3)&~3)
 resources+=struct.pack('<5I',length,0xffffff00,0,len(b),3)+n+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)
 assetrows.append(dict(component=c,path=path,resource_name=name,bytes=len(b),sha256=sha(b),license='Pinned component Apache-2.0 LICENSE; no separate file-level message notice'))
resources+=bytes(4);(ROOT/'resources.bin').write_bytes(resources);save(ROOT/'resources.json',assetrows)
save(ROOT/'result.json',dict(status='STATIC_ARM2_PASS',modules=reports,generated_tables='generated-tables.json',resources_sha256=sha(resources),baseline_rom_modified=False))
