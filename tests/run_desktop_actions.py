#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Real mouse drag, Pinboard shortcut launch and return across cold desktops."""
import hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
from PIL import Image
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
args=[x for x in sys.argv[1:] if not x.startswith('--')];root=REPO/(args[0] if args else 'build/arclibre');out=REPO/'build/desktop-actions';out.mkdir(exist_ok=True);start(out)
startup_extras=[c for c in ['ResFiler','ArcPalette','Free'] if any(m['component']==c for m in json.loads((root/'rom-layout.json').read_text())['modules'])]
desktop_tasks=4+len(startup_extras)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tests/build_desktop_app.py'],'fixture')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
results=[];stages=[];screens=[]
for n in COLD:
 p=out/f'cold-{n}';shutil.rmtree(p,ignore_errors=True);run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,REPO/'build/desktop-app/application.adf',p,'!ArcTest','drag'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['task_count']==desktop_tasks and not r['errors'];assert all(r['exceptions'][i]==0 for i in [3,4,5])
 verify(p,required=['DragASprit','Pinboard','Obey','Filer','Buffers'],root=root)
 # Moving the drag image changes the rendered frame; the untouched backdrop
 # retains its exact colour throughout. The shortcut is then actually launched.
 imgs={s:Image.open(p/(s+'.png')).convert('RGB') for s in ['disc-open','dragging','drag-moved','dropped']}
 assert len({im.tobytes() for im in imgs.values()})==4
 assert all(im.getpixel((600,180))==(119,119,119) for im in imgs.values())
 results.append(r);stages.append(json.loads((p/'stages.json').read_text()));screens.append({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.png')})
same(results);same(stages);same(screens)
probe_exit(out,root/'arclibre.rom',dict(result=results[0],stages=stages[0],screens=screens[0]),'Desktop drag')
report=dict(status='PASS',rom_sha256=results[0]['rom_sha256'],cold_boots=3,identical_observations=True,real_drag_swis=True,pinboard_shortcut_created_and_launched=True,returned_to_desktop=True,emulator_unchanged=True,screens=screens[0],limitations=['No FilerAct file operations are claimed by this gate.'])
finish(out,report);print('Desktop drag gate PASS')
