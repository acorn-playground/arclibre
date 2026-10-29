#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Repeat complete compiler/assembler/link builds and compare final bytes."""
import hashlib,json,pathlib,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];out=REPO/'build/desktop-c-runtime'
observations=[]
for n in [1,2]:
 with (out/f'reproducibility-{n}.log').open('w') as f:
  for script,args in [('build_c_desktop.py',[]),('build_arclibre_rom.py',['--with-c-desktop'])]:subprocess.run([sys.executable,REPO/'tools'/script,*args],stdout=f,stderr=subprocess.STDOUT,check=True)
 objects={}
 for file in ['link-inputs.json','filer-inputs.json']:objects.update(json.loads((out/file).read_text())['objects'])
 paths=set(objects.values())|{'build/desktop-c-runtime/SharedCLib.bin','build/desktop-c-runtime/FilerAct.bin','build/arclibre-c-desktop/arclibre.rom'}
 observations.append({p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)})
assert observations[0]==observations[1]
(out/'reproducibility.json').write_text(json.dumps(dict(status='PASS',complete_builds=2,hashes=observations[0]),indent=2)+'\n');print('C compilation/assembly/link reproducibility PASS')
