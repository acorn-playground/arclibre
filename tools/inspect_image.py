#!/usr/bin/env python3
"""Independent AOF reader and ARM2 instruction decoder. Apache-2.0.

No AsAsm encoding/disassembly code is used here. Mapping/provenance metadata
comes from AsAsm; emitted words and relocation resolution are checked directly.
"""
import collections,json,pathlib,struct
from paths import ROOT,REPO
MASK26=0x3ffffff
def words(b):return struct.unpack('<'+'I'*(len(b)//4),b)
def load_aof(path):
    b=path.read_bytes();magic,maximum,count=struct.unpack_from('<III',b)
    assert magic==0xc3cbc6c5 and count<=maximum
    chunks={}
    for i in range(maximum):
        name,offset,size=struct.unpack_from('<8sII',b,12+16*i)
        if offset:
            assert offset%4==0 and offset+size<=len(b)
            chunks[name.decode()]=b[offset:offset+size]
    assert len(chunks)==count
    h=words(chunks['OBJ_HEAD']);assert h[0]==0xc5e2d080 and h[1]==310 and h[2]==1
    name,attributes,size,relocs,base=h[6:11]
    assert attributes & 0x300==0x300 and not attributes & (0x10000|0x100000)
    assert relocs==0 and len(chunks['OBJ_AREA'])==size
    strings=chunks['OBJ_STRT']
    def string(n):return strings[n:strings.index(b'\0',n)].decode()
    syms=[]
    assert len(chunks['OBJ_SYMT'])==h[3]*16
    for n,a,v,area in struct.iter_unpack('<IIII',chunks['OBJ_SYMT']):
        assert a&1,'Unresolved external: '+string(n)
        syms.append(dict(name=string(n),attributes=a,value=v,area=area))
    return dict(base=base,size=size,relocations=relocs,symbols=syms,attributes=attributes,data=chunks['OBJ_AREA'])

# Only the ArcLibre ARM3Support module may use the ARM3's cache controller
# (MRC/MCR to coprocessor 15); its builder sets this for that module alone.
ALLOW_CP15=False

def ror(v,n):return ((v>>n)|(v<<(32-n)))&0xffffffff if n else v
def decode(w,pc):
    cond=w>>28;group=(w>>25)&7
    assert cond!=15 or w==0xf1a00000,'only the historical MOVNV r0,r0 delay is accepted with NV condition'
    d=dict(word=f'{w:08x}',condition=cond,reads=[],writes=[],kind='',branch=None,psr=False,return_pc=False)
    rn=(w>>16)&15;rd=(w>>12)&15;rm=w&15;s=(w>>20)&1
    def registers(r,writes):d['reads']=sorted(set(r));d['writes']=sorted(set(writes))
    if group==5:
        disp=w&0xffffff
        if disp&0x800000:disp-=0x1000000
        d.update(kind='BL' if w&(1<<24) else 'B',branch=(pc+8+disp*4)&MASK26)
        registers([15],[15,14] if w&(1<<24) else [15])
    elif group in (0,1):
        if w&0x0fc000f0==0x00000090:
            dest=rn;rs=(w>>8)&15;acc=bool(w&(1<<21))
            assert dest!=rm and 15 not in [dest,rs,rm]+([rd] if acc else []),'multiply register restriction'
            assert acc or rd==0,'reserved MUL accumulate field'
            d['kind']='MLA' if acc else 'MUL';registers([rm,rs]+([rd] if acc else []),[dest])
        else:
            assert not (group==0 and w&0x90==0x90),'post-ARM2 multiply/swap/halfword/extension encoding'
            op=(w>>21)&15;test=op in (8,9,10,11)
            assert not test or s,'post-ARM2 status/miscellaneous encoding'
            assert not test or rd in (0,15),'reserved test destination'
            d['kind']=['AND','EOR','SUB','RSB','ADD','ADC','SBC','RSC','TST','TEQ','CMP','CMN','ORR','MOV','BIC','MVN'][op]
            operands=[] if op in (13,15) else [rn]
            if group==1:d['immediate']=ror(w&255,((w>>8)&15)*2)
            else:
                operands.append(rm)
                if w&16:
                    assert not w&128,'reserved register shift bit'
                    rs=(w>>8)&15;assert rs!=15,'PC used as register shift count'
                    operands.append(rs)
            registers(operands,[] if test else [rd])
            d['psr']=test and rd==15
            d['return_pc']=not test and rd==15 and bool(s)
    elif group in (2,3):
        assert not (group==3 and w&16),'post-ARM2/undefined transfer encoding'
        load=bool(w&(1<<20));byte=bool(w&(1<<22));writeback=bool(w&(1<<21)) or not bool(w&(1<<24))
        assert not (rd==15 and byte),'byte transfer with PC'
        assert not (writeback and rn==15),'PC base writeback'
        d['kind']=('LDR' if load else 'STR')+('B' if byte else '')
        registers([rn]+([rm] if group==3 else [])+([] if load else [rd]),([rd] if load else [])+([rn] if writeback else []))
        if rn==15 and group==2 and w&(1<<24):d['literal']=(pc+8+(w&4095)*(1 if w&(1<<23) else -1))&MASK26
    elif group==4:
        load=bool(w&(1<<20));user=bool(w&(1<<22));wb=bool(w&(1<<21));regs=[i for i in range(16) if w&(1<<i)]
        assert rn!=15 and regs,'invalid block transfer base/list'
        assert not (user and (not load or 15 not in regs) and wb),'writeback on user-bank block transfer'
        d.update(kind='LDM' if load else 'STM',user_bank=user and not (load and 15 in regs),return_pc=user and load and 15 in regs)
        registers([rn]+([] if load else regs),(regs if load else [])+([rn] if wb else []))
    elif w&0x0f000000==0x0f000000:
        d.update(kind='SWI',swi=w&0xffffff);registers([],[])
    elif ALLOW_CP15 and w&0x0f000010==0x0e000010 and (w>>8)&15==15:
        load=bool(w&(1<<20));assert rd!=15,'CP15 transfer with PC'
        d.update(kind='MRC' if load else 'MCR',coprocessor=15,crn=rn,crm=rm)
        registers([] if load else [rd],[rd] if load else [])
    else:
        raise AssertionError('coprocessor instruction: not allowed in this original-board kernel')
    return d

def load_symbols():
    syms={}
    for line in (ROOT/'artifacts/symbols.tsv').read_text().splitlines():
        name,tag,value,reg,attr,size,file,line_no,string=line.split('\t')
        syms[name]=dict(tag=int(tag),value=int(value),reg=int(reg),attributes=int(attr),size=int(size),file=file,line=int(line_no),string=bytes.fromhex(string).decode('latin1'))
    return syms

def load_emissions():
    emissions={};instructions={}
    for line in (ROOT/'artifacts/emissions.tsv').read_text().splitlines():
        kind,off,size,value,times,file,line_no,caller,caller_line=line.split('\t')
        off,size,value,times=map(int,(off,size,value,times))
        row=dict(kind=kind,offset=off,size=size,value=value,times=times,file=file,line=int(line_no),caller=caller,caller_line=int(caller_line))
        for index in range(times):
            for j in range(size):emissions[off+index*size+j]=((value>>(8*j))&255,row)
        if kind=='I':instructions[off]=row
    return emissions,instructions

def inspect():
    obj=load_aof(ROOT/'artifacts/kernel.aof');base=obj['base'];data=obj['data'];syms=load_symbols()
    assert data==load_aof(ROOT/'artifacts/kernel-trace.aof')['data']
    emitted,ins=load_emissions()
    for offset,(byte,row) in emitted.items():assert data[offset]==byte,(offset,row)
    mapping=sorted((s['value'],s['name']) for s in obj['symbols'] if s['name'] in ('$a','$d','$t'))
    mapped_code=set()
    for i,(start,kind) in enumerate(mapping):
        end=mapping[i+1][0] if i+1<len(mapping) else len(data)
        assert kind!='$t'
        if kind=='$a':mapped_code.update(range(start,end,4))
    assert set(ins)<=mapped_code
    for off in mapped_code-set(ins):
        assert data[off:off+4]==bytes(4),'untraced nonzero code'
        previous=max(i for i in ins if i<off)
        ins[off]=dict(ins[previous],offset=off,value=0,alignment_padding=True)
    # Source DCD is an actual RAM-executed IRQ branch, explicitly reviewed.
    irq_vector=syms['MOSROMVecs']['value']-base+24
    assert emitted[irq_vector][1]['kind']=='D'
    ins[irq_vector]=dict(emitted[irq_vector][1],kind='I',size=4,value=struct.unpack_from('<I',data,irq_vector)[0],raw_instruction=True)
    # Without ProcessorVectors (the delivered kernel: 3.11's branch vectors),
    # the templates copied to &0 and &18 are the same reviewed branch DCDs.
    raw_templates=[]
    for name in ['BranchThroughZeroInstruction','BranchThroughZeroInstruction2','RealIRQHandler']:
        off=syms[name]['value']-base
        if emitted[off][1]['kind']=='D':
            word=struct.unpack_from('<I',data,off)[0];assert word>>24==0xEA,(name,hex(word))
            ins[off]=dict(emitted[off][1],kind='I',size=4,value=word,raw_instruction=True);raw_templates.append(off)
    runtime_regions=[('processor-vectors',syms['MOSROMVecs']['value'],syms['EndFiq']['value'],0)]
    if 'DefaultPreVeneers' in syms:
        runtime_regions.append(('processor-preveneers',syms['DefaultPreVeneers']['value'],syms['DefaultPreVeneers']['value']+syms['ProcVecPreVeneersSize']['value'],syms['ProcVecPreVeneers']['value']))
    runtime_regions+=[
        ('swi-dispatch',syms['SVCDespatcher']['value'],syms['DirtyBranch']['value'],syms['SWIDespatch']['value']),
        ('swi-exit-branch',syms['DirtyBranch']['value'],syms['DirtyBranch']['value']+4,syms['BranchToSWIExit']['value']),
        ('zero-vector-template',syms['BranchThroughZeroInstruction']['value'],syms['BranchThroughZeroInstruction']['value']+4,0),
        ('reset-zero-vector-template',syms['BranchThroughZeroInstruction2']['value'],syms['BranchThroughZeroInstruction2']['value']+4,0),
        ('normal-irq-vector-template',syms['RealIRQHandler']['value'],syms['RealIRQHandler']['value']+4,0x18),
        ('default-irq',syms['DefaultIRQ1Vcode']['value'],syms['DefaultIRQ1Vcode_end']['value'],syms['DefaultIRQ1V']['value'])]
    def runtime(off):
        address=base+off
        for name,start,end,dest in runtime_regions:
            if start<=address<end:return dest+address-start
        return address
    errors=[];decoded={}
    for offset,row in sorted(ins.items()):
        assert offset%4==0 and row['size']==4
        word=struct.unpack_from('<I',data,offset)[0]
        try:decoded[offset]=dict(decode(word,runtime(offset)),offset=offset,rom_address=base+offset,runtime_address=runtime(offset),source=row)
        except AssertionError as exc:errors.append(dict(offset=offset,word=f'{word:08x}',error=str(exc),source=row))
    for filename,value in [('instructions.json',list(decoded.values())),('instruction-errors.json',errors),('runtime-regions.json',runtime_regions)]:
        (ROOT/'artifacts'/filename).write_text(json.dumps(value,indent=2)+'\n')
    psr=[dict(offset=off,instruction=row,next=decoded.get(off+4)) for off,row in decoded.items() if row['psr'] or row.get('user_bank') and row['kind']=='LDM']
    (ROOT/'artifacts/psr-sequences.json').write_text(json.dumps(psr,indent=2)+'\n')
    (ROOT/'artifacts/kernel.bin').write_bytes(data)
    # Trace and ordinary AOF mapping must classify exactly the same instructions,
    # apart from the explicitly declared DCD vector instructions.
    assert set(ins)-{irq_vector}-set(raw_templates)==mapped_code
    listing=[]
    for off,row in sorted(decoded.items()):
        operand=(' -> &%08x'%row['branch']) if row['branch'] is not None else (' read='+str(row['reads'])+' write='+str(row['writes']))
        src=row['source'];location=pathlib.Path(src['caller']).relative_to(ROOT)
        listing.append(f"{row['rom_address']:08x} @{row['runtime_address']:08x} {row['word']} {row['kind']:<4}{operand} ; {location}:{src['caller_line']}\n")
    (ROOT/'artifacts/kernel-instructions.txt').write_text(''.join(listing))
    # Exhaustive, non-overlapping byte map; source DCD IRQ and alignment included.
    ranges=[]
    for off in range(0,len(data),4):
        kind='code' if off in ins else 'data'
        if ranges and ranges[-1]['kind']==kind:
            ranges[-1]['end_offset']=min(off+4,len(data))
        else:ranges.append(dict(kind=kind,start_offset=off,end_offset=min(off+4,len(data))))
    for row in ranges:
        row.update(rom_start=base+row['start_offset'],rom_end=base+row['end_offset'])
    assert sum(r['end_offset']-r['start_offset'] for r in ranges)==len(data)
    (ROOT/'artifacts/code-data-ranges.json').write_text(json.dumps(ranges,indent=2)+'\n')
    print('size',len(data),'instructions',len(ins),'errors',len(errors),'PSR/user-bank sequences',len(psr))
    for err in errors[:25]:print(err['offset'],err['word'],err['error'],err['source']['caller'],err['source']['caller_line'])
    return obj,decoded,syms,errors
if __name__=='__main__':inspect()
