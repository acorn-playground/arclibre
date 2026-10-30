#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The 2 MB ROM's shipped floppy: DOSFS, !Alarm and !Printers from one disc.

tools/build_extras_disc.py joins the DOSFS, Alarm and printing floppies,
each gated on its own (tests/run_dosfs.py, run_basic_utilities.py,
run_printing.py), into arclibre-extras.adf, checking every file against its
source disc. This gate runs the shipped disc itself: PrintProbe boots the
delivered 2 MB ROM to the desktop on an A440/1, three cold boots, with the
disc in drive 0, and at the real F12 command line

- reads *FX 0, which must name the version and date in manifests/release.json;
- loads DOSFS from the disc and reads its *Help;
- starts !Alarm and !Printers with *Filer_Run, as a double-click does,
  returns to the desktop, and lists the desktop's tasks through
  TaskManager_EnumerateTasks: Alarm and Printer Manager must be running, with no
  error box, and PDriver loaded from !Printers.Modules;
- opens the disc's directory, as you would, so the Filer runs !System's and
  !Scrap's !Boot: then Acorn C/C++'s installer's check (If "<System$Path>" =
  "" Then Error ...) passes, a module copied into <System$Dir>.Modules, as
  that installer does, is found in System:Modules, and a file saved as
  <Wimp$Scrap> is in <Wimp$ScrapDir>.

The negative control is the same disc without !Printers, !System and !Scrap:
Alarm still starts, Printer Manager is not a task and PDriver is not loaded,
and the installer's check fails.
"""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1]
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/extras-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-extras','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','PrintProbe'],'harness')
exe=R/'build/harness-extras/release/PrintProbe'
# --build (development checks): rebuild the three discs and this one first. The
# release suite builds them beforehand (make extras-disc), since its printing
# gate rewrites the printing disc while it runs.
if '--build' in sys.argv:
 for tool in ['build_dosfs.py','build_alarm_disc.py','build_printing_disc.py','build_extras_disc.py']:run([sys.executable,R/'tools'/tool],tool.removesuffix('.py'))
info=json.loads((R/'build/extras-disc/disc.json').read_text());disc=(R/'build/extras-disc/arclibre-extras.adf').read_bytes()
assert info['status']=='PASS' and sha(disc)==info['sha256']
negative=(R/'build/extras-disc/negative-without-printers.adf').read_bytes();assert sha(negative)==info['negative_without_printers_sha256']
release=json.loads((R/'manifests/release.json').read_text())
TITLE=f"ArcLibre {release['version']} ({release['date']}), compatible with RISC OS 3.11"
TASKS='DIM B% 512:SYS "TaskManager_EnumerateTasks",0,B%,512 TO ,E%:FOR P%=B% TO E%-16 STEP 16:N%=P%!4:N$="":REPEAT:N$+=CHR$?N%:N%+=1:UNTIL ?N%<32:PRINT "TASK ";N$:NEXT'
MODULES=[f'SYS "XOS_Module",18,"{m}" TO ;F%:PRINT "MODULE {m} ";1-(F% AND 1)' for m in ['DOSFS','PDriver']]
IFSYS='*If "<System$Path>" = "" Then Echo NOSYSTEM Else Echo SYSTEM'
COPYMOD='*Copy ADFS::ArcLibre.$.DOSFS <System$Dir>.Modules.DOSFS ~C~V'
SAVESCRAP='*Save <Wimp$Scrap> 8000 +100'
STEPS=['F12','*FX 0','*RMLoad ADFS::ArcLibre.$.DOSFS','*Help DOSFS','*Filer_OpenDir ADFS::ArcLibre.$','*Filer_Run ADFS::ArcLibre.$.!Alarm','*Filer_Run ADFS::ArcLibre.$.!Printers','','WAIT:30',
 'F12',IFSYS,'*Show System$Path','*Show Wimp$Scrap',COPYMOD,'*Ex System:Modules',SAVESCRAP,'*Ex <Wimp$ScrapDir>','BASIC',TASKS,*MODULES,'QUIT','']
def after(r,step):
 """The lines printed after a step's echo, which wraps at 80 columns after its prompt."""
 i=r['steps'].index(step);s=r['screens'][i]
 j=max(k for k,l in enumerate(s) if step[:70] in l)+(len(step)+1+79)//80
 return [l.rstrip() for l in s[j:] if l.strip() and l.strip() not in ['*','>','*_','>_']]
def trial(name,image):
 p=out/name;shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'disc.adf').write_bytes(image)
 run([exe,root/'arclibre.rom',root,p/'disc.adf',p/'run',*STEPS],name)
 r=json.loads((p/'run/result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((root/'arclibre.rom').read_bytes()),r
 tasks=sorted(l.split(' ',1)[1] for l in after(r,TASKS) if l.startswith('TASK '))
 modules={m:after(r,s)[0] for m,s in zip(['DOSFS','PDriver'],MODULES)}
 system=dict(check=after(r,IFSYS)[:1],path=after(r,'*Show System$Path')[:1],scrap=after(r,'*Show Wimp$Scrap')[:1],
  modules=[l.split()[0] for l in after(r,'*Ex System:Modules') if l.split()],scrapdir=[l.split()[0] for l in after(r,'*Ex <Wimp$ScrapDir>') if l.split()])
 return r,dict(title=after(r,'*FX 0')[0],dosfs_help=after(r,'*Help DOSFS')[:2],tasks=tasks,modules=modules,system=system,errors=[e['error'] for e in r['errors']])
def positive(n):
 r,o=trial(f'cold-{n}',disc)
 assert o['title']==TITLE,o['title']
 assert o['dosfs_help'][0]=='==> Help on keyword DOSFS' and 'Module is: DOSFS' in o['dosfs_help'][1],o['dosfs_help']
 assert not o['errors'],o['errors']
 assert {'Alarm','Printer Manager'}<=set(o['tasks']),o['tasks']
 assert o['modules']=={'DOSFS':'MODULE DOSFS 1','PDriver':'MODULE PDriver 1'},o['modules']
 y=o['system']
 assert y['check']==['SYSTEM'] and y['path']==['System$Path : ADFS::ArcLibre.$.!System.'] and y['scrap']==['Wimp$Scrap : ADFS::ArcLibre.$.!Scrap.ScrapDir.ScrapFile'],y
 assert 'DOSFS' in y['modules'] and 'ScrapFile' in y['scrapdir'],y
 return o
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:obs=list(pool.map(positive,COLD))
same(obs)
probe_exit(out,root/'arclibre.rom',obs[0],'Extras disc')
_,neg=trial('negative-without-printers',negative)
assert 'Alarm' in neg['tasks'] and 'Printer Manager' not in neg['tasks'] and neg['modules']['PDriver']=='MODULE PDriver 0',neg
assert neg['system']['check']==['NOSYSTEM'],neg['system']
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),disc_sha256=info['sha256'],version=release['version'],title=TITLE,
 emulator_unchanged=True,guest_code_injection=False,observations=obs[0],
 negative_control=dict(disc='build/extras-disc/negative-without-printers.adf',disc_sha256=info['negative_without_printers_sha256'],tasks=neg['tasks'],pdriver_loaded=False,system_check=neg['system']['check']),
 limits=['!System and !Scrap are seen from the disc in drive 0; on a real machine they belong on a hard disc, which this gate does not use.','Each part is gated in depth on its own disc (DOSFS formats and writes, Alarm\'s alarms, printing to all three printer classes); this gate checks that the shipped disc holds them and that each starts from it.']))
print('Extras disc PASS',flush=True)
