# SPDX-License-Identifier: Apache-2.0
"""Normalise GCCSDK AOF assembly sections for AsAsm."""
import re

def original_unchecked_prologues(s, functions=None):
 """Apply an original Norcroft -s1 region to GCCSDK's APCS prologues.

 GCCSDK ignores that pragma. Keep its frame, SL/static-base convention and
 allocation unchanged; omit only the recursive stack-extension check. Callers
 must identify an original unchecked region, never use this for ordinary code.
 """
 changed=[]
 pattern=r'(^\|([^|]+)\|\n(?:\tKEEP[^\n]*\n)?\t; args =[^\n]*\n)(.*?)(?=^\|[^|]+\|\n(?:\tKEEP[^\n]*\n)?\t; args =|\Z)'
 def function(m):
  name=m[2];body=m[3]
  if functions is not None and name not in functions:return m[0]
  check=re.search(r'\tcmp\t(sp|ip), sl\n\tblmi\t\|__rt_stkovf_split_(small|big)\|\n',body)
  if check is None:return m[0]
  # Only a compiler-generated entry prologue may precede the check.
  for line in body[:check.start()].splitlines():
   assert re.match(r'^\t(;|mov\tip, sp$|stmfd\tsp!,|sub\t(fp, ip,|ip, sp,)|sfmfd\t|(?:mov|ldr)\t[av][0-9],)',line),(name,line)
  changed.append(name)
  return m[1]+body[:check.start()]+'\t; Original Norcroft -s1: no recursive stack-extension check\n'+body[check.end():]
 result=re.sub(pattern,function,s,flags=re.M|re.S)
 assert changed,'expected original unchecked prologues'
 if functions is not None:assert set(changed)==set(functions),(changed,functions)
 return result,changed

def normalise(s):
 def area(m):
  name,attrs=m[1],m[2]
  if 'CODE' in attrs:return '\tAREA |C$$code|, CODE, READONLY\n\tALIGN'
  if 'READONLY' in attrs:return '\tAREA |C$$rodata|, DATA, READONLY\n\tALIGN'
  return '\tAREA |C$$data|, DATA\n\tALIGN'+ ('\n|'+name+'|' if 'COMMON' in attrs else '')
 return re.sub(r'^\s*AREA\s+\|([^|]+)\|([^\n]*)',area,s,flags=re.M)
