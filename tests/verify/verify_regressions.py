#!/usr/bin/env python3
"""Independent CAM, transition, repeatability and rendered-font checks. Apache-2.0."""
import collections,hashlib,json,pathlib,re,struct,sys
from paths import ROOT,REPO
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,v):(ROOT/'artifacts'/n).write_text(json.dumps(v,indent=2)+'\n')
S=json.loads((ROOT/'artifacts/symbols.json').read_text());rom=(ROOT/'artifacts/floppy.rom').read_bytes()
import verify_boot
verify_boot.ROOT=ROOT;verify_boot.S=S;verify_boot.kernel=(ROOT/'artifacts/kernel.bin').read_bytes();verify_boot.verify()
memc=verify_boot.memc
def checked(path):
    m=memc(path);soft=[]
    for ppn,a in enumerate(m['cam']):
        logical=(a&0x7f8000)|((a&0xc00)<<13);ppl=(a>>8)&3
        value=int.from_bytes(m['read'](S['CamEntries']+ppn*4,4),'little')
        assert value==logical|(ppl<<28),(path,ppn)
        assert logical%32768==0;soft.append(value)
    assert len({v&0xfffffff for v in soft})==128,'unexpected alias'
    m['soft']=soft
    return m
def word(m,a):return int.from_bytes(m['read'](a,4),'little')
reports=[]
for kind in ['natural','fixtures']:
    reference=None
    for i in [1,2,3]:
        folder=ROOT/f'artifacts/{kind}-{i}';r=json.loads((folder/'result.json').read_text());assert r['status']=='PASS' and r['cam_failures']==0
        assert all(r['exceptions'][j]==0 for j in [1,3,4,5,7])
        hashes={p.name:sha(p.read_bytes()) for p in folder.glob('*.bin')}
        snapshots={p.name:json.loads(p.read_text()) for p in folder.glob('*.json')}
        comparable=dict(hashes=hashes,snapshots=snapshots)
        if reference is None:reference=comparable
        else:assert comparable==reference,(kind,i,'repeat mismatch')
        stages={p.name[:-9]:checked(p) for p in folder.glob('*-MEMC.bin')}
        base=stages['pre-module'];base_soft=base['soft']
        if kind=='natural':
            before=stages['shrink-entry'];after=stages['shrink-return']
            # FileCore/ADFS legitimately grow the RMA by two physical pages.
            wanted=base_soft.copy();wanted[127]=0x1808000;wanted[126]=0x1810000
            assert before['soft']==after['soft']==wanted
            assert word(before,0x180000c)==word(after,0x180000c)==0x18000
            assert before['counter']-base['counter']==2
            assert before['table']==after['table'] and before['cam']==after['cam'] and before['sequence']==after['sequence']
            r=json.loads((folder/'shrink-return.json').read_text())
            assert r['heap_end']==0x6000 and r['app_end']==0x3a0000 and r['r'][1]==0 and r['psr']&0x10000000
            assert int.from_bytes(rom[r['r'][0]-0x3800000:r['r'][0]-0x3800000+4],'little')==0x1c1
            assert stages['supervisor-entry']['soft']==wanted
        else:
            expected={'oversized-shrink':{},'heap-grow':{127:0x1c08000},'heap-page-marker':{127:0x1c08000},'heap-shrink':{},'heap-grow-two':{127:0x1c08000,126:0x1c10000},'partial-shrink-two':{},'rma-grow':{127:0x1808000},'rma-shrink':{}}
            for stage,changes in expected.items():
                wanted=base_soft.copy()
                for ppn,value in changes.items():wanted[ppn]=value
                assert stages[stage]['soft']==wanted,(stage,[(j,hex(a),hex(b)) for j,(a,b) in enumerate(zip(stages[stage]['soft'],wanted)) if a!=b])
            writes={'oversized-shrink':0,'heap-grow':1,'heap-page-marker':1,'heap-shrink':2,'heap-grow-two':4,'partial-shrink-two':6,'rma-grow':7,'rma-shrink':8}
            for stage,count in writes.items():assert stages[stage]['counter']-base['counter']==count,(stage,'CAM programming count')
            marker=struct.pack('<I',0x51a7c0de)
            assert stages['heap-page-marker']['read'](0x1c08000,4)==marker
            assert stages['heap-shrink']['read'](0x3a8000,4)==marker
            assert stages['heap-page-marker']['ram'][0x3f8000:0x3f8004]==marker
        reports.append(dict(kind=kind,run=i,stages=len(stages),descriptors_per_stage=8192,software_cam_entries_per_stage=128))
negative=json.loads((ROOT/'artifacts/negative/result.json').read_text());assert negative['status']=='PASS' and negative['cam_failures']==1
n=json.loads((ROOT/'artifacts/negative/reproduced-cam-failure.json').read_text());assert n['r'][0]==0x1bfa000 and n['r'][2]==0xffffffff
save('cam-verification.json',dict(status='PASS',baseline_negative_control_reproduces_failure=True,repeat_state_identical=True,checks=reports,partial_shrink_error_number='0x1c1',no_fabricated_mappings=True))

