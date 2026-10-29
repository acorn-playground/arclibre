#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the original Squash SWIs and independently decompress their .Z streams."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
args=[a for a in sys.argv[1:] if not a.startswith('--')]
root=R/(args[0] if args else 'build/arclibre-squash');out=R/'build/squash-tests';out.mkdir(exist_ok=True)
(out/('probe.json' if '--probe' in sys.argv else 'acceptance.json')).unlink(missing_ok=True)
env=dict(os.environ,PYTHONPATH=str(R/'tools'),MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,R/'tests/build_squash_app.py'],'fixture')
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-squash','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
exe=R/'build/harness-squash/release/DesktopLaunchProbe';fixture=R/'build/squash-app/application.adf';rom_hash=sha(root/'arclibre.rom')
x=0x12345678;vectors=[]
for v,n in enumerate([1,256,8192,16000]):
 data=bytearray()
 for i in range(n):
  x=(x^(x<<13))&0xffffffff;x^=x>>17;x=(x^(x<<5))&0xffffffff
  data.append((0xe7 if v==0 else i if v==1 else i%7 if v==2 else x)&255)
 vectors.append(bytes(data))
def trial(n):
 p=out/f'cold-{n}'
 if '--verify-existing' not in sys.argv:
  shutil.rmtree(p,ignore_errors=True);run([exe,root/'arclibre.rom',root,fixture,p,'!SqTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==rom_hash and r['task_count']==desktop_task_count(root) and not r['errors']
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 assert all(any(e['text']=='ARCLIBRE SQUASH '+name+' PASS' for e in r['events']) for name in ['BOUNDARIES','INTERLEAVED'])
 streams=[]
 for v,original in enumerate(vectors):
  for mode in [0,1]:
   data=(p/f'squash-{v}-{mode}.Z').read_bytes()
   decoded=subprocess.run(['/usr/bin/gzip','-cd'],input=data,capture_output=True,check=True).stdout
   assert decoded==original,(v,mode,'independent gzip decoding mismatch')
   streams.append(dict(vector=v,restartable=bool(mode),input_bytes=len(original),compressed_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 contract=json.loads((root/'squash-runtime/workspace-contract.json').read_text());ws=json.loads((p/'squash-workspace.json').read_text())
 assert ws['words'][0]==ws['workspace']-contract['rom_base']-contract['template_offset'] & 0xffffffff
 assert ws['words'][2]==0x5c # Real error messages file was opened.
 v=verify(p,required=['Squash'],root=root);r.pop('disc');return dict(protocol=r,streams=streams,workspace=ws,trace=v)
count=1 if '--probe' in sys.argv else 3
with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:results=list(pool.map(trial,range(1,count+1)))
assert all(r==results[0] for r in results),'cold observations differ'
negative=None
if count==3:
 # The explicit negative profile removes only the real Squash service.
 negative_root=R/(args[1] if len(args)>1 else 'build/arclibre-without-squash')
 if len(args)<2:run([sys.executable,R/'tools/build_arclibre_rom.py','--without-squash'],'negative-rom')
 assert all(m['component']!='Squash' for m in json.loads((negative_root/'rom-layout.json').read_text())['modules'])
 p=out/'negative-missing-module';shutil.rmtree(p,ignore_errors=True)
 with (out/'negative.log').open('w') as f:control=subprocess.run([str(x) for x in [exe,negative_root/'arclibre.rom',negative_root,fixture,p,'!SqTest']],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert control.returncode==1
 failure=json.loads((p/'failure.json').read_text());assert failure['failure']=='Squash client assertion failure'
 events=json.loads((p/'launch-events.json').read_text());assert any(e['text']=='SWI &42700 not known' for e in events)
 assert all(failure['exceptions'][i]==0 for i in [3,4,5])
 negative=dict(status='EXPECTED_FAILURE',rom_sha256=sha(negative_root/'arclibre.rom'),error='SWI &42700 not known')
report=dict(status='PASS',rom_sha256=rom_hash,fixture_sha256=sha(fixture),cold_boots=count,independent_host_decoder='/usr/bin/gzip -cd',fast_and_restartable_cross_decode=True,canaries_preserved=True,size_queries_and_real_errors=True,empty_input_and_short_output=True,interleaved_workspaces=True,missing_module_control=negative,observations=results[0])
(out/('probe.json' if count==1 else 'acceptance.json')).write_text(json.dumps(report,indent=2)+'\n');print('Squash SWI gate PASS',flush=True)
