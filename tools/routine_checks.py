#!/usr/bin/env python3
"""Bounded tests of emitted kernel routines, not ROM/emulator boot testing.
Small independent ARM interpreter; unsupported instructions fail closed.
Apache-2.0. No MacArch implementation or ROM bytes are used.
"""
import json,struct
from inspect_image import ROOT,load_aof,load_symbols
MASK=0xffffffff
class Machine:
    def __init__(self,image):
        self.image=image;self.base=0x3800000;self.r=[0]*16;self.pc=0;self.psr=3
        self.memory={};self.writes=[];self.reads=[]
    def read(self,address,size=4):
        self.reads.append((address,size))
        if self.base<=address<self.base+len(self.image):
            return int.from_bytes(self.image[address-self.base:address-self.base+size],'little')
        assert address in self.memory,hex(address)
        return self.memory[address]&((1<<(8*size))-1)
    def condition(self,c):
        n,z,carry,v=[bool(self.psr&b) for b in [1<<31,1<<30,1<<29,1<<28]]
        return [z,not z,carry,not carry,n,not n,v,not v,carry and not z,not carry or z,n==v,n!=v,not z and n==v,z or n!=v,True,False][c]
    def reg(self,n,psr=False):return ((self.pc+8)|(self.psr if psr else 0)) if n==15 else self.r[n]
    def shifted(self,w):
        if w&(1<<25):
            n=((w>>8)&15)*2;v=w&255
            return ((v>>n)|(v<<(32-n)))&MASK if n else v
        v=self.reg(w&15,True);kind=(w>>5)&3
        n=(self.r[(w>>8)&15]&255) if w&16 else ((w>>7)&31)
        if w&16 and n==0:return v
        if kind==0:return (v<<n)&MASK if n<32 else 0
        if kind==1:return v>>(n or 32) if n<32 else 0
        if kind==2:
            signed=v-(1<<32) if v&(1<<31) else v
            return (signed>>min(n or 32,32))&MASK
        if not n:return ((self.psr>>29)&1)<<31 | v>>1
        n%=32;return ((v>>n)|(v<<(32-n)))&MASK if n else v
    def run(self,start,stops,limit=5000):
        self.pc=start
        for step in range(limit):
            if self.pc in stops:return step
            w=self.read(self.pc);following=(self.pc+4)&0x3ffffff
            if not self.condition(w>>28):self.pc=following;continue
            group=(w>>25)&7;rn=(w>>16)&15;rd=(w>>12)&15
            if group==5:
                imm=w&0xffffff;imm=imm-0x1000000 if imm&0x800000 else imm
                if w&(1<<24):self.r[14]=(self.pc+4)|self.psr
                following=(self.pc+8+imm*4)&0x3ffffff
            elif group in (0,1):
                assert not (group==0 and w&0x90==0x90),'multiply/extension not needed by fixture'
                op=(w>>21)&15;a=self.reg(rn);b=self.shifted(w);carry=(self.psr>>29)&1
                values={0:a&b,1:a^b,2:a-b,3:b-a,4:a+b,5:a+b+carry,6:a-b-1+carry,7:b-a-1+carry,8:a&b,9:a^b,10:a-b,11:a+b,12:a|b,13:b,14:a&~b,15:~b}
                value=values[op]&MASK;test=op in (8,9,10,11)
                if test and rd==15:self.psr=value&0xfc000003
                elif w&(1<<20):
                    self.psr=(self.psr&0x3fffffff)|(value&0x80000000)|(0x40000000 if value==0 else 0)
                    if op in (2,3,10,4,11):
                        aa,bb=(b,a) if op==3 else (a,b)
                        subtract=op in (2,3,10)
                        c=aa>=bb if subtract else aa+bb>MASK
                        v=((aa^bb)&(aa^value)&0x80000000)!=0 if subtract else (~(aa^bb)&(aa^value)&0x80000000)!=0
                        self.psr=(self.psr&~0x30000000)|(c<<29)|(v<<28)
                if not test:
                    if rd==15:
                        following=value&0x3fffffc
                        if w&(1<<20):self.psr=value&0xfc000003
                    else:self.r[rd]=value
            elif group in (2,3):
                base=self.reg(rn);offset=(w&4095) if group==2 else self.shifted(w&~(1<<25))
                updated=(base+offset if w&(1<<23) else base-offset)&MASK
                address=updated if w&(1<<24) else base
                size=1 if w&(1<<22) else 4
                if w&(1<<20):
                    value=self.read(address,size)
                    if rd==15:following=value&0x3fffffc
                    else:self.r[rd]=value
                else:
                    value=self.reg(rd,True)&((1<<(8*size))-1)
                    self.memory[address]=value;self.writes.append((address,value,size))
                if not w&(1<<24) or w&(1<<21):self.r[rn]=updated
            else:raise AssertionError(('unsupported fixture instruction',hex(self.pc),hex(w)))
            self.pc=following
        raise AssertionError('fixture instruction bound exceeded')

