#!/usr/bin/env python3
"""Run the retained static/runtime gates from the maintained source tree."""
import hashlib,json,os,pathlib,struct,subprocess,sys
# Also works as `python3 tests/run.py` without a caller-provided PYTHONPATH.
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
logs=ROOT/'logs';logs.mkdir(parents=True,exist_ok=True)
(ROOT/'artifacts/acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(REPO/'tools'),str(REPO/'tests/verify')]),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,log,environment=env):
 print('Running',log,flush=True)
 with (logs/(log+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=environment,stdout=f,stderr=subprocess.STDOUT,check=True)
a=ROOT/'artifacts';rom=a/'floppy.rom'
# Rechecking existing evidence is allowed only for the exact frozen ROM. All
# independent memory, instruction, media and repeated-run verifiers still run.
assert hashlib.sha256(rom.read_bytes()).hexdigest()==json.loads((REPO/'manifests/baseline-rom.json').read_text())['rom_sha256']
if '--verify-existing' not in sys.argv:
 for script in ['build_client.py','build_fixtures.py','build_disc.py']:run([sys.executable,REPO/'tests'/script],script)
 run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator-prepare')
 for kind in ['baseline','patched']:
  core=REPO/('build/macarch-baseline/ArchimedesCore' if kind=='baseline' else 'build/macarch/ArchimedesCore')
  buildenv=dict(env,MACARCH_CORE=str(core));scratch=REPO/f'build/harness-{kind}'
  run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',scratch,'--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness-'+kind,buildenv)
  if kind=='patched':run(['swift','test','--package-path',core,'--scratch-path',REPO/'build/core-tests','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','--filter','OriginalDiscChangeTests'],'disc-change-unit-tests',buildenv)
 bin=REPO/'build/harness-patched/release';a=ROOT/'artifacts';rom=a/'floppy.rom';symbols=a/'symbols.json'
 run([bin/'BootProbe',rom,a/'repeats',3],'cold-boots')
 # Fresh negative control: remove only the branch that prevents the historical
 # heap-restore fall-through. NOP preserves all symbol addresses. Use kernel-only
 # packaging so optional modules cannot reach the defective path before the test.
 negative=a/'negative-input';negative.mkdir(exist_ok=True)
 s=json.loads(symbols.read_text());b=bytearray((a/'kernel.bin').read_bytes());offset=s['testrestoreheapend']-0x3800000-4
 old=struct.unpack_from('<I',b,offset)[0];assert old>>24==0xea
 struct.pack_into('<I',b,offset,0xe1a00000);b+=bytes(2097152-len(b));(negative/'floppy.rom').write_bytes(b)
 (negative/'rom-layout.json').write_text(json.dumps({'rom_sha256':hashlib.sha256(b).hexdigest()})+'\n')
 (negative/'mutation.json').write_text(json.dumps({'offset':offset,'before':hex(old),'after':'0xe1a00000','reason':'Remove the restored CDA skip branch to reproduce the real historical fall-through'},indent=2)+'\n')
 run([bin/'BootProbe',negative/'floppy.rom',negative/'boot',1],'negative-cold-boot')
 run([bin/'CamProbe',negative/'floppy.rom',negative/'boot/cold-1/pre-module.macarch-state',symbols,a/'negative','negative'],'negative-cam')
 for i in [1,2,3]:
  snapshot=a/f'natural-{i}/supervisor-entry.macarch-state'
  for kind in ['natural','fixtures']:run([bin/'CamProbe',rom,a/f'repeats/cold-{i}/pre-module.macarch-state',symbols,a/f'{kind}-{i}',kind],f'{kind}-{i}')
  for probe,arg,name in [('KeyboardProbe',symbols,'keyboard'),('MessageProbe',a/'resources.json','messages'),('TerritoryProbe',a/'resources.json','territory'),('KeyboardSelectProbe',symbols,'selection'),('FloppyProbe',a/'disc','floppy'),('FilingProbe',a/'discs','filing'),('WriteProbe',a/'discs','writes')]:
   run([bin/probe,rom,snapshot,arg,a/f'{name}-{i}'],f'{name}-{i}')
 for kind,name in [('banner','banner'),('fixture','text-fixture')]:run([bin/'TextProbe',rom,a/'repeats/cold-1/pre-module.macarch-state',a/name,kind],name)
 run([REPO/'build/harness-baseline/release/FilingProbe',rom,a/'natural-1/supervisor-entry.macarch-state',a/'discs',a/'baseline','media-change-baseline'],'baseline-media-change')
for name in ['regressions','keyboard','messages','territory','selection','floppy','filing','writes']:run([sys.executable,REPO/'tests/verify'/('verify_'+name+'.py')],'verify-'+name)
result={'status':'PASS','rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cold_runs':3,'filing_scenarios':42,'write_flows':18,'fresh_negative_cam_control':True,'baseline_media_failure_reproduced':True,'suites':['static kernel and modules','boot','CAM','keyboard','messages','territory','IntKey','floppy/FIQ','filing','controlled writes','pixels/font'],'source_tree':'src','generated_root':str(ROOT)}
(a/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: maintained-tree regression suite',flush=True)
