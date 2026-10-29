#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Record a release: only completed gates, for the exact 2 MB and 4 MB ROMs and the extras disc.

The repository keeps the summary (docs/archimedes-desktop/reports/integration.json,
with every gate report's SHA-256) and the release record
(manifests/arclibre-desktop-release.json). The full reports are in the
release's evidence archive under evidence/reports/ (tools/package_arclibre.py).
"""
import argparse,hashlib,json,pathlib
from paths import REPO
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--milestone',required=True)
p.add_argument('--date',required=True)
args=p.parse_args()
def read(name):return json.loads((REPO/name).read_text())
def sha(name):return hashlib.sha256((REPO/name).read_bytes()).hexdigest()
def write(name,value):(REPO/name).write_text(json.dumps(value,indent=2)+'\n')
layout=read('build/arclibre/rom-layout.json');digest=sha('build/arclibre/arclibre.rom')
assert layout['rom_sha256']==digest
reports={
 'desktop-acceptance':'build/arclibre/acceptance.json',
 'sprite-command-acceptance':'build/sprite-commands/acceptance.json',
 'palette-acceptance':'build/palette/acceptance.json',
 'sound-acceptance':'build/sound/acceptance.json',
 'drag-acceptance':'build/desktop-actions/acceptance.json',
 'filing-acceptance':'build/desktop-c-runtime/acceptance.json',
 'edit-acceptance':'build/desktop-apps/acceptance/acceptance.json',
 'graphics-acceptance':'build/graphics-apps/acceptance/acceptance.json',
 'editing-acceptance':'build/app-workflows/acceptance.json',
 'task-services-acceptance':'build/task-service-tests/acceptance.json',
 'menu-acceptance':'build/menu-tests/acceptance.json',
 'menu-negative-control':'build/menu-tests/negative-control.json',
 'streams-acceptance':'build/stream-tests/acceptance.json',
 'ram-filing-acceptance':'build/ram-filing-tests/acceptance.json'}
if any(x['component']=='ScrBlank' for x in layout['modules']):reports['utilities-acceptance']='build/utility-tests/acceptance.json'
reports['dosfs-acceptance']='build/dosfs-tests/acceptance.json'
reports['format-acceptance']='build/format-tests/acceptance.json'
reports['dosfs-formats-acceptance']='build/dosfs-format-tests/acceptance.json'
reports['new-io-acceptance']='build/new-io-tests/acceptance.json'
reports['arm3-acceptance']='build/arm3-tests/acceptance.json'
if any(x['component']=='Econet' for x in layout['modules']):reports.update({'network-acceptance':'build/network-tests/acceptance.json','netfs-acceptance':'build/netfs-tests/acceptance.json'})
if any(x['component']=='Podule' for x in layout['modules']):reports['hardware-acceptance']='build/hardware-tests/acceptance.json'
reports['printing-acceptance']='build/printing-tests/acceptance.json'
reports['extras-acceptance']='build/extras-tests/acceptance.json'
if any(x['component']=='Debugger' for x in layout['modules']):reports['debugger-acceptance']='build/debugger-tests/acceptance.json'
if any(x['component']=='IIC' for x in layout['modules']):reports['clock-acceptance']='build/clock-tests/acceptance.json'
if any(x['component']=='Squash' for x in layout['modules']):reports['squash-acceptance']='build/squash-tests/acceptance.json'
if any(x['component']=='Chars' for x in layout['modules']):reports['basic-utilities-acceptance']='build/basic-utility-tests/acceptance.json'
calendar=read('build/desktop-c-runtime/identity-calendar.json')
assert calendar['status']=='PASS' and calendar['source_sha256']==sha('src/RISC_OSLib/c/armsys')
checks=[]
for name,path in reports.items():
 r=read(path);assert r['status']=='PASS' and r['rom_sha256']==digest,(path,r.get('rom_sha256'))
 checks.append(dict(report=path,status='PASS',sha256=sha(path),rom_sha256=digest,**{k:r[k] for k in ['cold_boots','cold_boots_per_application','cold_machines','application_cold_boots','independent_cold_boots','trials','trials_per_app'] if k in r}))
negative=read('build/stream-tests/sleep-negative.json')
assert negative['status']=='PASS' and negative['positive_rom_sha256']==digest
checks.append(dict(report='build/stream-tests/sleep-negative.json',status='PASS',sha256=sha('build/stream-tests/sleep-negative.json'),rom_sha256=digest))
repro=read('build/graphics-apps/reproducibility.json')
assert repro['status']=='PASS' and repro['hashes']['build/arclibre-graphics/arclibre.rom']==digest
# The 4 MB ROM: its own gate, for its own hash.
rom_4m=sha('build/arclibre-4m/arclibre.rom');rom_4m_report=read('build/rom-4m-tests/acceptance.json')
assert rom_4m_report['status']=='PASS' and rom_4m_report['cold_boots']==3 and rom_4m_report['rom_sha256']==rom_4m,'run make release-test first'
extras=read('build/extras-tests/acceptance.json');assert extras['disc_sha256']==sha('build/extras-disc/arclibre-extras.adf')
checks.append(dict(report='build/rom-4m-tests/acceptance.json',status='PASS',sha256=sha('build/rom-4m-tests/acceptance.json'),rom_sha256=rom_4m,cold_boots=3))
version=read('manifests/release.json')
# All prerequisites passed before replacing any release metadata.
integration=dict(status='PASS',rom_sha256=digest,checks=checks,build_reproducibility_sha256=sha('build/graphics-apps/reproducibility.json'),kernel_sha256=layout['kernel_sha256'],emulator_unchanged=True,used_bytes=layout['used_bytes'],free_bytes=2097152-layout['used_bytes'],compatibility_scope='Bounded desktop/application gates; not complete RISC OS 3.11 compatibility')
write('docs/archimedes-desktop/reports/integration.json',integration)
release=read('manifests/arclibre-desktop-release.json')
release.update(version=version['version'],rom_date=version['date'],rom_4m_sha256=rom_4m,extras_disc_sha256=extras['disc_sha256'],rom_4m_acceptance='evidence/reports/rom-4m-acceptance.json',milestone=args.milestone,date=args.date,acceptance=read('build/arclibre/acceptance.json'),modules=layout['modules'],rom_sha256=digest,used_bytes=layout['used_bytes'],free_bytes=2097152-layout['used_bytes'],integration='docs/archimedes-desktop/reports/integration.json')
# Report paths in the release's evidence archive (tools/package_arclibre.py).
for name in reports:release[name.replace('-','_')]='evidence/reports/'+name+'.json'
release['stream_sleep_negative']='evidence/reports/sleep-negative.json'
for k in ['nevryon_acceptance','zarch_acceptance']:release.pop(k,None)
release['evidence_reports']={**{f'evidence/reports/{name}.json':path for name,path in reports.items()},'evidence/reports/sleep-negative.json':'build/stream-tests/sleep-negative.json',
 'evidence/reports/rom-4m-acceptance.json':'build/rom-4m-tests/acceptance.json','evidence/reports/identity-calendar.json':'build/desktop-c-runtime/identity-calendar.json',
 'evidence/reports/reproducibility.json':'build/graphics-apps/reproducibility.json','evidence/reports/resources.json':'build/arclibre/desktop-resource-selection.json','evidence/reports/palette-assembly.json':'build/palette/result.json'}
release['evidence_report_sha256']={k:sha(v) for k,v in release['evidence_reports'].items()}
write('manifests/arclibre-desktop-release.json',release)
print('Recorded exact-ROM release',digest)
