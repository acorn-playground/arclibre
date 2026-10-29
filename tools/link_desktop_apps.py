#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind Edit's original ROM client veneers to the actual SharedCLibrary."""
import hashlib,json,re,subprocess
from paths import REPO,HOST
from aof import read
ROOT=REPO/'build/desktop-apps';CLIB=REPO/'build/desktop-c-runtime'
def link(base):
 symbols={n:int(v,16) for v,n in re.findall(r'\b([0-9a-f]{7,8})\s+(\S+)',(CLIB/'SharedCLib.symbols').read_text())}
 objects=[REPO/p for p in json.loads((ROOT/'edit-inputs.json').read_text())['objects'].values()]
 defined={s['name'] for p in objects for s in read(p)['symbols'] if s['attributes']&1}
 imports={s['name'] for p in objects for s in read(p)['symbols'] if not s['attributes']&1}
 bound={n:symbols[n] for n in imports-defined if n in symbols and not n.startswith('Image$$') and not n.endswith(('$$Base','$$Limit'))}
 source='\n'.join('        EXPORT |'+n+'|\n|'+n+'| EQU &'+format(v,'X') for n,v in sorted(bound.items()))+'\n        END\n'
 (ROOT/'exports.s').write_text(source)
 with (ROOT/'exports.log').open('w') as f:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-aof',str(ROOT/'exports.s'),str(ROOT/'exports.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (ROOT/'edit-link.log').open('w') as f:subprocess.run([str(REPO/'build/c-toolchain-release/install/bin/drlink'),'-bin','-base',hex(base),'-map','-symbols',str(ROOT/'Edit.symbols'),'-output',str(ROOT/'Edit.bin'),*[str(p) for p in reversed(objects)],str(ROOT/'exports.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
 row=dict(component='Edit',base=base,length=(ROOT/'Edit.bin').stat().st_size,sha256=hashlib.sha256((ROOT/'Edit.bin').read_bytes()).hexdigest(),link_log='edit-link.log')
 import shutil
 previous=json.loads((CLIB/'linked.json').read_text())
 for name in ['SharedCLib.bin','FilerAct.bin','link.log','filer-link.log']:shutil.copy2(CLIB/name,ROOT/name)
 (ROOT/'linked.json').write_text(json.dumps(dict(modules=previous['modules']+[row],bound_library_exports=bound),indent=2)+'\n')
 from verify_c_desktop import verify
 verify(ROOT)
 return row
