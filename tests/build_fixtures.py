#!/usr/bin/env python3
"""Original deterministic D/E and track-fault fixtures. SPDX-License-Identifier: Apache-2.0."""
import hashlib,json,pathlib,struct
from paths import ROOT,REPO,HOST;OUT=ROOT/'artifacts/discs';OUT.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
from adfs_fixture import pack,u24,directory,entry,oldcheck
def zonecheck(b):
 s=[0,0,0,0]
 for p in range(len(b)-4,0,-4):
  for i in range(4):prev=(i-1)%4;s[i]+=b[p+i]+(s[prev]>>8);s[prev]&=255
 s[0]+=s[3]>>8
 for i in range(1,4):s[i]+=b[i]+(s[i-1]>>8)
 return (s[0]^s[1]^s[2]^s[3])&255
def bits(b,start,width,value):
 assert value<(1<<width)
 for i in range(width):
  if value>>i&1:b[(start+i)//8]|=1<<((start+i)%8)
payload=bytes((i*37+(i>>7)*11+0x41)&255 for i in range(38895))
hello=pack(0xe28f0008,0xef000002,0xe3a00000,0xef000011)+b'NESTED ARM2 PROGRAM EXECUTED\r\n\0'
client=(ROOT/'artifacts/CheckFile.bin').read_bytes()
leaf=b'A leaf in the second nested directory.\r\n';sibling=b'Allocated separator between fragments.\r\n'
allreports=[]
for fmt in ('D','E'):
 for generation in ('A','B'):
  disc=bytearray(819200);roottext=('DISC '+generation+' -- same pathname, different media.\r\n').encode()
  files={'CheckFile':client,'Docs.Deep.Leaf':leaf,'Docs.Fragment':payload,'Docs.Sibling':sibling,'Hello':hello,'RootText':roottext,'Zero':b''}
  locations={};allocations=[]
  if fmt=='D':
   dirs={'$':0x400,'Docs':0xc00,'Docs.Deep':0x1400};nextoff=0x1c00
   for path,data in files.items():
    locations[path]=[(nextoff,max(1024,(len(data)+1023)&~1023))];nextoff+=locations[path][0][1]
   addresses={p:chunks[0][0]//256 for p,chunks in locations.items()};diraddr={p:o//256 for p,o in dirs.items()}
   u24(disc,0,nextoff//256);u24(disc,256,(819200-nextoff)//256);u24(disc,252,3200)
   name=('DTEST'+generation).ljust(10).encode()
   for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
   disc[507:509]=bytes([ord(generation),0x27]);disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
   signature=b'Hugo'
  else:
   # Object 6 is split by two other allocated objects, not by a synthetic read shim.
   specs=[(2,4096),(3,2048),(4,2048),(5,2048),(6,8192),(7,2048),(6,12288),(8,2048),(6,18432),(9,2048),(10,2048)]
   offset=0
   for object_id,length in specs:allocations.append(dict(id=object_id,offset=offset,length=length));offset+=length
   allocations+=[dict(id=0,offset=offset,length=819200-offset,free=True),dict(id=1,offset=819200,length=983040-819200)]
   dirs={'$':2048,'Docs':4096,'Docs.Deep':6144};diraddr={'$':0x203,'Docs':0x300,'Docs.Deep':0x400}
   addresses={'CheckFile':0xa00,'Docs.Deep.Leaf':0x900,'Docs.Fragment':0x600,'Docs.Sibling':0x700,'Hello':0x800,'RootText':0x502,'Zero':0x501}
   for path,a in addresses.items():
    obj=a>>8;skip=max(0,(a&255)-1)*1024;chunks=[]
    for alloc in allocations:
     if alloc['id']==obj:
      if skip>=alloc['length']:skip-=alloc['length'];continue
      chunks.append((alloc['offset']+skip,alloc['length']-skip));skip=0
    locations[path]=chunks
   zone=bytearray(1024);zone[3]=255;bits(zone,23,1,1) # FreeLink's terminating bit, required by SanityCheckNewMap.
   # Original FileCore definitions: double density=2; idlen=15; 128 bytes/map bit.
   zone[4:14]=bytes([10,5,2,2,15,7,0,0,0,1]);struct.pack_into('<H',zone,14,32)
   zone[16:24]=pack(0x203,819200);zone[24:26]=bytes([ord(generation),0x28]);zone[26:36]=('ETEST'+generation).ljust(10).encode()
   for alloc in allocations:
    start=512+alloc['offset']//128;width=alloc['length']//128;assert width>=16
    bits(zone,start,15,alloc['id']);bits(zone,start+width-1,1,1)
    if alloc.get('free'):bits(zone,8,15,start-8)
   zone[0]=zonecheck(zone);disc[:1024]=disc[1024:2048]=zone
   signature=b'Nick'
  rows=[]
  for path,data in files.items():
   remain=data;chunks=[]
   for off,size in locations[path]:
    part=remain[:size];disc[off:off+len(part)]=part;remain=remain[len(part):];chunks.append(dict(offset=off,allocated=size,data_bytes=len(part)))
   assert not remain
   load=0x10000 if path in ('Hello','CheckFile') else 0xffffff00;execute=0x10000 if path in ('Hello','CheckFile') else 0
   rows.append(dict(path=path,bytes=len(data),sha256=sha(data),load=load,execute=execute,attributes=17,address=addresses[path],chunks=chunks))
   p=OUT/(fmt+generation+'-'+path.replace('.','_'));p.write_bytes(data)
  rootentries=[entry('Docs',diraddr['Docs'],directory=True)]+[entry(p,addresses[p],files[p],load=(0x10000 if p in ('Hello','CheckFile') else 0xffffff00),execute=(0x10000 if p in ('Hello','CheckFile') else 0)) for p in ('CheckFile','Hello','RootText','Zero')]
  docentries=[entry('Deep',diraddr['Docs.Deep'],directory=True)]+[entry(p,addresses['Docs.'+p],files['Docs.'+p]) for p in ('Fragment','Sibling')]
  deepentries=[entry('Leaf',addresses['Docs.Deep.Leaf'],leaf)]
  for path,parent,entries in [('$','$',rootentries),('Docs','$',docentries),('Docs.Deep','Docs',deepentries)]:
   off=dirs[path];disc[off:off+2048]=directory(path.split('.')[-1],diraddr[parent],entries,signature)
  name=fmt+generation;image=OUT/(name+'.adf');image.write_bytes(disc)
  report=dict(name=name,format=fmt,generation=generation,sha256=sha(disc),files=rows,directories=dirs,allocations=allocations);allreports.append(report)
  if generation=='A':
   bad=bytearray(disc);bad[dirs['$']+2047]^=1;(OUT/(name+'-bad-directory.adf')).write_bytes(bad)
   if fmt=='E':
    bad=bytearray(disc);bad[0]^=1;bad[1024]^=1;(OUT/'EA-bad-maps.adf').write_bytes(bad)
    one=bytearray(disc);one[0]^=1;(OUT/'EA-first-map-bad.adf').write_bytes(one)
   # Track-level fault is in a file's data, beyond root/directory metadata.
   damaged=locations['Docs.Fragment'][0][0]//1024
   for fault in ('missing','id-crc','data-crc'):
    table=bytearray();sectors=bytearray();raw=bytearray(352)
    for track in range(160):
     table+=pack(len(sectors))
     for sector in range(5):
      logical=track*5+sector
      if logical==damaged and fault=='missing':continue
      flags=(0x10 if fault=='id-crc' else 0x20) if logical==damaged else 0
      sectors+=pack((sector*40<<24)|(2<<16)|(sector<<8)|3|flags,logical*1024)
     sectors+=pack(0xffffffff)
    raw[:4]=b'JFDI';struct.pack_into('<I',raw,4,1);struct.pack_into('<III',raw,24,352,352+len(table),352+len(table)+len(sectors))
    title=(name+' original '+fault+' fixture').encode();raw[48:48+len(title)]=title
    raw+=table+sectors+disc;struct.pack_into('<I',raw,8,len(raw));(OUT/(name+'-'+fault+'.jfd')).write_bytes(raw)
(OUT/'manifest.json').write_text(json.dumps(dict(status='GENERATED',images=allreports,files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(OUT.iterdir()) if p.name!='manifest.json'}),indent=2)+'\n')
print('Generated D/E nested, fragmented, replacement and corrupt-sector fixtures')
