# SPDX-License-Identifier: Apache-2.0
"""!System and !Scrap, the two applications a RISC OS 3.1 hard disc needs.

RISC OS 3.11 users got them on the Applications disc; neither is in the ROM,
which sets none of their variables. ArcLibre's are new, set up as Acorn's
were (their !System 0.56 and !Scrap 0.58, January 1992): the Filer runs each
!Boot the first time it shows the directory holding it, and !Boot sets a
variable only if it isn't set already, so the first one seen is used;
double-clicking one (its !Run) makes it the one used.

- !System: System$Dir and System$Path, for modules applications share in
  System:Modules. Installers (Acorn C/C++'s, for example) add theirs to
  <System$Dir>.Modules, so it must be somewhere writable.
- !Scrap: Wimp$ScrapDir and Wimp$Scrap, where applications put a document
  while passing it to another, and other temporary files.

The obey files and help are in src/ArcLibre/system; the icons are drawn here,
34 by 34 square pixels in the Wimp's 16 colours, and written as sprite files:
!Sprites (mode 12, every other row) and !Sprites22 (mode 20).
"""
import struct
from paths import SRC
from adfs_image import File

def system_icon(x,y):
 """A chip: a black package with grey legs above and below, a notch at one corner and a white mark."""
 if 5<=x<=28 and 9<=y<=24:
  if x in (5,28) or y in (9,24):return '6'
  if x-5+y-9<4:return '4'
  if 12<=y<=16 and 14<=x<=19:return '0' if y in (12,16) or x in (14,19) else '7'
  return '7'
 if 7<=x<=26 and (x-7)%4<2 and (4<=y<=8 or 25<=y<=29):return '2'
 return '.'

def scrap_icon(x,y):
 """A sheet of paper, its top right corner turned down, with lines of writing."""
 left,right,top,bottom,fold=6,27,2,31,8
 if not (left<=x<=right and top<=y<=bottom):return '.'
 cut=right-fold+(y-top)
 if y-top<fold and x>cut:return '.'
 if y-top<fold and x==cut:return '7'
 if y-top==fold and x>=right-fold:return '7'
 if y-top<fold and right-fold<x<cut:return '2'
 if x in (left,right) or y in (top,bottom) or (y-top<fold and x==right-fold):return '7'
 if top+fold+1<y<bottom-2 and (y-top)%3==0 and left+2<x<right-2-(5 if y%2==0 else 0):return '4'
 return '0'

def rows(icon):return [''.join(icon(x,y) for x in range(34)) for y in range(34)]

def sprite_file(name,mode,pixels):
 """A sprite file (a sprite area without its first word): one 16-colour sprite with a mask.
 Each string in pixels is a row of hex Wimp colours; '.' is transparent."""
 width=max(map(len,pixels));words=(width*4+31)//32;image=mask=b''
 for row in pixels:
  i=bytearray(words*4);m=bytearray(words*4)
  for x,c in enumerate(row.ljust(width,'.')):
   if c=='.':continue
   i[x//2]|=int(c,16)<<(4*(x%2));m[x//2]|=0xF<<(4*(x%2))
  image+=bytes(i);mask+=bytes(m)
 header=44
 sprite=struct.pack('<I',header+len(image)+len(mask))+name.encode()[:12].ljust(12,b'\0')
 sprite+=struct.pack('<7I',words-1,len(pixels)-1,0,(width*4-1)%32,header,header+len(image),mode)+image+mask
 return struct.pack('<3I',1,16,16+len(sprite))+sprite

def tree():
 """{'!System': {...}, '!Scrap': {...}} in tools/adfs_image.py's form, with empty Modules and ScrapDir."""
 out={}
 for app,icon,extra in [('!System',system_icon,'Modules'),('!Scrap',scrap_icon,'ScrapDir')]:
  folder=SRC/'ArcLibre/system'/app[1:];full=rows(icon)
  out[app]={'!Boot':File((folder/'!Boot').read_bytes(),0xfeb),'!Run':File((folder/'!Run').read_bytes(),0xfeb),'!Help':File((folder/'!Help').read_bytes(),0xfff),
   '!Sprites':File(sprite_file(app.lower(),12,full[::2]),0xff9),'!Sprites22':File(sprite_file(app.lower(),20,full),0xff9),extra:{}}
 return out
