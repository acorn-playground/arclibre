#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Classic client menu messages, actual pointer traversal and selection."""
import concurrent.futures,hashlib,json,os,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
root=REPO/'build/arclibre';out=REPO/'build/menu-tests';out.mkdir(exist_ok=True)
start(out)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name,expect=0):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as log:
  r=subprocess.run([str(v) for v in cmd],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==expect,(name,r.returncode,expect)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,REPO/'tests/build_menu_app.py'],'fixture')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
fixture=REPO/'build/menu-app/application.adf';digest=sha(fixture);rom_hash=sha(root/'arclibre.rom')
def trial(n):
 p=out/f'cold-{n}';shutil.rmtree(p,ignore_errors=True)
 run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,fixture,p,'!MenuTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text())
 assert r['status']=='PASS' and r['rom_sha256']==rom_hash and not r['errors'] and r['task_count']==desktop_task_count(root)
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 assert any(e['text']=='ARCLIBRE MENU CONTRACT PASS' for e in r['events'])
 v=verify(p,required=['Wimp','Filer'],root=root)
 r.pop('disc')
 return dict(result=r,trace=v,screens={f.name:sha(f) for f in sorted(p.glob('*.png'))})
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Menus')
assert sha(fixture)==digest
run([sys.executable,REPO/'tests/check_menu_negative.py'],'negative-control')
report=dict(status='PASS',rom_sha256=rom_hash,cold_boots=3,identical_repeats=True,
            fixture_sha256=digest,client_message_numbers_independent_of_headers=True,
            classic_version_200=True,menu_warning_400c0=True,dynamic_placeholder_8000=True,
            create_submenu_and_selection=True,direct_submenu=True,returned_to_desktop=True,
            kernel_and_emulator_unchanged=True,guest_code_injection=False,observations=results[0])
finish(out,report)
print('Classic menu contract PASS',flush=True)
