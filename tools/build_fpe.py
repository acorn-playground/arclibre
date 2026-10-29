#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the pinned ARM software FPEmulator and an isolated real FPA client.

Does not change the kernel, baseline ROM, or strict integer ARM2 decoder.
The FP emulator deliberately contains recursive FPA operations and hardware
probe operations; these are classified separately, never passed as ARM2 integer.
"""
import hashlib,json,os,pathlib,shutil,struct,subprocess
from paths import REPO,SRC,HOST
from module_image import load_aof
import inspect_image
ROOT=REPO/'build/fpemulator';ROOT.mkdir(exist_ok=True)
(ROOT/'result.json').unlink(missing_ok=True)
for name in ['emissions.tsv','symbols.tsv','references.tsv']:(ROOT/name).unlink(missing_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
manifest=json.loads((REPO/'manifests/fpemulator.json').read_text())
for row in manifest['files']:
 b=(SRC/'FPEmulator'/row['path']).read_bytes();assert sha(b)==row['sha256'] and len(b)==row['bytes'],row['path']
work=ROOT/'work';headers=ROOT/'Hdr'
for p in [work,headers]:
 if p.exists():shutil.rmtree(p)
 p.mkdir()
shutil.copytree(SRC/'FPEmulator',work/'FPEmulator')
h=json.loads((REPO/'manifests/header-exports.json').read_text());mapping=dict(h['kernel']);mapping.update(h['module_overrides'])
for name,source in mapping.items():
 p=headers/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/source,p)
save(ROOT/'header-exports.json',{n:dict(source=s,sha256=sha((SRC/s).read_bytes())) for n,s in mapping.items()})
env=dict(os.environ,HDR_PATH=str(headers),MACHINE='A440',IMAGESIZE='2048K',LOCALE='UK')
hashes=[]
for attempt in ['normal-1','normal-2','observer']:
 observer=attempt=='observer';e=dict(env)
 if observer:e.update(ASASM_TRACE=str(ROOT/'emissions.tsv'),ASASM_SYMBOLS=str(ROOT/'symbols.tsv'),ASASM_REFS=str(ROOT/'references.tsv'))
 cmd=[HOST/'bin'/('asasm-observer' if observer else 'asasm'),'-i'+str(headers),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','s/fpe400',ROOT/(attempt+'.aof')]
 with (ROOT/(attempt+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=work/'FPEmulator/riscos',env=e,stdout=f,stderr=subprocess.STDOUT,check=True)
 hashes.append(sha((ROOT/(attempt+'.aof')).read_bytes()))
assert len(set(hashes))==1
obj=load_aof(ROOT/'normal-1.aof');data=obj['data'];(ROOT/'module.bin').write_bytes(data)
symbols={line.split('\t')[0]:int(line.split('\t')[2]) for line in (ROOT/'symbols.tsv').read_text().splitlines()}
save(ROOT/'symbols.json',symbols)
for name,value in dict(Arm600=0,ARM2Safe=1,FPASCWanted=0,FPEWanted=1,MultipleContexts=1,Use64bitMultiply=0,UseCLZ=0,ContextLength=136,SVCSTK=0x1c02000,FPEAnchor=0xff4).items():
 assert symbols[name]==value,(name,symbols[name],value)
ins={}
for line in (ROOT/'emissions.tsv').read_text().splitlines():
 k,offset,size,value,times,file,ln,caller,cl=line.split('\t');offset,size,value,times=map(int,[offset,size,value,times])
 for i in range(times):
  for j in range(size):assert data[offset+i*size+j]==(value>>(8*j))&255
 if k=='I':ins[offset]=dict(word=value,file=str(pathlib.Path(file).relative_to(work/'FPEmulator')),line=int(ln))
ms=sorted((s['value'],s['name']) for s in obj['symbols'] if s['name'] in ['$a','$d','$t']);code=set()
for i,(start,kind) in enumerate(ms):
 end=ms[i+1][0] if i+1<len(ms) else len(data);assert kind!='$t'
 if kind=='$a':code.update(range(start,end,4))
assert code==set(ins),(len(code-set(ins)),len(set(ins)-code))
integer=[];fpa=[]
for offset,row in ins.items():
 w=row['word']
 try:d=inspect_image.decode(w,offset)
 except AssertionError as e:
  assert 'coprocessor instruction' in str(e) and (w>>8)&15 in [1,2],(offset,str(e))
  assert (w>>25)&7 in [6,7] and (w>>24)&15 != 15 and w>>28!=15
  source=(work/'FPEmulator'/row['file']).read_text().splitlines()[row['line']-1]
  mnemonic=source.strip().split()[0]
  fpa.append(dict(offset=offset,source=row,mnemonic=mnemonic,classification='runtime hardware detection' if row['file']=='coresrc/s/interf' else 'recursive software FP operation',decoder_rejection=str(e)))
  continue
 if d['branch'] is not None:assert d['branch'] in ins,(offset,'branch into data',d)
 if d['psr'] or d.get('user_bank') and d['kind']=='LDM':assert ins.get(offset+4,{}).get('word')==0xe1a00000,(offset,'ARM2 settling')
 if d['kind'] in ['MOV','MVN'] and 'immediate' in d:
  source=(work/'FPEmulator'/row['file']).read_text().splitlines()[row['line']-1];assert 'ADR' not in source,(offset,'absolute ADR')
 integer.append(dict(offset=offset,source=row,decoded=d))
# Explicitly retained FPA code only: no processor-control coprocessor accepted.
assert len(fpa)==396 and len([x for x in fpa if x['classification']=='runtime hardware detection'])==6
save(ROOT/'integer-instructions.json',integer);save(ROOT/'fpa-instructions.json',fpa)
# Real selected error resource; no default-success service handlers.
b=(SRC/'FPEmulator/riscos/Resources/UK/Messages').read_bytes();n=b'Resources.FPEmulator.Messages\0';n+=bytes(-len(n)%4)
length=24+len(n)+((len(b)+3)&~3)
resource=struct.pack('<5I',length,0xffffff00,0,len(b),3)+n+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)+bytes(4)
(ROOT/'resources.bin').write_bytes(resource)
source=REPO/'tests/fixtures/FPEClient.s'
with (ROOT/'client.log').open('w') as f:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',str(source),str(ROOT/'client.aof')],stdout=f,stderr=subprocess.STDOUT,check=True)
client=load_aof(ROOT/'client.aof');(ROOT/'client.bin').write_bytes(client['data']);save(ROOT/'client-symbols.json',{s['name']:s['value'] for s in client['symbols']})
result=dict(status='STATIC_PASS_WITH_EXPLICIT_SOFTWARE_FPA_TRAPS',bytes=len(data),sha256=sha(data),aof_sha256=hashes[0],unresolved_symbols=0,relocations=0,integer_arm2_instructions=len(integer),recursive_and_probe_fpa_instructions=len(fpa),psr_settling_checked=True,code_data_coverage=True,resource_sha256=sha(resource),client_sha256=sha(client['data']),baseline_rom_modified=False)
save(ROOT/'result.json',result);print(json.dumps(result,indent=2))
