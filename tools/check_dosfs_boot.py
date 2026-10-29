#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent checks of ArcLibre's DOSFS default boot sector.

check(sector, formats) verifies every BPB field of the 512-byte template and
of the sector DOSFS_LayoutStructure derives from it for each format in
DOSFS's own tables (read from the linked module, not from the C source), and
executes the x86 boot code in a deliberately tiny real-mode model that knows
only the instructions a non-system message loop needs. Anything else (an
unknown opcode, a memory write outside the stack, a disk read) fails.
"""
import struct

def bpb(s):
 f=dict(jump=s[0:3],oem=s[3:11],bytes_per_sector=struct.unpack_from('<H',s,11)[0],sectors_per_cluster=s[13],
  reserved=struct.unpack_from('<H',s,14)[0],fats=s[16],root_entries=struct.unpack_from('<H',s,17)[0],
  total_sectors=struct.unpack_from('<H',s,19)[0],media=s[21],sectors_per_fat=struct.unpack_from('<H',s,22)[0],
  sectors_per_track=struct.unpack_from('<H',s,24)[0],heads=struct.unpack_from('<H',s,26)[0],hidden=struct.unpack_from('<H',s,28)[0],
  signature=s[510:512])
 return f

def fat12_consistent(f):
 """The BPB describes a valid FAT12 volume whose FATs can map every cluster."""
 assert f['bytes_per_sector']==512 and f['reserved']==1 and f['fats']==2 and f['hidden']==0,f
 assert f['sectors_per_cluster'] in (1,2,4,8,16,32,64,128)
 assert (f['root_entries']*32)%512==0 and f['root_entries']>0
 root=f['root_entries']*32//512
 data=f['total_sectors']-f['reserved']-f['fats']*f['sectors_per_fat']-root
 clusters=data//f['sectors_per_cluster']
 assert 0<clusters<4085,'FAT12 cluster count'
 assert (clusters+2)*3//2+((clusters+2)&1)<=f['sectors_per_fat']*512,'FAT too small'
 assert f['media']>=0xF0 and f['sectors_per_track']>0 and f['heads'] in (1,2)
 assert f['total_sectors']%(f['sectors_per_track']*f['heads'])==0,'whole cylinders'
 assert f['signature']==b'\x55\xaa'
 return dict(clusters=clusters,root_sectors=root,first_data_sector=f['reserved']+f['fats']*f['sectors_per_fat']+root)

def run_x86(sector,cs=0,ip=0x7C00,int19_returns=False,limit=10000):
 """Execute from CS:IP with the sector at 0000:7C00. Returns the BIOS calls."""
 mem=bytearray(0x100000);mem[0x7C00:0x7E00]=sector
 r=dict(ax=0x1234,bx=0,cx=0,dx=0,si=0,di=0,sp=0x400,bp=0);seg=dict(cs=cs,ds=0x40,ss=0x30,es=0);zf=False;df=True;intr=True
 out=[];calls=[];writes=set()
 def lin(s,o):return ((s<<4)+(o&0xffff))&0xfffff
 def fetch():
  nonlocal ip
  b=mem[lin(seg['cs'],ip)];ip=(ip+1)&0xffff;return b
 R16=['ax','cx','dx','bx','sp','bp','si','di'];SREG=['es','cs','ss','ds']
 def get8(i):return (r[R16[i&3]]>>(8 if i>=4 else 0))&255
 def set8(i,v):
  k=R16[i&3];r[k]=(r[k]&(0x00ff if i>=4 else 0xff00))|((v&255)<<(8 if i>=4 else 0))
 for step in range(limit):
  op=fetch()
  if op==0xFA:intr=False
  elif op==0xFB:intr=True
  elif op==0xFC:df=False
  elif op==0x90:pass
  elif op in (0x31,0x30,0x08):
   m=fetch();assert m>>6==3,'register operands only';d,s=m&7,(m>>3)&7
   if op==0x31:v=r[R16[d]]^r[R16[s]];r[R16[d]]=v;zf=v==0
   elif op==0x30:v=get8(d)^get8(s);set8(d,v);zf=v==0
   else:v=get8(d)|get8(s);set8(d,v);zf=v==0
  elif op==0x8E:
   m=fetch();assert m>>6==3;seg[SREG[(m>>3)&3]]=r[R16[m&7]]
   assert (m>>3)&3!=1,'MOV CS is not used'
  elif 0xB8<=op<=0xBF:lo=fetch();hi=fetch();r[R16[op-0xB8]]=lo|hi<<8
  elif 0xB0<=op<=0xB7:set8(op-0xB0,fetch())
  elif op==0xAC:
   assert not df;set8(0,mem[lin(seg['ds'],r['si'])]);r['si']=(r['si']+1)&0xffff
  elif op in (0xEB,0x74):
   d=fetch();d-=256 if d>127 else 0
   if op==0xEB or zf:ip=(ip+d)&0xffff
  elif op==0xCD:
   n=fetch();calls.append(n);ah=r['ax']>>8
   if n==0x10:
    assert ah==0x0E and r['bx']>>8==0,'teletype output, page 0';out.append(r['ax']&255)
   elif n==0x16:
    assert ah==0,'wait for a key';r['ax']=0x1C0D
   elif n==0x19:
    if not int19_returns:return dict(text=bytes(out).decode('ascii'),calls=calls,ended='INT 19h',stack=(seg['ss'],r['sp']),interrupts_enabled=intr,steps=step+1)
   else:raise AssertionError('unexpected interrupt %02X'%n)
  elif op==0xF4:return dict(text=bytes(out).decode('ascii'),calls=calls,ended='HLT',steps=step+1)
  else:raise AssertionError('unmodelled opcode %02X at %04X'%(op,(ip-1)&0xffff))
 raise AssertionError('no end within %d instructions'%limit)

MESSAGE='\r\nNon-system disc: ArcLibre DOSFS data disc.\r\nThere is no operating system on it.\r\nRemove it and press a key to restart.\r\n'

def check(sector,formats,formatinfo):
 """sector: the 512-byte template. formats/formatinfo: DOSFS's tables."""
 assert len(sector)==512
 f=bpb(sector)
 assert f['jump'][0]==0xEB and f['jump'][2]==0x90;start=2+f['jump'][1];assert 0x3E<=start<0x1FE
 assert all(32<=c<127 for c in f['oem']) and f['oem']==b'ARCLIBRE'
 # Template values are the DOS/M (720K) ones.
 assert (f['sectors_per_cluster'],f['root_entries'],f['total_sectors'],f['media'],f['sectors_per_fat'],f['sectors_per_track'],f['heads'])==(2,112,1440,0xF9,3,9,2),f
 template=fat12_consistent(f)
 assert sector[0x1C:start]==bytes(start-0x1C),'no hidden/32-bit totals or extended BPB'
 runs=[]
 for cs,ip in [(0,0x7C00),(0x07C0,0)]:
  x=run_x86(sector,cs,ip);assert x['text']==MESSAGE and x['calls']==[0x10]*len(MESSAGE)+[0x16,0x19] and x['interrupts_enabled'],x;runs.append(x)
  assert x['stack']==(0,0x7C00-0)
 y=run_x86(sector,int19_returns=True);assert y['ended']=='HLT' and y['text']==MESSAGE
 # The sector DOSFS_LayoutStructure writes for each format (same field
 # assignments as c/DOSFS), checked as a complete FAT12 BPB.
 derived=[]
 for fm in formats:
  if fm['id']=='PCMCIA':continue  # size supplied by the caller at format time
  fi=formatinfo[fm['findex']];s=bytearray(sector)
  maxsect=fi['secstrk']*fi['tracks']
  s[13]=fm['secsclus'];s[17]=fm['rootsize'];s[19]=maxsect&255;s[20]=maxsect>>8;s[21]=fm['magic'];s[24]=fi['secstrk'];s[25]=0;s[22]=fm['secsFAT']
  s[26]=2 if fi['options']&(3<<2) in (0,3<<2) else 1
  if fm['id'].startswith('Atari'):s[0]=0
  g=bpb(bytes(s))
  if s[0]==0:g['jump']=b'\xeb\x00\x90'
  info=fat12_consistent(g)
  derived.append(dict(format=fm['id'],total_sectors=g['total_sectors'],sectors_per_cluster=g['sectors_per_cluster'],sectors_per_fat=g['sectors_per_fat'],
   root_entries=g['root_entries'],media='&%02X'%g['media'],heads=g['heads'],sectors_per_track=g['sectors_per_track'],**info))
 return dict(status='PASS',template=dict((k,v.hex() if isinstance(v,bytes) else v) for k,v in f.items()),template_layout=template,
  boot_code_start=start,boot_message=MESSAGE,x86_runs=[dict(entry='%04X:%04X'%e,ended=x['ended'],instructions=x['steps']) for e,x in zip([(0,0x7C00),(0x07C0,0)],runs)],
  if_int19_returns='HLT loop',formats=derived)

def tables(image,symbols,base=0):
 """Read DOSFS's s/StaticDefs format tables from a linked image."""
 def cstr(a):o=a-base;return image[o:image.index(0,o)].decode()
 formats=[];o=symbols['func_DOS_formats']
 while struct.unpack_from('<I',image,o)[0]:
  p,findex,menu,magic,spc,fat,root=struct.unpack_from('<I6B',image,o)
  formats.append(dict(id=cstr(p),findex=findex,in_menu=menu,magic=magic,secsclus=spc,secsFAT=fat,rootsize=root));o+=12
 info=[];o=symbols['func_DOS_formatinfo']
 while struct.unpack_from('<I',image,o)[0]:
  secsize,g0,g1,g3=struct.unpack_from('<4I',image,o);b=image[o+16:o+24];tracks=struct.unpack_from('<I',image,o+24)[0]
  info.append(dict(secsize=secsize,secstrk=b[0],density=b[1],options=b[2],startsec=b[3],tracks=tracks));o+=64
 return formats,info
