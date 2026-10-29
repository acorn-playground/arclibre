#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compact tokenised BBC BASIC V programs for ROM storage.

New ArcLibre tool; it is not Acorn's proprietary squish. Three stages:

1. crunch(): an exact host model of BASIC V's CRUNCH command
   (src/BASIC/Expr CRUNCHROUTINE). Its output is checked against the
   original interpreter by tests/check_basic_squish.py.
2. rename(): shortens variable, array, PROC and FN names by frequency.
3. merge(): joins lines with ':' where BASIC's line structure allows it.

Leading line-0 REM lines (the licence notice) are kept byte for byte.
Programs whose names may be resolved at run time are refused.
"""
import string,struct,sys

TAND,TEOR,TELSE,TTHEN,TCONST=0x80,0x82,0x8B,0x8C,0x8D
TFN,TRND,TTO,TOF,TELSE2,TDATA,TDEF,TIF,TON,TPROC,TREM,TERROR=0xA4,0xB3,0xB8,0xCA,0xCC,0xDC,0xDD,0xE7,0xEE,0xF2,0xF4,0x85
TOTHER,TWHEN,TENDCA,TENDIF=0x7F,0xC9,0xCB,0xCD
ESCAPES={0xC6,0xC7,0xC8}
TEVAL,TCHAIN=0xA0,0xD7
BY_STATEMENTS={0xDF,0xEC}                              # DRAW, MOVE
# Escaped statement/command tokens that load or name code at run time.
RUNTIME_NAMES={(0xC8,0x9A),(0xC8,0x9B),(0xC8,0xA3)}   # INSTALL, LIBRARY, OVERLAY

def ident(c):
 """BASIC's LVTABLE zero entries: 0-9, A-Z, _, `, a-z."""
 return 48<=c<=57 or 65<=c<=90 or c==95 or c==96 or 97<=c<=122

def lines(data):
 """Yield (number, body) from a tokenised program (13,hi,lo,len,body...)."""
 p=0
 assert data[0]==13
 while data[p+1]!=0xff:
  length=data[p+3];assert length>=4 and data[p]==13
  yield data[p+1]*256+data[p+2],bytes(data[p+4:p+length]);p+=length
 assert p+2==len(data),'trailing data after program end'

def program(rows):
 out=bytearray()
 for number,body in rows:
  assert len(body)+4<=255,'line too long'
  out+=bytes([13,number>>8,number&255,len(body)+4])+body
 return bytes(out+b'\r\xff')

def crunch_line(body,bits,first):
 """Model of one CRUNCHSTART..CRUNCHENDSTMT2 pass; returns crunched body."""
 out=bytearray([0]);src=body+b'\r';i=0  # out[0] stands for the zeroed length byte
 def nextc():
  nonlocal i
  c=src[i];i+=1;return c
 while True:
  # CRUNCHSTART: leading spaces of a statement.
  c=nextc()
  while c==32:
   if not bits&1:out.append(c)
   c=nextc()
  if c in (42,TDATA):                                  # '*' or DATA: copy rest of line
   while c!=13:out.append(c);c=nextc()
  else:
   while True:                                          # CRUNCHITEMS
    if c==32:
     if not bits&2:out.append(c);c=nextc();continue
     while c==32:c=nextc()
     prev=out[-1];panic=False
     if prev==34 and c==34:panic=True
     elif prev in (36,37,TRND):panic=c in (40,33,63)
     elif prev in (TEOR,TAND):panic=ident(c)
     elif c in (33,63) and prev==41:panic=True
     elif not ident(prev) and prev!=46:panic=False
     elif ident(c) or c in (46,36):panic=True
     else:panic=c in (40,33,63)
     if panic:out.append(32)
    # CRUNCHNOTSPACE
    if c==TREM:
     if first or not bits&4:
      while c!=13:out.append(c);c=nextc()
      break
     while c!=13:c=nextc()
    if c==34:
     out.append(c);c=nextc()
     while c!=34 and c!=13:out.append(c);c=nextc()
     if c==13:break
     out.append(c);c=nextc();continue
    if c in (58,TELSE,TTHEN,13):
     if bits&8 and out[-1]==58:out.pop()
     break
    out.append(c);c=nextc()
  # CRUNCHENDSTMT2
  if c==13:return bytes(out[1:])
  out.append(c)

def crunch(data,bits=0x1f):
 rows=[];first=True
 for number,body in lines(data):
  body=crunch_line(body,bits,first);first=False
  if bits&16 and not body:continue
  rows.append((number,body))
 return program(rows)

def licence_split(data):
 rows=list(lines(data));n=0
 while n<len(rows) and rows[n][0]==0 and rows[n][1].lstrip(b' ')[:1] in (bytes([TREM]),b''):n+=1
 return rows[:n],rows[n:]

