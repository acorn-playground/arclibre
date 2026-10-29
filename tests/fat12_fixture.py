# SPDX-License-Identifier: Apache-2.0
"""Independent host FAT12/FAT16 volume writer and strict parser for DOSFS tests.

Written from the published FAT layout (boot sector BPB, two FAT copies of
12-bit entries, or 16-bit ones from 4,085 clusters, a fixed root directory
and cluster chains) and the PC partition table, not from DOSFS.
The parser checks the volume as a whole: both FATs equal, media byte in FAT
entry 0, every chain well formed, no cross-linked or lost clusters, sizes
matching chain lengths and "." / ".." entries in subdirectories.
"""
import struct

GEOMETRY_720K=dict(total=1440,spc=2,reserved=1,fats=2,root_entries=112,media=0xF9,fat_sectors=3,spt=9,heads=2)
GEOMETRY_1440K=dict(total=2880,spc=1,reserved=1,fats=2,root_entries=224,media=0xF0,fat_sectors=9,spt=18,heads=2)
GEOMETRY_360K=dict(total=720,spc=2,reserved=1,fats=2,root_entries=112,media=0xFD,fat_sectors=2,spt=9,heads=2)
# A 4 MB hard disc partition: 8,192 sectors of 512 bytes, one per cluster, so FAT16.
GEOMETRY_FAT16_4M=dict(total=8160,spc=1,reserved=1,fats=2,root_entries=512,media=0xF8,fat_sectors=32,spt=32,heads=4,hidden=32)

def fat_bits(g):
 data=g['reserved']+g['fats']*g['fat_sectors']+g['root_entries']*32//512
 return 12 if (g['total']-data)//g['spc']<4085 else 16

def boot_sector(g,oem=b'HOSTFAT '):
 s=bytearray(512)
 s[0:3]=b'\xeb\x3c\x90';s[3:11]=oem
 struct.pack_into('<HBHBHHBHHHH',s,11,512,g['spc'],g['reserved'],g['fats'],g['root_entries'],g['total'],g['media'],g['fat_sectors'],g['spt'],g['heads'],g.get('hidden',0))
 s[0x3E:0x41]=b'\xf4\xeb\xfd'  # HLT loop: not a system disc
 s[510:512]=b'\x55\xaa';return bytes(s)

