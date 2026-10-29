#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare isolated Wimp fixture using independently verified real modules."""
import hashlib,json,shutil,struct
from paths import REPO
out=REPO/'build/wimp-stack';out.mkdir(exist_ok=True);(out/'acceptance.json').unlink(missing_ok=True)
modules=out/'modules'
if modules.exists():shutil.rmtree(modules)
shutil.copytree(REPO/'build/font-stack/modules',modules)
for name,source in [('FPEmulator',REPO/'build/fpemulator'),('Wimp',REPO/'build/desktop-components/modules/Wimp')]:
 b=(source/'module.bin').read_bytes()
 report=json.loads((REPO/('build/fpemulator/result.json' if name=='FPEmulator' else 'build/desktop-components/result.json')).read_text())
 expected=report['sha256'] if name=='FPEmulator' else next(x['sha256'] for x in report['modules'] if x['component']=='Wimp')
 assert hashlib.sha256(b).hexdigest()==expected
 target=modules/name;target.mkdir();shutil.copy2(source/'module.bin',target/'module.bin')
 if name=='Wimp':shutil.copy2(source/'symbols.json',target/'symbols.json')
records={}
for source in ['build/font-stack/resources.bin','build/fpemulator/resources.bin','build/desktop-components/external-resources.bin']:
 b=(REPO/source).read_bytes();p=0
 while (length:=struct.unpack_from('<I',b,p)[0]):
  end=b.index(0,p+20);name=b[p+20:end].decode();record=b[p:p+length]
  if name.endswith('.Messages'):assert (struct.unpack_from('<I',record,4)[0]>>8)&0xfff==0xfff,name
  if name not in records:records[name]=record
  else:
   old=records[name];oldsize=struct.unpack_from('<I',old,12)[0];size=struct.unpack_from('<I',record,12)[0]
   op=((old.index(0,20)+4)&~3)+4;np=((record.index(0,20)+4)&~3)+4
   assert old[op:op+oldsize]==record[np:np+size],name
  p+=length
 assert p==len(b)-4
resources=b''.join(records.values())+bytes(4);(out/'resources.bin').write_bytes(resources)
(out/'inputs.json').write_text(json.dumps(dict(modules={p.parent.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in modules.glob('*/module.bin')},resources=list(records),resources_sha256=hashlib.sha256(resources).hexdigest()),indent=2)+'\n')
print('Prepared Wimp with real FPA, rendering and font providers')
# Original diagnostic guest helper, separately assembled from all upstream code.
import subprocess
from paths import HOST
from module_image import load_aof
with (out/'client.log').open('w') as f:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',str(REPO/'tests/fixtures/WimpClient.s'),str(out/'client.aof')],stdout=f,stderr=subprocess.STDOUT,check=True)
client=load_aof(out/'client.aof');(out/'client.bin').write_bytes(client['data']);(out/'client-symbols.json').write_text(json.dumps({s['name']:s['value'] for s in client['symbols']},indent=2)+'\n')
report=json.loads((out/'inputs.json').read_text());report['diagnostic_client_sha256']=hashlib.sha256(client['data']).hexdigest();(out/'inputs.json').write_text(json.dumps(report,indent=2)+'\n')