def scan(body):
 """Split a crunched line body into ('name',class,stem,suffix) and ('raw',bytes) items.

 Class is 'PROC', 'FN' or the variable suffix and array marker, e.g. '%(' ."""
 items=[];i=0;start=True;n=len(body)
 def raw(b):items.append(('raw',bytes(b)))
 while i<n:
  c=body[i]
  if start and c==32:raw(body[i:i+1]);i+=1;continue
  if start and c in (42,TDATA):raw(body[i:]);break
  start=False
  if c==TREM:raw(body[i:]);break
  if c==34:
   j=body.find(b'"',i+1);j=n if j<0 else j+1;raw(body[i:j]);i=j;continue
  if c in (58,TELSE,TTHEN):raw(body[i:i+1]);i+=1;start=True;continue
  if c in ESCAPES:
   assert (c,body[i+1]) not in RUNTIME_NAMES,'program loads named code at run time'
   raw(body[i:i+2]);i+=2;continue
  if c==TCONST:raw(body[i:i+4]);i+=4;continue
  assert c not in (TEVAL,TCHAIN),'program resolves names at run time'
  assert not (c==91),'assembler statements are not renamed'
  if c==TTO and i+1<n and body[i+1]==80:raw(body[i:i+2]);i+=2;continue   # TOP
  # DRAW, MOVE, FILL and POINT read a relative 'BY' as plain letters
  # (src/BASIC/Stmt2 PLOTER1); it is syntax, not a variable.
  if c in BY_STATEMENTS or (c==0xC8 and i+1<n and body[i+1] in (0x90,0x92)):
   j=i+(2 if c==0xC8 else 1)
   while j<n and body[j]==32:j+=1
   if body[j:j+2]==b'BY':raw(body[i:j+2]);i=j+2;continue
  if c in (TPROC,TFN):
   j=i+1
   while j<n and ident(body[j]):j+=1
   raw(body[i:i+1]);items.append(('name','PROC' if c==TPROC else 'FN',bytes(body[i+1:j]),b''));i=j;continue
  if c==38:                                            # &hex
   j=i+1
   while j<n and (48<=body[j]<=57 or 65<=body[j]<=70 or 97<=body[j]<=102):j+=1
   raw(body[i:j]);i=j;continue
  if c==37 and i+1<n and body[i+1] in (48,49):         # %binary
   j=i+1
   while j<n and body[j] in (48,49):j+=1
   raw(body[i:j]);i=j;continue
  if 48<=c<=57 or c==46:                               # decimal, optional exponent
   j=i
   while j<n and (48<=body[j]<=57 or body[j]==46):j+=1
   if j<n and body[j] in (69,101) and j+1<n and (48<=body[j+1]<=57 or body[j+1] in (43,45)):
    j+=2
    while j<n and 48<=body[j]<=57:j+=1
   raw(body[i:j]);i=j;continue
  if ident(c):
   j=i
   while j<n and ident(body[j]):j+=1
   k=j
   if k<n and body[k] in (36,37):k+=1
   bracket=k<n and body[k]==40
   stem=bytes(body[i:j]);suffix=bytes(body[j:k])
   items.append(('name',suffix.decode()+('(' if bracket else ''),stem,suffix));i=k;continue
  raw(body[i:i+1]);i+=1
 return items

def resident(cls,stem):
 return cls=='%' and len(stem)==1 and 64<=stem[0]<=90

def new_names():
 first=string.ascii_lowercase;rest=first+string.digits+'_'
 for a in first:yield a
 for a in first:
  for b in rest:yield a+b
 for a in first:
  for b in rest:
   for c in rest:yield a+b+c

def rename(rows):
 counts={}
 for _,body in rows:
  for it in scan(body):
   if it[0]=='name' and not resident(it[1],it[2]):
    counts[(it[1],it[2])]=counts.get((it[1],it[2]),0)+1
 mapping={};generators={}
 # Most frequent names, weighted by length saved, get the shortest names
 # within each independent namespace.
 for (cls,stem),cnt in sorted(counts.items(),key=lambda kv:(-kv[1]*len(kv[0][1]),kv[0])):
  g=generators.setdefault(cls,new_names())
  mapping[(cls,stem)]=next(g).encode()
 out=[]
 for number,body in rows:
  o=bytearray()
  for it in scan(body):
   if it[0]=='raw':o+=it[1]
   else:
    cls,stem,suffix=it[1],it[2],it[3]
    o+=(stem if resident(cls,stem) else mapping[(cls,stem)])+suffix
  out.append((number,bytes(o)))
 return out,{f'{c}:{s.decode()}':v.decode() for (c,s),v in mapping.items()}

# Tokens which must begin a line (multi-line IF/CASE structure, DEF, WHILE end).
LINE_START={TOTHER,TWHEN,TENDCA,TELSE,TELSE2,TENDIF,TDEF,0xCE}
TWHILE=bytes([0xC8,0x95])
def structural(body):
 """True if the line's structure depends on its own line boundaries."""
 b=bytes(body)
 return (TIF in b or TOF in b or TDATA in b or TCONST in b or bytes([TON,TERROR]) in b
         or b[:1]==b'*' or TWHILE in b)

def merge(rows):
 out=[]
 for number,body in rows:
  if out and body[0] not in LINE_START and not structural(body) and not structural(out[-1][1]) \
     and not out[-1][1].endswith(bytes([TTHEN])) and len(out[-1][1])+1+len(body)+4<=255:
   out[-1]=(out[-1][0],out[-1][1]+b':'+body)
  else:out.append((number,body))
 return out

def squish(data):
 licence,body=licence_split(data)
 crunched=list(lines(crunch_rows(body)))
 renamed,mapping=rename(crunched)
 merged=merge(renamed)
 return program(licence+merged),mapping

def crunch_rows(rows):
 """Crunch body lines (not the first program line) exactly as CRUNCH -1 would."""
 out=[]
 for number,body in rows:
  body=crunch_line(body,0x1f,False)
  if body:out.append((number,body))
 return program(out)

if __name__=='__main__':
 import json
 src,dst=sys.argv[1:3]
 data,mapping=squish(open(src,'rb').read())
 open(dst,'wb').write(data)
 if len(sys.argv)>3:open(sys.argv[3],'w').write(json.dumps(mapping,indent=1,sort_keys=True)+'\n')
