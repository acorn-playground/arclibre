#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate bounded corrupt/valid areas; query the unchanged public C checker."""
import json,struct,subprocess,shutil
from paths import REPO
out=REPO/'build/sprite-checks';out.mkdir(exist_ok=True)
shutil.copy2(REPO/'src/SprExtend/c/SpriteOp',out/'SpriteOp.c')
subprocess.run(['clang','-O0','-Wno-pointer-to-int-cast','-I'+str(out),str(REPO/'tests/fixtures/spriteextend/check_area_reference.c'),'-o',str(out/'reference')],check=True)
def area(new=False):
 b=bytearray(256);n=52 if new else 48;struct.pack_into('<4I',b,0,len(b),1,16,16+n)
 struct.pack_into('<I',b,16,n);b[20:24]=b'test';struct.pack_into('<7I',b,32,0,0,0,31,44,48 if new else 44,(3<<27)|(90<<14)|(90<<1)|1 if new else 1);return b
cases=[]
for new in [False,True]:
 b=area(new);cases.append((f'valid-{new}',b))
 for off,values in [(8,[300]),(12,[300]),(16,[500,49]),(40,[32]),(44,[32]),(48,[300,43]),(52,[300,45]),(32,[30]),(36,[30])]:
  for value in values:
   c=bytearray(b);struct.pack_into('<I',c,off,value);cases.append((f'mutate-{new}-{off}-{value}',c))
 if new:
  c=bytearray(b);struct.pack_into('<I',c,40,1);cases.append(('new-first-bit',c))
  c=bytearray(b);struct.pack_into('<I',c,56,0x18000000);cases.append(('invalid-new-mode',c))
empty=bytearray(256);struct.pack_into('<4I',empty,0,256,0,16,16);cases.append(('empty',empty))
rows=[]
for i,(name,b) in enumerate(cases):
 p=out/f'{i}.bin';p.write_bytes(b);v=int(subprocess.check_output([str(out/'reference'),str(p)]));rows.append(dict(name=name,words=list(struct.unpack('<64I',b)),expected=v))
assert len({r['expected'] for r in rows})==2
(out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),'C-reference cases')
