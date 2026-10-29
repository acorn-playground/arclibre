#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original SpriteUtils commands, public artwork and real floppy round-trip."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from adfs_fixture import oldcheck
from verify_filer_disc import read_directory
from verify_desktop_rom_trace import verify
args=[x for x in sys.argv[1:] if not x.startswith('--')];root=REPO/(args[0] if args else 'build/arclibre');out=REPO/'build/sprite-commands';out.mkdir(exist_ok=True);start(out)
env=dict(os.environ,PYTHONPATH=str(REPO/'tools'),MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(v) for v in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
run([sys.executable,REPO/'tests/build_sprite_command_app.py'],'fixture')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
fixture=REPO/'build/sprite-command-app/application.adf';expected=(REPO/'build/sprite-command-app/input.sprite').read_bytes();rom_sha=hashlib.sha256((root/'arclibre.rom').read_bytes()).hexdigest()
def trial(n):
 p=out/f'cold-{n}';shutil.rmtree(p,ignore_errors=True);p.mkdir();shutil.copy2(fixture,p/'input.adf')
 run([REPO/'build/harness-patched/release/DesktopLaunchProbe',root/'arclibre.rom',root,p/'input.adf',p,'!SprTest'],f'cold-{n}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==rom_sha and not r['errors'] and all(r['exceptions'][i]==0 for i in [3,4,5]);r.pop('disc')
 b=(p/'saved.adf').read_bytes();assert b[255]==oldcheck(b[:255]) and b[511]==oldcheck(b[256:511])
 app=read_directory(b,read_directory(b,4)['!SprTest']['address']);assert set(app)=={'!Run','!RunImage','Input','Saved'}
 row=app['Saved'];saved=b[row['address']*256:row['address']*256+row['length']];assert saved==expected and row['load']>>8&4095==0xff9
 assert (p/'input.adf').read_bytes()==fixture.read_bytes(),'host fixture preserved'
 v=verify(p,required=['SpriteUtil','FileCore','ADFS'],root=root)
 return dict(result=r,trace=v,saved_sprite_sha256=hashlib.sha256(saved).hexdigest(),saved_disc_sha256=hashlib.sha256(b).hexdigest())
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Sprite commands')
report=dict(status='PASS',rom_sha256=rom_sha,cold_boots=3,identical_observations=True,original_module=True,public_fixture=True,emulator_unchanged=True,real_sprite_dynamic_area=True,all_16_pixels_checked=True,exact_load_save_roundtrip=True,missing_file_error_recovery=True,commands=['SNew','SLoad','SChoose','SCopy','SRename','SDelete','SFlipX','SFlipY','SList','SInfo','Help SLoad','SSave'],observations=results[0])
finish(out,report);print('Sprite command gate PASS')
