# SPDX-License-Identifier: Apache-2.0
"""Decode the Epson FX-80 commands PDumperDM sends, for the printing gates."""
def epson(data):
 """Decode the FX-80 commands PDumperDM sends into a set of (column, dot) at 120 x 72 dpi."""
 dots=set();x=0;y=0;spacing=12;i=0;commands=[]
 while i<len(data):
  c=data[i]
  if c==27:
   op=data[i+1]
   if op in b'LK*':
    if op==ord('*'):mode=data[i+2];i+=1
    n=data[i+2]|data[i+3]<<8;cols=data[i+4:i+4+n];assert len(cols)==n
    step={ord('L'):1,ord('K'):2}.get(op,1)
    for k,v in enumerate(cols):
     for bit in range(8):
      if v&(0x80>>bit):dots.add((x+k*step,y+bit))
    x+=n*step;commands.append(chr(op));i+=4+n
   elif op==ord('A'):spacing=data[i+2];commands.append('A%d'%spacing);i+=3
   elif op==ord('C'):commands.append('C%d'%data[i+2]);i+=3
   elif op==ord('J'):y+=data[i+2]*72//216;i+=3
   elif op==ord('@'):commands.append('@');i+=2
   else:raise AssertionError('unknown ESC %r at %d'%(chr(op),i))
  elif c==10:y+=spacing;i+=1
  elif c==13:x=0;i+=1
  elif c==12:commands.append('FF');i+=1
  else:raise AssertionError('unexpected byte %d at %d'%(c,i))
 return dots,commands
