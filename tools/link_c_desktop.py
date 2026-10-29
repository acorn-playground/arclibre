#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Link the real shared library and its FilerAct client at explicit ROM bases."""
import hashlib,json,os,pathlib,re,struct,subprocess,sys
from paths import REPO,HOST
from aof import read
ROOT=REPO/'build/desktop-c-runtime';LD=REPO/'build/c-toolchain-release/install/bin/drlink'
def run(cmd,name):
 with (ROOT/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,check=True)
def link(base):
 li=json.loads((ROOT/'link-inputs.json').read_text());lib=[REPO/li['objects'][n] for n in reversed(li['order'])]
 run([LD,'-bin','-base',hex(base),'-map','-symbols',ROOT/'SharedCLib.symbols','-output',ROOT/'SharedCLib.bin',*lib],'link')
 symbols={n:int(v,16) for v,n in re.findall(r'\b([0-9a-f]{7,8})\s+(\S+)',(ROOT/'SharedCLib.symbols').read_text())}
 fil=[REPO/p for p in json.loads((ROOT/'filer-inputs.json').read_text())['objects'].values()]
 definitions={s['name'] for p in fil for s in read(p)['symbols'] if s['attributes']&1}
 imports={s['name'] for p in fil for s in read(p)['symbols'] if not s['attributes']&1}
 bound={n:symbols[n] for n in imports-definitions if n in symbols and not n.startswith('Image$$') and not n.endswith(('$$Base','$$Limit'))}
 source='\n'.join('        EXPORT |'+n+'|\n|'+n+'| EQU &'+format(v,'X') for n,v in sorted(bound.items()))+'\n        END\n'
 (ROOT/'library-exports.s').write_text(source)
 run([HOST/'bin/asasm','-Uppercase','-aof',ROOT/'library-exports.s',ROOT/'library-exports.o'],'exports')
 libdata=(ROOT/'SharedCLib.bin').read_bytes();fbase=base+len(libdata)+4
 run([LD,'-bin','-base',hex(fbase),'-map','-symbols',ROOT/'FilerAct.symbols','-output',ROOT/'FilerAct.bin',*reversed(fil),ROOT/'library-exports.o'],'filer-link')
 # Compare the actual library init-table ranges with the original client
 # veneer reservation, including its public structures and private reserves.
 records=[]
 for address,size,name in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+R/O data\s+(\S+) from ',(ROOT/'link.log').read_text(),re.M):
  if name=='Lib$$Init':
   assert int(size,16)==20
   records.append(struct.unpack_from('<5I',libdata,int(address,16)-base))
 assert [x[0] for x in records]==[1,2,0x80000003]
 assert [x[4]-x[3] for x in records]==[796,2888,2432]
 assert records[0][4]==records[1][3] and records[1][4]==records[2][3]
 stubs=next(a for a in read(ROOT/'filer-romstubs.o')['areas'] if a['name']=='Stub$$Data')
 assert stubs['size']==sum(x[4]-x[3] for x in records)==6116
 contract=dict(status='STATIC_PASS',library_chunks=[dict(id=x[0],data_start=x[3],data_end=x[4],bytes=x[4]-x[3]) for x in records],client_stub_bytes=stubs['size'],client_offset_from_sl=-536,library_offset_from_sl=-540,private_reserves=dict(CLib=490*4,RLib=607*4),measured_private_bytes=li['private_data'])
 (ROOT/'workspace-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 report=dict(status='LINKED_NOT_RUNTIME_VALIDATED',modules=[dict(component=n,base=b,length=(ROOT/(n+'.bin')).stat().st_size,sha256=hashlib.sha256((ROOT/(n+'.bin')).read_bytes()).hexdigest()) for n,b in [('SharedCLib',base),('FilerAct',fbase)]],bound_library_exports=bound)
 (ROOT/'linked.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(link(int(sys.argv[1],0)),indent=2))
