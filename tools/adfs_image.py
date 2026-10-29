# SPDX-License-Identifier: Apache-2.0
"""Write an 800K ADFS D (old map) floppy image holding a tree of directories and files.

The layout follows tools/build_alarm_disc.py: $ at &400, each directory 2048
bytes, files 1 KiB aligned, one free-space entry after the last file.
A tree maps names to dicts (directories) or File tuples.
"""
import collections,sys
from paths import REPO
sys.path.insert(0,str(REPO/'tests'))
from adfs_fixture import u24,directory,entry,oldcheck
File=collections.namedtuple('File','data filetype attributes',defaults=[0xfff,0x11])
SIZE=819200
def image(tree,title,disc_id,stamp):
 """Return (image bytes, rows) for tree; stamp is the files' datestamp in centiseconds since 1900."""
 disc=bytearray(SIZE);offset=0xc00;rows=[]
 def place(path,node,parent):
  nonlocal offset
  if isinstance(node,dict):
   address=offset;offset+=2048;entries=[]
   for name in sorted(node,key=str.lower):
    child=place(path+'.'+name,node[name],address)
    entries.append(child)
   assert len(entries)<=47,path
   disc[address:address+2048]=directory(path.rsplit('.',1)[-1],parent//256,entries,b'Hugo')
   return entry(path.rsplit('.',1)[-1],address//256,directory=True)
  data=bytes(node.data);assert offset+len(data)<=SIZE,'disc full'
  disc[offset:offset+len(data)]=data
  e=entry(path.rsplit('.',1)[-1],offset//256,data,load=0xfff00000|(node.filetype<<8)|(stamp>>32),execute=stamp&0xffffffff);e['attributes']=node.attributes
  rows.append(dict(path=path,filetype='&%03X'%node.filetype,bytes=len(data),sector=offset//256))
  offset+=(len(data)+1023)&~1023;return e
 entries=[]
 for name in sorted(tree,key=str.lower):entries.append(place('$.'+name,tree[name],0x400))
 assert len(entries)<=47
 disc[0x400:0xc00]=directory('$',4,entries,b'Hugo')
 u24(disc,0,offset//256);u24(disc,256,(SIZE-offset)//256);u24(disc,252,3200)
 t=title.encode().ljust(10)[:10]
 for i in range(5):disc[247+i]=t[2*i];disc[502+i]=t[2*i+1]
 disc[507:509]=disc_id;disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
 return bytes(disc),rows
