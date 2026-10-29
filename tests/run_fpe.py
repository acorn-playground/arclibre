#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh cold boots, real dynamic module loading, independent FPA result checks."""
import hashlib,json,os,pathlib,re,shutil,struct,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
from module_image import load_aof
out=REPO/'build/fpemulator';logs=out/'logs';logs.mkdir(exist_ok=True)
(out/'acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print('Running',name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness')
bin=REPO/'build/harness-patched/release';a=ROOT/'artifacts';rom=a/'floppy.rom'
run([bin/'BootProbe',rom,out/'cold-boots',3],'cold-boots')
results=[]
for i in [1,2,3]:
 natural=out/f'natural-{i}';probe=out/f'run-{i}'
 if probe.exists():shutil.rmtree(probe)
 run([bin/'CamProbe',rom,out/f'cold-boots/cold-{i}/pre-module.macarch-state',a/'symbols.json',natural,'natural'],f'natural-{i}')
 run([bin/'FPEProbe',rom,natural/'supervisor-entry.macarch-state',out,probe],f'fpe-{i}')
 r=json.loads((probe/'result.json').read_text());assert r['status']=='PASS' and len(r['tests'])==12 and len(r['errors'])==3
 assert r['context_length']==136 and r['new_vector']!=r['old_vector'] and r['new_anchor']!=0
 assert all(r['exceptions'][n]==0 for n in [3,4,5,7]) and r['exceptions'][1]>0
 for t in r['tests']:assert t['undefined_traps']>0 and t['psr']&3==3
 assert next(t for t in r['tests'] if t['name']=='status')['result_words'][0]&0xffffff==0x70000
 for t in r['tests']:
  w=t['result_words']
  def d(n):return struct.unpack('>d',struct.pack('>II',w[n],w[n+1]))[0]
  if t['name'] in ['arithmetic','user_arithmetic']:
   assert d(0)==10 and d(2)==21 and d(4)==7/3 and w[6]==2
   if t['name']=='user_arithmetic':assert w[63]&3==0
  if t['name']=='save_restore':assert w[1:25]==w[32:56] and w[0]==w[56]
  if t['name']=='transcendentals':
   import math
   assert abs(d(0)-math.sin(0.5))<1e-15 and d(2)==2 and d(4)==0 and d(6)==1 and t['undefined_traps']>4
  if t['name']=='masked_zero_divide':assert d(0)==float('inf') and w[2]&2
 assert [e['number'] for e in r['errors']]==[0x80000202,0x80000000,0x80000000]
 assert r['errors'][0]['message']=='Floating point exception: division by zero'
 # Check observed execution enters the real undefined vector and module handler.
 texts=''.join(p.read_text() for p in sorted(probe.glob('*-trace.log')))
 assert re.search(r'^[0-9]+ 00000004 ',texts,re.M) and ' USR\n' in texts
 module=(out/'module.bin').read_bytes();base=r['module_base'];observed=set()
 for line in texts.splitlines():
  fields=line.split()
  if len(fields)<3 or len(fields[1])!=8:continue
  pc=int(fields[1],16)
  if base<=pc<base+len(module):
   word=int(fields[2],16);assert word==struct.unpack_from('<I',module,pc-base)[0]
   observed.add(pc-base)
 assert len(observed)>300,'software emulator execution coverage'
 symbols=json.loads((out/'symbols.json').read_text())
 assert symbols['core_activatecontext'] in observed
 assert any(symbols['FP_UndefHandlers_Start']<=x<symbols['FP_UndefHandlers_End'] for x in observed)
 results.append(r)
assert results[0]==results[1]==results[2],'cold-run result mismatch'
# Wimp's actual emitted FPA encodings are retained and appear in the exercised
# client. This includes all eight extended loads/stores and conditional WFSEQ.
wimp=REPO/'build/desktop-components/modules/Wimp'
needed=json.loads((wimp/'fpa-dependency.json').read_text())
client=load_aof(out/'client.aof')['data'];words=set(struct.unpack('<'+'I'*(len(client)//4),client))
assert len(needed)==21 and all(row['source']['word'] in words for row in needed)
build=json.loads((out/'result.json').read_text());romsha=hashlib.sha256(rom.read_bytes()).hexdigest()
assert romsha==json.loads((REPO/'manifests/baseline-rom.json').read_text())['rom_sha256']
report=dict(status='PASS',cold_runs=3,identical_results=True,rom_sha256=romsha,module_sha256=build['sha256'],module_bytes=build['bytes'],integer_arm2_instructions=build['integer_arm2_instructions'],classified_fpa_instructions=build['recursive_and_probe_fpa_instructions'],wimp_fpa_sites_covered=21,tests_per_run=12,error_paths_per_run=3,context_bytes=136,baseline_rom_modified=False,emulator_modified=False,scope='Isolated runtime FPEmulator with exact Wimp FPA encodings; not Wimp initialization or full floating-point/RISC OS 3.11 conformance')
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
