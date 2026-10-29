# SPDX-License-Identifier: Apache-2.0
"""Decode the HP PCL raster graphics PDumperLJ sends, for the printing gates.

An independent decoder of the PCL 4/5 commands a LaserJet dumper uses: ESC E
(reset), ESC & l / ESC & a (page setup and margins, recorded), ESC * t #R
(raster resolution), ESC * p #X/#Y (cursor position in 300 dpi units), ESC * r
#S/#A/B (raster width, start, end), ESC * b #M (compression: 0 unencoded,
1 run-length, 2 TIFF PackBits), ESC * b #W (a row of data), ESC * b #Y (skip
rows) and form feed. Anything else is an error. Returns the black dots as a
set of (column, row) at the raster resolution, with column 0 and row 0 at the
raster's start position, and the commands in order.
"""
import re
PARAM=re.compile(rb'\x1b([!-/])([`-~])((?:[-+]?[0-9.]*[`-~])*)([-+]?[0-9.]*)([@-^])')
def unpack(row,mode):
 if mode==0:return row
 out=bytearray();i=0
 if mode==1:   # (count-1, byte) pairs
  while i+1<len(row):out+=bytes([row[i+1]])*(row[i]+1);i+=2
  return bytes(out)
 assert mode==2,'compression mode %d'%mode
 while i<len(row):
  n=row[i];i+=1
  if n<128:out+=row[i:i+n+1];i+=n+1
  elif n>128:out+=bytes([row[i]])*(257-n);i+=1
 return bytes(out)
def pcl(data):
 dots=set();commands=[];i=0;y=0;mode=0;raster=False;resolution=75;width=None;start=None;cursor=[0,0]
 while i<len(data):
  c=data[i]
  if c==27 and data[i+1:i+2]==b'E':commands.append('E');i+=2;mode=0;continue
  if c==12:commands.append('FF');i+=1;continue
  m=PARAM.match(data,i);assert m,'unexpected byte %d at %d'%(c,i)
  group=(m.group(1)+m.group(2)).decode();i=m.end()
  parts=re.findall(rb'([-+]?[0-9.]*)([`-~@-^])',m.group(3)+m.group(4)+m.group(5))
  for value,term in parts:
   op=group+term.decode().upper();v=float(value) if value else 0
   if op=='*bW':
    n=int(v);row=unpack(data[i:i+n],mode);i+=n;assert raster,'row outside raster graphics'
    assert width is None or len(row)*8<=width or not any(row[(width+7)//8:]),'row wider than the raster'
    for k,b in enumerate(row):
     for bit in range(8):
      if b&(0x80>>bit):dots.add((k*8+bit,y))
    y+=1;commands.append('*bW')
   elif op=='*bM':mode=int(v);commands.append('*b%dM'%mode)
   elif op=='*bY':y+=int(v);commands.append('*bY')
   elif op=='*tR':resolution=int(v);commands.append('*t%dR'%resolution)
   elif op=='*rS':width=int(v);commands.append('*r%dS'%width)
   elif op=='*rA':raster=True;start=tuple(cursor);y=0;commands.append('*r%dA'%int(v))
   elif op in ('*rB','*rC'):raster=False;commands.append(op)
   elif op=='*pX':cursor[0]=int(v);commands.append('*pX')
   elif op=='*pY':cursor[1]=int(v);commands.append('*pY')
   elif op[:2] in ('&l','&a'):commands.append(op[:2]+('%g'%v)+op[2])
   else:raise AssertionError('unknown PCL command '+op)
 return dots,commands,dict(resolution=resolution,width=width,start=start)
