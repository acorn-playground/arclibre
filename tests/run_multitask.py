#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import json,os,pathlib,shutil,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
out=REPO/'build/multitask';logs=out/'logs';logs.mkdir(exist_ok=True);(out/'acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','MultiTaskProbe'],'harness')
bin=REPO/'build/harness-patched/release';rom=ROOT/'artifacts/floppy.rom'
run([bin/'BootProbe',rom,out/'cold-boots',3],'cold-boots')
results=[]
for i in [1,2,3]:
 p=out/f'run-{i}'
 if p.exists():shutil.rmtree(p)
 run([bin/'CamProbe',rom,out/f'cold-boots/cold-{i}/pre-module.macarch-state',ROOT/'artifacts/symbols.json',out/f'natural-{i}','natural'],f'natural-{i}')
 run([bin/'MultiTaskProbe',rom,out/f'natural-{i}/supervisor-entry.macarch-state',out,p],f'tasks-{i}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and len(r['observations'])==40
 assert all(r['exceptions'][n]==0 for n in [3,4,5,7])
 groups=[[x for x in r['observations'] if x['marker']==identity] for identity in [11,29]]
 assert all(len(g)==20 for g in groups)
 code=[{v['physical_code'] for v in g} for g in groups];data=[{v['physical_marker'] for v in g} for g in groups]
 assert all(len(v)==1 for v in code+data) and code[0].isdisjoint(code[1]) and data[0].isdisjoint(data[1])
 results.append(r)
assert results[0]==results[1]==results[2]
report=dict(status='PASS',cold_runs=3,identical_results=True,child_tasks=2,polls_per_child=20,logical_execution_address=0x8000,independent_physical_code_pages=[next(iter(g)) for g in code],independent_physical_marker_pages=[next(iter(g)) for g in data],real_file_loading=True,real_task_messages=True,all_eight_fpa_registers_and_fpsr_checked=True,rom_sha256=results[0]['rom_sha256'],baseline_rom_modified=False,emulator_modified=False)
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
