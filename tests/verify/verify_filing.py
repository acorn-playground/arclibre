#!/usr/bin/env python3
"""Check saved execution evidence against immutable media and CPU/memory captures."""
import hashlib,json,pathlib,re,struct,sys
from paths import ROOT as R,REPO
A=R/'artifacts';D=A/'discs'
def get(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
romhash='bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791'
assert sha((A/'floppy.rom').read_bytes())==romhash
assert sha((A/'floppy.rom').read_bytes())==get(REPO/'manifests/baseline-rom.json')['rom_sha256']
assert sha((A/'kernel.bin').read_bytes())=='cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30'
manifest=get(D/'manifest.json')
for name,meta in manifest['files'].items():
 data=(D/name).read_bytes();assert len(data)==meta['bytes'] and sha(data)==meta['sha256'],name
# Independently walk the E map's unary-terminated fragments, resolving object 6
# from encoded bits, not the generator's offsets or allocation list.
for name in ['EA','EB']:
 b=(D/(name+'.adf')).read_bytes();zone=b[:1024];assert zone==b[1024:2048]
 assert zone[4:10]==bytes([10,5,2,2,15,7]) and struct.unpack_from('<I',zone,16)[0]==0x203
 def bits(p,n):return sum(((zone[(p+k)//8]>>((p+k)%8))&1)<<k for k in range(n))
 p=512;extents=[]
 while p<8192:
  start=p;identifier=bits(p,15);p+=15
  while p<8192 and not bits(p,1):p+=1
  assert p<8192;p+=1
  if identifier==6:extents.append(((start-512)*128,(p-start)*128))
 assert len(extents)==3 and all(extents[i][0]+extents[i][1]<extents[i+1][0] for i in range(2))
 actual=b''.join(b[o:o+n] for o,n in extents)[:38895]
 assert actual==(D/(name+'-Docs_Fragment')).read_bytes()
# Fault fixtures must differ only at declared format checksums or sector IDs/flags.
for name in ['DA','EA']:
 b=(D/(name+'.adf')).read_bytes();bad=(D/(name+'-bad-directory.adf')).read_bytes()
 root=1024 if name=='DA' else 2048
 assert [i for i,(x,y) in enumerate(zip(b,bad)) if x!=y]==[root+2047]
 row=next(x for x in manifest['images'] if x['name']==name)
 damaged=next(x for x in row['files'] if x['path']=='Docs.Fragment')['chunks'][0]['offset']//1024
 for fault,flag in [('missing',None),('id-crc',0x10),('data-crc',0x20)]:
  j=(D/(name+'-'+fault+'.jfd')).read_bytes();assert j[:4]==b'JFDI'
  tables,sectors,data=struct.unpack_from('<III',j,24);assert j[data:]==b
  seen=[];damaged_seen=[]
  for track in range(160):
   p=sectors+struct.unpack_from('<I',j,tables+4*track)[0]
   while struct.unpack_from('<I',j,p)[0]!=0xffffffff:
    descriptor,offset=struct.unpack_from('<II',j,p);p+=8
    sector=(descriptor>>8)&255;assert offset==(track*5+sector)*1024
    seen.append(offset//1024)
    if descriptor&0x30:damaged_seen.append((offset//1024,descriptor&0x30))
  assert len(seen)==(799 if flag is None else 800)
  assert damaged_seen==([] if flag is None else [(damaged,flag)])
  assert (damaged not in seen)==(flag is None)
for file,wanted in [('EA-bad-maps.adf',[0,1024]),('EA-first-map-bad.adf',[0])]:
 b=(D/'EA.adf').read_bytes();bad=(D/file).read_bytes();assert [i for i,(x,y) in enumerate(zip(b,bad)) if x!=y]==wanted
import verify_boot
import inspect_image
client=get(A/'client-build.json');assert client['status']=='PASS' and client['relocations']==client['unresolved_symbols']==0
binary=(A/'CheckFile.bin').read_bytes();assert sha(binary)==client['sha256']
for offset in range(0,client['code_bytes'],4):inspect_image.decode(struct.unpack_from('<I',binary,offset)[0],0x10000+offset)
faults={'DA-bad-directory':0x108a8,'EA-bad-directory':0x108a8,'EA-bad-maps':0xd6,'EA-first-map-bad':0}
for prefix in ['DA','EA']:
 for suffix,n in [('missing',0x100108c7),('id-crc',0x180108c7),('data-crc',0x80108c7)]:faults[prefix+'-'+suffix]=n
expected_cases=set(['DA','EA','media-change','empty-drive']+list(faults))
reports=[];reference=None
for i in [1,2,3]:
 folder=A/f'filing-{i}';assert {p.parent.name for p in folder.glob('*/result.json')}==expected_cases
 runs={}
 for case in sorted(expected_cases):
  p=folder/case;j=get(p/'result.json');assert j['status']=='PASS' and j['rom_sha256']==romhash
  assert all(j['exceptions'][n]==0 for n in [1,3,4,5])
  assert all(m['protected'] and m['overlay']==0 for m in j['media'])
  for c in j['calls']:
   assert c['pc']==0x800c and c['end_tick']-c['start_tick']<60*24000000
   assert bool(c['psr']&0x10000000)==c['error']
  if case in ['DA','EA']:
   spec=next(x for x in manifest['images'] if x['name']==case)
   for f in spec['files']:
    expected=(D/(case+'-'+f['path'].replace('.','_'))).read_bytes()
    assert (p/('read-'+f['path']+'.bin')).read_bytes()==(p/('load-'+f['path']+'.bin')).read_bytes()==expected
   errors=[(c['name'],c['error_number']) for c in j['calls'] if c['error']]
   assert len(errors)==8 and all(n==(0xde if label.startswith('Closed handle') else 0xd6) for label,n in errors)
   events={e['event']:e for e in j['events'] if e['event'].startswith('application-')}
   assert events['application-entry']['pc']==0x10000 and events['application-entry']['psr']==0
   assert events['application-result']['message']=='ARM2 FILING CLIENT PASS\r\n' and events['application-result']['checksum']==4958583
   assert events['application-return']['pc']==get(A/'symbols.json')['RdchLoop']
   expected=(D/'EA-Docs_Fragment').read_bytes();assert (p/'application-data.bin').read_bytes()==expected
   assert verify_boot.memc(p/'final-MEMC.bin')['read'](0x20000,len(expected))==expected
   swi=(p/'swis.log').read_text();assert re.search(r' 100b4 2\n',swi) and re.search(r' 100bc 11\n',swi)
   trace=(p/'application-checksum-instructions.log').read_text();assert 'R6=4BA977' in trace and '00010094 E1560007' in trace
  elif case in faults:
   c=next(c for c in j['calls'] if c['name']=='Read fault fixture');assert c['error_number']==faults[case]
   assert (p/'recovered.bin').read_bytes()==(D/'EA-Docs_Fragment').read_bytes()
  elif case=='media-change':
   assert (p/'disc-B-read.bin').read_bytes()==(D/'DB-RootText').read_bytes()!=(D/'DA-RootText').read_bytes()
   assert not any('Dismount' in c['name'] for c in j['calls'])
  elif case=='empty-drive':assert any(c['name']=='Empty drive' and c['error'] for c in j['calls'])
  runs[case]=dict(calls=len(j['calls']),fdc_commands=j['fdc_commands'],fiqs=j['exceptions'][7],errors=[{'number':c['error_number'],'message':c['message']} for c in j['calls'] if c['error']])
  # Timing, register results and hardware accesses must repeat from each cold state.
  comparable={f.name:sha(f.read_bytes()) for f in p.iterdir() if f.name in ['result.json','fdc.log','swis.log'] or f.suffix=='.bin'}
  runs[case]['evidence_hashes']=comparable
 if reference is None:reference=runs
 else:assert runs==reference,('repeat mismatch',i)
 reports.append(dict(cold_run=i,scenarios=runs))
baseline=get(A/'baseline/media-change-baseline/result.json');assert baseline['status']=='KNOWN_BASELINE_DEFECT'
assert (A/'baseline/media-change-baseline/disc-B-read.bin').read_bytes()==(D/'DA-RootText').read_bytes()
assert any(c['name']=='Explicit dismount recovery' and not c['error'] for c in baseline['calls'])
assert get(A/'core-replay.json')['status']=='PASS'
report=dict(status='PASS',rom_sha256=romhash,identical_cold_runs=True,scenario_count=42,client_arm2_instructions=client['code_bytes']//4,baseline_stale_media_reproduced=True,patched_media_change_without_dismount=True,runs=reports)
(A/'filing-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: 42 filing scenarios, independent byte/fragment checks, baseline defect and patched recovery')
