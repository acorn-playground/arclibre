# SPDX-License-Identifier: Apache-2.0
"""Read a single-zone new-map ADFS floppy (E format) from its bytes.

Written from the documented structures (PRM FileCore chapter): zone check
byte, disc record, the allocation bitstream after the disc record (idlen-bit
fragment IDs ended by a set bit, 2^log2bpmb bytes per bit), the free-space
chain from FreeLink, and 'Nick' directories. It shares no code with FileCore
or with the fixture writer in build_fixtures.py.
"""
import struct

def zone_check(zone):
 s=[0,0,0,0]
 for p in range(len(zone)-4,0,-4):
  for i in range(4):
   prev=(i-1)%4;s[i]+=zone[p+i]+(s[prev]>>8);s[prev]&=255
 s[0]+=s[3]>>8
 for i in range(1,4):s[i]+=zone[i]+(s[i-1]>>8)
 return (s[0]^s[1]^s[2]^s[3])&255

def bit(zone,n):return zone[n//8]>>(n%8)&1

def read(disc):
 secsize=1024;zone=disc[:secsize]
 assert disc[secsize:2*secsize]==zone,'both map copies agree'
 assert zone_check(zone)==zone[0],'zone check byte'
 rec=dict(log2secsize=zone[4],secspertrack=zone[5],heads=zone[6],density=zone[7],idlen=zone[8],log2bpmb=zone[9],skew=zone[10],
  bootoption=zone[11],lowsector=zone[12],nzones=zone[13],zone_spare=struct.unpack_from('<H',zone,14)[0],root=struct.unpack_from('<I',zone,16)[0],
  disc_size=struct.unpack_from('<I',zone,20)[0],disc_id=struct.unpack_from('<H',zone,24)[0],name=zone[26:36].rstrip(b' \0').decode('latin-1'))
 assert rec['log2secsize']==10 and rec['nzones']==1
 idlen=rec['idlen'];bpmb=1<<rec['log2bpmb'];first=8*4+60*8 # after the zone header and disc record
 end=first+rec['disc_size']//bpmb
 # Fragments: an idlen-bit ID, then zeros up to and including a set bit.
 frags=[];p=first
 while p<end:
  fid=sum(bit(zone,p+i)<<i for i in range(idlen));q=p+idlen
  while not bit(zone,q):q+=1
  frags.append(dict(start=p,id=fid,offset=(p-first)*bpmb,length=(q+1-p)*bpmb));p=q+1
 assert p==end,'fragments tile the disc exactly'
 # Free space: FreeLink (bits 8-22 of the zone header) is the bit offset from
 # bit 8 to the first free fragment; each free fragment's ID field is the
 # offset from it to the next (0 ends the chain).
 free=set();link=sum(bit(zone,8+i)<<i for i in range(15));here=8
 while link:
  here+=link;f=next(f for f in frags if f['start']==here);free.add(here);link=f['id']
 for f in frags:f['free']=f['start'] in free
 return rec,frags

def locate(frags,address,secsize=1024):
 """Byte offset of an indirect disc address (fragment ID, sector offset)."""
 fid=address>>8;skip=max(0,(address&255)-1)*secsize
 for f in frags:
  if f['id']==fid and not f['free']:
   if skip<f['length']:return f['offset']+skip
   skip-=f['length']
 raise AssertionError(('no fragment',hex(address)))

def directory(disc,offset,size=2048):
 d=disc[offset:offset+size];assert d[1:5]==d[size-5:size-1]==b'Nick' and d[0]==d[size-6],'Nick directory'
 rows={};p=5
 while d[p]:
  name=bytes(x&127 for x in d[p:p+10]).split(b'\0')[0].split(b'\r')[0].decode('latin-1')
  load,execute,length=struct.unpack_from('<III',d,p+10)
  rows[name]=dict(load=load,execute=execute,length=length,address=int.from_bytes(d[p+22:p+25],'little'),attributes=d[p+25]);p+=26
 return rows