def checks():
    image=load_aof(ROOT/'artifacts/kernel.aof')['data'];s=load_symbols();value=lambda n:s[n]['value']
    total=0
    # Independent direct bit placement, rather than using the kernel's tables.
    for index in range(4):
        for ppn in range(128):
            for logical in [0,0x8000,0x1c00000,0x1f00000,0x1f80000]:
                for ppl in [0,1,2,3]:
                    m=Machine(image);m.r[2]=ppn;m.r[3]=logical;m.r[9]=index*4;m.r[11]=ppl;m.r[14]=0x100
                    m.run(value('BangCam'),{0x100})
                    physical=[ppn&255,(ppn&128)|((ppn&64)>>6)|((ppn&63)<<1),(ppn&128)|((ppn&96)>>5)|((ppn&31)<<2),((ppn&256)<<4)|(ppn&128)|((ppn&64)>>5)|((ppn&32)>>3)|((ppn&16)>>4)|((ppn&15)<<3)][index]
                    expected=0x3800000|physical|((logical&0x1800000)>>13)|(logical&0x7fffff&~((1<<(12+index))-1))|(ppl<<8)
                    assert m.writes==[(expected,expected,4)],(index,ppn,logical,ppl,m.writes,hex(expected))
                    total+=1
    # Packed soft CAM update uses one word per page, not ARM600's two words.
    m=Machine(image);m.r[2]=17;m.r[3]=0x1c00000;m.r[9]=12;m.r[11]=0;m.r[14]=0x100
    m.memory[value('CamEntriesPointer')]=0x164
    m.run(value('BangCamUpdate'),{0x100})
    assert m.writes[0]==(0x164+17*4,0x1c00000,4) and len(m.writes)==2
    # Reset's original packed entries: page zero, heap and write-protected cursor.
    cam_initialisations=0
    for page_size in [4096,8192,16384,32768]:
        for logical,ppl in [(0,0),(0x1c00000,0),(0x1f00000,1)]:
            m=Machine(image);m.r[0]=0x2000;m.r[1]=0x2000;m.r[2]=logical;m.r[7]=32768//page_size*4;m.r[8]=page_size;m.r[14]=0x100
            m.run(value('AddCamEntries'),{0x100})
            assert m.writes==[(0x2000+i*4,(logical+i*page_size)|(ppl<<28),4) for i in range(32768//page_size)]
            cam_initialisations+=1
    # Query success exits at the real shared SWI return entry. No service/module
    # is substituted; this fixture stops at that routine boundary.
    query_results=[]
    for reason in [2,3,4,5]:
        m=Machine(image);m.r=[0x11110000+i for i in range(16)];m.r[0]=reason
        m.memory[value('UniqueMachineID')]=0;m.memory[value('UniqueMachineID')+4]=0;m.memory[value('IOSystemType')]=0
        m.run(value('ReadSysInfo_Code'),{value('SLVK')})
        count=5 if reason in (2,3) else 2
        assert m.r[:count]==[0]*count,(reason,m.r)
        assert not m.writes
        assert not any(0x3000000<=address<0x3800000 for address,size in m.reads),'unexpected hardware access'
        query_results.append(dict(reason=reason,returned_registers=m.r[:count],hardware_accesses=0))
    report=dict(status='PASS',scope='bounded emitted-routine tests; no ROM boot or emulator modification',cam_encoding_cases=total,packed_cam_update_cases=1,cam_initialisation_cases=cam_initialisations,hardware_queries=query_results)
    (ROOT/'artifacts/routine-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':checks()
