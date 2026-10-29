#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reintroduce only the observed wrong MenuWarning number as a negative control."""
import hashlib,json,os,shutil,struct,subprocess
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
root=REPO/'build/arclibre';out=REPO/'build/menu-tests';negative=REPO/'build/arclibre-bad-menu';negative.mkdir(parents=True,exist_ok=True)
rom=bytearray((root/'arclibre.rom').read_bytes());layout=json.loads((root/'rom-layout.json').read_text())
wimp=next(m for m in layout['modules'] if m['component']=='Wimp');base=wimp['base']-0x3800000
rows=json.loads((REPO/'build/desktop-components/modules/Wimp/instructions.json').read_text())
loads=[]
for row in rows:
 s=row['source']
 if s['file'].endswith('Wimp05'):
  text=(REPO/'build/desktop-components'/s['file']).read_text().splitlines()[s['line']-1]
  if 'Message_MenuWarning' in text:loads.append(row)
assert len(loads)==1 and loads[0]['decoded']['kind']=='LDR'
offset=loads[0]['decoded']['literal'];assert struct.unpack_from('<I',rom,base+offset)[0]==0x400c0
original=hashlib.sha256(rom).hexdigest();struct.pack_into('<I',rom,base+offset,0x800c0)
layout['rom_sha256']=hashlib.sha256(rom).hexdigest()
wimp['sha256']=hashlib.sha256(rom[base:base+wimp['length']]).hexdigest()
(negative/'arclibre.rom').write_bytes(rom);(negative/'rom-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
probe=negative/'probe';shutil.rmtree(probe,ignore_errors=True)
with (out/'negative.log').open('w') as log:
 r=subprocess.run([str(REPO/'build/harness-patched/release/DesktopLaunchProbe'),str(negative/'arclibre.rom'),str(negative),str(REPO/'build/menu-app/application.adf'),str(probe),'!MenuTest'],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==1
failure=json.loads((probe/'failure.json').read_text());assert failure['failure']=='classic menu client assertion failure'
assert all(failure['exceptions'][i]==0 for i in [3,4,5])
report=dict(status='PASS',scope='Wrong message number rejected by the independent classic client',rom_sha256=original,negative_rom_sha256=layout['rom_sha256'],changed_word_address=wimp['base']+offset,old_message=0x400c0,negative_message=0x800c0,expected_failure=failure['failure'])
(out/'negative-control.json').write_text(json.dumps(report,indent=2)+'\n');print('Menu warning negative control PASS')
