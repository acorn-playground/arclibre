# SPDX-License-Identifier: Apache-2.0
"""PC floppies (512-byte MFM sectors) as HxC HFE v1 track images.

MacArch reads raw sector images only in Acorn geometries; a PC 720K disc is
presented to it as its recorded MFM tracks instead, exactly as a drive head
would see them: IBM System 34 layout (gap 4a, IAM, then per sector an ID
field C/H/R/N=2 and a data field, CRC-CCITT, sectors 1-9), 250 kbit/s,
6,250 bytes per track. Cells are stored least-significant bit first.
High density (1.44M, 18 sectors) is recorded at 500 kbit/s, 12,500 bytes per
track. A 40-track disc (360K) is as an 80-track drive reads it: each
cylinder's wide track under two head positions, so DOSFS double-steps.
"""
import struct
def crc16(data,crc=0xFFFF):
 for b in data:
  crc^=b<<8
  for _ in range(8):crc=((crc<<1)^0x1021)&0xFFFF if crc&0x8000 else (crc<<1)&0xFFFF
 return crc
def mfm(stream):
 """stream: list of (byte, missing_clock_mask). Returns the cell bytes."""
 cells=[];prev=0
 for byte,missing in stream:
  for k in range(7,-1,-1):
   d=(byte>>k)&1;c=1 if (prev==0 and d==0) else 0
   if missing>>k&1:c=0
   cells+=[c,d];prev=d
 out=bytearray(len(cells)//8)
 for i,c in enumerate(cells):out[i>>3]|=c<<(i&7)
 return bytes(out)
A1=(0xA1,0x04)  # A1 with the clock between bits 4 and 3 missing (cells 4489)
C2=(0xC2,0x08)  # C2 with a missing clock (cells 5224), index address mark
def track(cyl,head,sectors,gap3=84,length=6250):
 s=[(0x4E,0)]*80+[(0,0)]*12+[C2]*3+[(0xFC,0)]+[(0x4E,0)]*50
 for r,data in sectors:
  assert len(data)==512
  idf=bytes([0xFE,cyl,head,r,2]);crc=crc16(b'\xa1\xa1\xa1'+idf)
  s+=[(0,0)]*12+[A1]*3+[(b,0) for b in idf+crc.to_bytes(2,'big')]+[(0x4E,0)]*22
  dat=b'\xfb'+data;crc=crc16(b'\xa1\xa1\xa1'+dat)
  s+=[(0,0)]*12+[A1]*3+[(b,0) for b in dat+crc.to_bytes(2,'big')]+[(0x4E,0)]*gap3
 assert len(s)<=length;s+=[(0x4E,0)]*(length-len(s))
 return mfm(s)
def hfe(image,tracks=80,sides=2,spt=9,double_step=False):
 """image: raw sectors in track, side, sector order (as a PC sees the disc)."""
 cylinders=tracks//2 if double_step else tracks;assert len(image)==cylinders*sides*spt*512
 rate=500 if spt>=15 else 250;length=rate*25
 head=bytearray(b'\xff'*512);head[0:8]=b'HXCPICFE';head[8]=0;head[9]=tracks;head[10]=sides;head[11]=0
 struct.pack_into('<HHBBH',head,12,rate,300,7,1,1);head[20]=0xFF  # MFM, 250 or 500 kbit/s, 300 rpm, writable
 per=None;body=bytearray();table=bytearray(b'\xff'*512);block=2
 for t in range(tracks):
  c=t//2 if double_step else t
  sidecells=[track(c,h,[(r+1,image[((c*sides+h)*spt+r)*512:((c*sides+h)*spt+r+1)*512]) for r in range(spt)],length=length) for h in range(sides)]
  n=len(sidecells[0]);blocks=(n+255)//256;data=bytearray(blocks*512)
  for h,cells in enumerate(sidecells):
   for k in range(blocks):piece=cells[k*256:(k+1)*256];data[k*512+h*256:k*512+h*256+len(piece)]=piece
  struct.pack_into('<HH',table,t*4,block,n*sides);block+=blocks;body+=data
 return bytes(head)+bytes(table)+bytes(body)
