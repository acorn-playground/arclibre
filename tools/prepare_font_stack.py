#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare an isolated runtime fixture from verified provider/font artifacts."""
import hashlib,json,shutil,struct
from paths import REPO,SRC
root=REPO/'build/font-stack';root.mkdir(exist_ok=True);(root/'acceptance.json').unlink(missing_ok=True)
modules=root/'modules'
if modules.exists():shutil.rmtree(modules)
modules.mkdir();records=[]
for c in ['Colours','DrawMod','Super','Hourglass','FontManager','ROMFonts']:
 source=REPO/('build/desktop-components' if c in ['FontManager','ROMFonts'] else 'build/render-components')
 result=json.loads((source/'result.json').read_text());record=next(r for r in result['modules'] if r['component']==c)
 data=(source/'modules'/c/'module.bin').read_bytes();assert hashlib.sha256(data).hexdigest()==record['sha256']
 shutil.copytree(source/'modules'/c,modules/c);records.append(record)
b=(SRC/'FontManager/Resources/UK/Messages').read_bytes();n=b'Resources.Fonts.Messages\0';n+=bytes(-len(n)%4)
length=24+len(n)+((len(b)+3)&~3)
resources=(REPO/'build/render-components/resources.bin').read_bytes();assert resources[-4:]==bytes(4)
resources=resources[:-4]+struct.pack('<5I',length,0xffffff00,0,len(b),3)+n+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)+bytes(4)
(root/'resources.bin').write_bytes(resources);(root/'inputs.json').write_text(json.dumps(dict(modules=records,resources_sha256=hashlib.sha256(resources).hexdigest()),indent=2)+'\n')
print('Prepared real provider/font runtime fixture')
