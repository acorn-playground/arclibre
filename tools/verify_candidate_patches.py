#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prove candidate patches recover pinned bytes and reapply without fuzz."""
import hashlib,json,pathlib,shutil,subprocess,tempfile
from paths import REPO
rows=json.loads((REPO/'manifests/desktop-inputs.json').read_text())
for r in rows:r['original_sha256']=r['upstream_sha256']
groups=[('desktop-source',rows,'desktop-source/0001-assembly-contracts.patch'),('fpemulator',[dict(component='FPEmulator',**x) for x in json.loads((REPO/'manifests/fpemulator.json').read_text())['files']],'fpemulator/0001-arm2-build.patch')]
startup=json.loads((REPO/'manifests/desktop-startup-inputs.json').read_text())
for r in startup:r['original_sha256']=r['upstream_sha256']
groups.append(('desktop-startup',startup,'desktop-startup/0001-arm2-assembly.patch'))
sound=json.loads((REPO/'manifests/sound-inputs.json').read_text())
for r in sound:r['original_sha256']=r['upstream_sha256']
groups.append(('sound',sound,'sound/0001-arm2-build.patch'))
actions=json.loads((REPO/'manifests/desktop-action-inputs.json').read_text())
for r in actions:r['original_sha256']=r['upstream_sha256']
groups.append(('desktop-actions',actions,'desktop-actions/0001-drag-arm2.patch'))
c_inputs=json.loads((REPO/'manifests/desktop-c-inputs.json').read_text())
for r in c_inputs:r['original_sha256']=r['upstream_sha256']
groups.append(('desktop-c',c_inputs,'desktop-c/0001-gcc-arm2-library.patch'))
apps=json.loads((REPO/'manifests/desktop-app-inputs.json').read_text())
for r in apps:r['original_sha256']=r['upstream_sha256']
groups.append(('desktop-apps',apps,'desktop-apps/0001-original-app-build.patch'))
graphics=json.loads((REPO/'manifests/graphics-app-inputs.json').read_text())
for r in graphics:r['original_sha256']=r['upstream_sha256']
groups.append(('graphics-apps',graphics,'graphics-apps/0001-original-graphics-build.patch'))
tasks=json.loads((REPO/'manifests/task-services-inputs.json').read_text())
for r in tasks:r['original_sha256']=r['upstream_sha256']
groups.append(('task-services',tasks,'task-services/0001-arm2-assembly-contracts.patch'))
messages=json.loads((REPO/'manifests/public-message-inputs.json').read_text())
for r in messages:r['original_sha256']=r['upstream_sha256']
groups.append(('public-messages',messages,'public-messages/0001-canonical-message-bases.patch'))
streams=json.loads((REPO/'manifests/stream-inputs.json').read_text())
for r in streams:r['original_sha256']=r['upstream_sha256']
groups.append(('streams',streams,'streams/0001-arm2-assembly-contracts.patch'))
ram=json.loads((REPO/'manifests/ram-filing-inputs.json').read_text())
for r in ram:r['original_sha256']=r['upstream_sha256']
groups.append(('ram-filing',ram,'ram-filing/0001-arm2-build.patch'))
utilities=json.loads((REPO/'manifests/standard-utility-inputs.json').read_text())
for r in utilities:r['original_sha256']=r['upstream_sha256']
groups.append(('standard-utilities',utilities,'standard-utilities/0001-arm2-build.patch'))
desktop_utilities=json.loads((REPO/'manifests/desktop-utility-inputs.json').read_text())
for r in desktop_utilities:r['original_sha256']=r['upstream_sha256']
groups.append(('desktop-utilities',desktop_utilities,'desktop-utilities/0001-existing-squash-host-includes.patch'))
clock=json.loads((REPO/'manifests/clock-inputs.json').read_text())
for r in clock:r['original_sha256']=r['upstream_sha256']
groups.append(('clock',clock,'clock/0001-arm2-build.patch'))
debugger=json.loads((REPO/'manifests/debugger-inputs.json').read_text())
for r in debugger:r['original_sha256']=r['upstream_sha256']
groups.append(('debugger',debugger,'debugger/0001-arm2-build.patch'))
network=json.loads((REPO/'manifests/network-inputs.json').read_text())
for r in network:r['original_sha256']=r['upstream_sha256']
groups.append(('network',network,'network/0001-arm2-build.patch'))
hardware=json.loads((REPO/'manifests/hardware-inputs.json').read_text())
for r in hardware:r['original_sha256']=r['upstream_sha256']
groups.append(('hardware',hardware,'hardware/0001-arm2-build.patch'))
printing=json.loads((REPO/'manifests/printing-inputs.json').read_text())
for r in printing:r['original_sha256']=r['upstream_sha256']
groups.append(('printing',printing,'printing/0001-disc-build.patch'))
# DOSFS's s/StaticDefs import baseline excises the opaque boot-sector
# template (tools/import_dosfs.py records both hashes); reversing the patch
# must restore that baseline, and every other file's upstream bytes.
dosfs=json.loads((REPO/'manifests/dosfs-inputs.json').read_text())
for r in dosfs:r['original_sha256']=r.get('baseline_sha256',r['upstream_sha256'])
groups.append(('dosfs',dosfs,'dosfs/0001-disc-module-build.patch'))
report=[]
for name,rows,patch in groups:
 with tempfile.TemporaryDirectory(prefix='archimedes-patch-') as tmp:
  root=pathlib.Path(tmp)
  for row in rows:
   p=root/'src'/row['component']/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/'src'/row['component']/row['path'],p)
  for reverse,field in [(True,'original_sha256'),(False,'sha256')]:
   series=REPO/'patches'/name/'series';patches=series.read_text().splitlines()
   for filename in (reversed(patches) if reverse else patches):
    c=['patch','--batch','-p1','--fuzz=0']+(['-R'] if reverse else [])+['-i',str(series.parent/filename)]
    p=subprocess.run(c,cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
   for row in rows:assert hashlib.sha256((root/'src'/row['component']/row['path']).read_bytes()).hexdigest()==row[field],row
 report.append(dict(series=name,status='PASS',files=len(rows),reverse_restores_original_hashes=True,forward_restores_maintained_hashes=True))
out=REPO/'build/candidate-patches.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
