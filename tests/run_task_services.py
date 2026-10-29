#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cold ARM2 task/filter protocol and original Edit/BASIC acceptance gates."""
import concurrent.futures
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count

args=[v for v in sys.argv[1:] if not v.startswith('--')]
root=REPO/(args[0] if args else 'build/arclibre')
verify_existing='--verify-existing' in sys.argv
out=REPO/'build/task-service-tests';out.mkdir(exist_ok=True)
start(out)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as log:
  subprocess.run([str(v) for v in cmd],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tests/build_task_service_app.py'],'fixture')
for product in ['DesktopLaunchProbe','EditProbe']:
 run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product',product],product)
fixture=REPO/'build/task-service-app/application.adf'
fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest()
rom_hash=hashlib.sha256((root/'arclibre.rom').read_bytes()).hexdigest()
def trial(n):
 p=out/f'cold-{n}'
 if not verify_existing:
  shutil.rmtree(p,ignore_errors=True);p.mkdir()
  run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,fixture,p/'protocol','!TaskTest'],f'protocol-{n}')
 r=json.loads((p/'protocol/result.json').read_text())
 assert r['status']=='PASS' and r['rom_sha256']==rom_hash and not r['errors'] and r['task_count']==desktop_task_count(root)
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 markers={v['text'] for v in r['events'] if v['swi']==2}
 for marker in ['FILTER CONTRACT','TASK PREEMPT INPUT SUSPEND','TASK ERROR RECOVERY','TASK KILL CLEANUP','TASK SERVICES']:
  assert 'ARCLIBRE '+marker+' PASS' in markers
 fp=json.loads((REPO/'build/task-service-app/child-fpa-dependency.json').read_text())
 addresses={0x10000+v['offset'] for v in fp}
 traps=[t for t in r['undefined'] if t['pc'] in addresses]
 assert len(traps)==16 and {t['pc'] for t in traps}==addresses
 v=verify(p/'protocol',required=['TaskWindow','Filter'],root=root)
 r.pop('disc')
 if not verify_existing:
  run([REPO/'build/harness-patched/release/EditProbe',root/'arclibre.rom',root,p/'edit','taskwindow'],f'edit-{n}')
 e=json.loads((p/'edit/write/result.json').read_text())
 assert e['status']=='PASS' and e['rom_sha256']==rom_hash and not e['errors'] and e['task_count']==desktop_task_count(root)+1
 assert all(e['exceptions'][i]==0 for i in [3,4,5])
 assert e['text_buffers'][-1]['text'].endswith('>PRINT 6*7\n        42\n>REPEAT:UNTIL FALSE\n\nEscape\n>PRINT 7*7\n        49\n>QUIT\n')
 ev=verify(p/'edit/write',required=['TaskWindow','Edit','BASIC'],root=root)
 return dict(protocol=r,protocol_trace=v,edit=e,edit_trace=ev,
             edit_screens={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((p/'edit/write').glob('*.png'))})
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Task services')
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==fixture_hash
run([sys.executable,REPO/'tools/build_arclibre_rom.py','--without-task-services'],'negative-rom')
negative_root=REPO/'build/arclibre-without-tasks';negative=out/'negative-missing-modules'
shutil.rmtree(negative,ignore_errors=True)
with (out/'negative-missing-modules.log').open('w') as log:
 control=subprocess.run([str(REPO/'build/harness-patched/release/DesktopLaunchProbe'),str(negative_root/'arclibre.rom'),str(negative_root),str(fixture),str(negative),'!TaskTest'],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT)
assert control.returncode==1
failure=json.loads((negative/'failure.json').read_text())
assert failure['failure']=='task client assertion failure'
assert all(failure['exceptions'][i]==0 for i in [3,4,5])
assert any(e['swi']==2 and e['text']=='SWI &43380 not known' for e in json.loads((negative/'launch-events.json').read_text()))
report=dict(status='PASS',rom_sha256=rom_hash,fixture_sha256=fixture_hash,cold_machines=6,identical_repetitions=True,
            kernel_and_emulator_unchanged=True,guest_code_injection=False,
            filter_order_mask_claim_and_self_removal=True,filter_error_and_deregistration=True,
            cpu_bound_child_preemption=True,usr26_and_integer_context=True,eight_software_fpa_registers_preserved=True,
            input_suspend_resume=True,error_and_kill_cleanup=True,original_edit_basic=True,
            busy_basic_desktop_response=True,keyboard_escape_and_recovery=True,
            normal_quit_preserves_edit=True,missing_modules_negative_control=True,
            negative_rom_sha256=hashlib.sha256((negative_root/'arclibre.rom').read_bytes()).hexdigest(),observations=results[0])
finish(out,report)
print('TaskWindow and FilterManager PASS',flush=True)
