#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the distributable printing floppy (arclibre-printing.adf).

RISC OS 3.11 had !Printers, PDriver, PDriverDP, PDumperSupport and PDumperDM
in ROM; ArcLibre ships them on disc, by owner decision. The disc holds the
original !Printers in its disc install layout (the pinned PrinterManager
Makefile's `install` target) with its three printer classes, dot matrix (dp),
LaserJet (lj) and PostScript (ps), as in RISC OS 3.11; the modules where the
support code loads them (Printers:Modules: PDriver, PDriverDP, PDriverPS and
PDumperSupport; Printers:PDumpers: PDumperDM and PDumperLJ); and three
printer definitions: an Epson FX-80, an Apple LaserWriter and an HP LaserJet II.
The PostScript prologues are installed as the Makefile does, but not shrunk
(Acorn's psshrink is not public).

!Printers' BASIC is built as the original Makefile does, with public tools:
the C preprocessor (the bundled GCC's, -DDISC, without -DSparrow, the AUN
remote printing build whose modules have no public source), line numbers,
then TEXTLOAD and CRUNCH -1 (the original crunch scripts) in the ROM's own
BASIC under the pinned MacArch core. Acorn's squish is not used: the programs
are larger but otherwise the original. DataFiles.Code is assembled by running
the original SuppSrc in BASIC after the CONST_name% substitution of Acorn's
Constants tool (values from h.ConstVals).
"""
import datetime,hashlib,json,os,pathlib,re,shutil,struct,subprocess,sys
from paths import REPO,SRC
from adfs_image import File,image
sys.path.insert(0,str(REPO/'tests'))
from verify_filer_disc import read_directory
ROOT=REPO/'build/printing-disc';ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'disc.json').unlink(missing_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
pins={(r['component'],r['path']):r for r in json.loads((REPO/'manifests/printing-inputs.json').read_text())}
def pinned(component,path):
 b=(SRC/component/path).read_bytes();assert sha(b)==pins[(component,path)]['sha256'],(component,path);return b
PM=lambda path:pinned('PrinterManager',path)
stamp=int((datetime.datetime(2026,10,28)-datetime.datetime(1900,1,1)).total_seconds())*100
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name,cwd=REPO,**kw):
 with (ROOT/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,**kw)

# 1. The C preprocessor, as `cc -E` in the Makefile; RISC OS include names are
# dotted (h.Values) in RunImage and C-style (Values.h) in the Support files.
CPP=REPO/'build/c-toolchain-release/install/bin/gcc'
pre=ROOT/'preprocess';shutil.rmtree(pre,ignore_errors=True);pre.mkdir()
for h in ['Values','Trace']:
 (pre/('h.'+h)).write_bytes(PM('h/'+h));(pre/(h+'.h')).write_bytes(PM('h/'+h))
(pre/'sources.Sparrow').write_bytes(PM('sources/Sparrow'))
def preprocess(name):
 (pre/name).write_bytes(PM('sources/'+name))
 with (pre/('i.'+name)).open('wb') as f:subprocess.run([str(CPP),'-E','-P','-DDISC','-x','c',name],cwd=pre,stdout=f,check=True)
 return (pre/('i.'+name)).read_bytes()
# 2. Line numbers, as NUMBER: one per non-blank line, from 1 (TEXTLOAD would
# number unnumbered text in tens, past BASIC's last line for RunImage).
def number(text):
 lines=[l.rstrip() for l in text.decode('latin1').split('\n')];lines=[l for l in lines if l.strip()]
 assert len(lines)<65279
 return ''.join(f'{i} {l}\n' for i,l in enumerate(lines,1)).encode('latin1')
runimage_text=number(preprocess('RunImage'));CLASSES=['DP','LJ','PS'];support_text={c:number(preprocess('Support'+c)) for c in CLASSES}
# 3. Constants: CONST_name% becomes its value. h.ConstVals gives them as
# running offsets; h.Values, the preprocessor's copy, holds every one computed.
values={m.group(1):m.group(2) for m in re.finditer(r'^#define\s+CONST_([A-Za-z_0-9]+)\s+(\S+)',PM('h/Values').decode('latin1'),re.M)}
used=set()
def const(m):used.add(m.group(1));return values[m.group(1)]
suppsrc=re.sub(r'CONST_([A-Za-z_0-9]+)%',const,PM('sources/SuppSrc').decode('latin1')).encode('latin1')
assert b'CONST_' not in suppsrc

# 4. Tokenise and crunch in the ROM's BASIC; run SuppSrc to assemble Code.
rom_root=REPO/'build/arclibre'
inputs={'nRunImage':File(runimage_text),**{'nSupport'+c:File(support_text[c]) for c in CLASSES},'SuppSrc':File(suppsrc),'DataFiles':{},'Out':{}}
disc,_=image(inputs,'PRNBUILD',b'PB',stamp)
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-printing-disc','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','BasicRunProbe'],'harness')
programs=[]
for n in [1,2]:
 p=ROOT/f'basic-{n}';shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(disc)
 run([REPO/'build/harness-printing-disc/release/BasicRunProbe',rom_root/'arclibre.rom',rom_root,p/'input.adf',p,
  '*Dir adfs::0.$','BASIC','TEXTLOAD "nRunImage"','WAIT:240','CRUNCH -1','WAIT:240','SAVE "Out.RunImage"','WAIT:20',
  *[x for c in CLASSES for x in [f'TEXTLOAD "nSupport{c}"','WAIT:60','CRUNCH -1','WAIT:60',f'SAVE "Out.Support{c}"','WAIT:10']],'QUIT','*BASIC -quit SuppSrc','WAIT:120'],f'basic-{n}')
 b=(p/'disc.adf').read_bytes();top=read_directory(b,4);out=read_directory(b,top['Out']['address']);data=read_directory(b,top['DataFiles']['address'])
 assert set(out)=={'RunImage'}|{'Support'+c for c in CLASSES} and set(data)=={'Code'},(out,data)
 got=lambda row:b[row['address']*256:row['address']*256+row['length']]
 programs.append((got(out['RunImage']),{c:got(out['Support'+c]) for c in CLASSES},got(data['Code'])))
assert programs[0]==programs[1],'two builds differ'
runimage,supports,code=programs[0]
for name,prog in [('RunImage',runimage)]+[('Support'+c,supports[c]) for c in CLASSES]:
 assert prog[:1]==b'\r' and prog.endswith(b'\r\xff'),name   # a tokenised BASIC program
(ROOT/'RunImage,ffb').write_bytes(runimage);(ROOT/'Code,ffd').write_bytes(code)
for c in CLASSES:(ROOT/f'Support{c},ffb').write_bytes(supports[c])
(ROOT/'Support,ffb').unlink(missing_ok=True)
print('RunImage',len(runimage),*[f'Support{c} {len(supports[c])}' for c in CLASSES],'Code',len(code),flush=True)

# 5. The disc: !Printers as the Makefile's install target, with its dp, lj and ps classes.
proof=json.loads((REPO/'build/printing/result.json').read_text());assert proof['status']=='PASS'
mods={r['component']:r for r in proof['modules']}
def module(c):
 b=(REPO/'build/printing/modules'/c/'module.bin').read_bytes();assert sha(b)==mods[c]['sha256'];return b
F=lambda data,ft,attr=0x11:File(data,ft,attr)
def printer_class(c):
 return {'PrData':F(PM(f'DataFiles/{c}/PrData,fc6'),0xfc6,0x13),'Template':F(PM(f'DataFiles/{c}/Template,fc6'),0xfc6),
 'Resources':{'!Sprites':F(PM(f'DataFiles/{c}/Resources/!Sprites,ff9'),0xff9),'!Sprites22':F(PM(f'DataFiles/{c}/Resources/!Sprites22,ff9'),0xff9),
  '!Sprites23':F(PM(f'DataFiles/{c}/Resources/!Sprites23,ff9'),0xff9),'Messages':F(PM(f'UK/{c}/Resources/Messages'),0xfff),
  'PaperRO':F(PM(f'DataFiles/{c}/Resources/PaperRO,fc6'),0xfc6),'Support':F(supports[c.upper()],0xffb),
  'Templates':F(PM(f'UK/{c}/Resources/Templates,fec'),0xfec),'Template3D':F(PM(f'UK/{c}/Resources/Template3D,fec'),0xfec)}}
dp=printer_class('dp');lj=printer_class('lj');ps=printer_class('ps')
# The PostScript font encodings and prologues, and the (empty) directory the
# PostScript support code keeps per-printer font lists in.
ps['Adobe']={n:F(PM('DataFiles/ps/Adobe/'+n),0xfff) for n in ['Special','Standard']}
ps['PSFiles']={n:F(PM('prolog/'+n),0xfff) for n in ['OldLatin1','PSepilog','PSprolog','PSprolog2','PStprolog','Selwyn','Sidney']}
ps['Printers']={}
app={'!Boot':F(PM('DataFiles/!Boot,feb'),0xfeb),'!Help':F(PM('UK/!Help'),0xfff),'!Run':F(PM('UK/!Run,feb'),0xfeb),'!RunImage':F(runimage,0xffb),
 '!Sprites':F(PM('UK/!Sprites,ff9'),0xff9),'!Sprites22':F(PM('UK/!Sprites22,ff9'),0xff9),'!Sprites23':F(PM('UK/!Sprites23,ff9'),0xff9),
 'Code':F(code,0xffd),'Messages':F(PM('UK/Messages'),0xfff),'PaperRO':F(PM('UK/PaperRO,fc6'),0xfc6),'SetPrint':F(module('PrinterManager'),0xffc),
 'Templates':F(PM('UK/Templates,fec'),0xfec),'Template3D':F(PM('UK/Template3D,fec'),0xfec),
 'Palettes':{n:F(PM('DataFiles/Palettes/'+n),0xfff) for n in '012'},'dp':dp,'lj':lj,'ps':ps,
 'Modules':{'PDriver':F(module('PDriver'),0xffa),'PDriverDP':F(module('PDModules'),0xffa),'PDriverPS':F(module('PDriverPS'),0xffa),'PDumperSpt':F(module('PDumperSpt'),0xffa)},
 'PDumpers':{'PDumperDM':F(module('PDumpers'),0xffa),'PDumperLJ':F(module('PDumperLJ'),0xffa)}}
defs={'FX-80':'Epson/FX-80','LW':'Apple/LW','LasJet-II':'HP/LasJet-II'}
tree={'!Printers':app,'PrintDefs':{n:F(pinned('PrintDefs',f'Resources/NonSTB/{p},fc6'),0xfc6) for n,p in defs.items()},'ReadMe':F((SRC/'ArcLibre/printing/ReadMe').read_bytes(),0xfff)}
disc,rows=image(tree,'Printing',b'PR',stamp)
(ROOT/'arclibre-printing.adf').write_bytes(disc)
# The 4 MB ROM's copy: !Printers as Apps.!Printers in ResourceFS, without
# Modules and PDumpers (those modules are joined into that ROM, where the
# support code finds them).
def resource_block(node,prefix):
 out=bytearray()
 for name in sorted(node,key=str.lower):
  v=node[name]
  if name in ('Modules','PDumpers') and prefix=='Apps.!Printers':continue
  if isinstance(v,dict):out+=resource_block(v,prefix+'.'+name);continue
  data=bytes(v.data);nm=(prefix+'.'+name).encode()+b'\0';nm+=bytes(-len(nm)%4)
  out+=struct.pack('<5I',24+len(nm)+((len(data)+3)&~3),0xfff00000|(v.filetype<<8),0,len(data),3)+nm+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)
 return out
rom_resources=bytes(resource_block(app,'Apps.!Printers'))+bytes(4)
(ROOT/'rom-resources.bin').write_bytes(rom_resources)
# The printing gates' negative controls: the same disc without PDumperDM,
# without PDumperLJ, and without PDriverPS.
def without(folder,name):
 saved=app[folder].pop(name);b,_=image(tree,'Printing',b'PR',stamp);app[folder][name]=saved;return b
negative=without('PDumpers','PDumperDM');negative_lj=without('PDumpers','PDumperLJ');negative_ps=without('Modules','PDriverPS')
(ROOT/'negative-without-dumper.adf').write_bytes(negative);(ROOT/'negative-without-pdumperlj.adf').write_bytes(negative_lj);(ROOT/'negative-without-pdriverps.adf').write_bytes(negative_ps)
(ROOT/'disc.json').write_text(json.dumps(dict(status='PASS',image='build/printing-disc/arclibre-printing.adf',sha256=sha(disc),bytes=len(disc),format='ADFS D (old map) 800K',disc_name='Printing',
 files=rows,modules=proof['modules'],interpreter='ROM BASIC 1.14 under MacArch',rom_sha256=sha((rom_root/'arclibre.rom').read_bytes()),preprocessor='bundled GCC 3.4.6 cpp, -E -P -DDISC',
 programs=dict(runimage=dict(bytes=len(runimage),sha256=sha(runimage)),**{'support_'+c.lower():dict(bytes=len(supports[c]),sha256=sha(supports[c])) for c in CLASSES},code=dict(bytes=len(code),sha256=sha(code))),
 constants_substituted=sorted(used),identical_builds=2,free_bytes=int.from_bytes(disc[256:259],'little')*256,
 negative_without_dumper_sha256=sha(negative),negative_without_pdumperlj_sha256=sha(negative_lj),negative_without_pdriverps_sha256=sha(negative_ps),rom_resources_sha256=sha(rom_resources)),indent=2)+'\n')
print('floppy:',ROOT/'arclibre-printing.adf',sha(disc),sum(r['bytes'] for r in rows),'bytes in files',flush=True)
