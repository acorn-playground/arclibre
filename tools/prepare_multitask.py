#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,struct,subprocess
from paths import REPO,HOST
from module_image import load_aof
out=REPO/'build/multitask';out.mkdir(exist_ok=True)
for name in ['Master','Child']:
 with (out/(name+'.log')).open('w') as log:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',str(REPO/'tests/fixtures/multitask'/ (name+'.s')),str(out/(name+'.aof'))],stdout=log,stderr=subprocess.STDOUT,check=True)
 obj=load_aof(out/(name+'.aof'));(out/(name+'.bin')).write_bytes(obj['data']);(out/(name+'-symbols.json')).write_text(json.dumps({r['name']:r['value'] for r in obj['symbols']},indent=2)+'\n')
b=(REPO/'build/wimp-stack/resources.bin').read_bytes()[:-4];child=(out/'Child.bin').read_bytes();symbols=json.loads((out/'Child-symbols.json').read_text())
for name,identity in [('ArcTaskA',11),('ArcTaskB',29)]:
 data=bytearray(child);struct.pack_into('<I',data,symbols['identity'],identity)
 n=('Apps.'+name).encode()+b'\0';n+=bytes(-len(n)%4);length=24+len(n)+((len(data)+3)&~3)
 # Untyped Absolute file: real load and execution address &8000.
 b+=struct.pack('<5I',length,0x8000,0x8000,len(data),3)+n+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)
(out/'resources.bin').write_bytes(b+bytes(4))
print('Prepared real parent and two Absolute task files')
