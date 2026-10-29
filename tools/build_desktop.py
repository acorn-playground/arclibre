#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build isolated desktop candidates; never join them into the bootable ROM.

Wimp deliberately retains its real FPA operations. Its dependency on a working
FPEmulator is reported separately from integer ARM2 instruction validation.
"""
import hashlib,json,os,pathlib,shutil,struct,subprocess
from paths import REPO,SRC,HOST
import inspect_image
from module_image import load_aof
ROOT=REPO/'build/desktop-components'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def u32(b,p=0):return struct.unpack_from('<I',b,p)[0]
ROOT.mkdir(exist_ok=True);(ROOT/'result.json').unlink(missing_ok=True)
inputs=json.loads((REPO/'manifests/desktop-inputs.json').read_text())
for row in json.loads((REPO/'manifests/public-message-inputs.json').read_text()):
 assert sha((SRC/row['component']/row['path']).read_bytes())==row['sha256'],row
assets=json.loads((REPO/'manifests/desktop-assets.json').read_text())['files']
for row in inputs:
 b=(SRC/row['component']/row['path']).read_bytes();assert sha(b)==row['sha256'],row
for row in assets:
 b=(SRC/row['component']/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],row
work=ROOT/'work';headers=ROOT/'Hdr';out=ROOT/'modules'
for p in [work,headers,out]:
 if p.exists():shutil.rmtree(p)
 p.mkdir()
for comp in ['Wimp','FontManager','ROMFonts']:shutil.copytree(SRC/comp,work/comp)
# FLOAD/FEXEC in the original ResourceFile macro use host mtimes. Normalize only
# generated copies; preserve the original bytes and filename-derived file types.
for p in work.rglob('*'):
 if p.is_file():os.utime(p,(0,0))
h=json.loads((REPO/'manifests/header-exports.json').read_text());mapping=dict(h['kernel']);mapping.update(h['module_overrides']);mapping.update(json.loads((REPO/'manifests/desktop-header-exports.json').read_text()))
for name,source in mapping.items():
 p=headers/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/source,p)
exports={name:dict(source=source,sha256=sha((headers/name).read_bytes())) for name,source in mapping.items()}
save(ROOT/'header-exports.json',exports)
env=dict(os.environ,HDR_PATH=str(headers),MACHINE='A440',IMAGESIZE='2048K',LOCALE='UK')
reports=[]
for comp,source in [('Wimp','s/Wimp'),('FontManager','s/Fonts'),('ROMFonts','s/ROMFonts')]:
 d=out/comp;d.mkdir();hashes=[]
 for attempt in ['normal-1','normal-2','observer']:
  variables=dict(env);observer=attempt=='observer'
  if observer: variables.update(ASASM_TRACE=str(d/'emissions.tsv'),ASASM_SYMBOLS=str(d/'symbols.tsv'),ASASM_REFS=str(d/'references.tsv'))
  tool=HOST/'bin'/('asasm-observer' if observer else 'asasm');obj=d/(attempt+'.aof')
  cmd=[tool,'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','-Verbose',source,obj]
  with (d/(attempt+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=work/comp,env=variables,stdout=f,stderr=subprocess.STDOUT,check=True)
  hashes.append(sha(obj.read_bytes()))
 assert len(set(hashes))==1,(comp,'observer/repeat mismatch')
 obj=load_aof(d/'normal-1.aof');data=obj['data'];(d/'module.bin').write_bytes(data)
 symbols={}
 for line in (d/'symbols.tsv').read_text().splitlines():
  name,tag,value,*_=line.split('\t');symbols[name]=dict(tag=int(tag),value=int(value))
 save(d/'symbols.json',symbols)
 ins={}
 for line in (d/'emissions.tsv').read_text().splitlines():
  kind,offset,size,value,times,file,ln,caller,cl=line.split('\t');offset,size,value,times=map(int,[offset,size,value,times])
  for i in range(times):
   for j in range(size):assert data[offset+i*size+j]==(value>>(8*j))&255
  if kind=='I':ins[offset]=dict(word=value,file=str(pathlib.Path(file).relative_to(ROOT)),line=int(ln),caller=str(pathlib.Path(caller).relative_to(ROOT)),caller_line=int(cl))
 mapping_symbols=sorted((s['value'],s['name']) for s in obj['symbols'] if s['name'] in ['$a','$d','$t']);code=set()
 for i,(start,kind) in enumerate(mapping_symbols):
  end=mapping_symbols[i+1][0] if i+1<len(mapping_symbols) else len(data);assert kind!='$t'
  if kind=='$a':code.update(range(start,end,4))
 padding=sorted(code-set(ins))
 if padding:
  # The upstream ALIGN 16 inside Wimp's workspace declarations pads the
  # preceding returned function before the vduinput data table. AsAsm retains
  # its $a mapping over this non-executable, zero-filled alignment gap.
  assert comp=='Wimp' and len(padding)<=3 and padding==list(range(padding[0],symbols['vduinput']['value'],4))
  assert symbols['vduinput']['value']%16==0 and all(u32(data,p)==0 for p in padding)
  assert inspect_image.decode(ins[padding[0]-4]['word'],padding[0]-4)['return_pc']
  code-=set(padding)
 assert code==set(ins),(comp,'code/data coverage',len(code-set(ins)),len(set(ins)-code))
 save(d/'alignment-padding.json',padding)
 decoded=[];fpa=[]
 for offset,row in ins.items():
  try:info=inspect_image.decode(row['word'],offset)
  except AssertionError as e:
   # Preserve the strict decoder's rejection. Only the 21 original Wimp FPA
   # instructions are classified as an explicit runtime dependency, never PASS
   # for execution on a bare ARM2. All other decoding errors remain fatal.
   line=(ROOT/row['file']).read_text(encoding='latin1').splitlines()[row['line']-1]
   mnemonic=line.strip().split()[0]
   assert comp=='Wimp' and row['file']=='work/Wimp/s/Wimp07' and mnemonic in ['WFSEQ','WFS','LDFE','RFS','STFE'] and 'coprocessor instruction' in str(e),(comp,offset,str(e),line)
   assert (row['word']>>8)&15 in [1,2]
   fpa.append(dict(offset=offset,source=row,mnemonic=mnemonic,decoder_rejection=str(e)));continue
  if info['branch'] is not None:assert info['branch'] in ins,(comp,offset,'branch into data')
  if info['psr'] or info.get('user_bank') and info['kind']=='LDM':assert ins.get(offset+4,{}).get('word')==0xe1a00000,(comp,offset,'missing ARM2 settling')
  if info['kind'] in ['MOV','MVN'] and 'immediate' in info:
   line=(ROOT/row['file']).read_text(encoding='latin1').splitlines()[row['line']-1]
   assert 'ADR' not in line,(comp,offset,'absolute ADR materialisation')
  decoded.append(dict(offset=offset,decoded=info,source=row))
 assert len(fpa)==(21 if comp=='Wimp' else 0)
 if comp in ['Wimp','FontManager']:
  expected=0x400c0 if comp=='Wimp' else 0x40080
  assert symbols['MySWIBase']['value']==expected and u32(data,28)==expected
 if comp=='Wimp':assert symbols['XFPEmulator_Version']['value']==0x60480
 if comp=='Wimp':
  # Public 3.11 message numbers, checked independently of Hdr:Messages.
  expected_messages={'Message_Notify':0x40040,'Message_PrintFile':0x80140}
  for i,n in enumerate(['MenuWarning','ModeChange','TaskInitialise','TaskCloseDown','SlotSize','SetSlot','TaskNameRq','TaskNameIs','TaskStarted','MenusDeleted','Iconize','WindowClosed','WindowInfo','Swap','ToolsChanged','FontChanged','IconizeAt']):
   expected_messages['Message_'+n]=0x400c0+i
  for n,v in expected_messages.items():assert symbols[n]['value']==v,(n,symbols[n],v)
  save(d/'message-allocations.json',expected_messages)

 # Parse the actual embedded ResourceFS records and compare every payload to
 # the pinned asset manifest. Include metadata/ranges to make packaging reviewable.
 embedded=[]
 if comp in ['Wimp','ROMFonts']:
  p=symbols['resourcefsfiles' if comp=='Wimp' else 'ROMFonts']['value']
  while u32(data,p):
   length,load,execute,size,access=struct.unpack_from('<5I',data,p);end=data.index(0,p+20);name=data[p+20:end].decode();payload=(end+4)&~3
   assert u32(data,payload)==size+4;payload+=4
   row=next(r for r in assets if r['component']==comp and r['resource_name']==name and r['route'].startswith('embedded'))
   assert data[payload:payload+size]==(SRC/comp/row['path']).read_bytes()
   assert length==(payload-p+size+3)&~3 and p+length<=len(data)
   assert not any(payload<=off<payload+size for off in ins)
   embedded.append(dict(name=name,offset=payload,bytes=size,sha256=sha(data[payload:payload+size]),load=load,execute=execute,access=access));p+=length
  assert len(embedded)==(4 if comp=='Wimp' else 29)
 save(d/'instructions.json',decoded);save(d/'fpa-dependency.json',fpa);save(d/'embedded-assets.json',embedded)
 # Make header provenance/use review reproducible, including inherited public
 # registration headers from the separately documented kernel restoration pin.
 uses={}
 for line in (d/'references.tsv').read_text().splitlines():
  name,file,number,caller,caller_line=line.split('\t')
  if name in symbols and pathlib.Path(file).is_relative_to(headers):uses[name]=dict(**symbols[name],header=str(pathlib.Path(file).relative_to(headers)))
 save(d/'header-symbols.json',uses)
 report=dict(component=comp,status='ASSEMBLED_REQUIRES_FPEMULATOR' if fpa else 'STATIC_ARM2_PASS',bytes=len(data),sha256=sha(data),identical_aof_sha256=hashes[0],unresolved_symbols=0,relocations=0,integer_arm2_instructions=len(decoded),fpa_instructions=len(fpa),embedded_assets=len(embedded),runtime_tested=False)
 reports.append(report);print(comp,report['status'],len(data),'bytes',flush=True)
# The original module resource recipes also require these six external files.
external=b''
for row in assets:
 if not row['route'].startswith('external'):continue
 b=(SRC/row['component']/row['path']).read_bytes();name=row['resource_name'].encode()+b'\0';name+=bytes(-len(name)%4)
 filetype=0xff9 if ',ff9' in row['path'] else 0xfec if ',fec' in row['path'] else 0xfff
 length=24+len(name)+((len(b)+3)&~3)
 external+=struct.pack('<5I',length,0xfff00000|(filetype<<8),0,len(b),3)+name+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)
external+=bytes(4);(ROOT/'external-resources.bin').write_bytes(external)
result=dict(status='SOURCE_AND_ASSEMBLY_CLOSURE_PASS',runtime_status='STATIC_ONLY; runtime gates are make fpe-test, renderer-test, font-test and wimp-test',modules=reports,assets=len(assets),asset_bytes=sum(x['bytes'] for x in assets),external_resource_pack_sha256=sha(external),source_inputs_verified=len(inputs),boot_rom_modified=False)
save(ROOT/'result.json',result)
