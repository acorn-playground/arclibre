#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent bounded D/E decoder for generated-media write verification.

Uses FileCore/Doc/{OldMaps,EMaps,Dirs}. No emulator reader or fixture allocator.
Only the milestone's 800 KiB, 1024-byte-sector, one-zone E layout is supported.
"""
import struct

def le(b,p,n=4):return int.from_bytes(b[p:p+n],'little')
def old_sum(b):
 total=0
 for value in b[::-1]:total=(total&255)+value+(total>>8)
 return total&255

def zone_sum(b):
 sums=[0,0,0,0]
 for word in range(len(b)-4,0,-4):
  for lane in range(4):
   previous=(lane+3)%4
   sums[lane]+=b[word+lane]+(sums[previous]>>8);sums[previous]&=255
 sums[0]+=sums[3]>>8
 for lane in range(1,4):sums[lane]+=b[lane]+(sums[lane-1]>>8)
 return (sums[0]^sums[1]^sums[2]^sums[3])&255

def dir_sum(b,end):
 values=[le(b,p) for p in range(0,end//4*4,4)]
 values+=list(b[end//4*4:end])
 values+=[le(b,p) for p in range(2008,2044,4)]
 acc=0
 for v in values:acc=v^((acc>>13)|((acc&8191)<<19))
 return (acc^(acc>>8)^(acc>>16)^(acc>>24))&255

class Disc:
 def __init__(self,data):
  self.data=data;assert len(data)==819200
  self.files={};self.directories={};self.fragments=[];self.free=[];self.used=[]
  if data[1025:1029]==b'Hugo':
   self.format='D';root=4
   assert old_sum(data[:255])==data[255] and old_sum(data[256:511])==data[511],'old map check bytes'
   assert le(data,252,3)*256==len(data) and data[510]<=246 and data[510]%3==0
   end=1024
   for p in range(0,data[510],3):
    start,size=le(data,p,3)*256,le(data,256+p,3)*256
    assert size>0 and start>=end and start+size<=len(data),'old free list bounds/order'
    self.free.append((start,size));end=start+size
   self.used.append((0,1024,'<map>'))
  else:
   self.format='E';zone=data[:1024]
   assert zone==data[1024:2048],'map copies agree'
   assert zone_sum(zone)==zone[0] and zone[3]==255,'zone/cross checks'
   assert zone[4:10]==bytes([10,5,2,2,15,7]) and zone[13]==1 and le(zone,14,2)==32
   assert le(zone,20)==len(data);root=le(zone,16)
   def bits(p,n):return sum(((zone[(p+i)//8]>>((p+i)%8))&1)<<i for i in range(n))
   free=set();p=8;link=bits(p,15)
   while link:
    assert link>=16 and p+link<8192,'free chain bounds/progression'
    p+=link;free.add(p);link=bits(p,15)
   p=512;seen=set()
   while p<8192:
    start=p;identifier=bits(p,15);p+=15
    while p<8192 and not bits(p,1):p+=1
    assert p<8192,'unterminated fragment'
    p+=1;offset=(start-512)*128;size=(p-start)*128
    if start in free:
     assert offset+size<=len(data);self.free.append((offset,size));seen.add(start)
    else:
     assert identifier!=0
     if offset+size>len(data):assert identifier==1,'only bad/spare object beyond disc'
     self.fragments.append((identifier,offset,size))
   assert seen==free,'free chain points to fragment starts'
   self.used.append((0,2048,'<maps>'))
  self.walk(root,'$',root,0)
  for start,size,name in self.used:
   assert start>=0 and start+size<=len(data),(name,'allocated range')
   assert all(start+size<=f or start>=f+n for f,n in self.free),(name,'overlaps free space')
  ordered=sorted(self.used)
  for left,right in zip(ordered,ordered[1:]):assert left[0]+left[1]<=right[0],('overlapping objects',left,right)
  self.free_bytes=sum(n for _,n in self.free)

 def chunks(self,address,length):
  if length==0:return []
  if self.format=='D':return [(address*256,length)]
  identifier=address>>8;skip=max(0,(address&255)-1)*1024;out=[]
  for obj,start,size in self.fragments:
   if obj!=identifier:continue
   if skip>=size:skip-=size;continue
   take=min(length,size-skip);out.append((start+skip,take));length-=take;skip=0
   if length==0:return out
  assert False,('unresolved object',hex(address),length)

 def fetch(self,address,length,name):
  allocated=(length+1023)//1024*1024
  for start,size in self.chunks(address,allocated):self.used.append((start,size,name))
  out=b''.join(self.data[p:p+n] for p,n in self.chunks(address,length))
  assert len(out)==length
  return out

 def walk(self,address,path,parent,depth):
  assert depth<8 and path not in self.directories,'directory cycle'
  b=self.fetch(address,2048,path);signature=b'Hugo' if self.format=='D' else b'Nick'
  assert b[1:5]==b[2043:2047]==signature and b[0]==b[2042],'directory signatures/sequence'
  assert le(b,2010,3)==parent,'directory parent'
  p=5;rows=[]
  while p<2007 and b[p]:
   raw=b[p:p+10];name=bytes(x for x in raw if x>=32).decode('ascii')
   assert name and '.' not in name
   load,execute,size=struct.unpack_from('<III',b,p+10);ind=le(b,p+22,3);attr=b[p+25]
   rows.append((name,load,execute,size,ind,attr));p+=26
  assert p<=2007 and b[p]==0 and dir_sum(b,p)==b[-1],'directory terminator/check byte'
  assert [x[0].upper() for x in rows]==sorted(set(x[0].upper() for x in rows)),'directory order/uniqueness'
  self.directories[path]={'address':address,'sequence':b[0],'names':[r[0] for r in rows]}
  for name,load,execute,size,ind,attr in rows:
   here=name if path=='$' else path+'.'+name
   if attr&8:
    assert size==2048;self.walk(ind,here,address,depth+1)
   else:self.files[here]={'data':self.fetch(ind,size,here),'load':load,'execute':execute,'attributes':attr,'address':ind}
