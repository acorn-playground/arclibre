#!/usr/bin/env python3
"""Verify saved SWI results, ROM resources and repeatability independently. Apache-2.0."""
import hashlib,json,pathlib,struct,sys
from paths import ROOT,REPO

import verify_boot
def get(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
layout=get(ROOT/'artifacts/rom-layout.json');rom=(ROOT/'artifacts/floppy.rom').read_bytes();assert hashlib.sha256(rom).hexdigest()==layout['rom_sha256']
modules={m['component']:m for m in layout['modules']}
for name,base in [('ResourceFS',0x41b40),('MsgTrans',0x41500)]:
    data=(ROOT/'artifacts/modules'/name/'module.bin').read_bytes();assert struct.unpack_from('<I',data,28)[0]==base
kernel=get(ROOT/'artifacts/symbols.json')
interfaces={}
for name in modules:
    symbols=get(ROOT/'artifacts/modules'/name/'symbols.json')
    for n in ['SVCSTK','SysHeapStart','ScratchSpace','DomainId','IRQsema','SvcTable','BranchToSWIExit','RedirectInHandle','RedirectOutHandle']:
        if n in symbols:assert symbols[n]['value']==kernel[n],(name,n)
    if name in ['FileSwitch','ResourceFS']:
        assert symbols['FS_get']['value']==12 and symbols['FS_gbpb']['value']==40 and symbols['FS_size']['value']==48
    if name=='FileSwitch':assert symbols['fscb_get']['value']==12 and symbols['fscb_gbpb']['value']==40
    interfaces[name]='Public workspace matches the unchanged kernel; original FS offsets restored.'
resources=get(ROOT/'artifacts/resources.json')
msgsymbols=get(ROOT/'artifacts/modules/Messages/symbols.json')
offset=modules['Messages']['base']-0x3800000+msgsymbols['Messages']['value'];resource_pointers={}
for r in resources:
    nxt,load,execute,size,attr=struct.unpack_from('<5I',rom,offset)
    end=rom.index(0,offset+20);name=rom[offset+20:end].decode();start=(end+4)&~3
    assert name==r['name'] and size==r['length'] and nxt==r['record_bytes']
    assert load==0xffffff00 and execute==0 and attr==3
    assert struct.unpack_from('<I',rom,start)[0]==size+4
    b=rom[start+4:start+4+size];assert b==(ROOT/r['source']).read_bytes()
    resource_pointers[name]=0x3800000+start+4;offset+=nxt
assert rom[offset:offset+4]==bytes(4)
reference=None;reports=[]
for i in [1,2,3]:
    p=ROOT/f'artifacts/messages-{i}';result=get(p/'result.json');assert result['status']=='PASS' and result['rom_sha256']==layout['rom_sha256']
    calls=result['calls'];assert len(calls)==3*len(resources)+16
    errors=[c for c in calls if c['psr']&0x10000000]
    memory=verify_boot.memc(p/'final-MEMC.bin')
    assert int.from_bytes(memory['read'](errors[0]['output'][0],4),'little')==0x12345678
    assert [(c['name'],c['error_text']) for c in errors]==[('ErrorLookup','SWI &DEADBEEF not known'),('Missing token','Message token NeverDefinedToken not found')]
    for r in result['resource_reads']:
        source=next(x for x in resources if x['name']==r['name'])
        assert r['pointer']==resource_pointers[r['name']] and r['length']==source['length'] and r['size']==r['length']+4 and r['flags']&1
        assert (p/(r['name']+'.bin')).read_bytes()==(ROOT/source['source']).read_bytes()
    assert len(result['resource_reads'])==len(resources)
    assert all(result['exceptions'][j]==0 for j in [1,3,4,5,7])
    comparable=dict(result=result,swis=sha(p/'swis.log'),state={q.name:sha(q) for q in p.glob('final-*.bin')},help=(p/'expanded-help.txt').read_text())
    if reference is None:reference=comparable
    else:assert comparable==reference,'repeated client execution differs'
    reports.append(dict(run=i,client_calls=len(calls),message_trans_calls=len(calls)-2,byte_exact_resources=len(resources),expected_error_returns=2))
(ROOT/'artifacts/message-verification.json').write_text(json.dumps(dict(status='PASS',runs=reports,repeat_identical=True,public_workspace=interfaces,resources=resource_pointers,rom_sha256=layout['rom_sha256']),indent=2)+'\n')
print('PASS: repeated MessageTrans client results, exact ROM resource pointers/bytes, dictionary and real errors')
