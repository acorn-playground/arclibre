#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Public sound APIs, real scheduled voices and DMA across three cold desktops."""
import hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from verify_sound_rates import verify as verify_rates
args=[x for x in sys.argv[1:] if not x.startswith('--')];root=REPO/(args[0] if args else 'build/arclibre');out=REPO/'build/sound';out.mkdir(exist_ok=True);start(out)
startup_extras=[c for c in ['ResFiler','ArcPalette','Free'] if any(m['component']==c for m in json.loads((root/'rom-layout.json').read_text())['modules'])]
desktop_tasks=4+len(startup_extras)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tests/build_sound_app.py'],'fixture')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
results=[];stages=[];rates=[]
for n in COLD:
 p=out/f'cold-{n}';shutil.rmtree(p,ignore_errors=True);run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,REPO/'build/sound-app/application.adf',p,'!SndTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['task_count']==desktop_tasks and not r['errors'];assert all(r['exceptions'][i]==0 for i in [3,4,5])
 verify(p,required=['Sound0','Sound1','Sound2','WaveSynth','Percussion'],root=root)
 rates.append(verify_rates(p/'sound-rates.json'))
 results.append(r);stages.append(json.loads((p/'stages.json').read_text()))
assert all(stage['sound_mapping']==[0x7e000,0x7f000] for run in stages for stage in run)
same(rates)
same(results);same(stages)
probe_exit(out,root/'arclibre.rom',dict(result=results[0],stages=stages[0],rates=rates[0]),'Sound')
report=dict(status='PASS',rom_sha256=results[0]['rom_sha256'],cold_boots=3,identical_observations=True,original_floppy_program=True,stereo_set_query=True,unsupported_vidc20_swi_returns_error=True,wavesynth_percussion_and_scheduler=True,real_dma_non_silent=True,vidc_rate_and_dma_timing=True,sample_rate_cases=rates[0],returned_to_desktop=True,emulator_unchanged=True,workspace_contract=json.loads((out/'workspace-contract.json').read_text()),sound_stages=stages[0])
finish(out,report);print('Sound runtime gate PASS')
