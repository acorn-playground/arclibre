#!/usr/bin/env python3
"""Static milestone gates, independently decoded instruction/contract checks.
Apache-2.0. Kernel opcode safety is checked over all identified code, a superset
of reachable kernel paths; dynamically installed client code is out of scope.
"""
import collections,hashlib,json,pathlib,re,struct,sys
from inspect_image import ROOT,inspect,decode,load_aof
from paths import REPO
def save(name,value):(ROOT/'artifacts'/name).write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    obj,ins,syms,errors=inspect();assert not errors
    data=obj['data'];base=obj['base'];v=lambda n:syms[n]['value']
    read=lambda addr:struct.unpack_from('<I',data,addr-base)[0]
    normal=ROOT/'artifacts/kernel.aof';traced=ROOT/'artifacts/kernel-trace.aof'
    assert normal.read_bytes()==traced.read_bytes(),'observer changed object output'
    for result in ['assembly-result.json','trace-assembly-result.json']:
        assert json.loads((ROOT/'artifacts'/result).read_text())['returncode']==0
    negatives={'mrs':0xe10f0000,'msr':0xe129f000,'swp':0xe1020091,'bx':0xe12fff1e,'blx-immediate':0xfa000000,'halfword':0xe1d100b0,'long-multiply':0xe0810392,'clz':0xe16f0f11,'bad-multiply-alias':0xe0000090,'pc-byte-load':0xe5d1f000,'pc-writeback':0xe5bf0004}
    for name,word in negatives.items():
        try:decode(word,base)
        except AssertionError:pass
        else:raise AssertionError('negative opcode accepted: '+name)
    positives={0xe33ff003:'TEQ',0xe1b0f00e:'MOV',0xe25ef004:'SUB',0xe8fd800f:'LDM',0xf1a00000:'MOV'}
    for word,kind in positives.items():assert decode(word,base)['kind']==kind

    valid={r['runtime_address'] for r in ins.values()}|{r['rom_address'] for r in ins.values()}
    branches=[r for r in ins.values() if r['branch'] is not None]
    for r in branches:assert r['branch'] in valid,('branch into noncode',r)
    settled=0;exempt=[]
    for off,row in ins.items():
        if row['psr'] or row.get('user_bank') and row['kind']=='LDM':
            if v('SVCDespatcher')<=base+off<v('SVCDespatcher')+v('SWIDespatch_Size'):
                assert row['word']=='e33af000' and read(base+off-4)==0xe38ea003
                exempt.append(dict(address=base+off,reason='SWI entered SVC; preceding ORR r10,lr,#3 forces SVC. No bank change.'))
            else:
                assert read(base+off+4)==0xe1a00000,('missing ARM2 settling instruction',row)
                settled+=1
    assert len(exempt)==1
    expected={'USR_mode':0,'FIQ_mode':1,'IRQ_mode':2,'SVC_mode':3,'I_bit':0x8000000,'F_bit':0x4000000,
              'ROM':0x3800000,'PhysRam':0x2000000,'IOC':0x3200000,'VIDC':0x3400000,'MEMCADR':0x3600000,'CAM':0x3800000,
              'CamEntries':0x164,'CamEntriesPointer':0x564,'CursorChunkAddress':0x1f00000,'SysHeapChunkAddress':0x1c00000,
              'SVCSTK':0x1c02000,'SvcTable':0x1f033fc,'SWIDespatch_Size':116,'DefaultIRQ1V':0xc34,'DefIRQ1Vspace':752,
              'UniqueMachineID':0xf64,'ResetIndirection':0x118,'VduDriverWorkSpace':0x1000,'VDWSSize':0x3000,
              'ScratchSpace':0x4000,'ScratchSpaceSize':0x4000,'ProcVec_Start':0xf90,'ProcVec_End':0xfac}
    for name,value in expected.items():assert v(name)==value,(name,hex(v(name)),hex(value))
    hardware={'CPU_Type':'ARM2','IO_Type':'IOC-A1','VIDC_Type':'VIDC1a','MEMC_Type':'MEMC1a','MEMM_Type':'MEMC1','FDC_Type':'FDC1772','Keyboard_Type':'A1A500'}
    for name,value in hardware.items():assert syms[name]['string']==value
    for name in ['NewCDA','ExpandedCamMap','MorrisSupport','HasDallasID','IncludeTestSrc','Select16BitSound']:
        assert syms[name]['tag']==16 and v(name)==0
    # The delivered ROM probes for the A5000 family's IOEB at reset, as 3.11 did.
    assert syms['HasIOEB']['tag']==16 and v('HasIOEB')==(1 if '--desktop-defaults' in sys.argv else 0)
    for name in ['AMBControl_Init','L1L2PTenhancements','RawMachineID','IOMD_Base','ARM3_Support']:
        assert name not in syms or syms[name]['tag']==0,name
    # No newly invented workspace. Fixed ABI block sizes and region boundaries.
    assert sha(ROOT/'work/Kernel/hdr/Old/NewSpace')==json.loads((REPO/'manifests/contracts.json').read_text())['original_memc_workspace_sha256']
    assert v('DefaultIRQ1Vcode_end')-v('DefaultIRQ1Vcode')==v('DefIRQ1Vspace')
    assert v('JTABLE')-v('SVCDespatcher')==v('SWIDespatch_Size')
    assert v('DefaultIRQ1V')+v('DefIRQ1Vspace')==v('CallBack_Vector')
    assert v('ProcVecPreVeneers')==v('ProcVec_End') and v('ProcVecPreVeneers')+16<0xfec
    assert v('VduDriverWorkSpace')+v('VDWSSize')==v('ScratchSpace')
    assert v('ScratchSpace')+v('ScratchSpaceSize')==0x8000
    assert v('SWIDespatch')+v('SWIDespatch_Size')==v('SvcTable')
    assert v('SvcTable')+1024==v('BranchToSWIExit')
    assert v('CursorChunkAddress')+0x1000<v('IRQSTK')<v('CamEntriesForBigMachines')
    save('workspace-contract.json',dict(hardware=hardware,constants={n:dict(value=x,hex=hex(x)) for n,x in expected.items()},old_workspace_unmodified=True,top_of_page_zero_symbol_note='TopOfPageZero is a local scratch overlay offset (0x200), not the overall 32 KiB page-zero extent.',ram_copy_regions=json.loads((ROOT/'artifacts/runtime-regions.json').read_text())))

    # Inspect actual vector and handler words, applying their RAM destinations.
    vectors=[]
    reset=decode(read(base),0)
    assert reset['literal']==0x118 and read(base+0x118)==v('CONT')
    vectors.append(dict(path='cold reset',vector=0,target=v('CONT'),mechanism='ROM alias at zero: LDR pc,[pc,#0x110] loads physical CONT at offset 0x118'))
    handlers=[('undefined',4,'ProcVec_UndInst','UndPreVeneer','UndHan','UNDEF',1),('prefetch abort',12,'ProcVec_PrefAb','PAbPreVeneer','PAbHan','ABORTP',2),('data abort',16,'ProcVec_DataAb','DAbPreVeneer','DAbHan','ABORTD',3),('address exception',20,'ProcVec_AddrEx','AdXPreVeneer','AdXHan','ADDREX',4)]
    # The delivered kernel (no ProcessorVectors) has RISC OS 3.11's hardware
    # vectors: LDR pc from the environment slots, and branches for SWI and IRQ.
    if 'DefaultPreVeneers' not in syms:
     for name,address,slot,veneer,env,default,index in handlers:
        d=decode(read(v('MOSROMVecs')+address),address);assert d['literal']==v(env),name
        assert read(v('defhantab')+index*12)==v(default) and v(default) in valid
        vectors.append(dict(path=name,vector=address,environment_slot=v(env),default_handler=v(default),client_replacement='OS_ChangeEnvironment/OS_SetEnv contract; client code not certified'))
     assert decode(read(v('MOSROMVecs')+8),8)['branch']==v('SVC')
     vectors.append(dict(path='SWI',vector=8,mechanism='branch, as in RISC OS 3.11',dispatcher=v('SVC'),dispatcher_size=116,return_entry=v('SLVK')))
     early=decode(read(v('MOSROMVecs')+24),24)
     assert early['branch']==v('IRQ_Test_CTRL_or_R_Pressed')
     assert decode(read(v('RealIRQHandler')),24)['branch']==v('Initial_IRQ_Code')
     for template in ['BranchThroughZeroInstruction','BranchThroughZeroInstruction2']:assert decode(read(v(template)),0)['branch']==v('RESET1'),template
     vectors.append(dict(path='IRQ',vector=24,mechanism='branch, as in RISC OS 3.11',early_keyboard_handler=early['branch'],normal_entry=v('Initial_IRQ_Code'),default_dispatch_ram=v('DefaultIRQ1V')))
    else:
     for name,address,slot,veneer,env,default,index in handlers:
         d=decode(read(v('MOSROMVecs')+address),address);assert d['literal']==v(slot)
         pointer=read(v('DefaultProcVecs')+v(slot)-v('ProcVec_Start'));assert pointer==v(veneer)
         word=read(v('DefaultPreVeneers')+pointer-v('ProcVecPreVeneers'));d=decode(word,pointer)
         assert d['literal']==v(env)
         assert read(v('defhantab')+index*12)==v(default) and v(default) in valid
         vectors.append(dict(path=name,vector=address,table_slot=v(slot),veneer=pointer,environment_slot=v(env),default_handler=v(default),client_replacement='OS_ChangeEnvironment/OS_SetEnv contract; client code not certified'))
     assert read(v('DefaultProcVecs')+v('ProcVec_SWI')-v('ProcVec_Start'))==v('SVC')
     assert decode(read(v('MOSROMVecs')+8),8)['literal']==v('ProcVec_SWI')
     vectors.append(dict(path='SWI',vector=8,dispatcher=v('SVC'),dispatcher_size=116,return_entry=v('SLVK')))
     early=decode(read(v('MOSROMVecs')+24),24)
     assert early['branch']==v('IRQ_Test_CTRL_or_R_Pressed')
     assert decode(read(v('RealIRQHandler')),24)['literal']==v('ProcVec_IRQ')
     assert read(v('DefaultProcVecs')+v('ProcVec_IRQ')-v('ProcVec_Start'))==v('Initial_IRQ_Code')
     vectors.append(dict(path='IRQ',vector=24,early_keyboard_handler=early['branch'],normal_entry=v('Initial_IRQ_Code'),default_dispatch_ram=v('DefaultIRQ1V')))
    fiq=[read(v('MOSROMVecs')+28+i*4) for i in range(3)]
    assert fiq==[0xe3a0a632,0xe5caa038,0xe25ef004]
    vectors.append(dict(path='unclaimed FIQ',vector=28,words=[hex(w) for w in fiq],behaviour='disable IOC FIQ mask, return with SUBS pc,lr,#4; claimed FIQ handler is external'))
    assert decode(read(v('DirtyBranch')),v('BranchToSWIExit'))['branch']==v('SLVK')
    for name in ['NOCALL','Do_CallBack','callback_checking','VSet_GenerateError']:
        assert v(name) in valid
    save('exception-paths.json',dict(status='PASS: static routes and all resident instruction encodings',paths=vectors,psr_settled=settled,psr_same_mode_exceptions=exempt,limitations='Dynamic module SWIs, client callbacks, claimed vectors and hardware timing are external runtime obligations. This does not prove boot or application correctness.'))
    indirect=[r for r in ins.values() if 15 in r['writes'] and r['branch'] is None]
    save('indirect-control-flow.json',dict(scope='Complete inventory of decoded resident PC-writing instructions other than direct branches; runtime targets are not exhaustively proven.',sites=indirect))
    checkpoint_names=['CONT','InitMEMC','MemSize','TimeCPU','EmptyCamEntries','ResetPart1Done','CopyDefaultIRQ1V','VduInit','ExecuteInit','KeyInit','MouseInit','InitialiseMode','InitVariables','ModuleInit','UNDEF','ABORTP','ABORTD','ADDREX','DumpyTheRegisters','UNDEF1','RESET1','Initial_IRQ_Code','Do_CallBack','callback_checking','NOCALL','SLVK']
    save('boot-checkpoints.json',[dict(name=n,address=v(n),hex=hex(v(n)),source=syms[n]['file'],line=syms[n]['line']) for n in checkpoint_names])

    # Every diagnostic must belong to a reviewed benign optimisation category.
    result=json.loads((ROOT/'artifacts/assembly-result.json').read_text());log=(ROOT/result['log']).read_text()
    warnings=[line for line in log.splitlines() if 'Warning:' in line]
    for line in warnings:
        assert any(fragment in line for fragment in ['ADR instead of ADRL','Literal loading optimized as MOV/MVN/MOVW','note: LTORG was here']),line
    save('diagnostics-review.json',dict(error_count=0,warnings=warnings,interpretation='ADR/ADRL size optimisation hints and one unused literal-pool slot plus its location note; emitted opcodes and branch targets independently checked. No suppressed warnings.'))
    # Negative controls establish that the gate rejects modern instructions.
    report=dict(status='PASS',scope='kernel-only static assembly/ARM2 milestone; not a boot or RISC OS 3.11 compatibility result',
        kernel_bytes=len(data),kernel_sha256=hashlib.sha256(data).hexdigest(),aof_sha256=sha(normal),
        unresolved_symbols=0,relocations=obj['relocations'],instruction_words=len(ins),
        independent_opcode_failures=len(errors),direct_branch_targets_checked=len(branches),
        bank_settling_checks=settled,same_mode_dispatcher_exception_count=len(exempt),
        negative_opcode_controls=list(negatives),observer_object_identical=True,
        opcode_counts=dict(collections.Counter(r['kind'] for r in ins.values())),diagnostic_warnings=len(warnings))
    save('verification.json',report)
    print(json.dumps(report,indent=2))
if __name__=='__main__':verify()
