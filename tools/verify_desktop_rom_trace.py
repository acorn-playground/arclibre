#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify ROM execution against independently decoded original module bytes."""
import hashlib,json,pathlib,struct
from paths import REPO
import inspect_image

def verify(probe, required=None, root=None):
 probe=pathlib.Path(probe);root=pathlib.Path(root) if root is not None else REPO/'build/arclibre';layout=json.loads((root/'rom-layout.json').read_text());r=json.loads((probe/'result.json').read_text());rom=(root/'arclibre.rom').read_bytes();assert hashlib.sha256(rom).hexdigest()==r['rom_sha256']==layout['rom_sha256'];modules=[];allowed={}
 for row in layout['modules']:
  c=row['component']
  path=REPO/('build/fpemulator' if c=='FPEmulator' else 'build/desktop-components/modules/'+c if c in ['Wimp','FontManager','ROMFonts'] else 'build/render-components/modules/'+c if c in ['Colours','DrawMod','Super','Hourglass'] else 'build/desktop-c-runtime/modules/'+c if c in ['SharedCLib','FilerAct'] else 'build/desktop-actions/modules/'+c if c in ['DragASprit','FilerSWIs','SpriteUtil'] else 'build/sound/modules/'+c if c in ['Sound0','Sound1','Sound2','WaveSynth','Percussion'] else 'build/desktop-startup/modules/'+c if c in ['Desktop','Filer','Switcher','Pinboard','SprExtend','ADFSFiler','ShellCLI','Obey','Buffers'] else 'build/desktop-baseline/artifacts/modules/'+c)
  if c in ['SharedCLib','FilerAct']:path=root/'c-runtime/modules'/c
  if c in ['Edit','ResFiler','BASIC','BASICTrans']:path=root/'app-runtime/modules'/c
  if c in ['Draw','Paint']:path=root/'graphics-runtime/modules'/c
  if c in ['Filter','TaskWindow']:path=root/'task-runtime/modules'/c
  if c in ['DeviceFS','SystemDevs','PipeFS']:path=root/'stream-runtime/modules'/c
  if c in ['RamFS','RAMFSFiler','Free']:path=root/'ram-filing-runtime/modules'/c
  if c in ['ScrBlank','StringLib']:path=root/'utility-runtime/modules'/c
  if c in ['IIC','RTCAdjust']:path=root/'clock-runtime/modules'/c
  if c=='Debugger':path=root/'debugger-runtime/modules/Debugger'
  if c=='ARM3Support':path=root/'arm3-runtime/modules/ARM3Support'
  if c in ['Econet','BBCEconet','NetFS','NetFiler','NetPrint','NetStatus']:path=root/'network-runtime/modules'/c
  if c in ['Podule','Serial','SerialSpt','Parallel']:path=root/'hardware-runtime/modules'/c
  if c=='ArcCalc':path=root/'calc-runtime/modules/ArcCalc'
  if c=='ArcConfigure':path=root/'configure-runtime/modules/ArcConfigure'
  if c=='Squash':path=root/'squash-runtime/modules/Squash'
  if c in ['Chars','Help','Alarm']:path=root/'basic-utility-runtime/modules'/c
  if c in ['PDriver','PDModules','PDumperSpt','PDumpers']:path=root/'printing-runtime/modules'/c
  if c=='DOSFS':path=root/'dosfs-rom'
  if c=='ArcPalette':path=root/'palette-runtime/modules/ArcPalette'
  if c=='ADFS' and (root/'hardware/modules/ADFS').exists():path=root/'hardware/modules/ADFS'
  if c=='FileCore' and (root/'delivered/modules/FileCore').exists():path=root/'delivered/modules/FileCore'
  code=json.loads((path/('integer-instructions.json' if c=='FPEmulator' else 'instructions.json')).read_text());fp=json.loads((path/('fpa-instructions.json' if c=='FPEmulator' else 'fpa-dependency.json')).read_text()) if c in ['Wimp','FPEmulator','SharedCLib','FilerAct','Edit','Draw','Paint'] else []
  ins={v['offset']:v['source']['word'] for v in code+fp};b=rom[row['base']-0x3800000:row['base']-0x3800000+row['length']];assert hashlib.sha256(b).hexdigest()==row['sha256']
  for offset,w in ins.items():assert struct.unpack_from('<I',b,offset)[0]==w,(c,offset)
  for v in fp:allowed[row['base']+v['offset']]=v['source']['word']
  # ARM3Support's processor test: on an ARM2 its read of CP15 register 0
  # traps, by design, through the briefly installed undefined vector.
  if c=='ARM3Support':
   for v in code:
    if v['decoded']['kind']=='MRC' and v['decoded']['crn']==0:allowed[row['base']+v['offset']]=v['source']['word']
  modules.append(dict(name=c,base=row['base'],end=row['base']+row['length'],ins=ins,seen=set()))
 client_code={};client_veneers={};menu_end=0
 if r.get('application')=='!MenuTest':
  client=REPO/'build/menu-app';manifest=json.loads((client/'manifest.json').read_text());data=(client/'client.bin').read_bytes()
  assert hashlib.sha256(pathlib.Path(r['disc']).read_bytes()).hexdigest()==manifest['sha256']
  assert hashlib.sha256(data).hexdigest()==manifest['program_sha256']
  menu_end=0x10000+len(data)
  client_code={0x10000+v['offset']:v['word'] for v in json.loads((client/'instructions.json').read_text())}
  for pc,w in client_code.items():assert struct.unpack_from('<I',data,pc-0x10000)[0]==w
 if r.get('application') in ['!CAbiTest','!TaskTest','!StrTest','!RamTest','!UtilTest','!SqTest']:
  client=REPO/('build/task-service-app' if r['application']=='!TaskTest' else 'build/stream-app' if r['application']=='!StrTest' else 'build/ram-app' if r['application']=='!RamTest' else 'build/utility-app' if r['application']=='!UtilTest' else 'build/squash-app' if r['application']=='!SqTest' else 'build/c-abi-app');manifest=json.loads((client/'manifest.json').read_text());assert hashlib.sha256(pathlib.Path(r['disc']).read_bytes()).hexdigest()==manifest['sha256']
  data=(client/'client.aif').read_bytes();assert hashlib.sha256(data).hexdigest()==manifest['program_sha256']
  ci=json.loads((client/'instructions.json').read_text());cf=json.loads((client/'fpa-dependency.json').read_text())
  client_code={0x8000+v['offset']:v['source']['word'] for v in ci+cf}
  for pc,w in client_code.items():assert struct.unpack_from('<I',data,pc-0x8000)[0]==w
  for v in cf:allowed[0x8000+v['offset']]=v['source']['word']
  if r['application']=='!TaskTest':
   child=(client/'child.bin').read_bytes()
   child_fp=json.loads((client/'child-fpa-dependency.json').read_text())
   for v in json.loads((client/'child-instructions.json').read_text())+child_fp:
    pc=0x10000+v['offset'];assert pc not in client_code
    assert struct.unpack_from('<I',child,v['offset'])[0]==v['source']['word']
    client_code[pc]=v['source']['word']
   for v in child_fp:allowed[0x10000+v['offset']]=v['source']['word']
  expected=json.loads((client/'runtime-veneers.json').read_text());actual=json.loads((probe/'client-veneers.json').read_text());assert sorted(v['pc'] for v in actual)==expected
  targets={m['base']+off for m in modules if m['name']=='SharedCLib' for off in m['ins']}
  for v in actual:
   d=inspect_image.decode(v['word'],v['pc']);assert d['kind']=='B' and d['condition']==14 and d['branch'] in targets,v
   client_veneers[v['pc']]=v['word']
 if r.get('application')=='!StrTest':
  child=(client/'child.bin').read_bytes()
  for row in json.loads((client/'child-instructions.json').read_text()):
   pc=0x10000+row['offset'];assert pc not in client_code
   assert struct.unpack_from('<I',child,row['offset'])[0]==row['word']
   client_code[pc]=row['word']
  driver=json.loads((probe/'stream-driver.json').read_text());data=(client/'device.bin').read_bytes()
  assert list(struct.unpack('<'+'I'*(len(data)//4),data))==driver['words']
  for row in json.loads((client/'device-instructions.json').read_text()):
   pc=driver['base']+row['offset'];assert pc not in client_code
   assert struct.unpack_from('<I',data,row['offset'])[0]==row['word']
   client_code[pc]=row['word']
 if r.get('application')=='!UtilTest':
  copied=json.loads((probe/'string-ram-code.json').read_text());original=next(m for m in modules if m['name']=='StringLib')['ins']
  for row in copied['instructions']:
   assert row['pc']==copied['base']+row['offset']-copied['source_offset']
   assert original[row['offset']]==row['word']
   assert row['pc'] not in client_code
   client_code[row['pc']]=row['word'];inspect_image.decode(row['word'],row['pc'])
  entries=json.loads((probe/'string-entries.json').read_text());assert len(entries)>=4 and all(pc in client_code for pc in entries)
 for p in probe.glob('*-trace.log'):
  for line in p.read_text().splitlines():
   f=line.split();pc,w=int(f[1],16),int(f[2],16)
   if menu_end and 0x10000<=pc<menu_end:assert client_code.get(pc)==w,(p,hex(pc),'menu client data execution or mismatch')
   if pc in client_veneers:assert w==client_veneers[pc],(p,hex(pc),'bad library entry veneer')
   elif pc in client_code:assert w==client_code[pc],(p,hex(pc),'client instruction mismatch')
   for m in modules:
    if m['base']<=pc<m['end']:
     offset=pc-m['base'];assert offset in m['ins'] and m['ins'][offset]==w,(p,m['name'],hex(offset),'executed data or byte mismatch');m['seen'].add(offset);break
 assert r['sprite_vector_calls']>0
 for ins in r['generated_sprite_code']:inspect_image.decode(ins['word'],ins['pc'])
 assert len(r['undefined'])==r['exceptions'][1]>0
 for trap in r['undefined']:assert allowed.get(trap['pc'])==trap['word'],trap
 report=dict(status='PASS',scope='All undefined exceptions; sampled ROM instruction paths, not exhaustive branch coverage',generated_sprite_instructions=len(r['generated_sprite_code']),classified_software_fpa_traps=len(r['undefined']),unclassified_undefined_exceptions=0,modules={m['name']:len(m['seen']) for m in modules})
 assert all(report['modules'][c]>0 for c in (required or ['Desktop','Filer','Switcher','Pinboard','Wimp','ADFSFiler','ShellCLI','Buffers']))
 (probe/'trace-verification.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 import sys
 print(json.dumps(verify(sys.argv[1]),indent=2))
