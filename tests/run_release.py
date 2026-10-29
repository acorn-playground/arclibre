#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the complete release suite (the same steps as `make arclibre-test`) in lanes.

The frozen kernel/filing baseline keeps its required order in one lane; the
component gates are spread over two more, balanced by measured duration. Every
step is the unchanged runner writing the same acceptance record. Negative
control ROM joins are serialised by tools/build_arclibre_rom.py's link lock,
and no step rebuilds the default build/arclibre ROM the gates read.
"""
import concurrent.futures,os,pathlib,subprocess,sys,time
REPO=pathlib.Path(__file__).resolve().parents[1];OUT=REPO/'build/release-run';OUT.mkdir(parents=True,exist_ok=True)
PY=sys.executable
baseline=dict(os.environ,ARCLIBRE_OUTPUT=str(REPO/'build/desktop-baseline'))
# desktop-test rebuilds the shared desktop component modules that every other
# gate's trace check reads, so it runs alone before the lanes start.
FIRST=('desktop-and-multitask',['make','desktop-test','multitask-test'],baseline)
LANES=[
 [('baseline-suite',[PY,'tests/run.py'],baseline),
  ('apps-build',[PY,'tests/check_apps_build.py','--graphics'],None),
  ('squash',[PY,'tests/run_squash.py','build/arclibre'],None),
  ('standard-utilities',[PY,'tests/run_standard_utilities.py'],None),
  ('ram-filing',[PY,'tests/run_ram_filing.py'],None),
  ('sprite-commands',[PY,'tests/run_sprite_commands.py'],None),
  ('palette',[PY,'tests/run_palette.py'],None),
  ('basic-utilities',[PY,'tests/run_basic_utilities.py','build/arclibre'],None),
  ('streams',[PY,'tests/run_streams.py'],None),
  ('stream-sleep-negative',[PY,'tests/check_stream_sleep_negative.py'],None),
  ('extras',[PY,'tests/run_extras.py'],None)],
 [('desktop-rom',[PY,'tests/run_desktop_rom.py'],None),
  ('filer-actions',[PY,'tests/run_filer_actions.py'],None),
  ('sound',[PY,'tests/run_sound.py'],None),
  ('desktop-actions',[PY,'tests/run_desktop_actions.py'],None),
  ('arm3',[PY,'tests/run_arm3.py'],None),
  ('network',[PY,'tests/run_network.py'],None),
  ('netfs',[PY,'tests/run_netfs.py'],None),
  ('hardware',[PY,'tests/run_hardware.py'],None),
  ('printing',[PY,'tests/run_printing.py'],None),
  ('task-services',[PY,'tests/run_task_services.py'],None)],
 [('app-workflows',[PY,'tests/run_app_workflows.py'],None),
  ('desktop-apps',[PY,'tests/run_desktop_apps.py'],None),
  ('graphics-apps',[PY,'tests/run_graphics_apps.py'],None),
  ('clock',[PY,'tests/run_clock.py'],None),
  ('menus',[PY,'tests/run_menus.py'],None),
  ('debugger',[PY,'tests/run_debugger.py'],None),
  ('dosfs',[PY,'tests/run_dosfs.py'],None),
  ('format',[PY,'tests/run_format.py'],None),
  ('dosfs-formats',[PY,'tests/run_dosfs_formats.py'],None),
  ('new-io',[PY,'tests/run_new_io.py'],None)],
]
def lane(steps):
 done=[]
 for name,cmd,env in steps:
  t=time.monotonic();print('start',name,flush=True)
  with (OUT/(name+'.log')).open('w') as f:rc=subprocess.run(cmd,cwd=REPO,env=env or os.environ,stdout=f,stderr=subprocess.STDOUT).returncode
  done.append((name,time.monotonic()-t,rc));print(('PASS ' if rc==0 else 'FAIL ')+name,flush=True)
  if rc:break
 return done
start=time.monotonic()
results=lane([FIRST])
if all(rc==0 for _,_,rc in results):
 with concurrent.futures.ThreadPoolExecutor(max_workers=len(LANES)) as pool:results+=[r for lane_result in pool.map(lane,LANES) for r in lane_result]
for name,secs,rc in results:print(f'  {name:24} {secs/60:5.1f} min  {"PASS" if rc==0 else "FAIL"}')
expected=1+sum(len(l) for l in LANES)
ok=len(results)==expected and all(rc==0 for _,_,rc in results)
print(f'release suite {"PASS" if ok else "FAIL"} in {(time.monotonic()-start)/60:.1f} min ({len(results)}/{expected} steps)')
sys.exit(0 if ok else 1)
