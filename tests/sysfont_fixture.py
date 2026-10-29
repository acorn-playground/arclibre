# SPDX-License-Identifier: Apache-2.0
"""Read printed VDU 5 text back as system font characters, for the printing gates.

The glyphs are the kernel's own 8 x 8 system font (src/Kernel/s/vdu/vdufontl1,
characters 32-127). VDU 5 text in the default mode is 16 x 32 OS units a
character, so a font pixel is 2 x 4 OS units. Given the printed black dots,
the dots per OS unit and the text's top-left corner, read_text samples each
font pixel at its centre and names the character whose glyph matches exactly.
find_text places that grid over a block of printed text: it tries corners up
to 4 OS units left of and 1 OS unit above or below the block's top-left dot,
a quarter dot apart, and returns the first reading in which every character
matches a glyph.
"""
import math,pathlib,re
SOURCE=pathlib.Path(__file__).resolve().parents[1]/'src/Kernel/s/vdu/vdufontl1'
def system_font():
 text=SOURCE.read_text(encoding='latin1');body=text[text.index('HardFont'):]
 rows=[[int(v,16) for v in re.findall(r'&([0-9A-Fa-f]{2})',l.split(';')[0])] for l in body.splitlines()[1:97]]
 assert len(rows)==96 and all(len(r)==8 for r in rows);return {chr(32+i):tuple(r) for i,r in enumerate(rows)}
def read_text(black,left,top,dx,dy,count,down=True):
 """Characters printed at left/top (dots), dx/dy dots per OS unit; rows go down the page if down."""
 font={v:k for k,v in system_font().items()};out=''
 for n in range(count):
  glyph=[]
  for row in range(8):
   y=top+(row*4+2)*dy if down else top-(row*4+2)*dy
   glyph.append(sum(0x80>>col for col in range(8) if (math.floor(left+(n*16+col*2+1)*dx),math.floor(y)) in black))
  out+=font.get(tuple(glyph),'?')
 return out
def find_text(black,dx,dy,count,down=True):
 xs=[x for x,_ in black];ys=[y for _,y in black];x0=min(xs);y0=min(ys) if down else max(ys)+1
 for i in range(int(16*dx)+1):
  for j in range(-int(4*dy),int(4*dy)+1):
   left=x0-i/4;top=y0+j/4;t=read_text(black,left,top,dx,dy,count,down)
   if '?' not in t:return t,(left,top)
 return None,None
