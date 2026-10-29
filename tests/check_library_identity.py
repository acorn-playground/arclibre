#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile the actual library identification with two hostile calendar dates."""
import hashlib,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parents[1];out=R/'build/desktop-c-runtime';options=json.loads((out/'build-options.json').read_text());original=(out/'lib-armsys.gcc.s').read_bytes();hashes=[]
for n,date in enumerate(['Jan  1 1970','Dec 31 2099']):
 p=out/f'identity-calendar-{n}.s'
 with (out/f'identity-calendar-{n}.log').open('w') as f:
  subprocess.run([options['compiler'],*options['flags'],*options['library_flags'],'-D__DATE__="'+date+'"','-S','-x','c','src/RISC_OSLib/c/armsys','-o',str(p)],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
 assert p.read_bytes()==original,'host calendar changed library assembly'
 hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
(out/'identity-calendar.json').write_text(json.dumps(dict(status='PASS',simulated_dates=['Jan  1 1970','Dec 31 2099'],identical_to_normal_build=True,source_sha256=hashlib.sha256((R/'src/RISC_OSLib/c/armsys').read_bytes()).hexdigest(),assembly_sha256=hashes[0]),indent=2)+'\n')
print('C library identification is independent of compilation date')
