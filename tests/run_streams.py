#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cold public character-stream tests; real file-loaded, independently audited guests."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
REPO=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
args=[v for v in sys.argv[1:] if not v.startswith('--')]
root=REPO/(args[0] if args else 'build/arclibre')
negative_root=REPO/(args[1] if len(args)>1 else 'build/arclibre-without-streams')
existing='--verify-existing' in sys.argv
out=REPO/'build/stream-tests';out.mkdir(exist_ok=True);start(out)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=REPO,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,REPO/'tests/build_stream_app.py'],'fixture')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-streams','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
exe=REPO/'build/harness-streams/release/DesktopLaunchProbe';fixture=REPO/'build/stream-app/application.adf'
fixture_hash=sha(fixture);rom_hash=sha(root/'arclibre.rom')
def trial(n):
 p=out/f'cold-{n}'
 if not existing:
  shutil.rmtree(p,ignore_errors=True)
  run([exe,root/'arclibre.rom',root,fixture,p,'!StrTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text())
 assert r['status']=='PASS' and r['rom_sha256']==rom_hash and r['task_count']==desktop_task_count(root) and not r['errors']
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 markers={v['text'] for v in r['events'] if v['swi']==2}
 for text in ['SYSTEM STREAMS','DEVICE BUFFER LIFECYCLE','PIPE CONTENT EOF','PIPE READER WAKE','PIPE WRITER WAKE','TASK SLEEP REMOVAL REJECTED','PIPE KILL CLEANUP','STREAM CONTRACT']:
  assert 'ARCLIBRE '+text+' PASS' in markers,(n,text)
 v=verify(p,required=['DeviceFS','SystemDevs','PipeFS','TaskWindow'],root=root)
 r.pop('disc');return dict(protocol=r,trace=v)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Streams')
assert sha(fixture)==fixture_hash
run([sys.executable,REPO/'tools/build_arclibre_rom.py','--without-streams'],'negative-rom')
# Only the three providers/resources differ; every existing module remains.
a=json.loads((root/'rom-layout.json').read_text());b=json.loads((negative_root/'rom-layout.json').read_text())
# The serial and parallel drivers are DeviceFS devices and leave with it.
assert {v['component'] for v in a['modules']}-{v['component'] for v in b['modules']}=={'DeviceFS','SystemDevs','PipeFS','Serial','SerialSpt','Parallel'}
assert {v['component'] for v in b['modules']} < {v['component'] for v in a['modules']}
# Position-dependent C modules are relinked; non-C providers must match.
for row in b['modules']:
 if row['component'] not in ['Messages','SharedCLib','FilerAct','Edit','Draw','Paint','Squash']:
  assert row['sha256']==next(v['sha256'] for v in a['modules'] if v['component']==row['component'])
# Squash joins the existing fixed-address C modules. Its bytes change when
# providers before it disappear; require each independently audited link.
for profile,layout in [(root,a),(negative_root,b)]:
 squash=next((row for row in layout['modules'] if row['component']=='Squash'),None)
 if squash:
  proof=json.loads((profile/'squash-runtime/verification.json').read_text())['modules'][0]
  assert proof['sha256']==squash['sha256'] and proof['base']==squash['base']
  assert proof['unresolved_symbols']==0 and proof['all_nonrelocation_bytes_match'] and proof['all_linked_bytes_mapped']
negative=out/'negative-missing-modules';shutil.rmtree(negative,ignore_errors=True)
with (out/'negative.log').open('w') as f:
 p=subprocess.run([str(x) for x in [exe,negative_root/'arclibre.rom',negative_root,fixture,negative,'!StrTest']],cwd=REPO,env=env,stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==1
failure=json.loads((negative/'failure.json').read_text())
assert failure['failure']=='stream client assertion failure' and all(failure['exceptions'][i]==0 for i in [3,4,5])
events=json.loads((negative/'launch-events.json').read_text())
assert any(e['swi']==2 and e['text']=='Filing system or path null: not present' for e in events)
report=dict(status='PASS',rom_sha256=rom_hash,fixture_sha256=fixture_hash,cold_boots=3,identical_repetitions=True,
 kernel_and_emulator_unchanged=True,guest_code_injection=False,
 device_registration_stream_limits_and_deregistration=True,buffered_rx_tx_and_eof=True,
 null_vdu_rawvdu_rawkbd=True,pipe_contents_and_eof=True,
 empty_reader_sleep_wakeup=True,full_writer_sleep_wakeup=True,
 sleeping_word_removal_rejected_with_error_0xa84=True,killed_task_handle_explicitly_closed=True,
 global_file_handles_not_implicitly_owned_by_task=True,
 missing_modules_negative_control=True,negative_rom_sha256=sha(negative_root/'arclibre.rom'),observations=results[0])
finish(out,report)
print('DeviceFS, SystemDevices and PipeFS PASS',flush=True)
