#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""ARM3Support: the ARM3 cache on an ARM3, dormant on an ARM2.

ARM3Probe boots the delivered ROM on an emulated ARM3 and reads the real
cache controller (CP15) after each command typed at the F12 command line:
the cache is on at the desktop with the 3.60 kernel's default areas; a BASIC
loop runs several times faster with it on; Cache_Control/_Cacheable/
_Updateable/_Disruptive/_Flush, *Cache and *Configure Cache act on the
controller and CMOS RAM; *RMReInit applies the configured state. On an ARM2
the same ROM boots normally with the module dormant (commands and SWIs
unknown). The negative control is the ROM without ARM3Support on an ARM3:
the cache stays off, as the kernel does not enable it.
"""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/arm3-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-arm3','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','ARM3Probe'],'harness')
exe=R/'build/harness-arm3/release/ARM3Probe'
CACHEABLE,UPDATEABLE,DISRUPTIVE=0xFC007CFF,0x00007FFF,0xF0000000
LOOP='T%=TIME:FOR I%=1 TO 100000:NEXT:PRINT "{} ";TIME-T%'
ARM3=['*Cache','BASIC',LOOP.format('ON'),
 'SYS "Cache_Control",0,&FFFFFFFE TO A%:PRINT "OLD ";A%',LOOP.format('OFF'),
 'SYS "Cache_Control",1,-1 TO A%:PRINT "OLD ";A%',
 'SYS "Cache_Cacheable",0,-1 TO A%:SYS "Cache_Updateable",0,-1 TO B%:SYS "Cache_Disruptive",0,-1 TO C%:PRINT "AREAS ";~A%;" ";~B%;" ";~C%',
 'SYS "Cache_Cacheable",&100,-1 TO A%:SYS "Cache_Cacheable",0,-1 TO B%:PRINT "TOGGLED ";~B%',
 'SYS "Cache_Cacheable",&100,-1:SYS "Cache_Flush":PRINT "FLUSHED"','QUIT',
 '*Cache Off','*Cache','*Cache On','*Cache Sideways',
 '*Status Cache','*Configure Cache Off','*Status Cache','*Configure Cache Maybe',
 '*RMReInit ARM3Support','*Cache','*Configure Cache On','*RMReInit ARM3Support','*Cache']
ARM2=['*Cache','BASIC','SYS "Cache_Flush"','QUIT','*ROMModules']
NEGATIVE=['*Cache','BASIC',LOOP.format('LOOP'),'QUIT']
def trial(rom_root,cpu,cmds,name):
 p=out/name;shutil.rmtree(p,ignore_errors=True)
 run([exe,rom_root/'arclibre.rom',rom_root,cpu,p,*cmds],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((rom_root/'arclibre.rom').read_bytes()),r
 assert not r['errors'],r['errors']
 return p,r
def screen(r,i):return '\n'.join(l.rstrip() for l in r['screens'][i] if l.strip())
def after(r,i):
 """The lines printed after command i's echo."""
 s=r['screens'][i];cmd=r['commands'][i][:70]
 j=max(k for k,l in enumerate(s) if cmd in l)
 return '\n'.join(l.rstrip() for l in s[j+1:] if l.strip() and not l.startswith('?'))
