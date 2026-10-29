#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Link the original graphics clients against the actual ROM SharedCLibrary."""
import hashlib,json,re,shutil,struct,subprocess
from paths import REPO,HOST
from aof import read
ROOT=REPO/'build/graphics-apps';CLIB=REPO/'build/desktop-c-runtime'
def link(base):
 symbols={n:int(v,16) for v,n in re.findall(r'\b([0-9a-f]{7,8})\s+(\S+)',(CLIB/'SharedCLib.symbols').read_text())}
 previous=json.loads((CLIB/'linked.json').read_text());rows=[];bindings={}
 for comp in ['Draw','Paint']:
  work=ROOT/comp
  objects=[REPO/p for p in json.loads((work/'inputs.json').read_text())['objects'].values()]
  defined={s['name'] for p in objects for s in read(p)['symbols'] if s['attributes']&1}
  imports={s['name'] for p in objects for s in read(p)['symbols'] if not s['attributes']&1}
  bound={n:symbols[n] for n in imports-defined if n in symbols and not n.startswith('Image$$') and not n.endswith(('$$Base','$$Limit'))}
  source='\n'.join('        EXPORT |'+n+'|\n|'+n+'| EQU &'+format(v,'X') for n,v in sorted(bound.items()))+'\n        END\n'
  (work/'exports.s').write_text(source);bindings[comp]=bound
  with (work/'exports.log').open('w') as f:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-aof',str(work/'exports.s'),str(work/'exports.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
  with (ROOT/(comp+'-link.log')).open('w') as f:subprocess.run([str(REPO/'build/c-toolchain-release/install/bin/drlink'),'-bin','-base',hex(base),'-map','-symbols',str(ROOT/(comp+'.symbols')),'-output',str(ROOT/(comp+'.bin')),*[str(p) for p in reversed(objects)],str(work/'exports.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
  b=(ROOT/(comp+'.bin')).read_bytes()
  if comp=='Draw':
   name=b'Resources.Draw.Sprites\0';at=b.index(name);entry=at-20;length_word=(at+len(name)+3)&~3
   asset=(REPO/'src/Draw/Resources/Sprites,ff9').read_bytes()
   length,load,execution,size,attributes=struct.unpack_from('<5I',b,entry)
   assert (load,execution,size,attributes)==(0xfffff900,0,len(asset),3)
   assert struct.unpack_from('<I',b,length_word)[0]==len(asset)+4
   assert b[length_word+4:length_word+4+len(asset)]==asset
   assert entry+length==(length_word+4+len(asset)+3)&~3
  rows.append(dict(component=comp,base=base,length=len(b),sha256=hashlib.sha256(b).hexdigest(),link_log=comp+'-link.log'));base+=len(b)+4
 for name in ['SharedCLib.bin','FilerAct.bin','link.log','filer-link.log']:shutil.copy2(CLIB/name,ROOT/name)
 (ROOT/'linked.json').write_text(json.dumps(dict(modules=previous['modules']+rows,bound_library_exports=bindings),indent=2)+'\n')
 from verify_c_desktop import verify
 verify(ROOT)
 return rows
if __name__=='__main__':print(json.dumps(link(0x3800000+1688368),indent=2))
