#!/usr/bin/env python3
"""Independent checks of recorded real key events, kernel returns and protocol state. Apache-2.0."""
import collections,hashlib,json,pathlib,re,struct,sys
from paths import ROOT,REPO
S=json.loads((ROOT/'artifacts/symbols.json').read_text())
rom=(ROOT/'artifacts/floppy.rom').read_bytes()
def get(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(ROOT/'artifacts'/n).write_text(json.dumps(v,indent=2)+'\n')
# Exact byte expectations derive from the public key tables, including both repaired literals.
assert S['AssembleA1KeyHandler']==1
for table,index in [('KeyTran',0x51),('KeyTran2',0x33)]:
    a=S[table]-0x3800000+index*4
    assert rom[a:a+4]==bytes([0x5c,0x7c,0x1c,0x1c]),(table,rom[a:a+4])
expected={'ready':[],'abc':[97,98,99],'backspace':[8],'shift-release':[68,69,102],
          'ctrl-u':[21],'ctrl-release':[117],'caps-on':[65],'caps-off':[98],'escape':[27],
          'repeat-release':[120]*12,'repeat-recovery':[21,97],'help-typed':[21,104,101,108,112],'help-return':[13]}
lines={'ready':'*','abc':'*abc','backspace':'*ab','shift-release':'*abDEf','ctrl-u':'*',
       'ctrl-release':'*u','caps-on':'*uA','caps-off':'*uAb','escape':'*','repeat-release':'*'+'x'*12,
       'repeat-recovery':'*a','help-typed':'*help','help-return':'*'}
from intkey_contract import inspect
reports=[];reference=None
for i in [1,2,3]:
    p=ROOT/f'artifacts/keyboard-{i}';contract=inspect(ROOT/f'artifacts/natural-{i}/supervisor-entry-MEMC.bin');assert inspect(p/'final-MEMC.bin')==contract;stages=get(p/'stages.json');inputs=get(p/'input-events.json');log=(p/'events.log').read_text()
    assert get(p/'protocol-errors.json')==[]
    last=[]
    for stage in stages:
        n=stage['stage'];assert stage['chars'][len(last):]==expected[n],(i,n,stage['chars'][len(last):]);last=stage['chars']
        # Only a single flashing underscore cursor is removed from the observed last line.
        line=stage['screen'][-1];assert line in [lines[n],lines[n]+'_'],(n,line)
        w=stage['workspace'];assert w[S['CurrKey']]==w[S['OldKey']]==255
        assert w[S['KbId']]==w[S['LastKbId']]==1
        assert int.from_bytes(bytes(w[S['KeyVec']:S['KeyVec']+4]),'little')==contract['workspace']
        assert w[S['KeysDown']:S['KeysDown']+20]==[0]*20
        assert stage['leds']==(3 if n=='caps-on' else 2)
        assert all(stage['exceptions'][j]==0 for j in [1,3,4,5,7])
        # Public keyboard serializer: idle, scans enabled, no queued/held keys or mouse delta.
        k=(p/(n+'-KBD.bin')).read_bytes()
        assert len(k)==28 and k[:3]==bytes([5,1,1]) and k[3:27]==bytes(24) and k[27]==stage['leds']
    assert 'Escape' in stages[-1]['screen']
    assert '==> Help on keyword Help' in stages[-1]['screen']
    assert 'Syntax          Explain the syntax message format' in stages[-1]['screen']
    assert not any('NoSuchSWI' in line or 'TokNFnd' in line for line in stages[-1]['screen'])
    keyevents=[(int(t),int(reason,16),int(code,16)) for t,reason,code in re.findall(r'(?m)^(\d+) KEY reason=&([\dA-F]+) key=&([\dA-F]+)$',log)]
    assert [(reason,code) for _,reason,code in keyevents if reason==3]==[(3,3),(3,2)] # real LED requests
    keyevents=[e for e in keyevents if e[1] in [1,2]]
    assert len(keyevents)==len(inputs)==56
    held=set()
    for inp,(tick,reason,code) in zip(inputs,keyevents):
        assert code==inp['code'] and reason==(2 if inp['action']=='down' else 1)
        assert inp['tick']<=tick<inp['tick']+240000 # serial/IRQ delivery within 10 ms
        if inp['action']=='down':assert code not in held;held.add(code)
        else:assert code in held;held.remove(code)
    assert not held
    returned=[(int(t),int(code,16)) for t,code in re.findall(r'(?m)^(\d+) CHAR r0=&([\dA-F]+)$',log)]
    assert [c for _,c in returned]==last
    down=next(x['tick'] for x in inputs if x['code']==0x4f and x['action']=='down')
    up=next(x['tick'] for x in inputs if x['code']==0x4f and x['action']=='up')
    repeat=[t for t,c in returned if c==120]
    assert len(repeat)==12 and all(down<t<up for t in repeat)
    end=next(s['tick'] for s in stages if s['stage']=='repeat-release')
    assert end-up>=int(.95*24000000) and not any(up<t<=end for t,_ in returned)
    missing=collections.Counter(int(n,16) for n in re.findall(r'MISSING swi=&([\dA-F]+)',log))
    assert missing=={0x42fc0:1,0x401c0:1},missing
    assert len(re.findall(r'(?m)^\d+ HELP$',log))==1
    kart=len(re.findall(r' KART ',log));assert kart>=4*len(inputs)
    comparable=dict(stages=stages,inputs=inputs,log=log,kbd=[sha(p/(s['stage']+'-KBD.bin')) for s in stages],final_ram=sha(p/'final-MEMC.bin'))
    if reference is None:reference=comparable
    else:assert comparable==reference,'cold repeat differs'
    reports.append(dict(run=i,key_events=len(inputs),readc_returns=len(returned),repeat_characters=len(repeat),kart_accesses=kart,exceptions=stages[-1]['exceptions']))
save('keyboard-verification.json',dict(status='PASS',scope='Original A1 input through real IntKey with full Help output; original input regressions retained.',runs=reports,identical_cold_repeats=True,no_stuck_keys=True,help_complete=True,missing_swis={'0x42fc0':'Portable_Speed (optional idle probe, tolerated)','0x401c0':'Sound_QInit (Escape path)'},break_tested=False))
print('PASS: three identical keyboard suites; real Help dispatch, complete MessageTrans output')
