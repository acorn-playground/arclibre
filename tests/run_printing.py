#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The printing disc: !Printers installs a printer of each class and a job prints through it.

PrintProbe boots the delivered ROM on an emulated A440/1 with the printing
floppy (build/printing-disc) in drive 0 and uses the real desktop: it opens
the floppy, double-clicks !Printers and drags a printer definition from
PrintDefs to its icon bar icon, which installs the printer (loading its
driver and dumper modules from the disc). At the command line a BASIC client
(tests/fixtures/PrintTest.bas) prints one page as an application does,
through PDriver_SelectJob on a file: a filled rectangle and a line of VDU 5
text. The host decodes the file and checks it, for each of !Printers' three
classes:

- dot matrix: an Epson FX-80 (PDriverDP, PDumperDM); its Epson commands
  are decoded into a bitmap (tests/epson_fixture.py);
- LaserJet: an HP LaserJet II (PDriverDP, PDumperLJ); its PCL raster
  graphics are decoded into a bitmap (tests/pcl_fixture.py);
- PostScript: an Apple LaserWriter (PDriverPS); its document structure is
  checked, and the job, prologue and all, is run by a small independent
  PostScript interpreter that rasterises the page at 300 dpi
  (tests/postscript_fixture.py).

The text is read back from each bitmap as the kernel's system font glyphs
(tests/sysfont_fixture.py). The negative controls are the disc without
PDumperDM, without PDumperLJ and without PDriverPS: installing the printer
that needs it fails and nothing is printed.
"""
import collections,concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tests'))
from verify_filer_disc import read_directory
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/printing-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-printing','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','PrintProbe'],'harness')
exe=R/'build/harness-printing/release/PrintProbe'
# The disc is built from the pinned sources with this ROM's BASIC, as the basic-utilities gate builds Alarm's.
run([sys.executable,R/'tools/build_printing_disc.py'],'printing-disc')
disc_info=json.loads((R/'build/printing-disc/disc.json').read_text());assert disc_info['status']=='PASS'
disc=(R/'build/printing-disc/arclibre-printing.adf').read_bytes();assert sha(disc)==disc_info['sha256']
program=[l for l in (R/'tests/fixtures/PrintTest.bas').read_text().splitlines() if l.strip()]
# OS coordinates on the 640x256 desktop: the :0 icon, then in the floppy's
# directory viewer !Printers and PrintDefs, a definition in PrintDefs' viewer
# (FX-80, LasJet-II and LW, left to right), and !Printers' icon on the icon
# bar (the third icon).
DEFINITION={'dot_matrix':114,'laserjet':304,'postscript':492}
def steps(x):
 return ['CLICK:64,68','CLICK:94,928,2','WAIT:20','CLICK:282,928,2',f'DRAG:{x},900,280,76','WAIT:25',
  'F12','BASIC']+[f'{(i+1)*10} {l}' for i,l in enumerate(program)]+['RUN','WAIT:150','QUIT','']
def trial(image,name,printer):
 p=out/name;shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(image);s=steps(DEFINITION[printer])
 run([exe,root/'arclibre.rom',root,p/'input.adf',p,*s],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((root/'arclibre.rom').read_bytes()),r
 b=(p/'disc.adf').read_bytes();top=read_directory(b,4)
 printed=b[top['PrintOut']['address']*256:top['PrintOut']['address']*256+top['PrintOut']['length']] if 'PrintOut' in top else None
 screen='\n'.join(l.rstrip() for l in r['screens'][s.index('WAIT:150')] if l.strip())
 return r,printed,screen

from epson_fixture import epson
from pcl_fixture import pcl
from postscript_fixture import render
from sysfont_fixture import find_text

def printed_page(n,printer,driver):
 r,printed,screen=trial(disc,f'{printer}-{n}',printer)
 assert not r['errors'],r['errors']
 assert driver in screen,screen
 assert printed is not None and f'PRINTED {len(printed)}' in screen,screen
 return printed

def dot_matrix(n):
 printed=printed_page(n,'dot_matrix','DRIVER 7 120 72')
 dots,commands=epson(printed)
 assert commands[0]=='C70' and commands[-2:]==['FF','@'],commands[:3]+commands[-3:]
 # The rectangle: 4 x 1 inches is 480 columns by 72 dots, solidly filled.
 ys=sorted({y for _,y in dots});bottom=max(ys)
 rect=[(x,y) for x,y in dots if y>bottom-72]
 x0=min(x for x,_ in rect);x1=max(x for x,_ in rect)
 assert x1-x0+1==480,(x0,x1)
 assert len(rect)==480*72,len(rect)
 # VDU 5 text "ArcLibre" in the system font above it: 8 characters of 16
 # OS units (128 = 85 columns), from y=300 OS units (an inch is 180).
 text=[(x,y) for x,y in dots if y<=bottom-72]
 tx0=min(x for x,_ in text);tx1=max(x for x,_ in text);ty0=min(y for _,y in text);ty1=max(y for _,y in text)
 assert tx0>=x0 and 70<=tx1-tx0<=90 and 8<=ty1-ty0+1<=14,(tx0,tx1,ty0,ty1)
 assert 0.2<len(text)/((tx1-tx0+1)*(ty1-ty0+1))<0.8,'glyphs, not a block'
 return dict(printout_bytes=len(printed),printout_sha256=sha(printed),driver='type 7 (dot matrix), 120 x 72 dpi',
  rectangle=dict(columns=480,dots=72,filled=True,left_column=x0),text=dict(columns=tx1-tx0+1,dots=ty1-ty0+1,black_dots=len(text)),
  commands=sorted(set(commands)))

def laserjet(n):
 printed=printed_page(n,'laserjet','DRIVER 7 150 150')
 dots,commands,raster=pcl(printed)
 # Reset, 150 dpi raster graphics 600 dots wide, uncompressed rows, end of
 # graphics, form feed, left margin back to column 0 and reset.
 assert commands[0]=='E' and commands[-4:]==['*rB','FF','&a0C','E'] and raster['resolution']==150 and raster['width']==600,(commands[:8],commands[-4:],raster)
 assert '*t150R' in commands and '*r1A' in commands and not [c for c in commands if c.startswith('*b') and c!='*bW'],sorted(set(commands))
 # The rectangle: 4 x 1 inches is 600 columns by 150 rows at 150 dpi (one
 # more row: RECTANGLE FILL includes its top edge), solidly filled.
 rows=collections.Counter(y for _,y in dots);full=sorted(y for y in rows if rows[y]==600)
 assert full and full==list(range(full[0],full[-1]+1)) and len(full) in (150,151) and full[-1]==max(rows),full[:3]
 assert {x for x,y in dots if y in full}==set(range(600))
 # The text above it reads "ArcLibre" in the system font, at 150/180 dots an OS unit.
 text={(x,y) for x,y in dots if y<full[0]}
 words,corner=find_text(text,150/180,150/180,8);assert words=='ArcLibre',words
 return dict(printout_bytes=len(printed),printout_sha256=sha(printed),driver='type 7 (PDriverDP with PDumperLJ), 150 x 150 dpi',
  raster=dict(resolution=150,width=600,start_300dpi=list(raster['start']),rows=commands.count('*bW')),
  rectangle=dict(columns=600,rows=len(full),filled=True,top_row=full[0]),text=dict(reads=words,top_left=list(corner),black_dots=len(text)),
  commands=sorted(set(commands)))

PROLOGUE=(R/'src/PrinterManager/prolog/PSprolog2').read_bytes();EPILOGUE=(R/'src/PrinterManager/prolog/PSepilog').read_bytes()
def postscript(n):
 printed=printed_page(n,'postscript','DRIVER 0 300 300')
 lines=printed.decode('latin1').split('\n')
 # The document structure PDriverPS 4.35 writes, with the LaserWriter
 # definition's setup and its own prologue and epilogue files.
 assert lines[0]=='%!PS-Adobe-2.0' and lines[1]=='%%Creator: PostScript PDriver module 4.35',lines[:2]
 order=['%%BeginProlog','%%EndProlog','%%BeginSetup','%%BeginFeature: ManualFeed False','%%BeginFeature: PageSize A4','%%EndSetup','%%Page: ? 1','%%PageBoundingBox: 72 576 360 720',
  '%%Trailer','%%Pages: 1','%%BoundingBox: 72 576 360 720','%% PDriverPS Epilogue']
 at=[lines.index(l) for l in order];assert at==sorted(at),order
 # The job ends with the epilogue's (\004)cvn{}def, which makes the
 # end-of-job Ctrl-D sent after it a harmless name, then the Ctrl-D.
 assert PROLOGUE.split(b'\n')[1] in printed and printed.endswith(EPILOGUE.rstrip().split(b'\n')[-1]+b'\n\x04'),'prologue and epilogue files'
 assert {'/Copies {/#copies ED showpage} BD','/Rc {Bx VFl} BD'}<={l.strip() for l in lines},'the prologue defines the page operators'
 page=lines[lines.index('%%Page: ? 1')+1:lines.index('%%Trailer')]
 # The page: the black rectangle as a path filled by Rc, the text shown by
 # V in the driver's bitmap font, and one copy of the page shown.
 assert '0 G 720 180 0 0 Rc' in page and '(ArcLibre)' in page and page[page.index('(ArcLibre)')+1].endswith(' V') and page[-2:]==['1 Copies','end'],page
 # Rasterised at 300 dpi: one page, the rectangle 4 x 1 inches (1200 x 300
 # pixels, plus at most the driver's 2 OS unit outline stroke), its bottom
 # left corner 1 inch from the left and 8 inches up the page.
 pages,_=render(printed,300);assert len(pages)==1 and pages[0]['copies']==1,len(pages)
 black={k for k,v in pages[0]['paint'].items() if v<0.5}
 rows=collections.Counter(y for _,y in black);full=sorted(y for y in rows if rows[y]>=1200)
 assert full==list(range(2400,full[-1]+1)) and 300<=len(full)<=304,(full[:2],len(full))
 assert {x for x,y in black if y in full}==set(range(300,1500)),'4 inches from 1 inch'
 text={(x,y) for x,y in black if y>full[-1]}
 words,corner=find_text(text,300/180,300/180,8,down=False);assert words=='ArcLibre',words
 return dict(printout_bytes=len(printed),printout_sha256=sha(printed),driver='type 0 (PostScript), 300 x 300 dpi',
  structure=order,page_operators=[l for l in page if l in ('0 G 720 180 0 0 Rc','(ArcLibre)','1 Copies')],
  rendered=dict(dpi=300,pages=1,rectangle=dict(columns=1200,rows=len(full),left=300,bottom=2400,filled=True),text=dict(reads=words,top_left=list(corner),black_pixels=len(text))))

CLASSES={'dot_matrix':dot_matrix,'laserjet':laserjet,'postscript':postscript}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 jobs={(c,n):pool.submit(f,n) for c,f in CLASSES.items() for n in COLD};results={k:j.result() for k,j in jobs.items()}
for c in CLASSES:same([results[(c,n)] for n in COLD])
obs={c:results[(c,COLD[0])] for c in CLASSES}
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'Printing')
# Negative controls: the same disc without the module each class needs.
NEGATIVES=[('dot_matrix','negative-without-dumper','PDumperDM','negative_without_dumper_sha256'),('laserjet','negative-without-pdumperlj','PDumperLJ','negative_without_pdumperlj_sha256'),
 ('postscript','negative-without-pdriverps','PDriverPS','negative_without_pdriverps_sha256')]
def negative(row):
 printer,name,module,key=row
 image=(R/f'build/printing-disc/{name}.adf').read_bytes();assert sha(image)==disc_info[key]
 r,printed,screen=trial(image,name,printer)
 assert printed is None or 'PRINTERR' in screen,screen
 errors=[e['error'] for e in r['errors']];assert f'Module {module} not found' in errors,errors
 return printer,dict(missing=module,errors=errors,printout=None if printed is None else len(printed))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:negatives=dict(pool.map(negative,NEGATIVES))
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),disc_sha256=sha(disc),emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_controls=negatives,
 limits=['Output goes to a file through PDriver_SelectJob; the parallel port itself is covered by the hardware gate (it reads BUSY in MacArch).',
  'One definition per class (Epson FX-80, HP LaserJet II, Apple LaserWriter) at its default settings; colour, outline fonts, sprites and JPEGs in print jobs are not exercised.',
  'The PostScript is checked by an independent interpreter of the operators the job uses, not by a PostScript printer or Ghostscript; MakePSFont (outline font mapping and downloading) is not on the disc.',
  'Physical printers are untested.']))
print('Printing PASS',flush=True)
