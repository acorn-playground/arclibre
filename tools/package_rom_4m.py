#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Copy the tested 4 MB ROM into dist/: arclibre-4m.rom, its SHA-256 sidecar and
a MacArch machine file (the 2 MB one's A440/1 configuration and CMOS).

Refuses unless tests/run_rom_4m.py passed (three cold boots and its negative
control) for exactly this ROM. The 2 MB release packaging is unaffected.
"""
import hashlib,json,shutil
from paths import REPO
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rom=REPO/'build/arclibre-4m/arclibre.rom';dist=REPO/'dist';dist.mkdir(exist_ok=True)
report=json.loads((REPO/'build/rom-4m-tests/acceptance.json').read_text())
assert report['status']=='PASS' and report['cold_boots']==3 and report['rom_sha256']==sha(rom),'run make arclibre-test-4m first'
shutil.copy2(rom,dist/'arclibre-4m.rom')
(dist/'arclibre-4m.rom.sha256').write_text(sha(rom)+'  arclibre-4m.rom\n')
machine=json.loads((dist/'arclibre.machine.json').read_text());machine['romPaths']=['arclibre-4m.rom']
(dist/'arclibre-4m.machine.json').write_text(json.dumps(machine,indent=2)+'\n')
print(dist/'arclibre-4m.rom',sha(rom))
