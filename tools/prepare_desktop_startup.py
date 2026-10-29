#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,pathlib,struct
from paths import REPO,SRC
out=REPO/'build/desktop-startup';b=(REPO/'build/wimp-stack/resources.bin').read_bytes()[:-4];records=[]
for c in ['Desktop','Filer','Switcher','Pinboard','SprExtend','ADFSFiler','ShellCLI','Obey','Buffers']:
 for name in ['Messages','Templates,fec']:
  p=SRC/c/'Resources/UK'/name
  if not p.exists():continue
  data=p.read_bytes();n=('Resources.'+c+'.'+name.split(',')[0]).encode()+b'\0';n+=bytes(-len(n)%4);ft=0xfec if ',' in name else 0xfff
  length=24+len(n)+((len(data)+3)&~3);b+=struct.pack('<5I',length,0xfff00000|(ft<<8),0,len(data),3)+n+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)
  records.append(dict(component=c,path=str(p.relative_to(REPO)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),filetype=ft,license_basis='Pinned component Apache-2.0; no separate native-asset notice'))
(out/'resources.bin').write_bytes(b+bytes(4));(out/'resources.json').write_text(json.dumps(records,indent=2)+'\n')
