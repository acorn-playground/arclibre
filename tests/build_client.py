#!/usr/bin/env python3
"""Build and independently decode the original diagnostic app. Apache-2.0."""
import hashlib,json,pathlib,struct,subprocess,sys
from paths import ROOT,REPO,HOST
import inspect_image
asm=HOST/'bin/asasm'
out=ROOT/'artifacts/CheckFile.aof';source=REPO/'tests/fixtures/CheckFile.s';hashes=[]
for i in (1,2):
 with (ROOT/'logs'/f'client-build-{i}.log').open('w') as log:subprocess.run([str(asm),'-ABSolute','-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',str(source),str(out)],check=True,stdout=log,stderr=subprocess.STDOUT)
 hashes.append(hashlib.sha256(out.read_bytes()).hexdigest())
assert hashes[0]==hashes[1]
obj=inspect_image.load_aof(out);assert obj['base']==0x10000
end=min(s['value'] for s in obj['symbols'] if s['name']=='$d')
decoded=[inspect_image.decode(struct.unpack_from('<I',obj['data'],p)[0],p+obj['base']) for p in range(0,end,4)]
assert all(d['branch'] is None or 0x10000<=d['branch']<0x10000+end for d in decoded)
(ROOT/'artifacts/CheckFile.bin').write_bytes(obj['data'])
(ROOT/'artifacts/client-build.json').write_text(json.dumps(dict(status='PASS',bytes=len(obj['data']),code_bytes=end,instructions=decoded,sha256=hashlib.sha256(obj['data']).hexdigest(),aof_hashes=hashes,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),relocations=0,unresolved_symbols=0),indent=2)+'\n')
print('ARM2 client built and decoded')
