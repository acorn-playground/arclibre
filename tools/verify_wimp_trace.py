#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Match sampled executed module bytes to independently classified source code."""
import json,pathlib,struct
from paths import REPO

def verify(probe):
 probe=pathlib.Path(probe);r=json.loads((probe/'result.json').read_text());modules=[]
 for row in r['loaded']:
  c=row['component']
  root=REPO/('build/fpemulator' if c=='FPEmulator' else ('build/desktop-components/modules/'+c if c in ['Wimp','FontManager','ROMFonts'] else 'build/render-components/modules/'+c))
  code=json.loads((root/('integer-instructions.json' if c=='FPEmulator' else 'instructions.json')).read_text())
  fp=json.loads((root/('fpa-instructions.json' if c=='FPEmulator' else 'fpa-dependency.json')).read_text()) if c in ['Wimp','FPEmulator'] else []
  b=(root/'module.bin').read_bytes();assert len(b)==row['bytes']
  modules.append(dict(name=c,base=row['base'],binary=b,code={v['offset']:v['source']['word'] for v in code+fp},seen=set(),fpa={v['offset'] for v in fp}))
 traps=0
 for p in sorted(probe.glob('*-trace.log')):
  for line in p.read_text().splitlines():
   fields=line.split();pc=int(fields[1],16);word=int(fields[2],16)
   if pc==4:traps+=1
   for m in modules:
    offset=pc-m['base']
    if 0<=offset<len(m['binary']):
     assert offset in m['code'],(p,m['name'],hex(offset),'executed module data')
     assert word==m['code'][offset]==struct.unpack_from('<I',m['binary'],offset)[0],(p,m['name'],hex(offset),'executed byte mismatch')
     m['seen'].add(offset)
 assert traps>0
 result={m['name']:dict(distinct_instructions=len(m['seen']),classified_fpa_sites=len(m['seen']&m['fpa'])) for m in modules}
 assert result['Wimp']['distinct_instructions']>500 and result['FPEmulator']['distinct_instructions']>100
 report=dict(status='PASS',scope='Sampled instruction traces, not complete path coverage',undefined_vector_observations=traps,modules=result)
 (probe/'trace-verification.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 import sys
 print(json.dumps(verify(sys.argv[1]),indent=2))
