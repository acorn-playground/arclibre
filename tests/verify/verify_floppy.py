#!/usr/bin/env python3
"""Independent disc bytes, ARM2 FIQ paths and three-cold-boot gate. Apache-2.0."""
import hashlib,json,pathlib,re,struct,sys
from paths import ROOT,REPO
import inspect_image
import verify_boot
def get(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def u32(b,p=0):return struct.unpack_from('<I',b,p)[0]
S=get(ROOT/'artifacts/symbols.json');verify_boot.S=S
manifest=get(ROOT/'artifacts/disc/manifest.json');disc=(ROOT/'artifacts/disc/arm2-test.adf').read_bytes()
assert len(disc)==819200 and sha(disc)==manifest['sha256']
assert disc[0x401:0x405]==disc[0xbfb:0xbff]==b'Hugo'
layout=get(ROOT/'artifacts/rom-layout.json');adfs=next(m for m in layout['modules'] if m['component']=='ADFS')
symbols=get(ROOT/'artifacts/modules/ADFS/symbols.json');symbol=lambda n:symbols[n]['value']
assert all(symbol(n)==1 for n in ['A1','FDC1772','MEMC1A','Top16Write','FIQ32bit'])
assert symbol('BigDisc')==symbol('BigBit')==0 and symbol('FdcAddress')==0x3310000
module=(ROOT/'artifacts/modules/ADFS/module.bin').read_bytes()
rom=(ROOT/'artifacts/floppy.rom').read_bytes()
assert rom[adfs['base']-0x3800000:adfs['base']-0x3800000+len(module)]==module
# Driver flag is a mask, not a bit index; FileCore uses this to convert sector to byte addresses.
assert u32(module,symbol('FSCreateBlock')) & symbol('BigDiscSupport') == 0
reports=[];reference=None
for i in (1,2,3):
 folder=ROOT/f'artifacts/floppy-{i}';j=get(folder/'result.json');assert j['status']=='PASS'
 assert j['rom_sha256']==layout['rom_sha256'] and j['write_protected'] and j['overlay_entries']==0
 assert len(j['calls'])==35 and len(j['fiqs'])==8
 assert all(j['exceptions'][n]==0 for n in [1,3,4,5]) and j['exceptions'][7]>80000
 assert j['program_entry']['pc']==0x10000 and j['program_entry']['psr']==0 and j['program_exit_pc']==S['RdchLoop']
 assert 'ARM2 FLOPPY PROGRAM EXECUTED' in j['screen']
 for f in manifest['files']:
  data=(ROOT/'artifacts/disc'/f['name']).read_bytes();assert sha(data)==f['sha256']
  assert disc[f['offset']:f['offset']+len(data)]==data
  for operation in ('read','load'):assert (folder/f'{operation}-{f["name"]}.bin').read_bytes()==data
  info=next(c for c in j['calls'] if c['name']=='Info '+f['name']);assert info['output'][0]==1
  assert info['output'][2:6]==[f['load'],f['execute'],f['length'],f['attributes']]
 faults=[c for c in j['calls'] if c['psr']&0x10000000]
 assert len(faults)==1 and faults[0]['name']=='Missing file' and "not found" in faults[0]['error_text']
 assert all(c['pc']==0x800c for c in j['calls'])
 # The loaded program must come through the real catalogue and retain its exact bytes.
 mem=verify_boot.memc(folder/'program-entry-MEMC.bin');hello=(ROOT/'artifacts/disc/Hello').read_bytes()
 assert mem['read'](0x10000,len(hello))==hello
 assert all(inspect_image.decode(u32(hello,p),0x10000+p) for p in range(0,16,4))
 paths=[]
 for f in j['fiqs']:
  capture=(folder/f['capture']).read_bytes();assert f['psr']&0x0c000003==0x0c000001
  # Match copied code with the original module, ending at its zero sentinel.
  matches=[]
  for name in ['VerifyFiq','ReadSecsFiq','WriteSecsFiq','ReadTrackFiq','WriteTrackFiq','SeekFiq']:
   start=symbol(name);end=start
   while u32(module,end):end+=4
   code=module[start:end]
   if capture[:len(code)]==code and u32(capture,len(code))==0xe51ff004 and u32(capture,len(code)+4)==adfs['base']+symbol('NotDrq'):
    matches.append((name,len(code)))
  assert len(matches)==1,(f['call'],matches)
  name,length=matches[0];assert name in ['ReadTrackFiq','ReadSecsFiq']
  for p in range(0,length+4,4):inspect_image.decode(u32(capture,p),0x1c+p)
  # Verify every actually sampled instruction, including the ROM completion path.
  for row in f['instructions']:
   pc=row['pc'];expected=u32(capture,pc-0x1c) if 0x1c<=pc<0x1c+length+4 else u32(rom,pc-0x3800000)
   assert row['word']==expected and row['psr']&3==1
   decoded=inspect_image.decode(row['word'],pc)
   assert decoded['kind'] not in ['SWI']
  lr=f['r'][14]
  assert f['return_pc']==(lr&0x03fffffc)-4
  assert f['return_psr']==lr&0xfc000003
  paths.append(dict(call=f['call'],handler=name,instructions=len(f['instructions']),return_pc=hex(f['return_pc']),return_psr=hex(f['return_psr'])))
 fdc=(folder/'fdc.log').read_text();commands=re.findall(r'cmd ([0-9A-F]+) (\w+) drive=(\d+) side=(\d+) trk=(\d+) sec=(\d+)',fdc)
 assert commands and all(c[1] in ['restore','seek','step','stepIn','stepOut','readSector','readAddress','readTrack'] for c in commands)
 assert {c[3] for c in commands}=={'0','1'} and max(int(c[4]) for c in commands)>=4
 assert all(c[2]=='0' for c in commands) and not any(s in fdc for s in ['writeSector','writeTrack','RNF'])
 swis=(folder/'swis.log').read_text().splitlines();application=[line.split()[1:] for line in swis if line.split()[1] in ['10004','1000c']]
 assert application==[['10004','2'],['1000c','11']]
 comparable=dict(result=j,fdc=fdc,captures={p.name:sha(p.read_bytes()) for p in folder.glob('fiq-*.bin')},memory={p.name:sha(p.read_bytes()) for p in folder.glob('program-*-MEMC.bin')})
 if reference is None:reference=comparable
 else:assert comparable==reference,('cold repeat mismatch',i)
 reports.append(dict(run=i,calls=len(j['calls']),fiq_exceptions=j['exceptions'][7],sampled_instructions=sum(p['instructions'] for p in paths),paths=paths,fdc_commands=j['fdc_commands'],disc_reads_byte_exact=True,program_usr26_and_exit=True))
(ROOT/'artifacts/floppy-verification.json').write_text(json.dumps(dict(status='PASS',rom_sha256=layout['rom_sha256'],disc_sha256=manifest['sha256'],identical_cold_runs=True,original_byte_address_driver=True,runs=reports),indent=2)+'\n')
print('PASS: three identical read-only disc runs, exact data/program loading and ARM2 FIQ entry/return paths')
