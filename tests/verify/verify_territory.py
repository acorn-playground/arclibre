#!/usr/bin/env python3
"""Independent saved-state registration/table/dispatch and repeat gate. Apache-2.0."""
import hashlib,json,pathlib,re,struct,sys
from paths import ROOT,REPO
import verify_boot
def get(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
layout=get(ROOT/'artifacts/rom-layout.json');modules={m['component']:m for m in layout['modules']}
rom=(ROOT/'artifacts/floppy.rom').read_bytes();assert sha(ROOT/'artifacts/floppy.rom')==layout['rom_sha256']
ks=get(ROOT/'artifacts/symbols.json');ts=get(ROOT/'artifacts/modules/TerritoryManager/symbols.json');us=get(ROOT/'artifacts/modules/UK/symbols.json')
def tv(n):return ts[n]['value']
assert struct.unpack_from('<I',rom,modules['TerritoryManager']['base']-0x3800000+28)[0]==0x43040
assert (tv('entry_points'),tv('t_entries'),tv('t_block_size'))==(25,12,112)
assert (tv('FirstReservedSWI'),tv('LastReservedSWI'),tv('maxnewswi'))==(34,52,10)
source=(ROOT/'sources/UK/s/ModHead').read_text(encoding='latin1');chunk=source.split('ADRL    r0,ReadTimeZones')[1].split('SWI     XTerritory_Register')[0]
entries=['ReadTimeZones']+re.findall(r'ADR[L]?\s+r0,(\w+)',chunk)
assert len(entries)==24 and entries[-2:]==['NameToNumber','TransformString']
code={v['offset'] for v in get(ROOT/'artifacts/modules/UK/instructions.json')}
for n in entries:assert us[n]['value'] in code
expected=get(ROOT/'artifacts/territory-tables.json')['tables'];resources=get(ROOT/'artifacts/resources.json')
reports=[];reference=None
for i in [1,2,3]:
 p=ROOT/f'artifacts/territory-{i}';result=get(p/'result.json');assert result['status']=='PASS' and result['rom_sha256']==layout['rom_sha256']
 # Inspect the unmodified natural-boot state, before any client programs run.
 m=verify_boot.memc(ROOT/f'artifacts/natural-{i}/supervisor-entry-MEMC.bin')
 def read(a,n):return rom[a-0x3800000:a-0x3800000+n] if a>=0x3800000 else m['read'](a,n)
 def word(a):return int.from_bytes(read(a,4),'little')
 node=word(ks['Module_List']);workspace={};seen=set()
 while node:
  assert node not in seen;seen.add(node)
  base=word(node+ks['Module_code_pointer']);title=read(base+word(base+ks['Module_Title']),64).split(b'\0')[0].decode()
  incarnation=word(node+ks['Module_incarnation_list']);workspace[title]=word(incarnation+ks['Incarnation_Workspace']);node=word(node+ks['Module_chain_Link'])
 tm=workspace['TerritoryManager'];uk=workspace['UK'];assert 0x1800000<=tm<0x1c00000 and 0x1800000<=uk<0x1c00000
 assert word(tm+tv('configured_territory'))==1
 registration=word(tm+tv('territories'));assert word(registration+tv('next_ptr'))==0 and word(registration+tv('t_number'))==1 and word(registration+tv('t_wsptr'))==uk
 pointers=[word(registration+tv('t_entries')+4*j) for j in range(24)]
 assert pointers==[modules['UK']['base']+us[n]['value'] for n in entries]
 for t,r in zip(expected,result['table_reads']):
  assert r['name']==t['name'] and r['pointer']==modules['UK']['base']+us[t['name']]['value']
  assert (p/(t['name']+'.bin')).read_bytes()==bytes(t['bytes'])==read(r['pointer'],len(t['bytes']))
 assert len(result['table_reads'])==17
 assert len(result['resource_reads'])==len(resources)*4
 for resource in resources:
  rows=[r for r in result['resource_reads'] if r['name']==resource['name']];assert len(rows)==4 and len({r['pointer'] for r in rows})==1
  assert read(rows[0]['pointer'],resource['length'])==(ROOT/resource['source']).read_bytes()
 errors=[c for c in result['calls'] if c['psr']&0x10000000]
 assert [c['name'] for c in errors]==['Unknown property','Reserved entry 24','Reserved last','Missing territory']
 assert all(c['error_text'] for c in errors)
 assert all(result['exceptions'][j]==0 for j in [1,3,4,5,7])
 comparable=dict(result=result,state={q.name:sha(q) for q in p.glob('final-*.bin')},swis=sha(p/'swis.log'),trace=sha(p/'instructions.log'))
 if reference is None:reference=comparable
 else:assert comparable==reference,'territory cold repeat mismatch'
 reports.append(dict(run=i,client_calls=len(result['calls']),tables=17,property_bits=11*256,conversion_bytes=5*256+16,resource_variants=4*len(resources),manager_workspace=tm,uk_workspace=uk,registration=registration,entry_pointers=dict(zip(entries,pointers)),expected_errors=[dict(name=c['name'],text=c['error_text']) for c in errors]))
report=dict(status='PASS',runs=reports,identical_cold_repeats=True,all_24_entry_pointers_match_real_rom_code=True,reserved_25th_slot_unreachable=True,source_tables_independently_parsed=True)
(ROOT/'artifacts/territory-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: all territory entry addresses, workspace contracts, full public tables, case folding and repeated real SWI clients')
