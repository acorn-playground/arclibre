#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently inspect final linked C modules, not just compiler assembly."""
import hashlib,json,pathlib,re,struct
from paths import REPO
from aof import read
import inspect_image
ROOT=REPO/'build/desktop-c-runtime'
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def verify(root=ROOT):
 linked=json.loads((root/'linked.json').read_text());allcode={};results=[]
 for module,log in [(m,m.get('link_log',{'SharedCLib':'link.log','FilerAct':'filer-link.log'}.get(m['component']))) for m in linked['modules']]:
  name=module['component'];base=module['base'];b=(root/(name+'.bin')).read_bytes();assert hashlib.sha256(b).hexdigest()==module['sha256']
  code={};covered=set();relocations=0
  for address,size,kind,area,path in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+(R/[OW] (?:data|code))\s+(\S+) from (.+)$',(root/log).read_text(),re.M):
   address,size=int(address,16),int(size,16);p=pathlib.Path(path);obj=read(p);a=next(a for a in obj['areas'] if a['name']==area);assert size==a['size']
   offset=address-base;assert 0<=offset<=len(b) and offset+size<=len(b)
   assert not covered.intersection(range(offset,offset+size));covered.update(range(offset,offset+size));changes=set()
   for r in a['relocations']:
    flags=r['flags'];assert flags>>31==1;ft=(flags>>24)&3;length=1<<ft if ft<3 else 4
    if ft==3:
     w=struct.unpack_from('<I',a['data'],r['offset'])[0];count=(flags>>29)&3
     if (w>>25)&7!=5:assert count>0,('unbounded instruction relocation',p,r)
     length=4*max(count,1)
    changes.update(range(r['offset'],r['offset']+length));relocations+=1
   actual=b[offset:offset+size]
   assert all(x==y or i in changes for i,(x,y) in enumerate(zip(actual,a['data']))),(name,p,area,'non-relocation bytes changed')
   markers=sorted((s['value'],s['name']) for s in obj['symbols'] if s['area']==area and s['name'] in ['$a','$d','$t'])
   if size:assert markers and markers[0][0]==0,(p,area,'unmapped bytes')
   for i,(start,tag) in enumerate(markers):
    end=markers[i+1][0] if i+1<len(markers) else size;assert tag!='$t'
    if tag=='$a':
     assert a['attributes']&0x200 and start%4==end%4==0
     for off in range(start,end,4):
      pc=address+off;w=struct.unpack_from('<I',actual,off)[0]
      code[pc]=dict(offset=pc-base,source=dict(word=w,object=str(p.relative_to(REPO)),area=area,area_offset=off))
  assert covered==set(range(len(b))),(name,'unmapped linked bytes')
  allcode.update(code);results.append((module,code,relocations))
 reports=[]
 for module,code,relocations in results:
  integer=[];fp=[]
  for pc,row in code.items():
   w=row['source']['word']
   try:d=inspect_image.decode(w,pc)
   except AssertionError as e:
    assert 'coprocessor instruction' in str(e) and (w>>8)&15 in [1,2] and (w>>25)&7 in [6,7] and w>>28!=15,(module['component'],hex(pc),hex(w),str(e))
    fp.append(dict(row,classification='original library software FPA dependency',decoder_rejection=str(e)));continue
   if d['branch'] is not None:assert d['branch'] in allcode,(hex(pc),'branch to unmapped code',d)
   if d['psr'] or d.get('user_bank') and d['kind']=='LDM':assert allcode.get(pc+4,{}).get('source',{}).get('word')==0xe1a00000,(hex(pc),'ARM2 settling',d)
   integer.append(dict(row,decoded=d))
  out=root/'modules'/module['component'];out.mkdir(parents=True,exist_ok=True)
  save(out/'instructions.json',integer);save(out/'fpa-dependency.json',fp)
  reports.append(dict(**module,status='STATIC_PASS_WITH_SOFTWARE_FPA',integer_arm2_instructions=len(integer),software_fpa_instructions=len(fp),resolved_relocations=relocations,unresolved_symbols=0,all_linked_bytes_mapped=True,all_nonrelocation_bytes_match=True,branches_and_psr_settling_checked=True))
 save(root/'verification.json',dict(status='PASS',modules=reports));return reports
if __name__=='__main__':print(json.dumps(verify(),indent=2))