def dos_time(y,mo,d,h,mi,s):return ((h<<11)|(mi<<5)|(s//2)),(((y-1980)<<9)|(mo<<5)|d)

def name83(name):
 base,_,ext=name.partition('.');assert 0<len(base)<=8 and len(ext)<=3,name
 return (base.ljust(8)+ext.ljust(3)).encode('ascii')

def make(files,label=None,g=GEOMETRY_720K,stamp=(2026,10,1,12,30,0)):
 """files: {path: bytes or None for a directory}, paths use '/' as separator."""
 img=bytearray(g['total']*512);img[0:512]=boot_sector(g)
 nfat=g['fat_sectors']*512;bits=fat_bits(g);eoc=(1<<bits)-1;fat=[0]*(nfat*8//bits)
 fat[0]=(eoc&~0xFF)|g['media'];fat[1]=eoc
 root_sector=g['reserved']+g['fats']*g['fat_sectors'];root_size=g['root_entries']*32
 data_sector=root_sector+root_size//512;cluster_bytes=g['spc']*512
 clusters=(g['total']-data_sector)//g['spc'];nxt=[2]
 def alloc(n):
  first=nxt[0];chain=list(range(first,first+n));nxt[0]+=n;assert nxt[0]<=clusters+2
  for a,b in zip(chain,chain[1:]+[eoc]):fat[a]=b
  return chain
 def coff(c):return (data_sector+(c-2)*g['spc'])*512
 t,d=dos_time(*stamp)
 def entry(nm,attr,first,size):return name83(nm)+struct.pack('<B10xHHHI',attr,t,d,first,size)
 dirs={'':[]}
 if label:dirs[''].append(label.ljust(11).encode()[:11]+struct.pack('<B10xHHHI',0x08,t,d,0,0))
 # Directories first so their clusters exist, then files.
 order=sorted(files,key=lambda p:(files[p] is not None,p.count('/'),p))
 dircluster={'':0}
 for path in order:
  parent,_,leaf=path.rpartition('/');content=files[path]
  if content is None:
   chain=alloc(1);dircluster[path]=chain[0];dirs[path]=[b'.'.ljust(11)+struct.pack('<B10xHHHI',0x10,t,d,chain[0],0),b'..'.ljust(11)+struct.pack('<B10xHHHI',0x10,t,d,dircluster[parent],0)]
   dirs[parent].append(entry(leaf,0x10,chain[0],0))
  else:
   n=(len(content)+cluster_bytes-1)//cluster_bytes;chain=alloc(n) if n else []
   for i,c in enumerate(chain):piece=content[i*cluster_bytes:(i+1)*cluster_bytes];img[coff(c):coff(c)+len(piece)]=piece
   dirs[parent].append(entry(leaf,0x20,chain[0] if chain else 0,len(content)))
 for path,ents in dirs.items():
  blob=b''.join(ents)
  if path=='':assert len(blob)<=root_size;img[root_sector*512:root_sector*512+len(blob)]=blob
  else:assert len(blob)<=cluster_bytes;o=coff(dircluster[path]);img[o:o+len(blob)]=blob
 packed=bytearray(nfat)
 if bits==16:packed[:]=b''.join(v.to_bytes(2,'little') for v in fat)
 else:
  for i in range(0,len(fat)-1,2):
   v=fat[i]|(fat[i+1]<<12);packed[i*3//2:i*3//2+3]=v.to_bytes(3,'little')
 for k in range(g['fats']):o=(g['reserved']+k*g['fat_sectors'])*512;img[o:o+nfat]=packed
 return bytes(img)

class Volume:
 def __init__(self,img):
  self.img=img;s=img[:512]
  (self.bps,self.spc,self.reserved,self.fats,self.root_entries,self.total,self.media,self.fat_sectors,self.spt,self.heads,self.hidden)=struct.unpack_from('<HBHBHHBHHHH',s,11)
  assert s[0] in (0xEB,0xE9) and s[510:512]==b'\x55\xaa','boot sector'
  assert self.bps==512 and self.reserved>=1 and self.fats>=1 and self.spc>0 and self.total*512<=len(img)
  self.boot=s;self.oem=s[3:11]
  fats=[img[(self.reserved+k*self.fat_sectors)*512:(self.reserved+(k+1)*self.fat_sectors)*512] for k in range(self.fats)]
  assert all(f==fats[0] for f in fats),'FAT copies differ'
  raw=fats[0];self.root_sector=self.reserved+self.fats*self.fat_sectors
  self.data_sector=self.root_sector+self.root_entries*32//512;self.clusters=(self.total-self.data_sector)//self.spc
  self.bits=12 if self.clusters<4085 else 16;top=(1<<self.bits)-1;self.bad=top-8;self.last=top-7
  self.fat=[]
  for i in range(self.clusters+2):
   if self.bits==16:self.fat.append(int.from_bytes(raw[i*2:i*2+2],'little'));continue
   v=int.from_bytes(raw[i*3//2:i*3//2+2],'little');self.fat.append(v>>4 if i&1 else v&0xFFF)
  assert self.fat[0]==(top&~0xFF)|self.media and self.fat[1]>=self.last,'reserved FAT entries'
  self.used={};self.tree={};self.label=None
  self._walk(self._root(),'',None)
  for c in range(2,self.clusters+2):
   if self.fat[c] not in (0,self.bad):assert c in self.used,'lost cluster %d'%c
  self.free=sum(1 for c in range(2,self.clusters+2) if self.fat[c]==0)
 def _root(self):o=self.root_sector*512;return self.img[o:o+self.root_entries*32]
 def chain(self,first,owner):
  out=[];c=first
  while True:
   assert 2<=c<self.clusters+2,('bad cluster',owner,c);assert c not in self.used,('cross-linked',owner,self.used.get(c));self.used[c]=owner;out.append(c)
   n=self.fat[c]
   if n>=self.last:return out
   assert n not in (0,1,self.bad),('chain break',owner,c,n);c=n
 def cdata(self,c):o=(self.data_sector+(c-2)*self.spc)*512;return self.img[o:o+self.spc*512]
 def _walk(self,blob,path,cluster):
  for i in range(0,len(blob),32):
   e=blob[i:i+32]
   if e[0]==0:break
   if e[0]==0xE5:continue
   attr=e[11];name=e[0:8].decode('latin1').rstrip();ext=e[8:11].decode('latin1').rstrip()
   first,size=struct.unpack_from('<HI',e,26);t,d=struct.unpack_from('<HH',e,22)
   if attr&0x08:
    assert path=='' and self.label is None;self.label=(name+ext).rstrip();continue
   full=name+('.'+ext if ext else '')
   if full in ('.','..'):
    assert attr&0x10 and path;assert first==(cluster if full=='.' else self.tree[path]['parent_cluster']),('dot entry',path,full);continue
   key=(path+'/' if path else '')+full
   info=dict(attr=attr,first=first,size=size,time=t,date=d,parent=path)
   if attr&0x10:
    chain=self.chain(first,key);info.update(chain=chain,parent_cluster=cluster or 0);self.tree[key]=info
    sub=b''.join(self.cdata(c) for c in chain);self._walk(sub,key,first)
   else:
    chain=self.chain(first,key) if first else []
    cb=self.spc*512;assert len(chain)==(size+cb-1)//cb,('size/chain',key,size,len(chain))
    info.update(chain=chain,data=b''.join(self.cdata(c) for c in chain)[:size]);self.tree[key]=info
 def files(self):return {k:v['data'] for k,v in self.tree.items() if 'data' in v}
 def dirs(self):return sorted(k for k,v in self.tree.items() if v['attr']&0x10)

def partitioned(volume,start=32,kind=0x04,heads=4,spt=32):
 """A hard disc image: a PC partition table (one bootable entry) and the volume at sector start."""
 n=len(volume)//512
 def chs(lba):c,r=divmod(lba,heads*spt);h,sct=divmod(r,spt);return bytes([h,((c>>2)&0xC0)|(sct+1),c&0xFF])
 mbr=bytearray(512);mbr[0x1BE:0x1CE]=bytes([0x80])+chs(start)+bytes([kind])+chs(start+n-1)+struct.pack('<II',start,n);mbr[510:512]=b'\x55\xaa'
 return bytes(mbr)+bytes((start-1)*512)+volume

def partition(img):
 """The volume of a partitioned image's first entry, checked against its boot sector."""
 assert img[510:512]==b'\x55\xaa','partition table signature'
 e=img[0x1BE:0x1CE];start,n=struct.unpack_from('<II',e,8);assert e[0] in (0,0x80) and n
 v=Volume(img[start*512:(start+n)*512]);assert v.total==n and v.hidden==start,(v.total,n,v.hidden,start);return v