# Verify genuine module installation and FileSwitch's filing-system vector.
m=checked(ROOT/'artifacts/natural-1/supervisor-entry-MEMC.bin')
def anyread(a,n):return rom[a-0x3800000:a-0x3800000+n] if a>=0x3800000 else m['read'](a,n)
def anyword(a):return int.from_bytes(anyread(a,4),'little')
node=word(m,S['VecPtrTab']+4*S['FSCV']);handler=anyword(node+8)
layout=json.loads((ROOT/'artifacts/rom-layout.json').read_text())['modules'];fs=next(x for x in layout if x['component']=='FileSwitch')
assert fs['base']<=handler<fs['base']+fs['length']
link=word(m,S['Module_List']);modules=[];seen=set()
while link:
    assert link not in seen;seen.add(link)
    code=anyword(link+S['Module_code_pointer']);title=code+anyword(code+S['Module_Title'])
    modules.append(anyread(title,64).split(b'\0')[0].decode());link=anyword(link+S['Module_chain_Link'])
assert modules==['UtilityModule','FileSwitch','ResourceFS','MessageTrans','Messages','TerritoryManager','UK','International','InternationalKeyboard','FileCore','ADFS']
numbers=collections.Counter(int(x,16) for x in re.findall(r'MISSING swi=&([0-9A-F]+)',(ROOT/'artifacts/natural-1/events.log').read_text()))
names={0x4028a:'Podule_EnumerateChunksWithInfo',0x41501:'MessageTrans_OpenFile',0x40750:'ColourTrans_InvalidateCache',0x40186:'Sound_ControlPacked',0x41502:'MessageTrans_Lookup',0x43057:'Territory_LowerCaseTable',0x43058:'Territory_UpperCaseTable'}
save('runtime-dependencies.json',dict(status='OBSERVED',modules=modules,filing_system_vector=dict(node=hex(node),handler='FileSwitch',address=hex(handler),meaning='Real FileSwitch FSCV handler; ResourceFS and original FileCore/ADFS installed.'),missing_swis={hex(n):dict(name=names.get(n,'unknown'),count=c) for n,c in numbers.items()}))

# Retain the proven font and full active-display pixel comparisons.
font=bytes(int(h,16) for l in (ROOT/'work/Kernel/s/vdu/vdufontl1').read_text().splitlines() if l.lstrip().startswith('=') for h in re.findall(r'&([0-9a-fA-F]+)',l.split(';')[0]))
assert len(font)==1792 and S['HardFont']%4==0 and rom[S['HardFont']-0x3800000:S['HardFont']-0x3800000+1792]==font
for i in [1,2,3]:assert checked(ROOT/f'artifacts/repeats/cold-{i}/pre-module-MEMC.bin')['read'](0x3700,1792)==font
# The genuine International alphabet service installs its public Latin1 glyphs.
# Parse that source independently and retain the pre-module kernel-font gate above.
font_source=(ROOT/'sources/Inter/s/InterFonts').read_text(encoding='latin1')
glyphs={}
for line in font_source.split('\n'):
    match=re.match(r'^(\w+)\s*=\s*(.*)',line)
    if match:
        b=bytes(int(x,16) for x in re.findall(r'&([0-9a-fA-F]{2})\b',match[2].split(';')[0]));assert len(b)==8
        glyphs[match[1]]=b
latin=font_source.split('Latin1  InterTable')[1].split('InterEnd')[0]
names=[n.strip() for line in latin.split('\n') if line.strip().startswith('FONTS') for n in line.split('FONTS')[1].split(',')]
assert len(names)==224
runtimefont=bytearray(font)
for i,n in enumerate(names):
    if n!='UNK001':runtimefont[i*8:i*8+8]=glyphs[n]
assert runtimefont[:95*8]==font[:95*8] # all original printable-ASCII regressions retained
fontchanges=[dict(character=i//8+32,row=i%8,before=a,after=b) for i,(a,b) in enumerate(zip(font,runtimefont)) if a!=b]
assert fontchanges==[dict(character=252,row=2,before=0,after=0x66)]
textchecks=[]
for name in ['banner','text-fixture']:
    p=ROOT/'artifacts'/name;m=checked(p/'MEMC.bin');r=json.loads((p/'result.json').read_text());pixels=(p/'frame.rgba').read_bytes()
    assert (p/'soft-font.bin').read_bytes()==(runtimefont if name=='banner' else font)
    assert (r['bpp'],r['width'],r['height'],r['line_length'])==(4,832,288,320)
    screen=m['read'](r['screen_start'],320*256);assert screen==m['ram'][:320*256]
    for y in range(256):
        for x in range(640):
            index=(screen[y*320+x//2]>>(4*(x%2)))&15;assert index in [0,7]
            offset=((y+16)*832+x+96)*4
            assert pixels[offset:offset+4]==bytes([255 if index else 0]*3+[255])
    if name=='text-fixture':
        for char in range(32,127):
            cx=(char-32)%32;cy=(char-32)//32
            for y in range(8):
                for x in range(8):
                    px=cx*8+x;py=cy*8+y;index=(screen[py*320+px//2]>>(4*(px%2)))&15
                    assert index==(7 if font[(char-32)*8+y]&(128>>x) else 0)
    textchecks.append(dict(capture=name,display_pixels=163840,font_bytes=1792,ascii_glyphs=95 if name=='text-fixture' else 0))
save('text-verification.json',dict(status='PASS',checks=textchecks,public_international_latin1_changes=fontchanges,pre_module_original_font_preserved=True))
print('PASS: negative control, three natural transitions, three page-transfer suites, CAM/MEMC contracts and text regression')
