#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check tools/basic_squish.py against the original interpreter and itself.

1. Stage 1 must reproduce BASIC 1.14's own CRUNCH output. The lengths and
   rotate-xor hashes below were computed by the ROM's BASIC module running
   in MacArch (TEXTLOAD, CRUNCH n, then hashing PAGE..TOP-1).
2. A squished program must be the original statement stream once spaces,
   REMs, line breaks and the recorded renaming are accounted for. This
   scanner is deliberately separate from the one used to rename.
"""
import hashlib,json,pathlib,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
import basic_squish

ORACLE={
 'Alarm/bas/!RunImage,ffb':{0x1f:(98993,0xc9e53478),0x0b:(128698,0xf2147d71)},
 'Alarm/bas/AlarmSrc,ffb':{0x1f:(8910,0xc2d993f7),0x0f:(9090,0x6f016e45)},
}
def rothash(b):
 h=0
 for x in b:h=((h<<5|h>>27)&0xffffffff)^x
 return h

# Words BASIC reads from plain letters in context rather than as tokens
# (src/BASIC/Stmt2 PLOTER1: DRAW/MOVE/FILL/POINT BY). They must never be renamed.
CONTEXT_WORDS={'BY'}
def relative(body,i,cur):
 j=i
 while j<len(body) and body[j]==32:j+=1
 if body[j:j+2]==b'BY':cur.append(('tok',b'BY'));return j+2
 return i

def statements(data,mapping,skip_licence):
 """Flatten a program into statements of comparable items."""
 rows=list(basic_squish.lines(data))
 if skip_licence:rows=rows[len(basic_squish.licence_split(data)[0]):]
 out=[];cur=[]
 def end():
  nonlocal cur
  if cur:out.append(tuple(cur))
  cur=[]
 for _,body in rows:
  i=0;n=len(body);start=True
  while i<n:
   c=body[i]
   if c==32 and (start or not cur or cur[-1][0]!='rest'):i+=1;continue
   if start and c in (42,0xDC):cur.append(('rest',body[i:].rstrip(b' ')));break
   start=False
   if c==0xF4:break
   if c==34:
    j=body.find(b'"',i+1);j=n if j<0 else j+1;cur.append(('str',body[i:j]));i=j;continue
   if c in (58,0x8B,0x8C):
    if c!=58:end();out.append((('sep',c),))
    end();i+=1;start=True;continue
   if c in (0xC6,0xC7,0xC8):
    cur.append(('tok',body[i:i+2]));i+=2
    if c==0xC8 and body[i-1] in (0x90,0x92):i=relative(body,i,cur)   # FILL, POINT
    continue
   if c in (0xDF,0xEC):cur.append(('tok',bytes([c])));i=relative(body,i+1,cur);continue   # DRAW, MOVE
   if c in (0xF2,0xA4):
    j=i+1
    while j<n and basic_squish.ident(body[j]):j+=1
    kind='PROC' if c==0xF2 else 'FN';name=body[i+1:j].decode()
    cur.append(('tok',bytes([c])));cur.append(('name',kind,mapping.get(f'{kind}:{name}',name)));i=j;continue
   if c==38 or (48<=c<=57) or c==46 or (c==37 and i+1<n and body[i+1] in b'01'):
    j=i+1
    while j<n and (basic_squish.ident(body[j]) or body[j]==46) and not (c!=38 and 97<=body[j]<=122):j+=1
    cur.append(('num',body[i:j]));i=j;continue
   if basic_squish.ident(c):
    j=i
    while j<n and basic_squish.ident(body[j]):j+=1
    k=j+(1 if j<n and body[j] in b'$%' else 0)
    cls=body[j:k].decode()+('(' if k<n and body[k]==40 else '');stem=body[i:j].decode()
    cur.append(('name',cls,mapping.get(f'{cls}:{stem}',stem)+body[j:k].decode()));i=k;continue
   cur.append(('tok',bytes([c])));i+=1
  end()
 return out

def check(path,data=None):
 if data is None:data=source(path)
 for bits,(length,h) in ORACLE.get(path,{}).items():
  c=basic_squish.crunch(data,bits);assert (len(c),rothash(c))==(length,h),(path,bits,len(c),hex(rothash(c)))
 squished,mapping=basic_squish.squish(data)
 assert not [k for k in mapping if k.split(':',1)[1] in CONTEXT_WORDS],'context syntax renamed as a variable'
 licence=basic_squish.licence_split(data)[0]
 assert list(basic_squish.lines(squished))[:len(licence)]==licence,'licence lines changed'
 a=statements(data,mapping,True);b=statements(squished,{},True)
 assert a==b,next((i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y)
 for cls in {k.split(':')[0] for k in mapping}:
  new=[v for k,v in mapping.items() if k.split(':')[0]==cls];assert len(set(new))==len(new),cls
 return dict(path=path,original_bytes=len(data),squished_bytes=len(squished),sha256=hashlib.sha256(squished).hexdigest(),names=len(mapping),statements=len(a),crunch_oracle_cases=len(ORACLE.get(path,{})))

def source(path):
 component,rel=path.split('/',1)
 return (REPO/'src'/component/rel).read_bytes()

if __name__=='__main__':
 report=[check(p) for p in sys.argv[1:]]
 print(json.dumps(report,indent=2))
