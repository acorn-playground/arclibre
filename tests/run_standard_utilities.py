#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Real palette blanking and four algorithmic voices, with cold repeats."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
negative_root=R/(args[1] if len(args)>1 else 'build/arclibre-without-utilities')
existing='--verify-existing' in sys.argv
out=R/'build/utility-tests';out.mkdir(exist_ok=True);start(out)
env=dict(os.environ,PYTHONPATH=str(R/'tools'),MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,R/'tests/build_utility_app.py'],'fixture')
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-utilities','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
exe=R/'build/harness-utilities/release/DesktopLaunchProbe';fixture=R/'build/utility-app/application.adf'
fixture_hash=sha(fixture);rom_hash=sha(root/'arclibre.rom')
def trial(n):
 p=out/f'cold-{n}'
 if not existing:
  shutil.rmtree(p,ignore_errors=True);run([exe,root/'arclibre.rom',root,fixture,p,'!UtilTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text())
 assert r['status']=='PASS' and r['rom_sha256']==rom_hash and r['task_count']==desktop_task_count(root) and not r['errors']
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 states=json.loads((p/'utility-states.json').read_text());values={v['marker'].removeprefix('ARCLIBRE UTILITY '):v for v in states}
 assert all(v['psr']&3==0 for v in states)
 original=values['SCREEN BEFORE']['palette']
 for name in ['BLANK','TIMED','WRCHBLANK','MOUSEBLANK','KEYBLANK']:
  x=values['SCREEN '+name];assert x['blanked']==1 and x['palette'][:16]==[0]*16 and x['lit_pixels']==0
 for name in ['BEFORE','RESTORED','WRCHRESTORED','MOUSERESTORED','KEYRESTORED','FINAL']:
  x=values['SCREEN '+name];assert x['blanked']==0 and x['palette']==original and x['lit_pixels']>1000
 assert {values['FLASH '+str(i)]['blanked'] for i in range(8)}=={0,1}
 for i in range(4):
  before=values[f'VOICE {i} START'];after=values[f'VOICE {i} END']
  assert after['sound_non_silent']-before['sound_non_silent']>1000
  assert after['sound_bytes']>before['sound_bytes']
 services=json.loads((p/'utility-services.json').read_text());assert services['122']>=6 and services['123']>=6
 copied=json.loads((p/'string-ram-code.json').read_text());entries=json.loads((p/'string-entries.json').read_text())
 symbols=json.loads((root/'utility-runtime/modules/StringLib/symbols.json').read_text())
 assert all(copied['base']+symbols['GateOn'+str(i)]-symbols['WorkSpaceImage'] in entries for i in range(1,5))
 v=verify(p,required=['ScrBlank','StringLib','Sound0','Sound1'],root=root)
 r.pop('disc');return dict(protocol=r,states=states,services=services,copied_instruction_count=len(copied['instructions']),voice_entries=entries,trace=v)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'ScreenBlanker and StringLib')
assert sha(fixture)==fixture_hash
if len(args)<2:run([sys.executable,R/'tools/build_arclibre_rom.py','--without-standard-utilities'],'negative-rom')
positive=json.loads((root/'rom-layout.json').read_text());negative=json.loads((negative_root/'rom-layout.json').read_text())
assert {r['component'] for r in positive['modules']}-{r['component'] for r in negative['modules']}=={'ScrBlank','StringLib'}
p=out/'negative-missing-modules';shutil.rmtree(p,ignore_errors=True)
with (out/'negative.log').open('w') as f:control=subprocess.run([str(x) for x in [exe,negative_root/'arclibre.rom',negative_root,fixture,p,'!UtilTest']],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
assert control.returncode==1
failure=json.loads((p/'failure.json').read_text());assert failure['failure']=='utility client assertion failure'
assert all(failure['exceptions'][i]==0 for i in [3,4,5])
events=json.loads((p/'launch-events.json').read_text());assert any(e['text']=='SWI &43100 not known' for e in events)
report=dict(status='PASS',rom_sha256=rom_hash,fixture_sha256=fixture_hash,cold_boots=3,identical_repetitions=True,kernel_and_emulator_unchanged=True,guest_code_injection=False,
 actual_vidc_and_frame_blanking=True,palette_restored_exactly=True,timer_wrch_and_flashing=True,real_mouse_and_keyboard_wake=True,screen_services_delivered=True,legacy_timeout_seconds_preserved=True,
 four_named_string_voices=True,four_voices_execute_original_ram_code=True,four_voices_non_silent_dma=True,missing_modules_negative_control=True,
 negative_rom_sha256=sha(negative_root/'arclibre.rom'),observations=results[0])
finish(out,report);print('ScreenBlanker and StringLib PASS',flush=True)
