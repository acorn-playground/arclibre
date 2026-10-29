#!/usr/bin/env python3
"""Independent checks of captured MacArch state; no guest-state mutation. Apache-2.0."""
import collections,gzip,hashlib,json,pathlib,re,struct
from paths import ROOT,REPO
S=json.loads((ROOT/'artifacts/symbols.json').read_text())
kernel=(ROOT/'artifacts/kernel.bin').read_bytes()
def save(name,value):(ROOT/'artifacts'/name).write_text(json.dumps(value,indent=2)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def memc(path):
    b=path.read_bytes();p=0
    def take(fmt):
        nonlocal p
        value=struct.unpack_from('<'+fmt,b,p);p+=struct.calcsize('<'+fmt)
        return value[0] if len(value)==1 else value
    ticks=take('Q');abort=take('B');privileged=take('B');size=take('I')
    assert size==4194304 and abort==0
    ram=b[p:p+size];p+=size
    assert take('I')==128;cam=take('128I')
    assert take('I')==128;sequence=take('128Q');counter=take('Q')
    table=take('8192I');page,low,high,refresh=take('4I')
    video,sound,osmode=take('3B');romticks=take('Q');overlay=take('B')
    dma=take('10I');assert page==3 and not overlay
    # Independent original MEMC1 32 KiB CAM reconstruction, including aliases.
    chosen={}
    for ppn,a in enumerate(cam):
        if a==0xffffffff:continue
        decoded_ppn=((a>>3)&15)|((a&1)<<4)|((a&4)<<3)|((a&2)<<5)
        assert decoded_ppn==ppn
        logical=(a&0x7f8000)|((a&0xc00)<<13)
        if logical not in chosen or sequence[ppn]>chosen[logical][0]:chosen[logical]=(sequence[ppn],ppn,(a>>8)&3)
    expected=[0]*8192
    for logical,(_,ppn,ppl) in chosen.items():
        for off in range(0,32768,4096):expected[(logical+off)>>12]=0x4000000|(ppl<<24)|(ppn*32768+off)
    assert tuple(expected)==table,'independent CAM reconstruction differs from emulator page table'
    def read(a,n):
        out=bytearray()
        for addr in range(a,a+n):
            descriptor=table[addr>>12];assert descriptor&0x4000000
            out.append(ram[(descriptor&0xffffff)|(addr&4095)])
        return bytes(out)
    return dict(ram=ram,cam=cam,sequence=sequence,table=table,read=read,counter=counter,ticks=ticks,video=video,sound=sound,dma=dma,osmode=osmode)

def verify():
    rep=json.loads((ROOT/'artifacts/repeats/repeatability.json').read_text());assert rep['status']=='PASS'
    runs=rep['runs'];assert len(runs)==3
    reports=[];reference=None
    for run in runs:
        i=run['cold_run'];folder=ROOT/f'artifacts/repeats/cold-{i}'
        assert run['no_log_loss'] and run['largest_drain']<run['log_limit']
        finals=[]
        for stage in ['fixed-mappings','vectors-installed','pre-module']:
            m=memc(folder/f'{stage}-MEMC.bin');read=m['read'];word=lambda a:struct.unpack('<I',read(a,4))[0]
            for logical,physical in [(0,0x80000),(0x1c00000,0x88000),(0x1f00000,0x78000)]:
                for off in range(0,32768,4096):
                    assert m['table'][(logical+off)>>12]&0xffffff==physical+off
            copies=[]
            if stage!='fixed-mappings':
                for dest,source,n in [('DefaultIRQ1V','DefaultIRQ1Vcode',752),('SWIDespatch','SVCDespatcher',116),('ProcVec_Start','DefaultProcVecs',44),('BranchToSWIExit','DirtyBranch',4)]:
                    expected=kernel[S[source]-0x3800000:S[source]-0x3800000+n]
                    assert read(S[dest],n)==expected,(stage,dest)
                    copies.append(dict(destination=dest,source=source,bytes=n,sha256=sha(expected)))
                assert word(S['Page_Size'])==32768 and word(S['RAMLIMIT'])==4194304
                assert word(S['MemorySpeed'])==0x11f40
                assert word(S['ResetIndirection'])==S['CONT_Break']
                assert word(S['CamEntriesPointer'])==S['CamEntries']
                assert word(S['Module_List'])==0 and word(S['ROMModuleChain'])==0
                assert read(0,28)==struct.pack('<7I',*([0xe59fff88]*7))
                assert read(28,12)==struct.pack('<3I',0xe3a0a632,0xe5caa038,0xe25ef004)
                # Soft CAM is an original 4-byte packed entry per physical page.
                for ppn,a in enumerate(m['cam']):
                    logical=(a&0x7f8000)|((a&0xc00)<<13);ppl=(a>>8)&3
                    assert word(S['CamEntries']+ppn*4)==logical|(ppl<<28),(stage,ppn)
            if stage=='pre-module':
                assert word(S['MEMC_CR_SoftCopy'])==0x036e058c
                assert read(S['UniqueMachineID'],8)==bytes(8) and read(S['IOSystemType'],1)==b'\0'
                assert m['video']==1 and m['sound']==0
                finals.append(dict(memory_sha256=sha(m['ram']),cam_sha256=sha(struct.pack('<128I',*m['cam'])),ticks=m['ticks']))
            reports.append(dict(run=i,stage=stage,cam_descriptors_checked=8192,fixed_pages_checked=24,copies=copies,memc_cam_writes=m['counter']))
        # Compare all diagnostic section bytes, not just register summaries.
        checksums={p.name:sha(p.read_bytes()) for p in folder.glob('*.bin')}
        comparable=dict(stages=run['stages'],sections=checksums,hardware_writes=run['hardware_write_events'])
        if reference is None:reference=comparable
        else:assert comparable==reference,'cold runs differ'
    save('boot-verification.json',dict(status='PASS',cold_runs=3,all_checkpoint_registers_hardware_and_exported_state_identical=True,checks=reports,final_instructions=runs[0]['stages'][-1]['instructions'],final_ticks=runs[0]['stages'][-1]['ticks'],exception_counts=runs[0]['stages'][-1]['exceptions'],hardware_writes=runs[0]['hardware_write_events'],log_overflow=False,scope='Reset through entry to ModuleInit only; module initialisation has not executed.'))
    print('PASS: three identical cold boots, CAM/workspace/vector checks.')
if __name__=='__main__':verify()
