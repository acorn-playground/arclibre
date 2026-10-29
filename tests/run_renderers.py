#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise real rendering providers and independently verify their output."""
import hashlib,json,os,pathlib,shutil,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
out=REPO/'build/render-components';logs=out/'logs';logs.mkdir(exist_ok=True);(out/'acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print('Running',name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness')
bin=REPO/'build/harness-patched/release';a=ROOT/'artifacts';rom=a/'floppy.rom'
run([bin/'BootProbe',rom,out/'cold-boots',3],'cold-boots')
results=[]
# Reference convolution operates on pixels directly, without the generated LUTs
# or the ARM routines. These kernels are documented in original s/Super.
kernels=[[[(4-abs(x-3))*(4-abs(y-3)) for x in range(7)] for y in range(7)],[[0,0,0,0,1,0,0,0,0],[1,2,4,6,6,6,4,2,1],[1,4,8,12,13,12,8,4,1],[1,4,8,12,14,12,8,4,1],[1,4,8,12,13,12,8,4,1],[1,2,4,6,6,6,4,2,1],[0,0,0,0,1,0,0,0,0]]]
for i in [1,2,3]:
 natural=out/f'natural-{i}';probe=out/f'run-{i}'
 if probe.exists():shutil.rmtree(probe)
 run([bin/'CamProbe',rom,out/f'cold-boots/cold-{i}/pre-module.macarch-state',a/'symbols.json',natural,'natural'],f'natural-{i}')
 run([bin/'RenderProbe',rom,natural/'supervisor-entry.macarch-state',out,probe],f'render-{i}')
 r=json.loads((probe/'result.json').read_text());assert r['status']=='PASS' and len(r['loaded'])==4
 assert all(r['exceptions'][n]==0 for n in [1,3,4,5,7])
 assert r['line_length']==320 and r['draw_changed_bytes']==2500
 before=(probe/'draw-before.bin').read_bytes();after=(probe/'draw-after.bin').read_bytes();assert len(before)==len(after)==320*256
 # Draw rectangle spans x=100..300 and y=100..300 OS units in mode 12.
 # Eigen factors 1,2 yield a 100x50-pixel half-open rectangle. Memory is top down.
 for y in range(256):
  for x in range(640):
   offset=y*320+x//2;shift=(x&1)*4;old=before[offset]>>shift&15;new=after[offset]>>shift&15
   assert new==(7 if 50<=x<150 and 181<=y<231 else old),(i,x,y,old,new)
 assert [v['logical'] for v in r['colours']]==[0,7,4,1,2]
 assert [v['hsv'] for v in r['conversions'][:3]]==[[0,65536,65536],[120*65536,65536,65536],[240*65536,65536,65536]]
 assert r['transformed']==[2,1280,2560,8,3328,4608,0]
 for row in r['samples']:
  expected=[]
  for y in [0,4]:
   v=0
   for x in range(7):
    total=sum(weight*((row['input'][y+dy]>>(4*x+dx))&1) for dy,weights in enumerate(kernels[row['algorithm']]) for dx,weight in enumerate(weights))
    value=min(15,(total+14)//16);value=value if value>1 else 0;v|=value<<(4*x)
   expected.append(v)
  assert row['output']==expected,(i,row,expected)
 hg=json.loads((probe/'hourglass-percentage update.json').read_text());assert hg['depth']==1 and hg['bytes'][0:2]==[42,42] and hg['bytes'][17]==0
 assert bytes(r['hourglass_shape'])==(probe/'hourglass-shape.bin').read_bytes()
 results.append(r)
assert results[0]==results[1]==results[2],'cold-run result mismatch'
report=dict(status='PASS',cold_runs=3,identical_results=True,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),modules=json.loads((out/'result.json').read_text())['modules'],swi_calls_per_run=len(results[0]['calls']),draw_exact_pixels=5000,supersample_cases_per_run=8,supersample_reference='independent 2D convolution',hourglass_ticker_and_percentage=True,baseline_rom_modified=False,emulator_modified=False,scope='Selected provider APIs, framebuffer geometry and timer updates; not general rendering or RISC OS 3.11 conformance')
assert report['rom_sha256']==json.loads((REPO/'manifests/baseline-rom.json').read_text())['rom_sha256']
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
