#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""*Format and low-level writes through the delivered FileCore.

FileCore 3.60's EnsureFSLock asked FSLock (absent in RISC OS 3.11 and in
ArcLibre) about every SWI DiscOp write, so *Format and ADFS_DiscOp writes
failed. The delivered FileCore (ArcLibreDelivered in src/FileCore/s/GenSWIs)
skips floppies and treats a missing FSLock as no lock. At the real F12 command
line this gate formats a floppy in E and D formats, writes a file with BASIC,
and writes and reads back a hard-disc sector with ADFS_DiscOp. The floppies
are read back by independent host parsers (tests/adfs_newmap.py for E, the
directory reader and old free-space map for D). The negative control is
the same ROM with the frozen baseline FileCore, which must fail both.
"""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tests'))
import adfs_newmap
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/format-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-format','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','FormatProbe'],'harness')
exe=R/'build/harness-format/release/FormatProbe'
# A populated D-format floppy to be reformatted (the baseline fixture).
fixture=(R/'build/desktop-baseline/artifacts/discs/DA.adf').read_bytes()
PATTERN=bytes((i*7+3)&255 for i in range(3000))
WRITE='F%=OPENOUT ":0.$.Pattern":FOR I%=0 TO 2999:BPUT#F%,(I%*7+3) AND 255:NEXT:CLOSE#F%:PRINT "WRITTEN"'
# Drive 4 (the ST506 disc) at byte 16 MiB: write 256 bytes, read them back.
HARD=('DIM b% 1024:FOR I%=0 TO 255:b%?I%=I% EOR &5A:NEXT:SYS "ADFS_DiscOp",,2,&81000000,b%,256:'
 'SYS "ADFS_DiscOp",,1,&81000000,b%+512,256:o%=0:FOR I%=0 TO 255:o%=o% OR (b%?I% EOR b%?(I%+512)):NEXT:PRINT "HARD DISC ";o%')
def commands(fmt):return ['*Format 0 '+fmt,'KEYS:Y','WAIT:240','BASIC',WRITE,HARD,'QUIT','*Cat :0']
NEGATIVE=['*Format 0 E','KEYS:Y','WAIT:20','BASIC',HARD,'QUIT']
def trial(rom_root,cmds,name):
 p=out/name;shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'drive0.adf').write_bytes(fixture)
 run([exe,rom_root/'arclibre.rom',rom_root,p/'drive0.adf',p,*cmds],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((rom_root/'arclibre.rom').read_bytes()),r
 return p,r
def screen(r,i):return '\n'.join(l.rstrip() for l in r['screens'][i] if l.strip())
def check(fmt,p,r):
 s=lambda c:screen(r,r['commands'].index(c))
 assert not r['errors'],r['errors']
 formatted=s('WAIT:240');assert 'A total of 160 tracks need to be formatted' in formatted and 'Formatting track 160' in formatted,formatted
 assert 'WRITTEN' in s(WRITE) and re.search(r'^HARD DISC 0$',s(HARD),re.M),(s(WRITE),s(HARD))
 assert re.search(r'Pattern\s+WR/',s('*Cat :0')),s('*Cat :0')
 disc=(p/'disc0.adf').read_bytes();assert len(disc)==819200
 if fmt=='E':
  rec,frags=adfs_newmap.read(disc)
  rows=adfs_newmap.directory(disc,adfs_newmap.locate(frags,rec['root']))
  assert set(rows)=={'Pattern'} and rows['Pattern']['length']==3000,rows
  o=adfs_newmap.locate(frags,rows['Pattern']['address']);assert disc[o:o+3000]==PATTERN
  free=sum(f['length'] for f in frags if f['free'])
  layout=dict(log2secsize=rec['log2secsize'],secspertrack=rec['secspertrack'],heads=rec['heads'],density=rec['density'],idlen=rec['idlen'],log2bpmb=rec['log2bpmb'],root=rec['root'],disc_size=rec['disc_size'])
  assert layout==dict(log2secsize=10,secspertrack=5,heads=2,density=2,idlen=15,log2bpmb=7,root=0x203,disc_size=819200),layout
  return dict(format='E',disc_record=layout,fragments=len(frags),free_bytes=free,files={'Pattern':sha(PATTERN)})
 # FileCore 3.60 writes D-format directories with 'Nick' markers (old map).
 rows=adfs_newmap.directory(disc,0x400)
 assert set(rows)=={'Pattern'} and rows['Pattern']['length']==3000,rows
 a=rows['Pattern']['address']*256;assert disc[a:a+3000]==PATTERN
 # Old map: the free-space start/length lists in sectors 0 and 1 (3-byte entries).
 n=disc[0x1fe];free=sum(int.from_bytes(disc[256+3*i:259+3*i],'little') for i in range(n//3))*256
 assert disc[252:255]==bytes([0x80,0x0c,0]),disc[252:255] # 3,200 sectors of 256 bytes
 return dict(format='D',root_address=4,free_bytes=free,files={'Pattern':sha(PATTERN)})
specs=[(fmt,n) for n in COLD for fmt in ('E','D')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=list(pool.map(lambda s:check(s[0],*trial(root,commands(s[0]),f'{s[0].lower()}-{s[1]}')),specs))
same([r for r in results if r['format']=='E'],[r for r in results if r['format']=='D'])
obs={'E':next(r for r in results if r['format']=='E'),'D':next(r for r in results if r['format']=='D')}
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'Format')
# Negative control: the same ROM with the frozen baseline FileCore.
run([sys.executable,R/'tools/build_arclibre_rom.py','--baseline-filecore'],'negative-rom')
neg=R/'build/arclibre-baseline-filecore'
p,r=trial(neg,NEGATIVE,'negative-baseline-filecore')
fmt=screen(r,r['commands'].index('WAIT:20'));hard=screen(r,r['commands'].index(HARD))
# It stops at the first track write: no track after 1 is reached.
assert 'SWI &44781 not known' in fmt and not re.search(r'Formatting track ([2-9]|1\d)',fmt),fmt
assert 'SWI &44781 not known' in hard and not re.search(r'^HARD DISC \d',hard,re.M),hard
assert (p/'disc0.adf').read_bytes()==fixture,'the floppy is untouched'
negative=dict(rom_sha256=sha((neg/'arclibre.rom').read_bytes()),format='SWI &44781 not known at the first track',hard_disc_discop='SWI &44781 not known',floppy_unchanged=True)
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),fixture_sha256=sha(fixture),independent_parsers=['tests/adfs_newmap.py'],
 guest_code_injection=False,emulator_unchanged=True,observations=obs,negative_control=negative))
print('Format PASS',flush=True)
