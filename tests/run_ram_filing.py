#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cold RAM filing, real icon input and independently checked Free window state."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre');negative_root=R/(args[1] if len(args)>1 else 'build/arclibre-without-ram-filing')
existing='--verify-existing' in sys.argv
out=R/'build/ram-filing-tests';out.mkdir(exist_ok=True);start(out)
env=dict(os.environ,PYTHONPATH=str(R/'tools'),MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,R/'tests/build_ram_app.py'],'fixture')
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-ram','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
exe=R/'build/harness-ram/release/DesktopLaunchProbe';fixture=R/'build/ram-app/application.adf'
fixture_hash=sha(fixture);rom_hash=sha(root/'arclibre.rom')
def trial(n):
 p=out/f'cold-{n}'
 if not existing:
  shutil.rmtree(p,ignore_errors=True);run([exe,root/'arclibre.rom',root,fixture,p,'!RamTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text())
 assert r['status']=='PASS' and r['rom_sha256']==rom_hash and r['task_count']==desktop_task_count(root) and not r['errors']
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 assert all(v['psr']&3==0 for v in r['events'] if v['text'].startswith('ARCLIBRE RAM '))
 markers={v['text'] for v in r['events'] if v['swi']==2}
 for t in ['EMPTY RESIZE','CONTENTS RESIZE GUARD','FULL CLEANUP','CONTRACT']:assert 'ARCLIBRE RAM '+t+' PASS' in markers
 assert 'RAM FULL ERROR 117C6 The disc has no more available space' in markers
 state=json.loads((p/'ram-free-states.json').read_text());assert len(state)==3
 for label,x in zip(['BEFORE','AFTER','CLEAN'],state):
  words=x['marker'].split();assert words[3]==label and int(words[4])==x['window_free_lo']
  assert x['window_fs']==23 and x['window_size_lo']==262144 and x['window_size_lo']==x['window_free_lo']+x['window_used_lo']
  assert all(x[k]==0 for k in ['window_size_hi','window_free_hi','window_used_hi'])
 assert state[0]['window_free_lo']-state[1]['window_free_lo']==65536
 assert state[0]['window_free_lo']==state[2]['window_free_lo']
 manager=json.loads((p/'ram-taskmanager.json').read_text());assert manager['filertaskhandle'] and manager['task_count']==desktop_task_count(root)+2
 assert any(x['title'].startswith('RAM::') for x in json.loads((p/'filing-windows.json').read_text()))
 v=verify(p,required=['RamFS','RAMFSFiler','Free','Switcher','FileCore','Filer'],root=root)
 r.pop('disc');return dict(protocol=r,free=state,taskmanager=manager,trace=v,screens={f.name:sha(f) for f in sorted(p.glob('*.png'))})
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'RAM filing')
assert sha(fixture)==fixture_hash
if len(args)<2:run([sys.executable,R/'tools/build_arclibre_rom.py','--without-ram-filing'],'negative-rom')
positive=json.loads((root/'rom-layout.json').read_text());negative_layout=json.loads((negative_root/'rom-layout.json').read_text())
assert {r['component'] for r in positive['modules']}-{r['component'] for r in negative_layout['modules']}=={'RamFS','RAMFSFiler','Free'}
p=out/'negative-missing-modules';shutil.rmtree(p,ignore_errors=True)
with (out/'negative.log').open('w') as f:control=subprocess.run([str(x) for x in [exe,negative_root/'arclibre.rom',negative_root,fixture,p,'!RamTest']],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
assert control.returncode==1
failure=json.loads((p/'failure.json').read_text());assert failure['failure']=='RAM client assertion failure'
assert all(failure['exceptions'][i]==0 for i in [3,4,5])
events=json.loads((p/'launch-events.json').read_text())
assert any(e['swi']==2 and e['text']=='Filing system or path RAM: not present' for e in events)
report=dict(status='PASS',rom_sha256=rom_hash,fixture_sha256=fixture_hash,cold_boots=3,identical_repetitions=True,
 kernel_and_emulator_unchanged=True,guest_code_injection=False,empty_disk_grow_shrink=True,
 public_area_and_limits_agree=True,ram_contents_and_eof=True,nonempty_resize_error_0x1c3=True,
 full_disk_error_0x117c6=True,cleanup_restores_free_space=True,
 original_taskmanager_restarts_ramfsfiler=True,real_mouse_opens_ram_directory=True,
 original_free_window_matches_filesystem=True,icon_task_removed_with_disk=True,
 missing_modules_negative_control=True,negative_rom_sha256=sha(negative_root/'arclibre.rom'),observations=results[0])
finish(out,report);print('RAM filing and Free PASS',flush=True)
