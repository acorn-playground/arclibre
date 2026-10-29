#!/usr/bin/env python3
"""Independent ARM2 decoding and public workspace/interface checks. Apache-2.0."""
import json,pathlib,struct,sys
from paths import ROOT,REPO
import inspect_image as audit
from module_image import load_aof
reports=[];errors=[]
for p in sorted((ROOT/'artifacts/modules').iterdir()):
    obj=load_aof(p/'module.aof');data=obj['data'];assert data==(p/'module.bin').read_bytes()
    emissions={};ins={};symbols={}
    for l in (p/'symbols.tsv').read_text().splitlines():
        v=l.split('\t');symbols[v[0]]=dict(tag=int(v[1]),value=int(v[2]))
    for l in (p/'emissions.tsv').read_text().splitlines():
        kind,off,size,value,times,file,line,caller,cl=l.split('\t');off,size,value,times=map(int,[off,size,value,times])
        for i in range(times):
            for j in range(size):assert data[off+i*size+j]==(value>>(8*j))&255
        if kind=='I':ins[off]=dict(word=value,file=file,line=int(line),caller=caller,caller_line=int(cl))
    mapping=sorted((s['value'],s['name']) for s in obj['symbols'] if s['name'] in ['$a','$d','$t']);code=set()
    for i,(start,kind) in enumerate(mapping):
        end=mapping[i+1][0] if i+1<len(mapping) else len(data);assert kind!='$t'
        if kind=='$a':code.update(range(start,end,4))
    if p.name=='Messages':
        start=symbols['Messages']['value'];resource=(ROOT/'build/resources.bin').read_bytes()
        assert start%4==0 and data[start:start+len(resource)]==resource
        assert start+len(resource)==len(data)-4 and data[-4:]==bytes(4)
        # AsAsm BIN leaves its preceding $a mapping active. The original BIN range
        # is explicitly data, independently byte-compared with the resource pack.
        code-=set(range(start,start+len(resource),4))
    assert code==set(ins),(p.name,'unobserved code',len(code-set(ins)))
    decoded={}
    for off,src in ins.items():
        try:decoded[off]=dict(audit.decode(src['word'],off),offset=off,source=src)
        except AssertionError as e:errors.append(dict(component=p.name,offset=off,error=str(e),source=src))
    # Every emitted ADR/ADRL must retain its base register: ORG-0 MOV folding
    # was legal ARM2 encoding but invalid for a module moved into ROM.
    for off,row in decoded.items():
        src=ins[off]
        if row['kind'] in ['MOV','MVN'] and 'immediate' in row and src['line']:
            line=pathlib.Path(src['file']).read_bytes().decode('latin1').split('\n')[src['line']-1]
            assert 'ADR' not in line,(p.name,off,'absolute ADR materialisation',line)
    if p.name=='TerritoryManager':
        start=symbols['spritedata']['value'];asset=(ROOT/'work/TerritoryManager/SystemDiscSquashed').read_bytes()
        assert data[start:start+len(asset)]==asset
        assert not any(start<=off<start+len(asset) for off in ins)
    psr=[]
    for off,row in decoded.items():
        if row['branch'] is not None and row['branch'] not in decoded:errors.append(dict(component=p.name,error='branch into data',instruction=row))
        if row['psr'] or row.get('user_bank') and row['kind']=='LDM':
            psr.append(row)
            if off+4 not in decoded or decoded[off+4]['word']!='e1a00000':errors.append(dict(component=p.name,error='missing conservative ARM2 settling NOP',instruction=row))
    (p/'instructions.json').write_text(json.dumps(list(decoded.values()),indent=2)+'\n')
    (p/'symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')
    reports.append(dict(component=p.name,bytes=len(data),instructions=len(decoded),direct_branches=sum(x['branch'] is not None for x in decoded.values()),psr_sequences=len(psr),relocations=0,unresolved_symbols=0))
(ROOT/'artifacts/module-audit.json').write_text(json.dumps(dict(status='FAIL' if errors else 'PASS',modules=reports,errors=errors),indent=2)+'\n')
print(json.dumps(dict(modules=reports,errors=errors[:15]),indent=2))
assert not errors
