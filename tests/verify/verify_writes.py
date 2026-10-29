#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify physical write results, allocation/checksums and executed ARM2 write FIQ."""
import hashlib,json,pathlib,re,struct,sys
from paths import ROOT,REPO
from disc_image import Disc
import inspect_image
A=ROOT/'artifacts'
def get(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def pattern(n,seed):return bytes((i*53+(i>>8)*17+seed)&255 for i in range(n))
def u32(b,p=0):return struct.unpack_from('<I',b,p)[0]
rom=(A/'floppy.rom').read_bytes();layout=get(A/'rom-layout.json');romhash=sha(rom)
assert romhash==layout['rom_sha256']==get(REPO/'manifests/baseline-rom.json')['rom_sha256']
mod=(A/'modules/ADFS/module.bin').read_bytes();symbols=get(A/'modules/ADFS/symbols.json')
sym=lambda n:symbols[n]['value'];base=next(m['base'] for m in layout['modules'] if m['component']=='ADFS')
start=sym('WriteSecsFiq');end=start
while u32(mod,end):end+=4
handler=mod[start:end]
stages=['01-save','02-overwrite','03-appended','03-stream','04-fragment','05-namespace','06-deleted','07-full','08-final']
report=[];reference=None
# Optional single-run mode is useful during development. Default is the full gate.
run_count=int(sys.argv[1]) if len(sys.argv)>1 else 3
assert run_count in [1,3]
for i in range(1,run_count+1):
 root=A/f'writes-{i}';assert {p.parent.name for p in root.glob('*/result.json')}=={'DA','EA','DA-reopen','EA-reopen','DA-protected','EA-protected'}
 runs={}
 for fmt in ['DA','EA']:
  original=(A/'discs'/f'{fmt}.adf').read_bytes();baseline=Disc(original)
  spec=next(x for x in get(A/'discs/manifest.json')['images'] if x['name']==fmt);assert sha(original)==spec['sha256']
  expected={n:dict(row) for n,row in baseline.files.items()};dirs=set(baseline.directories)
  patch=pattern(37,0xa6);stream=pattern(16393,0x77)+b'\x5a';updated=bytearray(stream[:10013]);updated[1019:1056]=patch
  new=lambda data:dict(data=data,load=0x12345678,execute=0x23456780,attributes=3)
  stage_reports=[];before_full=None
  for stage in stages:
   if stage=='01-save':expected['Written']=new(pattern(32791,0x31))
   if stage=='02-overwrite':expected['Written']=new(pattern(7191,0x59))
   if stage=='03-appended':expected['Stream']={'data':stream,'attributes':3}
   if stage=='03-stream':expected['Stream']={'data':bytes(updated),'attributes':3}
   if stage=='04-fragment':
    data=bytearray(expected['Docs.Fragment']['data'])
    for off in [8190,20478]:data[off:off+len(patch)]=patch
    expected['Docs.Fragment']['data']=bytes(data);expected['Docs.Fragment']['attributes']=0x33
    # FileSwitch timestamps a modified typed file when closing it. Preserve
    # the file type, not the fixture's obsolete zero timestamp.
    del expected['Docs.Fragment']['load'];del expected['Docs.Fragment']['execute']
   if stage=='05-namespace':expected['Renamed']=expected.pop('Written');expected['NewDir.Child']=new(patch);dirs.add('NewDir')
   if stage=='06-deleted':del expected['Stream'];del expected['NewDir.Child'];dirs.remove('NewDir')
   if stage=='08-final':expected['Recovery']=new(patch)
   raw=(root/fmt/(stage+'.adf')).read_bytes();disc=Disc(raw)
   assert set(disc.files)==set(expected) and set(disc.directories)==dirs,(fmt,stage,'namespace')
   for name,row in expected.items():
    for key,value in row.items():
     if key!='address':assert disc.files[name][key]==value,(fmt,stage,name,key)
   if stage=='06-deleted':before_full=raw
   if stage=='07-full':assert raw==before_full,'failed allocation must leave entire disc unchanged'
   if stage in stages[4:]:
    assert disc.files['Docs.Fragment']['load']&0xffffff00==0xffffff00
    assert disc.files['Docs.Fragment']['execute']!=0
   if stage=='04-fragment' and fmt=='EA':
    obj=disc.files['Docs.Fragment']['address']>>8
    chunks=[(o,n) for ident,o,n in disc.fragments if ident==obj]
    assert len(chunks)==3,'still exercising noncontiguous fragments'
   stage_reports.append({'stage':stage,'sha256':sha(raw),'free_bytes':disc.free_bytes,'files':len(disc.files),'directories':len(disc.directories)})
  writer=get(root/fmt/'result.json');assert len(writer['checkpoints'])==len(stages)
  for checkpoint,stage in zip(writer['checkpoints'],stages):
   assert checkpoint['name']==stage
   raw=(root/fmt/(stage+'.adf')).read_bytes();sectors=checkpoint['overlay_sectors'];assert sectors and all(o%1024==0 and 0<=o<len(raw) for o in sectors)
   changed={p//1024*1024 for p,(b,c) in enumerate(zip(raw,original)) if b!=c}
   assert changed<=set(sectors) and sum(b!=c for b,c in zip(raw,original))==checkpoint['changed_bytes']
  errors={c['name']:c['error_number'] for c in writer['calls'] if c['error']}
  assert errors=={'Read-only file rejects update':0xc1,'Disc full allocation':0x108c6}
  calls={c['name']:c for c in writer['calls']}
  for name in ['GBPB sequential write','GBPB positioned write','Write fragment boundary 8190','Write fragment boundary 20478']:
   c=calls[name];assert c['output'][3]==0 and c['output'][2]==c['input'][2]+c['input'][3]
  assert calls['Read pointer']['output'][2]==16393 and calls['Read truncated extent']['output'][2]==10013
  assert len(writer['fiqs'])==1
  f=writer['fiqs'][0];capture=(root/fmt/'write-fiq.bin').read_bytes();assert capture[:len(handler)]==handler
  assert u32(capture,len(handler))==0xe51ff004 and u32(capture,len(handler)+4)==base+sym('NotDrq')
  assert f['psr']&0x0c000003==0x0c000001
  wrote_data=False
  for row in f['instructions']:
   pc=row['pc'];wanted=u32(capture,pc-0x1c) if 0x1c<=pc<0x1c+len(handler)+4 else u32(rom,pc-0x3800000)
   assert row['word']==wanted and row['psr']&3==1
   decoded=inspect_image.decode(wanted,pc);assert decoded['kind']!='SWI'
   # STRCSB Temp,[FDC,#FdcData] must actually execute with C set.
   if wanted&0xfff00000==0x25c00000:
    assert row['psr']&0x20000000
    reg=(wanted>>16)&15;assert row['r'][reg]+(wanted&4095)==sym('FdcAddress')+sym('FdcData')
    wrote_data=True
  assert wrote_data,'sample contains actual FDC data-register byte write'
  assert f['return_pc']==(f['r'][14]&0x03fffffc)-4 and f['return_psr']==f['r'][14]&0xfc000003
  # The decoder must reject damaged map and directory evidence.
  final=(root/fmt/'08-final.adf').read_bytes()
  for offset in [255 if fmt=='DA' else 0,(1024 if fmt=='DA' else 2048)+2047]:
   bad=bytearray(final);bad[offset]^=1
   try:Disc(bad)
   except AssertionError:pass
   else:raise AssertionError('corrupted disc accepted')
  for suffix in ['', '-reopen','-protected']:
   case=fmt+suffix;p=root/case;j=get(p/'result.json');assert j['status']=='PASS' and j['rom_sha256']==romhash
   assert all(j['exceptions'][n]==0 for n in [1,3,4,5])
   assert all(c['pc']==0x800c and c['end_tick']-c['start_tick']<60*24000000 and bool(c['psr']&0x10000000)==c['error'] for c in j['calls'])
   if suffix=='-protected':
    assert j['write_protected'] and j['base_sha256']==sha(original) and not j['fiqs']
    assert (p/'protected.adf').read_bytes()==original and not j['checkpoints'][0]['overlay_sectors']
    assert [(c['name'],c['error_number']) for c in j['calls'] if c['error']]==[('Save Denied',0x108c9)]
   elif suffix=='-reopen':
    assert j['write_protected'] and j['base_sha256']==sha(final) and not any(c['error'] for c in j['calls'])
    assert all(c['output'][0]==0 for c in j['calls'] if c['name'].startswith('Absent '))
   else:
    assert not j['write_protected'] and j['base_sha256']==sha(original)
    fdc=(p/'fdc.log').read_text();statuses=re.findall(r'done writeSector status=([0-9A-F]{2})',fdc)
    assert statuses and all(int(status,16)&0x7f==0 for status in statuses) and 'writeTrack' not in fdc
   runs[case]={'calls':len(j['calls']),'fiq_exceptions':j['exceptions'][7],'fdc_commands':j['fdc_commands'],'evidence_hashes':{f.name:sha(f.read_bytes()) for f in p.iterdir() if f.name in ['result.json','fdc.log'] or f.suffix in ['.adf','.bin']}}
  runs[fmt]['stages']=stage_reports;runs[fmt]['write_fiq_instructions']=len(f['instructions'])
 if reference is None:reference=runs
 else:assert runs==reference,('cold write repeat mismatch',i)
 report.append({'cold_run':i,'flows':runs})
result={'status':'PASS','rom_sha256':romhash,'cold_runs':run_count,'flows':6*run_count,'identical_cold_runs':run_count==3,'independent_disc_decoder':True,'per_format_checkpoints':len(stages),'write_fiq_arm2_verified':True,'disc_full_unchanged':True,'protected_media_unchanged':True,'fresh_machine_reopen':True,'runs':report}
(A/'writes-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS:',6*run_count,'write/reopen/protection flows; physical D/E data/maps/directories and ARM2 write FIQ')
