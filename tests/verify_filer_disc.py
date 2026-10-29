# SPDX-License-Identifier: Apache-2.0
"""Independent checks of file data, metadata, directory and free-space writes."""
import hashlib,pathlib,struct
from adfs_fixture import oldcheck

def read_directory(b,address):
 d=b[address*256:address*256+2048];assert d[1:5]==d[2043:2047]==b'Hugo' and d[0]==d[2042]
 rows={};end=5
 while d[end]:
  p=end;name=bytes(x&127 for x in d[p:p+10]).split(b'\0')[0].split(b'\r')[0].decode();load,execute,length=struct.unpack_from('<III',d,p+10);sector=int.from_bytes(d[p+22:p+25],'little');attrs=d[p+25]
  rows[name]=dict(load=load,execute=execute,length=length,address=sector,attributes=attrs);end+=26;assert end<=2007
 acc=0
 def step(v,a):return v^((a>>13)|((a<<19)&0xffffffff))
 for p in range(0,end&~3,4):acc=step(struct.unpack_from('<I',d,p)[0],acc)
 for p in range(end&~3,end):acc=step(d[p],acc)
 for p in range(2008,2044,4):acc=step(struct.unpack_from('<I',d,p)[0],acc)
 assert d[-1]==(acc^(acc>>8)^(acc>>16)^(acc>>24))&255,'directory checksum'
 return rows

def verify(path,operation):
 b=pathlib.Path(path).read_bytes();root=pathlib.Path(__file__).resolve().parents[1];original=(root/'build/filer-action-disc/actions.adf').read_bytes();payload=(root/'build/filer-action-disc/CopyMe').read_bytes()
 assert len(b)==len(original)==819200
 assert b[255]==oldcheck(b[:255]) and b[511]==oldcheck(b[256:511]),'free-map checksum'
 files=read_directory(b,4);dest=read_directory(b,12)
 assert set(files)==({'CopyMe','Dest'} if operation=='copy' else {'Dest'})
 assert set(dest)==({'CopyMe'} if operation in ['copy','move'] else set())
 source=read_directory(original,4)['CopyMe'];used=[(0,0x1400)]
 for entries in [files,dest]:
  if 'CopyMe' in entries:
   row=entries['CopyMe'];assert all(row[k]==source[k] for k in ['load','execute','length','attributes'])
   start=row['address']*256;assert b[start:start+row['length']]==payload
   used.append((start,start+((len(payload)+1023)&~1023)))
 used.sort();assert all(a[1]<=z[0] for a,z in zip(used,used[1:]))
 free=[];assert b[510]%3==0
 for p in range(0,b[510],3):
  start=int.from_bytes(b[p:p+3],'little')*256;length=int.from_bytes(b[256+p:259+p],'little')*256
  assert length>0 and start%1024==0 and length%1024==0 and start+length<=len(b)
  assert all(start+length<=u or start>=v for u,v in used);free.append((start,start+length))
 assert all(a[1]<=z[0] for a,z in zip(free,free[1:]));assert sum(v-u for u,v in used+free)==len(b),'allocated/free space accounted for'
 return dict(status='PASS',operation=operation,sha256=hashlib.sha256(b).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest(),root=files,destination=dest,free_bytes=sum(v-u for u,v in free))
if __name__=='__main__':
 import json,sys
 print(json.dumps(verify(sys.argv[1],sys.argv[2]),indent=2))
