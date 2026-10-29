#!/usr/bin/env python3
"""Independent real-keyboard selection/ownership/regression gate. Apache-2.0."""
import collections,hashlib,json,pathlib,re,struct
from intkey_contract import inspect
from paths import ROOT,REPO
def get(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
k=get(ROOT/'artifacts/symbols.json');layout=get(ROOT/'artifacts/rom-layout.json');rom=(ROOT/'artifacts/floppy.rom').read_bytes()
module=next(m for m in layout['modules'] if m['component']=='IntKey');symbols=get(ROOT/'artifacts/modules/IntKey/symbols.json')
# The supplied A1 table is entirely literal bytes; independently parse its complete
# normal translation and top-bit tables, without using assembler symbol values for lengths.
source=(ROOT/'sources/IntKey/UK/Source/UkA1Kbd').read_bytes().decode('latin1');checks={}
for start,end in [('KeyTran1 ROUT','KeyTran1End'),('TopBitSetTable1','ProcessK1TopBitSet')]:
 chunk=source.split(start,1)[1].split(end,1)[0]
 data=bytearray()
 for line in chunk.split('\n'):
  line=line.split(';')[0].strip()
  if line.startswith('&'):
   assert line.split()==['&','-1'];data+=bytes([255]*4)
  elif line.startswith('='):
   for token in re.findall(r'"[^"]*"|&[0-9A-Fa-f]+|\d+',line[1:]):
    data.extend(token[1:-1].encode('latin1') if token.startswith('"') else [int(token[1:],16) if token.startswith('&') else int(token)])
 data=bytes(data)
 label=start.split()[0];offset=symbols[label]['value'];actual=rom[module['base']-0x3800000+offset:module['base']-0x3800000+offset+len(data)]
 assert data==actual and len(data)==(404 if label=='KeyTran1' else 464),(label,len(data))
 checks[label]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
expected={'ready':[],'query':list(b'keyboard\r'),'invalid':list(b'keyboard nonsense\r'),'query-after-error':list(b'keyboard\r'),'backslash-bar':[92,124],'keypad':[21,54,53],'alt-digits':[21,65],'recovery':[21,97],'help-keyboard':list(b'\x15help keyboard\r')}
for j in [1,2,3]:expected['select-'+str(j)]=list(b'keyboard uk\r');expected['input-'+str(j)]=[97,68,21]
reports=[];reference=None
for i in [1,2,3]:
 p=ROOT/f'artifacts/selection-{i}';stages=get(p/'stages.json');result=get(p/'result.json');assert result['status']=='CAPTURED' and result['rom_sha256']==layout['rom_sha256']
 contract=inspect(ROOT/f'artifacts/natural-{i}/supervisor-entry-MEMC.bin');assert inspect(p/'final-MEMC.bin')==contract
 assert get(p/'protocol-errors.json')==[]
 inputs=get(p/'input-events.json');log=(p/'events.log').read_text();last=[]
 for t in stages:
  name=t['stage'];assert t['chars'][len(last):]==expected[name],(name,t['chars'][len(last):]);last=t['chars']
  w=t['workspace'];assert w[k['KbId']]==w[k['LastKbId']]==1
  assert int.from_bytes(bytes(w[k['KeyVec']:k['KeyVec']+4]),'little')==contract['workspace']
  assert w[k['KeysDown']:k['KeysDown']+20]==[0]*20 and w[k['CurrKey']]==w[k['OldKey']]==255
  b=(p/(name+'-KBD.bin')).read_bytes();assert b[:3]==bytes([5,1,1]) and b[3:27]==bytes(24)
  assert all(t['exceptions'][j]==0 for j in [1,3,4,5,7])
  if name.startswith(('select-','input-')):assert t['screen'][-1] in ['*','*_']
  if name=='invalid':assert any('Unknown keyboard (Error number &642)' in line for line in t['screen'])
  if name=='backslash-bar':assert t['screen'][-1] in ['*\\|','*\\|_']
  if name=='keypad':assert t['screen'][-1] in ['*65','*65_']
  if name=='alt-digits':assert t['screen'][-1] in ['*A','*A_']
  if name=='recovery':assert t['screen'][-1] in ['*a','*a_']
 assert any('Syntax: *Keyboard [<country name>]' in line for line in stages[-1]['screen'])
 keyevents=[(int(t),int(reason,16),int(code,16)) for t,reason,code in re.findall(r'(?m)^(\d+) KEY reason=&([\dA-F]+) key=&([\dA-F]+)$',log) if int(reason,16) in [1,2]]
 assert len(keyevents)==len(inputs)==result['key_events']
 held=set()
 for inp,(tick,reason,code) in zip(inputs,keyevents):
  assert inp['code']==code and reason==(2 if inp['action']=='down' else 1) and inp['tick']<=tick<inp['tick']+240000
  if inp['action']=='down':assert code not in held;held.add(code)
  else:assert code in held;held.remove(code)
 assert not held
 calls=collections.Counter(re.findall(r'INTKEY (\w+)',log));assert calls['SetUpKeyStructureAndHandlerIfUs']==3 and calls['KeyStructInit']==0 # same owner: no unnecessary handler reinitialisation
 assert all(calls[n]>0 for n in ['ProcessKShift','ProcessKCtrl','ProcessKAlt','ProcessK1Pad'])
 missing=collections.Counter(int(n,16) for n in re.findall(r'MISSING swi=&([\dA-F]+)',log));assert missing=={0x42fc0:1},missing
 comparable=dict(stages=stages,inputs=inputs,log=log,state={q.name:sha(q) for q in p.glob('final-*.bin')})
 if reference is None:reference=comparable
 else:assert comparable==reference,'selection cold repeat differs'
 # Confirm the separately exercised unsupported newer service reasons stay unclaimed.
 territory=get(ROOT/f'artifacts/territory-{i}/result.json');extra=[c for c in territory['calls'] if c['name'].startswith('Unimplemented International')]
 assert len(extra)==3
 for c in extra:assert c['output'][1:6]==c['input'][1:6] and not c['psr']&0x10000000
 select=next(c for c in territory['calls'] if c['name']=='SelectKeyboardHandler');assert not select['psr']&0x10000000
 reports.append(dict(run=i,key_events=len(inputs),characters=len(last),runtime_handler_calls=dict(calls),contract=contract,territory_selection_succeeds=True,newer_services_unclaimed=[7,8,255]))
(ROOT/'artifacts/selection-verification.json').write_text(json.dumps(dict(status='PASS',runs=reports,identical_cold_repeats=True,original_a1_tables=checks,no_injected_keyboard_success=True),indent=2)+'\n')
print('PASS: real UK selection, live A1 handler/ROM table contract, keypad/Alt, invalid selection recovery and retained keys')
