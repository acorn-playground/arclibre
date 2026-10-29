#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the original DOSFS 0.62 as a disc-loaded, self-relocating module.

Outputs in build/dosfs/: DOSFS,ffa (the module), link maps/symbols,
verification.json, instructions.json and arclibre-dosfs.adf, a
distributable old-map ADFS D floppy holding the module (filetype FFA) and a
ReadMe. DOSFS is not joined into the ROM.

The C sources are compiled by the project's GCC 3.4.6 (ARM2, APCS-26,
SharedCLibrary, module statics, no stack checking as the original -zps1),
normalised and assembled with AsAsm. The header and veneers are ArcLibre's
src/ArcLibre/s/DOSFSHdr; the C library is reached through the original RAM
stubs (RISC_OSLib clib/s/cl_stub_r).

Relocation: the image is linked as a binary at &8000 and again at another
base. The words that differ, each by exactly the base difference, are the
absolute address words; their offsets, ending with -1, are appended to the
image and applied by DOSFSHdr's own __RelocCode. The table is cross-checked
against the word relocations in the object files and against the table
drlink -rmf produces for the same objects (drlink's relocation code itself
is not used). Applying the table in a simulation reproduces the other link.
"""
import hashlib,json,os,pathlib,re,shutil,struct,subprocess,sys
from paths import REPO,SRC,HOST
from c_build_support import normalise
from aof import read as read_aof
import inspect_image
ROOT=REPO/'build/dosfs';ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'verification.json').unlink(missing_ok=True)
CC=REPO/'build/c-toolchain-release/install/bin/gcc';LD=CC.parent/'drlink'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,x):(ROOT/name).write_text(json.dumps(x,indent=2)+'\n')
for row in json.loads((REPO/'manifests/dosfs-inputs.json').read_text()):
 b=(SRC/'DOSFS'/row['path']).read_bytes();assert sha(b)==row['sha256'] and len(b)==row['bytes'],row['path']
ARCLIBRE=['s/DOSFSHdr','s/DOSFSReloc','s/DOSFSBoot','h/DOSFShdr','s/GCCDiv','dosfs/ReadMe']
work=ROOT/'work'
if work.exists():shutil.rmtree(work)
shutil.copytree(SRC/'DOSFS',work)
inc=ROOT/'include'
if inc.exists():shutil.rmtree(inc)
shutil.copytree(REPO/'build/desktop-c-runtime/include',inc)
# Original DOSFS headers, under both RISC OS and Unix spellings; on a
# case-insensitive host these replace any same-named library header.
for p in sorted((SRC/'DOSFS/h').iterdir()):
 for n in [p.name+'.h','h.'+p.name]:shutil.copy2(p,inc/n)
for n in ['DOSFShdr.h','h.DOSFShdr']:shutil.copy2(SRC/'ArcLibre/h/DOSFShdr',inc/n)
env=dict(os.environ,HDR_PATH=str(REPO/'build/desktop-c-runtime/Hdr'),MACHINE='A440')
def run(cmd,name,cwd=REPO):
 with (ROOT/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
objects={};proofs=[]
def assemble(name,source,cwd,upper=True,defines=(),apcs='3/26bit'):
 hashes=[]
 for attempt in range(2):
  target=ROOT/(name+('.o' if attempt==0 else '.repeat.o'))
  run([HOST/'bin/asasm',*(['-Uppercase'] if upper else []),'-cpu=ARM2','-apcs',apcs,'-aof',*defines,source,target],name+'-'+str(attempt),cwd)
  hashes.append(sha(target.read_bytes()))
 assert hashes[0]==hashes[1],name
 objects[name]=ROOT/(name+'.o');proofs.append(dict(name=name,sha256=hashes[0],identical_assemblies=2))
# Original Makefile objects (o.init excluded: see src/ArcLibre/s/DOSFSHdr).
make=(SRC/'DOSFS/Makefile').read_text()
order=re.findall(r'o\.(\w+)',re.search(r'^OBJS =(.*?)\n\n',make,re.M|re.S).group(1))
assert order==['DOSFS','DOSFSops','DOSFSctl','DOSnaming','FSerrors','TIMEconv','wcompare','debug','MsgTrans','Statics','StaticDefs','init'],order
flags=['-mcpu=arm2','-mapcs-26','-mlibscl','-mmodule','-mno-apcs-stack-check','-Os','-fno-builtin','-fno-common','-nostdinc','-I'+str(inc)]
for name in order:
 if name=='init':continue
 if (SRC/'DOSFS/c'/name).exists():
  raw=ROOT/(name+'.gcc.s');run([CC,*flags,'-S','-x','c',pathlib.Path('src/DOSFS/c')/name,'-o',raw],name+'-cc')
  # APCS-26 returns change the PSR: give them the ARM2 settling slot used by
  # every other ArcLibre C build. Prologues and calculations are unchanged.
  code=normalise(raw.read_text())
  code=re.sub(r'(^\t(?:ldm[^\n]*\^|movs\tpc, lr)[^\n]*\n)',r'\1\tmov\tr0, r0 ; ARM2 status settling\n',code,flags=re.M)
  gen=ROOT/(name+'.s');gen.write_text(code);assemble(name,gen,REPO,upper=False)
 # The original Makefile assembles DOSFSctl with "-apcs none": it names
 # its own registers (av, v1-v5 differ from the APCS names).
 else:assemble(name,'s/'+name,work,apcs='none' if name=='DOSFSctl' else '3/26bit')
assemble('DOSFSBoot',SRC/'ArcLibre/s/DOSFSBoot',REPO)
assemble('GCCDiv',SRC/'ArcLibre/s/GCCDiv',REPO)
assemble('stubs','clib/s/cl_stub_r',SRC/'RISC_OSLib')
# The unmodified Messages file as a ResourceFS block (Resources.DOSFS.Messages).
data=(SRC/'DOSFS/Resources/UK/Messages').read_bytes();rname=b'Resources.DOSFS.Messages\0';rname+=bytes(-len(rname)%4)
block=struct.pack('<5I',24+len(rname)+((len(data)+3)&~3),0xffffff00,0,len(data),3)+rname+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)+bytes(4)
res='; Generated by tools/build_dosfs.py from src/DOSFS/Resources/UK/Messages\n        AREA    |DOSFS$$Resources|, DATA, READONLY\n        EXPORT  |DOSFS_Resources|\n|DOSFS_Resources|\n'
res+=''.join('        DCB     '+','.join('&%02X'%x for x in block[i:i+16])+'\n' for i in range(0,len(block),16))+'        END\n'
(ROOT/'DOSFSRes.s').write_text(res);assemble('DOSFSRes',ROOT/'DOSFSRes.s',REPO,upper=False)
assemble('DOSFSHdr',SRC/'ArcLibre/s/DOSFSHdr',REPO)
assemble('DOSFSReloc',SRC/'ArcLibre/s/DOSFSReloc',REPO)
# The 4 MB ROM's DOSFS, in its original ROM form: the header without
# self-relocation and the ROM C stubs (clib s/cl_stub_rm); tools/build_arclibre_rom.py
# links these at the module's ROM address against the shared library's symbols.
assemble('DOSFSHdrROM',SRC/'ArcLibre/s/DOSFSHdr',REPO,defines=['-PreDefine=ArcLibreDOSFSROM SETL {TRUE}'])
assemble('romcstubs','clib/s/cl_stub_rm',SRC/'RISC_OSLib')
# Header first; drlink places equal-attribute areas by name, so the header
# area is named to sort first and is checked below.
link=['DOSFSHdr']+[n for n in order if n in objects]+['DOSFSBoot','DOSFSRes','GCCDiv','stubs']
def drlink(kind,out,*extra):
 run([LD,kind,*extra,'-map','-symbols',ROOT/(out+'.symbols'),'-output',ROOT/out,*[objects[n] for n in link]],out+'-link')
 return (ROOT/out).read_bytes()
save('rom-link.json',dict(objects=[str(objects[n].relative_to(REPO)) for n in ['DOSFSHdrROM']+link[1:-1]+['romcstubs']]))
LINKBASE=0x8000;B=0x1238000
rmf=drlink('-rmf','DOSFS.rmf')
binary=drlink('-bin','DOSFS-a.bin','-base',hex(LINKBASE))
moved_link=drlink('-bin','DOSFS-b.bin','-base',hex(B))
save('inputs.json',dict(objects={n:str(objects[n].relative_to(REPO)) for n in link+['DOSFSReloc']},object_proofs=proofs,compiler_sha256=sha(CC.read_bytes()),linker_sha256=sha(LD.read_bytes()),flags=flags,
 source_manifest_sha256=sha((REPO/'manifests/dosfs-inputs.json').read_bytes()),arclibre_sources={p:sha((SRC/'ArcLibre'/p).read_bytes()) for p in ARCLIBRE}))

# --- Relocation -------------------------------------------------------------
def word(b,o):return struct.unpack_from('<I',b,o)[0]
symbols={n:int(v,16) for v,n in re.findall(r'\b([0-9a-f]{6,8})\s+(\S+)',(ROOT/'DOSFS.rmf.symbols').read_text())}
end=symbols['Image$$RW$$Limit']
assert symbols['Image$$RO$$Base']==0 and symbols['Image$$ZI$$Base']==symbols['Image$$ZI$$Limit']==end and end%4==0,'no zero-init data'
image=rmf[:end]
# drlink -rmf links at &8000 and puts __RelocCode (its gcc/riscos-aof/drlink
# stdcode.c modcode, 17 words) at the image end, then its table. Only the
# table is used, as a cross-check; the code is replaced below.
MODCODE=[0xE1A00000,0xE59F1030,0xE24FB010,0xE05B1001,0x01A0F00E,0xE59FB024,0xE08BB001,0xE28F2020,
 0xE4920004,0xE3700001,0xD1A0F00E,0xE79B3000,0xE0833001,0xE78B3000,0xEAFFFFF8]
assert list(struct.unpack_from('<15I',rmf,end))==MODCODE and word(rmf,end+60)==LINKBASE+end and word(rmf,end+64)==LINKBASE
rmf_table=[];p=end+68
while word(rmf,p)!=0xffffffff:rmf_table.append(word(rmf,p));p+=4
assert p+4==len(rmf) and rmf_table[-2:]==[end+60,end+64]
# The calls to __RelocCode: binary links have no such code (drlink gives the
# symbol the value 0 there), so these BLs are the only other differences.
def bl_target(o):
 w=word(image,o);return o+8+((((w&0xffffff)^0x800000)-0x800000)<<2) if (w>>24)&0xf==0xb else None
calls=sorted(o for o in range(0,end,4) if bl_target(o)==end)
assert len(calls)==2 and calls[0]<0x400,'the header and the RAM stubs call __RelocCode'
assert len(binary)==len(moved_link)==end
assert {o for o in range(0,end,4) if word(binary,o)!=word(image,o)}==set(calls),'-rmf image is the &8000 link'
delta=B-LINKBASE
table=[o for o in range(0,end,4) if word(moved_link,o)!=word(binary,o) and o not in calls]
assert all((word(moved_link,o)-word(binary,o))&0xffffffff==delta for o in table)
assert all(binary[o]==moved_link[o] for o in range(end) if o&~3 not in set(table)|set(calls)),'only whole relocated words differ'
# Cross-check 1: each listed word is a word-sized, non-PC-relative relocation
# in its object file (positions from the link map).
maplog=(ROOT/'DOSFS.rmf-link.log').read_text();word_relocs=set()
for address,size,kind,area,path in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+(R/[OW] (?:code|data))\s+(\S+) from (.+)$',maplog,re.M):
 address,size=int(address,16),int(size,16);obj=read_aof(pathlib.Path(path));a=next(x for x in obj['areas'] if x['name']==area and x['size']==size)
 for r in a['relocations']:
  if (r['flags']>>24)&3==2 and not (r['flags']>>26)&1:word_relocs.add(address+r['offset'])
assert set(table)<=word_relocs,sorted(set(table)-word_relocs)[:8]
# Cross-check 2: drlink's own table lists the same words.
assert sorted(rmf_table[:-2])==table,'drlink -rmf table'
# ArcLibre's relocation code at the image end, its two link-address words
# filled in and listed, then the table.
assert objects['DOSFSReloc']
ra=[x for x in read_aof(objects['DOSFSReloc'])['areas'] if x['name']=='DOSFS$$Reloc'];assert len(ra)==1 and not ra[0]['relocations']
code=bytearray(ra[0]['data']);assert len(code)==68 and code[60:68]==bytes(8)
struct.pack_into('<II',code,60,LINKBASE+end,LINKBASE)
full=sorted(table+[end+60,end+64])
module=image+bytes(code)+struct.pack('<%dI'%(len(full)+1),*full,0xffffffff)
# Apply the table as the code does: the image then equals the link at that
# base (the BLs to the appended code are PC-relative and do not move), and a
# second pass changes nothing.
def relocate(m,base):
 m=bytearray(m);d=(base+end-word(m,end+60))&0xffffffff
 if d:
  for o in full:struct.pack_into('<I',m,o,(word(m,o)+d)&0xffffffff)
 return bytes(m)
once=relocate(module,B)
assert all(once[o:o+4]==moved_link[o:o+4] for o in range(0,end,4) if o not in calls) and all(once[o:o+4]==image[o:o+4] for o in calls)
assert relocate(once,B)==once and word(once,end+60)==B+end and word(once,end+64)==B
reloc=end;table_image=full
print('DOSFS linked:',len(module),'bytes,',len(full),'relocations',flush=True)

# Module header: offsets inside the image, title/help strings, SWI chunk.
h=struct.unpack_from('<12I',image,0)
assert h[0]==0 and h[7]==0x44B00 and h[10]==0 and all(0<x<len(image) and x%4==0 for x in [h[1],h[2],h[3],h[8]])
def cstr(o):return image[o:image.index(0,o)].decode('latin1')
assert cstr(h[4])=='DOSFS' and cstr(h[5]).startswith('DOSFS\t\t0.62 ') and cstr(h[11])=='Resources:$.Resources.DOSFS.Messages'
names=image[h[9]:image.index(b'\0\0',h[9])].split(b'\0');assert names==[b'DOSFS',b'DiscFormat',b'LayoutStructure'],names
commands=[];o=h[6]
while image[o]:
 n=cstr(o);o=(o+len(n)+4)&~3;entry=struct.unpack_from('<4I',image,o);o+=16
 commands.append(dict(name=n,code=entry[0],min=entry[1]&255,gstrans=(entry[1]>>8)&255,max=(entry[1]>>16)&255,flags=entry[1]>>24,syntax=cstr(entry[2]),help=cstr(entry[3])))
assert [(c['name'],c['min'],c['max'],c['gstrans'],c['flags'],c['help'],c['syntax']) for c in commands]==[('DOSMap',0,2,0xff,0x10,'HDOSMAP','SDOSMAP'),('CopyBoot',2,2,0xff,0x10,'HDOSCPB','SDOSCPB')],commands
messages=data.decode('latin1')
for t in ['HDOSMAP','SDOSMAP','HDOSCPB','SDOSCPB']:assert re.search('^'+t+':',messages,re.M),t
# Every linked byte comes from a mapped object area, and only relocated
# words differ from the object bytes (checked against the base-0x8000 link).
binA=image;maplog=(ROOT/'DOSFS-a.bin-link.log').read_text();codewords={};covered=set();areas=[]
for address,size,kind,area,path in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+(R/[OW] (?:code|data))\s+(\S+) from (.+)$',maplog,re.M):
 address,size=int(address,16),int(size,16);obj=read_aof(pathlib.Path(path));a=next(x for x in obj['areas'] if x['name']==area and x['size']==size)
 off=address-0x8000;assert not covered.intersection(range(off,off+size));covered.update(range(off,off+size))
 changed=set()
 for r in a['relocations']:
  ft=(r['flags']>>24)&3;n=4 if ft>=2 else 1<<ft;changed.update(range(r['offset'],r['offset']+n))
 assert all(x==y or i in changed for i,(x,y) in enumerate(zip(binA[off:off+size],a['data']))),(path,area)
 marks=sorted((s['value'],s['name']) for s in obj['symbols'] if s['area']==area and s['name'] in ['$a','$d','$t'])
 if size:assert marks and marks[0][0]==0,(path,area,'unmapped bytes')
 for i,(start,tag) in enumerate(marks):
  end=marks[i+1][0] if i+1<len(marks) else size;assert tag!='$t'
  if tag=='$a':
   assert a['attributes']&0x200
   for x in range(start,end,4):codewords[off+x]=dict(object=str(pathlib.Path(path).relative_to(REPO)),area=area)
 areas.append(dict(offset=off,size=size,kind=kind,area=area,object=str(pathlib.Path(path).relative_to(REPO))))
assert covered==set(range(len(image))),'unmapped linked bytes'
for x in range(reloc,reloc+60,4):codewords[x]=dict(object='src/ArcLibre/s/DOSFSReloc (appended)',area='DOSFS$$Reloc')
settling={0xe1a00000};decoded=[];fpa=[]
for off in sorted(codewords):
 w=word(module,off);pc=LINKBASE+off
 try:d=inspect_image.decode(w,pc)
 except AssertionError as e:fpa.append(dict(offset=off,word=w,error=str(e),**codewords[off]));continue
 if d['branch'] is not None:assert d['branch']-0x8000 in codewords,(hex(off),'branch outside code',d)
 if d['psr'] or d.get('user_bank') and d['kind']=='LDM':assert word(module,off+4) in settling and off+4 in codewords,(hex(off),'ARM2 settling',codewords[off])
 decoded.append(dict(offset=off,word=w,decoded=d,**codewords[off]))
assert not fpa,('floating-point or undecodable instructions',fpa[:4])
(ROOT/'instructions.json').write_text(json.dumps(decoded,indent=1)+'\n')
rw=symbols['Image$$RW$$Limit']-symbols['Image$$RW$$Base']
(ROOT/'DOSFS,ffa').write_bytes(module)
verification=dict(status='STATIC_PASS',module_bytes=len(module),module_sha256=sha(module),image_bytes=len(image),relocation_code_offset=reloc,
 relocations=len(table_image),relocation_code='src/ArcLibre/s/DOSFSReloc',relocation_check='binary links at 0x8000 and 0x1238000: the differing words (each by the base difference) are the table; all are object word relocations; equal to drlink -rmf table; applying it reproduces the second link',
 rw_template_bytes=rw,rma_workspace_bytes=rw+12,  # + RISC_OSLib s/h_stubs fixedwssize (size and two relocation words)
 integer_arm2_instructions=len(decoded),fpa_instructions=0,branches_in_code=True,psr_settling_checked=True,
 all_bytes_mapped_to_object_areas=True,header=dict(init=h[1],final=h[2],service=h[3],swi_chunk=h[7],swi_handler=h[8],commands=commands,messages=cstr(h[11])),
 areas=areas,resources=dict(name='Resources.DOSFS.Messages',source='src/DOSFS/Resources/UK/Messages',sha256=sha(data)))
# The boot sector LayoutStructure starts from, and DOSFS's own format tables.
import check_dosfs_boot
boot=symbols['func_default_dbsector'];assert symbols['default_dbsector']>=symbols['Image$$RW$$Base']
sector=image[boot:boot+512];assert sector==next(a for a in read_aof(objects['DOSFSBoot'])['areas'] if a['name']=='DOSFS_BootSector')['data']
formats,formatinfo=check_dosfs_boot.tables(image,symbols,LINKBASE)
verification['boot_sector']=check_dosfs_boot.check(sector,formats,formatinfo)
verification['boot_sector'].update(offset=boot,sha256=sha(sector),source='src/ArcLibre/s/DOSFSBoot')
verification['symbols']={n:symbols[n] for n in ['func_default_dbsector','func_DOS_formats','func_DOS_formatinfo','default_dbsector','DOS_formats','DOS_formatinfo']}
save('verification.json',verification)
print('DOSFS module verified:',len(module),'bytes,',len(decoded),'ARM2 instructions,',len(table_image),'relocations',flush=True)

# --- Distributable floppy: old-map ADFS D, files 1 KiB aligned -------------
sys.path.insert(0,str(REPO/'tests'))
from adfs_fixture import u24,directory,entry,oldcheck
import datetime
stamp=int((datetime.datetime(2026,10,27)-datetime.datetime(1900,1,1)).total_seconds())*100
def typed(t):return 0xfff00000|(t<<8)|(stamp>>32),stamp&0xffffffff
readme=(SRC/'ArcLibre/dosfs/ReadMe').read_bytes()
files=[('DOSFS',module,0xffa),('ReadMe',readme,0xfff)]
disc=bytearray(819200);offset=0xc00;entries=[]
for name,content,ft in files:
 disc[offset:offset+len(content)]=content;load,exe=typed(ft);entries.append(entry(name,offset//256,content,load=load,execute=exe));offset+=(len(content)+1023)&~1023
disc[0x400:0xc00]=directory('$',4,entries,b'Hugo')
u24(disc,0,offset//256);u24(disc,256,(819200-offset)//256);u24(disc,252,3200)
title=b'DOSFS     '
for i in range(5):disc[247+i]=title[2*i];disc[502+i]=title[2*i+1]
disc[507:509]=b'\x44\x46';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(ROOT/'arclibre-dosfs.adf').write_bytes(disc)
save('disc.json',dict(image='build/dosfs/arclibre-dosfs.adf',sha256=sha(disc),bytes=len(disc),format='ADFS D (old map) 800K',disc_name='DOSFS',
 files=[dict(name=n,filetype='&%03X'%t,bytes=len(c),sha256=sha(c),sector=e['address']) for (n,c,t),e in zip(files,entries)]))
print('floppy:',ROOT/'arclibre-dosfs.adf',sha(disc),flush=True)
