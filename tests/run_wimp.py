#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Isolated real Wimp task, three fresh cold boots, ARM2/USR26 and pixels."""
import hashlib,json,os,pathlib,shutil,struct,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
from verify_wimp_trace import verify as verify_trace
out=REPO/'build/wimp-stack';logs=out/'logs';logs.mkdir(exist_ok=True);(out/'acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print('Running',name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def pixels(b):return [v for byte in b for v in (byte&15,byte>>4)]
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness')
bin=REPO/'build/harness-patched/release';a=ROOT/'artifacts';rom=a/'floppy.rom'
run([bin/'BootProbe',rom,out/'cold-boots',3],'cold-boots')
results=[];hashes=[];pixel_reports=[]
for i in [1,2,3]:
 natural=out/f'natural-{i}';probe=out/f'run-{i}'
 if probe.exists():shutil.rmtree(probe)
 run([bin/'CamProbe',rom,out/f'cold-boots/cold-{i}/pre-module.macarch-state',a/'symbols.json',natural,'natural'],f'natural-{i}')
 run([bin/'WimpProbe',rom,natural/'supervisor-entry.macarch-state',out,probe],f'wimp-{i}')
 r=json.loads((probe/'result.json').read_text());assert r['status']=='PASS' and len(r['loaded'])==8
 assert all(r['exceptions'][n]==0 for n in [3,4,5,7]) and r['exceptions'][1]>0
 assert r['task'][0]==366 and r['original_memc_path'] and r['fpa_preserved']
 initial=next(j for j,c in enumerate(r['calls']) if c['name']=='Initialise diagnostic task')
 final=next(j for j,c in enumerate(r['calls']) if c['name']=='Return to Supervisor')
 assert all(c['psr']&3==0 for c in r['calls'][initial:final]),'every task SWI returns USR26'
 reasons=[e['reason'] for e in r['events']];assert set([0,1,2,3,4,5,6,8,12,17]).issubset(reasons)
 assert all(e['undefined_traps']>0 for e in r['events']),'real FPA traps during polling'
 click=next(e for e in r['events'] if e['reason']==6);assert click['block'][:5]==[400,412,4,r['window'],0xffffffff]
 msg=next(e for e in r['events'] if e['reason']==17);assert msg['block'][0]==24 and msg['block'][1]==r['task'][1] and msg['block'][4:6]==[0x4c435241,0x11223344]
 assert r['moved'][1:5]==[300,300,900,900] and not r['closed'][8]&0x10000
 images={name:(probe/(name+'.bin')).read_bytes() for name in ['window','moved','closed']}
 assert all(len(b)==81920 for b in images.values());px={n:pixels(b) for n,b in images.items()}
 ink=sum(px['window'][y*640+x]==7 for y in range(65,90) for x in range(60,330));assert ink>100,'client redraw text is visible inside the window'
 # Window work-area position moves +100 physical pixels horizontally and +25
 # vertically. Untouched interior background/text pixels must move exactly.
 compared=0
 for y in range(58,205):
  for x in range(51,349):
   assert px['window'][y*640+x]==px['moved'][(y-25)*640+x+100],(i,x,y)
   compared+=1
 # The genuine close request removes the complete window and restores desktop.
 assert set(px['closed'])=={4},'window close restores the uniform desktop'
 hashes.append({n:hashlib.sha256(b).hexdigest() for n,b in images.items()})
 pixel_reports.append(dict(client_text_ink_pixels=ink,translated_interior_pixels=compared,closed_desktop_pixels=640*256))
 verify_trace(probe)
 results.append(r)
assert results[0]==results[1]==results[2] and hashes[0]==hashes[1]==hashes[2]
# A same-address negative control removes only the restored list-pointer load.
# It must reproduce incorrect message registration, with no CPU fault.
negative=out/'negative-input'
if negative.exists():shutil.rmtree(negative)
negative.mkdir();shutil.copytree(out/'modules',negative/'modules')
for name in ['resources.bin','client.bin','client-symbols.json']:shutil.copy2(out/name,negative/name)
symbols=json.loads((negative/'modules/Wimp/symbols.json').read_text());offset=symbols['restore_initial_message_list']['value']
p=negative/'modules/Wimp/module.bin';b=bytearray(p.read_bytes());assert struct.unpack_from('<I',b,offset)[0]==0xe59d300c
struct.pack_into('<I',b,offset,0xe1a00000);p.write_bytes(b)
negative_run=out/'negative-message-list'
if negative_run.exists():shutil.rmtree(negative_run)
with (logs/'negative-message-list.log').open('w') as f:
 failed=subprocess.run([str(bin/'WimpProbe'),str(rom),str(out/'natural-1/supervisor-entry.macarch-state'),str(negative),str(negative_run)],env=env,stdout=f,stderr=subprocess.STDOUT)
assert failed.returncode==1
failure=json.loads((negative_run/'failure.json').read_text());assert failure['failure']=='caller message-interest list preserved'
assert all(failure['exceptions'][n]==0 for n in [3,4,5,7])
negative_report=dict(status='EXPECTED_FAILURE',instruction_offset=offset,replaced='LDR R3,[SP,#12]',replacement='NOP',module_sha256=hashlib.sha256(b).hexdigest(),failure=failure['failure'],contract=json.loads((negative_run/'message-contract.json').read_text()))
(out/'negative-control.json').write_text(json.dumps(negative_report,indent=2)+'\n')
report=dict(status='PASS' ,cold_runs=3,identical_results=True,message_list_negative_control=negative_report,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),inputs=json.loads((out/'inputs.json').read_text()),swi_calls_per_run=len(results[0]['calls']),requested_wimp_api=310,reported_wimp_version=366,task_mode='USR26',original_memc_path=True,event_reasons=sorted(set(e['reason'] for e in results[0]['events'])),real_keyboard_and_mouse=True,real_message_delivery=True,fpa_registers_and_fpsr_preserved=True,pixel_verification=pixel_reports[0],framebuffer_hashes=hashes[0],baseline_rom_modified=False,emulator_modified=False,sampled_module_trace_audit=True,scope='One diagnostic task, window, input, self-message, FPA save/restore and cleanup; not multi-task scheduling, full desktop or RISC OS 3.11 conformance')
assert report['rom_sha256']==json.loads((REPO/'manifests/baseline-rom.json').read_text())['rom_sha256']
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
