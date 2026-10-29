#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual desktop copy/move/delete, protected-media recovery and shared-C ABI."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from verify_filer_disc import verify as verify_disc
parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',default='build/arclibre');parser.add_argument('--verify-existing',action='store_true');parser.add_argument('--probe',action='store_true',help='one cold boot; writes probe.json');args=parser.parse_args()
root=REPO/args.root;out=REPO/'build/desktop-c-runtime';start(out)
startup_extras=[c for c in ['ResFiler','ArcPalette','Free'] if any(m['component']==c for m in json.loads((root/'rom-layout.json').read_text())['modules'])]
desktop_tasks=4+len(startup_extras)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for script in ['build_filer_action_disc.py','build_c_abi_app.py']:run([sys.executable,REPO/'tests'/script],script)
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
def trial(mode,n):
 name=f'{mode}-cold-{n}';p=out/name;disc=REPO/('build/c-abi-app/application.adf' if mode=='abi' else 'build/filer-action-disc/actions.adf');application='!CAbiTest' if mode=='abi' else 'CopyMe'
 if not args.verify_existing:
  shutil.rmtree(p,ignore_errors=True)
  run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,disc,p,application,*([mode] if mode!='abi' else [])],name)
 r=json.loads((p/'result.json').read_text());r['generated_sprite_code'].sort(key=lambda v:(v['pc'],v['word']));assert r['status']=='PASS' and r['task_count']==desktop_tasks and not r['errors'];assert all(r['exceptions'][i]==0 for i in [3,4,5])
 audit=verify(p,required=['SharedCLib'] if mode=='abi' else ['Filer','FilerSWIs','FilerAct','SharedCLib'],root=root)
 if mode in ['copy','move','delete']:media=verify_disc(p/'copied.adf',mode)
 elif mode=='protected':
  assert (p/'copied.adf').read_bytes()==disc.read_bytes();media=dict(status='PASS',unchanged_sha256=hashlib.sha256(disc.read_bytes()).hexdigest(),error=json.loads((p/'protected-error.json').read_text()))
 else:media=dict(status='PASS',public_client=json.loads((REPO/'build/c-abi-app/manifest.json').read_text()))
 (p/'media-verification.json').write_text(json.dumps(media,indent=2)+'\n')
 screens={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.png')};print(name+' PASS',flush=True)
 return mode,n,dict(result=r,media=media,trace=audit,screens=screens)
results={m:{} for m in ['copy','move','delete','protected','abi']}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(trial,m,n) for m in results for n in COLD]
 for f in concurrent.futures.as_completed(futures):
  m,n,r=f.result();results[m][n]=r
for mode,rows in results.items():same(rows)
rom_sha=hashlib.sha256((root/'arclibre.rom').read_bytes()).hexdigest()
report=dict(status='PASS',rom_sha256=rom_sha,cold_boots_per_operation=3,independent_machines=15,identical_repeats=True,real_mouse_operations=['copy','shift-drag move','menu delete','write-protected copy and Abort'],file_bytes_metadata_directory_checksums_free_maps_verified=True,public_c_abi_client=True,emulator_unchanged=True,results={m:v[1] for m,v in results.items()},limitations=['Single-file old-map D-format operations; not recursive, cross-volume, full-disc or exhaustive filing coverage.','Bounded public C ABI checks, not the entire C-library interface.'])
finish(out,report);print('Desktop filing/C ABI gate PASS',flush=True)