def number(r,i,tag):return int(re.search(tag+r' +(-?\d+)',after(r,i)).group(1))
def arm3(n):
 p,r=trial(root,'ARM3',ARM3,f'arm3-{n}');c=r['commands'];at=lambda cmd,k=0:[i for i,x in enumerate(c) if x==cmd][k];st=lambda i:r['states'][i]
 d=r['desktop'];assert d['enabled'] and (d['cacheable'],d['updateable'],d['disruptive'])==(CACHEABLE,UPDATEABLE,DISRUPTIVE),d
 assert d['control']==3 and d['cmos_c3']&0x20==0,d
 assert after(r,at('*Cache')).startswith('Cache on'),after(r,0)
 on=number(r,at(LOOP.format('ON')),'ON');off=number(r,at(LOOP.format('OFF')),'OFF')
 assert number(r,c.index('SYS "Cache_Control",0,&FFFFFFFE TO A%:PRINT "OLD ";A%'),'OLD')==3 and not st(c.index(LOOP.format('OFF')))['enabled']
 assert number(r,c.index('SYS "Cache_Control",1,-1 TO A%:PRINT "OLD ";A%'),'OLD')==2 and st(c.index('SYS "Cache_Control",1,-1 TO A%:PRINT "OLD ";A%'))['control']==3
 assert off>=3*on,(on,off)
 areas=after(r,[i for i,x in enumerate(c) if x.endswith('"AREAS ";~A%;" ";~B%;" ";~C%')][0])
 assert re.search(r'AREAS FC007CFF 7FFF F0000000',areas),areas
 i=[i for i,x in enumerate(c) if 'TOGGLED' in x][0];assert 'TOGGLED FC007DFF' in after(r,i) and st(i)['cacheable']==CACHEABLE^0x100
 i=[i for i,x in enumerate(c) if 'FLUSHED' in x][0];assert 'FLUSHED' in after(r,i) and st(i)['cacheable']==CACHEABLE
 assert not st(at('*Cache Off'))['enabled'] and after(r,at('*Cache',1)).startswith('Cache off')
 assert st(at('*Cache On'))['enabled'] and st(at('*Cache On'))['control']==3
 assert 'Syntax: *Cache [On|Off]' in after(r,at('*Cache Sideways')) and st(at('*Cache Sideways'))['enabled']
 assert after(r,at('*Status Cache')).startswith('Cache      On') and st(at('*Configure Cache Off'))['cmos_c3']&0x20
 assert after(r,at('*Status Cache',1)).startswith('Cache      Off') and st(at('*Configure Cache Off'))['enabled'],'configuring does not change the running state'
 # V set with r0=0 from a configure keyword: the 3.60 kernel's wording.
 assert 'Configure option not recognised' in after(r,at('*Configure Cache Maybe')) and st(at('*Configure Cache Maybe'))['cmos_c3']&0x20
 assert not st(at('*RMReInit ARM3Support'))['enabled'] and after(r,at('*Cache',2)).startswith('Cache off'),'reinitialised with the configured state'
 assert st(at('*RMReInit ARM3Support',1))['enabled'] and after(r,at('*Cache',3)).startswith('Cache on')
 return dict(desktop=d,control_values=[3,2,3],loop_centiseconds=dict(on=on,off=off),speedup_at_least=3,areas=dict(cacheable=CACHEABLE,updateable=UPDATEABLE,disruptive=DISRUPTIVE),
  commands=['*Cache','*Cache On','*Cache Off','*Status Cache','*Configure Cache On|Off','*RMReInit ARM3Support'],swis=['Cache_Control','Cache_Cacheable','Cache_Updateable','Cache_Disruptive','Cache_Flush'])
def arm2(n):
 p,r=trial(root,'ARM2',ARM2,f'arm2-{n}');c=r['commands']
 assert 'cacheable' not in r['desktop'],'no cache controller on an ARM2'
 # No such command: *Cache runs a file of that name, and no disc is fitted.
 assert 'The disc drive is empty' in after(r,0),after(r,0)
 assert 'SWI name not known' in after(r,c.index('SYS "Cache_Flush"'))
 mods=screen(r,c.index('*ROMModules'));line=re.search(r'^\s*\d+ System ROM\s+ARM3Support\s+(\S+)\s+(\S+)$',mods,re.M)
 assert line and line.group(2)=='Dormant',mods[-300:]
 return dict(cache_command='The disc drive is empty (no such command)',swi='SWI name not known',status=line.group(2),version=line.group(1))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 a3=list(pool.map(arm3,COLD));a2=list(pool.map(arm2,COLD))
# Cold boots must agree; the loop's exact centiseconds may vary by one tick.
same([dict(x,loop_centiseconds=None) for x in a3],a2)
obs=dict(arm3=a3[0],arm2=a2[0])
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'ARM3')
run([sys.executable,R/'tools/build_arclibre_rom.py','--without-arm3'],'negative-rom')
neg=R/'build/arclibre-without-arm3';assert all(m['component']!='ARM3Support' for m in json.loads((neg/'rom-layout.json').read_text())['modules'])
p,r=trial(neg,'ARM3',NEGATIVE,'negative-without-arm3')
assert not r['desktop']['enabled'] and r['desktop']['control']==0,r['desktop']
assert 'The disc drive is empty' in after(r,0)
loop=number(r,r['commands'].index(LOOP.format('LOOP')),'LOOP');assert loop>=3*obs['arm3']['loop_centiseconds']['on'],loop
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_control=dict(rom_sha256=sha((neg/'arclibre.rom').read_bytes()),cache_enabled=False,control=0,loop_centiseconds=loop),
 limits=['MacArch models the ARM3 cache for timing only: it never returns stale data, so missing flushes cannot be detected here.',
  'Physical ARM3 hardware is untested.']))
print('ARM3 PASS',flush=True)
