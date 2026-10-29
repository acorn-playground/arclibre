#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Three cold boots, desktop filing, F12, FPA audit and hardware-pointer controls."""
import hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
args=[v for v in sys.argv[1:] if not v.startswith('--')]
verify_existing='--verify-existing' in sys.argv
out=REPO/(args[0] if args else 'build/arclibre');logs=out/'logs';logs.mkdir(exist_ok=True);start(out)
startup_extras=[c for c in ['ResFiler','ArcPalette','Free'] if any(m['component']==c for m in json.loads((out/'rom-layout.json').read_text())['modules'])]
desktop_tasks=4+len(startup_extras)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name,overrides=None):
 print(name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],env=dict(env,**(overrides or {})),stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator')
for script in ['build_client.py','build_fixtures.py']:
 run([sys.executable,REPO/'tests'/script],script,dict(ARCLIBRE_OUTPUT=str(REPO/'build/desktop-baseline')))
fixture=REPO/'build/desktop-baseline/artifacts/discs/DA.adf'
fixture_sha=hashlib.sha256(fixture.read_bytes()).hexdigest()
assert fixture_sha=='6f770c2b9a63d77a02057e8263c128d30464ef3287bba1bbaf040fea98c73d52'
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness')
run([sys.executable,REPO/'tests/build_desktop_app.py'],'application-fixture')
results=[];screens=[];launches=[]
for i in COLD:
 p=out/f'cold-{i}'
 if not verify_existing:
  shutil.rmtree(p,ignore_errors=True);run([REPO/'build/harness-patched/release/DesktopROMProbe',out/'arclibre.rom',out,p],f'cold-{i}')
  run([REPO/'build/harness-patched/release/PointerProbe','inspect',out/'arclibre.rom',p/'desktop.macarch-state',p/'pointer'],'pointer-'+str(i))
 pointer=json.loads((p/'pointer/result.json').read_text());assert pointer['status']=='PASS' and pointer['visible'] and pointer['moved'] and pointer['rom_sha256']==hashlib.sha256((out/'arclibre.rom').read_bytes()).hexdigest()
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['task_count']==desktop_tasks and r['reported_total']==4194304 and not r['errors'];assert all(x['psr']&3==0 for x in r['initialisations']);assert all(r['exceptions'][n]==0 for n in [3,4,5]);r['services']=sorted(r['services'],key=lambda v:v['service']);verify(p,root=out);results.append(r)
 screens.append([hashlib.sha256((p/(n+'-screen.bin')).read_bytes()).hexdigest() for n in ['desktop','task-manager','floppy-root','docs','deep','shell-start','shell-catalogue','shell-file','shell-error','shell-recovery','shell-program','shell-return','desktop-recovery']])
for i in COLD:
 p=out/f'launch-{i}'
 if not verify_existing:
  shutil.rmtree(p,ignore_errors=True)
  run([REPO/'build/harness-patched/release/DesktopLaunchProbe',out/'arclibre.rom',out,REPO/'build/desktop-app/application.adf',p,'!ArcTest'],f'launch-{i}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['task_count']==desktop_tasks and not r['errors'];assert all(r['exceptions'][n]==0 for n in [3,4,5])
 verify(p,required=['Desktop','Filer','Wimp','ADFSFiler','Obey','Buffers'],root=out);launches.append(r)
same(launches)
same(results);same(screens)
probe_exit(out,out/'arclibre.rom',dict(result=results[0],screens=screens[0]),'Desktop ROM')
run([sys.executable,REPO/'tools/prepare_sprite_checks.py'],'checker-cases')
bin=REPO/'build/harness-patched/release';base=REPO/'build/desktop-baseline/artifacts'
run([bin/'BootProbe',base/'floppy.rom',out/'checker-boot',1],'checker-boot')
run([bin/'CamProbe',base/'floppy.rom',out/'checker-boot/cold-1/pre-module.macarch-state',base/'symbols.json',out/'checker-natural','natural'],'checker-natural')
run([bin/'PointerProbe','checks',base/'floppy.rom',out/'checker-natural/supervisor-entry.macarch-state',REPO/'build/desktop-startup/modules/SprExtend',REPO/'build/sprite-checks/cases.json',out/'checker'],'checker-parity')
run([sys.executable,REPO/'tools/build_arclibre_rom.py','--without-spriteextend'],'negative-rom')
negative=REPO/'build/arclibre-without-spriteextend';shutil.rmtree(negative/'cold-1',ignore_errors=True)
negative_layout=json.loads((negative/'rom-layout.json').read_text())
assert {m['component'] for m in negative_layout['modules']}=={m['component'] for m in json.loads((out/'rom-layout.json').read_text())['modules']}-{'SprExtend'}
run([bin/'DesktopROMProbe',negative/'arclibre.rom',negative,negative/'cold-1'],'negative-boot')
r=subprocess.run([str(v) for v in [bin/'PointerProbe','inspect',negative/'arclibre.rom',negative/'cold-1/desktop.macarch-state',out/'negative-pointer']],env=env,capture_output=True,text=True)
assert r.returncode==1,r.stdout+r.stderr
neg=json.loads((out/'negative-pointer/result.json').read_text());assert neg['status']=='FAIL' and not neg['visible']
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==fixture_sha
layout=json.loads((out/'rom-layout.json').read_text())
report=dict(status='PASS',desktop_application_double_click=True,nested_obey_and_application_exit=True,buffered_fast_mouse_clicks=True,application_cold_boots=3,cold_boots=3,identical_observations=True,identical_rendered_memory=True,rom_sha256=results[0]['rom_sha256'],kernel_sha256=layout['kernel_sha256'],kernel_unchanged=layout['kernel_unchanged'],emulator_unchanged=True,no_guest_code_injection=True,no_host_module_loading=True,original_startup_tasks=['Desktop','Filer','TaskManager','Pinboard','ADFSFiler']+[c for c in startup_extras if c!='ArcPalette'],additional_startup_tasks=[c for c in startup_extras if c=='ArcPalette'],persistent_tasks=desktop_tasks,floppy_root_and_nested_directories_by_mouse=True,f12_catalogue_file_error_recovery_program_exit=True,shell_task_terminates_and_desktop_resumes=True,wd1772_reads_and_fiq_observed=True,read_only_test_media=True,test_floppy_sha256=fixture_sha,task_manager_opened_by_real_mouse=True,reported_memory_bytes=4194304,all_undefined_exceptions_classified=True,hardware_cursor_visible_and_moves=True,missing_spriteextend_negative_control=True,negative_removes_only_spriteextend=True,negative_rom_sha256=negative_layout['rom_sha256'],sprite_checker_c_reference_cases=len(json.loads((REPO/'build/sprite-checks/cases.json').read_text())),screen_sha256=screens[0])
finish(out,report);print(json.dumps(report,indent=2))
