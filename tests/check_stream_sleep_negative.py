#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Restore the observed unclaimed-vector defect in an explicit negative ROM."""
import hashlib,json,pathlib,shutil,struct,subprocess
R=pathlib.Path(__file__).resolve().parents[1];root=R/'build/arclibre';out=R/'build/arclibre-bad-sleep';out.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
layout=json.loads((root/'rom-layout.json').read_text());data=bytearray((root/'arclibre.rom').read_bytes());assert sha(data)==layout['rom_sha256']
row=next(x for x in layout['modules'] if x['component']=='TaskWindow');module=root/'task-runtime/modules/TaskWindow'
symbols=json.loads((module/'symbols.json').read_text());start=symbols['sleepnomore']
code=json.loads((module/'instructions.json').read_text());matches=[v['offset'] for v in code if start<=v['offset']<start+80 and v['source']['word']==0xe8bd4000]
assert len(matches)==1
address=row['base']+matches[0];offset=address-0x3800000
assert struct.unpack_from('<I',data,offset)[0]==0xe8bd4000
struct.pack_into('<I',data,offset,0xe1a00000) # omit claiming the vector, as in the pinned original
row['sha256']=sha(data[row['base']-0x3800000:row['base']-0x3800000+row['length']]);layout['rom_sha256']=sha(data)
(out/'arclibre.rom').write_bytes(data);(out/'rom-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
# Harness observation uses PipeFS symbols, not patched TaskWindow metadata.
shutil.copytree(root/'stream-runtime',out/'stream-runtime',dirs_exist_ok=True)
probe=out/'probe';shutil.rmtree(probe,ignore_errors=True)
with (out/'probe.log').open('w') as f:p=subprocess.run([str(x) for x in [R/'build/harness-streams/release/DesktopLaunchProbe',out/'arclibre.rom',out,R/'build/stream-app/application.adf',probe,'!StrTest']],stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==1
failure=json.loads((probe/'failure.json').read_text());assert failure['failure']=='stream client assertion failure'
assert all(failure['exceptions'][i]==0 for i in [3,4,5])
events=json.loads((probe/'launch-events.json').read_text())
assert any(e['swi']==2 and e['text']=='sleeping word removal was not rejected' for e in events)
report=dict(status='PASS',positive_rom_sha256=sha((root/'arclibre.rom').read_bytes()),negative_rom_sha256=sha(data),modified_instruction_address=address,original_word='E8BD4000',negative_word='E1A00000',purpose='Reproduce unclaimed SleepNoMore vector error; all other ROM bytes identical',expected_failure=failure['failure'],sleeping_removal_error_lost=True)
(R/'build/stream-tests/sleep-negative.json').write_text(json.dumps(report,indent=2)+'\n');print('Unclaimed SleepNoMore negative control PASS')
