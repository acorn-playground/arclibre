#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The 4 MB ROM: what the 2 MB ROM ships on discs, working from ROM.

build/arclibre-4m (make arclibre-rom-4m) is the delivered 2 MB ROM plus
DOSFS (in its original ROM form), !Alarm, and printing: !Printers in
ResourceFS with PDriver, PDriverDP, PDriverPS, PDumperSupport, PDumperDM and
PDumperLJ. On an
emulated A440/1, three cold boots each:

- DOSFS from ROM (DOSFSProbe, nothing *RMLoaded): its base address is in
  ROM; it catalogues a host-made PC 720K disc and copies a file each way,
  checked with the independent FAT parser (tests/fat12_fixture.py). *FX 0
  first, which must give manifests/release.json's version and date.
- The desktop (PrintProbe): !Printers and !Alarm double-clicked in
  Resources:$.Apps; the Epson FX-80 dragged to !Printers from a floppy that
  holds only its definition, so the dot-matrix support code finds the
  modules in ROM; the task list shows both; the BASIC client prints the
  printing gate's page, decoded on the host as there.

The negative control is the delivered 2 MB ROM: the same module checks
report DOSFS, the printing modules and !Alarm missing.
"""
import concurrent.futures,hashlib,json,os,pathlib,random,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tests'))
import fat12_fixture,hfe_fixture
from adfs_image import File,image
from verify_filer_disc import read_directory
from epson_fixture import epson
root=R/'build/arclibre-4m';normal=R/'build/arclibre'
out=R/'build/rom-4m-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
layout=json.loads((root/'rom-layout.json').read_text());rom=(root/'arclibre.rom').read_bytes()
assert len(rom)==4194304 and sha(rom)==layout['rom_sha256']
components={m['component']:m for m in layout['modules']}
for c in ['DOSFS','Alarm','PDriver','PDModules','PDumperSpt','PDumpers','PDriverPS','PDumperLJ','Podule','Econet','Draw','Paint','Edit']:assert c in components,c
for product in ['DOSFSProbe','PrintProbe']:
 run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-rom-4m','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product',product],'harness-'+product)
bin_=R/'build/harness-rom-4m/release'

# --- DOSFS from ROM ----------------------------------------------------------
module_disc=(R/'build/dosfs/arclibre-dosfs.adf').read_bytes()
README=(R/'src/ArcLibre/dosfs/ReadMe').read_bytes()
rng=random.Random(1996);DATA=bytes(rng.randrange(256) for _ in range(5000))
pc=fat12_fixture.make({'HELLO.TXT':b'Hello from a host-made FAT12 disc\r\n','DATA.BIN':DATA},label='HOSTDISC');pc_hfe=hfe_fixture.hfe(pc)
release=json.loads((R/'manifests/release.json').read_text())
TITLE=f"ArcLibre {release['version']} ({release['date']}), compatible with RISC OS 3.11"
DOSFS_COMMANDS=['*FX 0','*Help DOSFS','*Cat ADFS::1.$','*Copy ADFS::1.$.DATA/BIN ADFS::0.$.DataCopy ~C~V','*Copy ADFS::0.$.ReadMe ADFS::1.$.README/TXT ~C~V',
 'BASIC','SYS "OS_Module",18,"DOSFS" TO ,,,B%:PRINT "BASE ";~B%','QUIT','DUMP:written']
def after(r,i):
 cmd=r['commands'][i];lines=r['screens'][i]
 j=max(k for k,l in enumerate(lines) if l[:1] in '*>' and l[1:].startswith(cmd[:79]))
 return '\n'.join(l.rstrip() for l in lines[j+(len(cmd)+80)//80:] if l.strip() and l.strip() not in ['*','>','*_','>_'])
def dosfs(n):
 p=out/f'dosfs-{n}';shutil.rmtree(p,ignore_errors=True);p.mkdir()
 (p/'drive0.adf').write_bytes(module_disc);(p/'drive1.hfe').write_bytes(pc_hfe)
 run([bin_/'DOSFSProbe',root/'arclibre.rom',root,p/'drive0.adf',p/'drive1.hfe',p,*DOSFS_COMMANDS],p.name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==layout['rom_sha256'],r
 assert not r['drive1_faults'],r['drive1_faults'][:4]
 c=DOSFS_COMMANDS.index
 title=after(r,c('*FX 0')).splitlines()[0];assert title==TITLE,title
 help_=after(r,c('*Help DOSFS'));assert 'Module is: DOSFS' in help_ and '0.62 (28 Oct 2026) ArcLibre' in help_ and 'disc' not in help_,help_
 cat=after(r,c('*Cat ADFS::1.$'));assert 'Dir. ADFS::HOSTDISC.$' in cat and 'DATA/BIN' in cat and 'HELLO/TXT' in cat,cat
 base=int(re.search(r'BASE ([0-9A-F]+)',after(r,DOSFS_COMMANDS.index('SYS "OS_Module",18,"DOSFS" TO ,,,B%:PRINT "BASE ";~B%'))).group(1),16)
 assert base==components['DOSFS']['base'],(hex(base),hex(components['DOSFS']['base']))
 adfs=read_directory((p/'disc0.adf').read_bytes(),4);b=(p/'disc0.adf').read_bytes()
 assert b[adfs['DataCopy']['address']*256:adfs['DataCopy']['address']*256+adfs['DataCopy']['length']]==DATA
 v=fat12_fixture.Volume((p/'written.img').read_bytes());assert v.files().get('README.TXT')==README,sorted(v.files())
 return dict(title=title,help=next(l for l in help_.splitlines() if l.startswith('Module is')),base=hex(base),catalogue=sorted(re.findall(r'(\S+)\s+WR/',cat)),copied_from_pc=len(DATA),copied_to_pc=len(README))

# --- The desktop: !Printers and !Alarm from ROM, printing --------------------
stamp=int((__import__('datetime').datetime(2026,10,28)-__import__('datetime').datetime(1900,1,1)).total_seconds())*100
fx80=(R/'src/PrintDefs/Resources/NonSTB/Epson/FX-80,fc6').read_bytes()
defs_disc,_=image({'PrintDefs':{'FX-80':File(fx80,0xfc6)}},'PrintDefs',b'PD',stamp)
program=[l for l in (R/'tests/fixtures/PrintTest.bas').read_text().splitlines() if l.strip()]
CHECKS=['*RMEnsure DOSFS 0.62 Echo DOSFS missing','*RMEnsure PDriver 3.25 Echo PDriver missing','*RMEnsure PDriverDP 4.00 Echo PDriverDP missing',
 '*RMEnsure PDumperSupport 1.00 Echo PDumperSupport missing','*RMEnsure PDumperDM 0.10 Echo PDumperDM missing','*RMEnsure PDriverPS 4.35 Echo PDriverPS missing','*RMEnsure PDumperLJ 1.14 Echo PDumperLJ missing','*RMEnsure !Alarm 2.00 Echo Alarm missing']
TASKS='DIM b% 256:t%=0:REPEAT:SYS "TaskManager_EnumerateTasks",t%,b%,256 TO t%,e%:FOR p%=b% TO e%-16 STEP 16:q%=p%!4:PRINT "TASK ";:WHILE ?q%>=32:VDU ?q%:q%+=1:ENDWHILE:PRINT:NEXT:UNTIL t%<0'
# OS coordinates: Apps on the icon bar; !Printers and !Alarm in the Apps
# viewer; the floppy; PrintDefs (its first item) and FX-80 in their viewers;
# !Printers' icon bar icon (the third icon).
STEPS=['CLICK:162,68','CLICK:98,680,2','WAIT:20','CLICK:98,932,2','WAIT:10','CLICK:64,68','CLICK:222,928,2','DRAG:240,900,280,76','WAIT:25',
 'F12',*CHECKS,'BASIC',TASKS]+[f'{(i+1)*10} {l}' for i,l in enumerate(program)]+['RUN','WAIT:150','QUIT','']
def desktop(n,rom_root=root,steps=STEPS,name=None):
 p=out/(name or f'desktop-{n}');shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(defs_disc)
 run([bin_/'PrintProbe',rom_root/'arclibre.rom',rom_root,p/'input.adf',p,*steps],p.name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS'
 return p,r
def screen_after(r,step):
 lines=r['screens'][r['steps'].index(step)]
 return '\n'.join(l.rstrip() for l in lines if l.strip())
# Lines RMEnsure's Echo printed (not the echoed commands, which contain them).
def missing_lines(text):return re.findall(r'^(\S+) missing$',text,re.M)
def positive(n):
 p,r=desktop(n)
 assert not r['errors'],r['errors']
 checks=screen_after(r,CHECKS[-1]);assert CHECKS[0] in checks and not missing_lines(checks),checks
 tasks=screen_after(r,TASKS);names=re.findall(r'^TASK (.+)$',tasks,re.M)
 assert 'Printer Manager' in names and 'Alarm' in names,names
 done=screen_after(r,'WAIT:150');assert 'DRIVER 7 120 72' in done and 'PRINTED' in done,done[-400:]
 b=(p/'disc.adf').read_bytes();top=read_directory(b,4);e=top['PrintOut'];printed=b[e['address']*256:e['address']*256+e['length']]
 assert f'PRINTED {len(printed)}' in done
 dots,commands=epson(printed);bottom=max(y for _,y in dots);rect=[(x,y) for x,y in dots if y>bottom-72]
 x0=min(x for x,_ in rect);x1=max(x for x,_ in rect);assert x1-x0+1==480 and len(rect)==480*72,(x0,x1,len(rect))
 assert commands[0]=='C70' and commands[-2:]==['FF','@']
 return dict(tasks=sorted(set(names)),printout_bytes=len(printed),printout_sha256=sha(printed),rectangle=dict(columns=480,dots=72,filled=True))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 d=list(pool.map(dosfs,COLD));w=list(pool.map(positive,COLD))
same(d,w)
obs=dict(rom_bytes=len(rom),used_bytes=layout['used_bytes'],dosfs=d[0],desktop=w[0],
 added_modules={c:dict(base=hex(components[c]['base']),bytes=components[c]['length']) for c in ['Alarm','PDriver','PDModules','PDumperSpt','PDumpers','PDriverPS','PDumperLJ','DOSFS']})
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'4 MB ROM')
# Negative control: the 2 MB ROM has none of them in ROM.
p,r=desktop(0,normal,['F12',*CHECKS],'negative-2mb')
missing=missing_lines(screen_after(r,CHECKS[-1]))
assert missing==['DOSFS','PDriver','PDriverDP','PDumperSupport','PDumperDM','PDriverPS','PDumperLJ','Alarm'],missing
finish(out,dict(status='PASS',rom_sha256=layout['rom_sha256'],emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_control=dict(rom='build/arclibre (2 MB)',rom_sha256=sha((normal/'arclibre.rom').read_bytes()),missing=['DOSFS','PDriver','PDriverDP','PDumperSupport','PDumperDM','PDriverPS','PDumperLJ','!Alarm']),
 limits=['The other release gates run on the 2 MB ROM; the 4 MB ROM shares every module and resource of it, with the additions above appended.',
  "The kernel is the 2 MB ROM's (IMAGESIZE 2048K); like RISC OS 3.11's it has no OS_Memory to report a ROM size.",
  '!Printers in ResourceFS cannot save its choices (ResourceFS is read-only).',
  'Physical 4 MB ROM boards are untested.']))
print('4 MB ROM PASS',flush=True)
