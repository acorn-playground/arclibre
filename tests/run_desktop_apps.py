#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Three real desktop Edit save/power-off/reopen cycles on disposable ST506 media."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
from verify_filer_disc import read_directory
from adfs_fixture import oldcheck
parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',default='build/arclibre');parser.add_argument('--verify-existing',action='store_true');parser.add_argument('--probe',action='store_true',help='one cold boot; writes probe.json');args=parser.parse_args()
root=REPO/args.root;out=REPO/'build/desktop-apps/acceptance';out.mkdir(parents=True,exist_ok=True);start(out)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
payload=b'ArcLibre document saved by the original Edit.\nSecond line survives a cold restart.\n'
def media(p):
 b=p.read_bytes();assert len(b)==615*4*32*256
 assert b[255]==oldcheck(b[:255]) and b[511]==oldcheck(b[256:511])
 rows=read_directory(b,4);assert set(rows)=={'ReadMe','Document'};used=[(0,0xe00)]
 for name,data in [('Document',payload),('ReadMe',b'ArcLibre original ST506 hard disc.\n')]:
  r=rows[name];start=r['address']*256;assert r['length']==len(data) and b[start:start+len(data)]==data
  assert r['load']>>8==0xffffff and r['attributes']==3
  used.append((start,start+((len(data)+255)&~255)))
 assert b[510]%3==0
 free=[]
 for i in range(0,b[510],3):
  start=int.from_bytes(b[i:i+3],'little')*256;length=int.from_bytes(b[256+i:259+i],'little')*256
  assert length>0;free.append((start,start+length))
 spans=sorted(used+free);assert spans[0][0]==0 and spans[-1][1]==len(b)
 assert all(a[1]==z[0] for a,z in zip(spans,spans[1:])), 'complete non-overlapping allocation map'
 return dict(sha256=sha(p),files=rows,bytes=len(b),free_bytes=sum(z-a for a,z in free),checksums_and_allocation_accounting=True)
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','EditProbe'],'harness')
def trial(n):
 p=out/f'cold-{n}'
 if not args.verify_existing:
  shutil.rmtree(p,ignore_errors=True)
  run([REPO/'build/harness-patched/release/EditProbe',root/'arclibre.rom',root,p],f'write-{n}')
  before=media(p/'test.hdf')
  (p/'written-media.json').write_text(json.dumps(before,indent=2)+'\n')
  run([REPO/'build/harness-patched/release/EditProbe',root/'arclibre.rom',root,p,'reopen'],f'reopen-{n}')
 before=load(p/'written-media.json');after=media(p/'test.hdf');assert before==after,'reopening leaves disk bytes unchanged'
 results={}
 for phase in ['write','reopen']:
  r=load(p/phase/'result.json');assert r['status']=='PASS' and r['rom_sha256']==sha(root/'arclibre.rom')
  assert r['phase']==phase and r['task_count']==desktop_task_count(root)+1 and not r['errors'] and all(r['exceptions'][i]==0 for i in [3,4,5])
  assert r['configuration']['cmosSettings']==[]
  assert r['configuration']['powerOnKeys']==([0x34] if phase=='write' else [])
  assert any(t['text'].encode('latin1')==payload for t in r['text_buffers'])
  assert r['cmos'][199]==9 and r['cmos'][75]&7==0 and r['cmos'][80]&16==0 and r['cmos'][249]==10 and r['cmos'][20]==12
  assert r['writes']>0 if phase=='write' else r['writes']==0
  trace=verify(p/phase,required=['SharedCLib','Edit','ADFS','Filer','BASIC'],root=root)
  # Paths differ per trial; compare the actual observations, not host filenames.
  r.pop('configuration');results[phase]=dict(result=r,trace=trace,screens={f.name:sha(f) for f in (p/phase).glob('*.png')})
 return n,dict(media=after,phases=results)
results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for n,r in pool.map(trial,COLD):results[n]=r
same(results)
report=dict(status='PASS',rom_sha256=sha(root/'arclibre.rom'),trials=3,independent_cold_boots=6,identical_repeats=True,original_edit_and_apps=True,real_st506_controller=True,no_guest_code_injection=True,emulator_unchanged=True,save_then_power_off_then_desktop_double_click=True,actual_edit_buffer_and_on_disc_bytes_match=True,saved_cmos_reloaded_without_overrides=True,payload_sha256=hashlib.sha256(payload).hexdigest(),result=results[1])
finish(out,report);print('Edit hard-disc persistence gate PASS',flush=True)
