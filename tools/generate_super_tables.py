#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 1996 Acorn Computers Ltd (original generator algorithms).
# Host port of Acorn Computers' Apache-2.0 GenMatrix1/GenMatrix2 generators.
# Original tokenised BASIC programs and their notices remain under src/Super.
"""Generate the original SuperSampler tables from their actual BASIC formulas.

Only the original timestamp comment is replaced with a deterministic comment.
The version >=5 reverse 511..1 table (with no zero entry) is intentional.
"""
import hashlib,json,pathlib,re,sys
from paths import SRC
def lines(name):
 b=(SRC/'Super'/name).read_bytes();p=0;out={}
 manifest=json.loads((SRC.parent/'manifests/desktop-inputs.json').read_text());row=next(r for r in manifest if r['component']=='Super' and r['path']==name)
 assert hashlib.sha256(b).hexdigest()==row['upstream_sha256']
 while p<len(b)-1:
  assert b[p]==13
  if b[p+1]==255:break
  number=b[p+1]*256+b[p+2];length=b[p+3];assert length>=4 and p+length<=len(b)
  if number:out[number]=b[p+4:p+length]
  p+=length
 assert b[p:p+2]==b'\r\xff'
 return out
def coefficients(expression):
 # BBC BASIC's FN token is &A4. Parse only the original sum-of-weighted-bits.
 terms=expression.removeprefix(b'y%=').split(b'+');weights=[]
 for i,term in enumerate(terms):
  m=re.fullmatch(rb'(?:(\d+)\*)?\xa4bit\((\d+)\)',term);assert m and int(m[2])==i,term
  weights.append(int(m[1] or b'1'))
 return weights
def table(weights,indices):return [sum(w*((x>>i)&1) for i,w in enumerate(weights)) for x in indices]
def rows(values):return ''.join('        DCB '+','.join('&%02X'%v for v in values[i:i+16])+'\n' for i in range(0,len(values),16))
def generate(out):
 one,two=lines('GenMatrix1,ffb'),lines('GenMatrix2,ffb')
 assert one[120]==b'\xe3 x%=0 \xb8 127' and two[130]==b'\xe3 x%=511 \xb8 1 \x88 -1' and two[230]==two[330]==b'\xe3 x%=0 \xb8 511'
 assert one[260]==two[470]==b'\xdd \xa4bit(b%) = (x%>>b%)\x801'
 weights1=coefficients(one[130]);weights2=coefficients(two[140]);assert weights2==coefficients(two[240]);weights3=coefficients(two[340])
 t1=table(weights1,range(128));rev=table(weights2,range(511,0,-1));forward=table(weights2,range(512));t2=table(weights3,range(512))
 # Independently documented 7x7 bilinear weighting and the original optimized
 # horizontal/vertical kernels; zero/full inputs and complement symmetry.
 assert weights1==[1,2,3,4,3,2,1] and weights2==[1,2,4,6,6,6,4,2,1] and weights3==[1,4,8,12,13,12,8,4,1]
 for t,total in [(t1,16),(forward,32),(t2,63)]:assert t[0]==0 and t[-1]==total and all(a+b==total for a,b in zip(t,reversed(t)))
 out.mkdir(parents=True,exist_ok=True)
 prefix='; Generated from original Acorn GenMatrix BASIC formulas; deterministic host port.\n'
 (out/'Matrix1').write_text(prefix+'LookupTable\n'+rows(t1)+'        END\n')
 (out/'Matrix2').write_text(prefix+'        [ Version >= 5\n'+rows(rev)+'        |\nLookupTable1\n'+rows(forward)+'        ]\nLookupTable2\n'+rows(t2)+'        END\n')
 return dict(status='PASS',matrix1_bytes=len(t1),matrix2_current_bytes=len(rev)+len(t2),weights=[weights1,weights2,weights3],table_sha256=[hashlib.sha256(bytes(x)).hexdigest() for x in [t1,rev,forward,t2]])
if __name__=='__main__':print(json.dumps(generate(pathlib.Path(sys.argv[1])),indent=2))
