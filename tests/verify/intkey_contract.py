"""Read actual module workspaces and installed A1 handler. Apache-2.0."""
import json,pathlib,struct,sys
from paths import ROOT,REPO
import verify_boot
def get(p):return json.loads(p.read_text())
def inspect(path):
    rom=(ROOT/'artifacts/floppy.rom').read_bytes();m=verify_boot.memc(path)
    k=get(ROOT/'artifacts/symbols.json');s=get(ROOT/'artifacts/modules/IntKey/symbols.json');layout=get(ROOT/'artifacts/rom-layout.json')['modules']
    def read(a,n):return rom[a-0x3800000:a-0x3800000+n] if a>=0x3800000 else m['read'](a,n)
    def word(a):return int.from_bytes(read(a,4),'little')
    node=word(k['Module_List']);work={};seen=set()
    while node:
        assert node not in seen;seen.add(node)
        base=word(node+k['Module_code_pointer']);name=read(base+word(base+k['Module_Title']),64).split(b'\0')[0].decode()
        incarnation=word(node+k['Module_incarnation_list']);work[name]=word(incarnation+k['Incarnation_Workspace']);node=word(node+k['Module_chain_Link'])
    wp=work['InternationalKeyboard'];iwp=work['International'];assert 0x1800000<=wp<0x1c00000 and 0x1800000<=iwp<0x1c00000
    assert word(k['KeyWorkSpace']+k['KeyVec'])==wp
    assert s['A1Key_WorkspaceSize']['value']==64 and s['KVSize']['value']==44
    base=next(x['base'] for x in layout if x['component']=='IntKey');structure=base+s['KeyStruct1']['value'];entries=[]
    for offset in range(0,44,4):
        value=word(wp+offset);original=word(structure+offset)
        if offset==4:assert value==original==101
        else:assert (wp+value)&0xffffffff==(structure+original)&0xffffffff
        entries.append(value)
    assert word(wp+44)==k['NewKeyStruct'] # original kernel handler retained for genuine Die restore
    assert word(wp+48)==1 and word(wp+52)==101
    assert read(base+s['KeyTran1']['value']+0x33*4,4)==bytes([255]*4) # special-key path
    assert read(base+s['TopBitSetTable1']['value']+14*16,8)==bytes([92,0,124,0,28,0,28,0])
    # Source service table covers exactly its seven historical entries.
    inter=get(ROOT/'artifacts/modules/Inter/symbols.json');assert inter['Inter_SupportedCount']['value']==7 and inter['Inter_WorkspaceSize']['value']==20
    return dict(workspace=wp,international_workspace=iwp,old_handler=word(wp+44),keyboard=word(wp+48),alphabet=word(wp+52),osbyte_variables=word(wp+56),header_words=entries)
