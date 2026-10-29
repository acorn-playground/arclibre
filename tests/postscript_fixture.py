# SPDX-License-Identifier: Apache-2.0
"""Run the PostScript PDriverPS writes and rasterise its pages, for the printing gates.

Ghostscript isn't a host dependency, so this is a small, independent Level 1
interpreter: the operators the PDriverPS prologue and a simple page use, and
nothing else (an unknown operator is an error, so a change in the driver's
output can't pass unnoticed). It executes the whole job: the prologue's own
procedure definitions draw the page. Painting is sampled at device pixel
centres at `dpi`, with the device origin at the bottom left of the page;
paths may hold straight lines only. A page is a dict of device pixel to gray
(0 black, 1 white) for every pixel painted.
"""
import math,re
class Name(str):
 def __new__(cls,s,executable):o=str.__new__(cls,s);o.executable=executable;return o
class Proc(list):pass
class Mark:pass
MARK=Mark()
class PSString:
 """A string object: getinterval shares the underlying bytes, as in PostScript."""
 def __init__(self,buf,off=0,n=None):self.buf=buf;self.off=off;self.n=len(buf)-off if n is None else n
 def bytes(self):return bytes(self.buf[self.off:self.off+self.n])
 def __eq__(self,o):return isinstance(o,PSString) and self.bytes()==o.bytes()
 def __hash__(self):return hash(self.bytes())
class Op:
 def __init__(self,name,fn):self.name=name;self.fn=fn
class Stop(Exception):pass

class Reader:
 """The job file: tokens are read lazily, so readhexstring from currentfile works."""
 DELIM=b'()<>[]{}/%'
 def __init__(self,data):self.d=data;self.i=0
 def skip(self):
  d=self.d
  while self.i<len(d):
   c=d[self.i]
   if c in b' \t\r\n\f\0':self.i+=1
   elif c==37:
    while self.i<len(d) and d[self.i] not in b'\r\n':self.i+=1
   else:break
 def token(self):
  self.skip();d=self.d
  if self.i>=len(d):return None
  c=d[self.i]
  if c==40:   # ( string ) with nesting and escapes
   depth=1;self.i+=1;out=bytearray()
   while True:
    c=d[self.i];self.i+=1
    if c==92:
     e=d[self.i];self.i+=1
     if e in b'01234567':
      v=e-48
      for _ in range(2):
       if d[self.i] in b'01234567':v=v*8+d[self.i]-48;self.i+=1
      out.append(v&255)
     elif e in b'\r\n':
      if e==13 and d[self.i]==10:self.i+=1
     else:out.append({110:10,114:13,116:9,98:8,102:12}.get(e,e))
    elif c==40:depth+=1;out.append(c)
    elif c==41:
     depth-=1
     if not depth:return PSString(out)
     out.append(c)
    else:out.append(c)
  if c==60:
   j=d.index(b'>',self.i);h=re.sub(rb'\s',b'',d[self.i+1:j]);self.i=j+1
   return PSString(bytearray(bytes.fromhex((h+b'0'*(len(h)%2)).decode())))
  if c in b'[]{}':self.i+=1;return {91:Name('[',True),93:Name(']',True),123:'{',125:'}'}[c]
  j=self.i+1 if c==47 else self.i
  if c==47 and j<len(d) and d[j]==47:raise AssertionError('immediately evaluated names are not used')
  k=j
  while k<len(d) and d[k] not in b' \t\r\n\f\0' and d[k] not in self.DELIM:k+=1
  s=d[j:k].decode('latin1');self.i=k
  if c==47:return Name(s,False)
  if re.fullmatch(r'[-+]?\d+',s):return int(s)
  if re.fullmatch(r'[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?',s):return float(s)
  if re.fullmatch(r'\d+#[0-9A-Za-z]+',s):b,v=s.split('#');return int(v,int(b))
  return Name(s,True)
 def object(self):
  t=self.token()
  if t=='{':
   p=Proc()
   while True:
    x=self.object()
    if x=='}':return p
    assert x is not None,'unterminated procedure'
    p.append(x)
  return t

def mul(a,b):  # PostScript matrices [a b c d e f]: a then b
 return [a[0]*b[0]+a[1]*b[2],a[0]*b[1]+a[1]*b[3],a[2]*b[0]+a[3]*b[2],a[2]*b[1]+a[3]*b[3],a[4]*b[0]+a[5]*b[2]+b[4],a[4]*b[1]+a[5]*b[3]+b[5]]
def apply(m,x,y):return (m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5])
def invert(m):
 det=m[0]*m[3]-m[1]*m[2];a,b,c,d=m[3]/det,-m[1]/det,-m[2]/det,m[0]/det
 return [a,b,c,d,-(m[4]*a+m[5]*c),-(m[4]*b+m[5]*d)]

UNSUPPORTED='curveto arc arcn stringwidth charpath pathbbox ashow awidthshow kshow widthshow image colorimage findfont itransform transform dtransform idtransform invertmatrix atan cvs token exit currentpoint eofill eoclip initclip setscreen settransfer flattenpath'.split()
class Interpreter:
 def __init__(self,data,dpi=300,page=(595,842)):
  self.r=Reader(data);self.o=[];self.e=0;self.pages=[];self.dpi=dpi;self.unknown=[]
  self.system={};self.user={};self.d=[self.system,self.user];self.status={}
  s=dpi/72;self.default=[s,0,0,s,0,0];self.size=(round(page[0]*s),round(page[1]*s))
  self.g=dict(ctm=list(self.default),path=[],point=None,clip=[(0,0,self.size[0],self.size[1])],gray=0.0,lw=1.0,cap=0,font=None,dash=None)
  self.gstack=[];self.paint={};self.copies_name=Name('#copies',False);self.user['#copies']=1
  for n in dir(self):
   if n.startswith('op_'):self.system[n[3:]]=Op(n[3:],getattr(self,n))
  for n,f in {'[':self.op_mark,']':self.op_endarray,'=':self.op_pop,'==':self.op_pop}.items():self.system[n]=Op(n,f)
  self.system['userdict']=self.user;self.system['statusdict']=self.status;self.system['systemdict']=self.system
  # Operators the prologue binds to names but this page model doesn't paint
  # with: using one is an error.
  for n in UNSUPPORTED:self.system[n]=Op(n,lambda n=n:self.unsupported(n))
  self.system['true']=True;self.system['false']=False;self.system['null']=None
 def unsupported(self,n):raise AssertionError(n+' is not supported by this checker')
 # Execution.
 def lookup(self,n):
  for d in reversed(self.d):
   if n in d:return d[n]
  raise KeyError(n)
 def run(self):
  while True:
   x=self.r.object()
   if x is None:break
   assert x!='}','unbalanced }'
   self.execute(x,direct=True)
  return self
 def execute(self,x,direct=False):
  if isinstance(x,Name) and x.executable:
   v=self.lookup(x)
   if isinstance(v,Op):v.fn()
   elif isinstance(v,Proc) and getattr(v,'executable',True):self.call(v)
   else:self.o.append(v)
  elif isinstance(x,Op):x.fn()
  else:self.o.append(x)
 def call(self,p):
  self.e+=1;assert self.e<200,'recursion'
  try:
   for x in p:
    if isinstance(x,Proc):self.o.append(x)
    else:self.execute(x)
  finally:self.e-=1
 def pop(self,n=1):
  assert len(self.o)>=n,'stack underflow'
  v=self.o[-n:];del self.o[-n:];return v if n>1 else v[0]
 def num(self):v=self.pop();assert isinstance(v,(int,float)) and not isinstance(v,bool),v;return v
 # Stack, arithmetic and control.
 def op_pop(self):self.pop()
 def op_exch(self):a,b=self.pop(2);self.o+=[b,a]
 def op_dup(self):self.o.append(self.o[-1])
 def op_copy(self):
  n=self.pop()
  if isinstance(n,int):self.o+=self.o[len(self.o)-n:] if n else []
  else:
   src=self.pop()
   if isinstance(n,PSString):n.buf[n.off:n.off+src.n]=src.bytes();self.o.append(PSString(n.buf,n.off,src.n))
   elif isinstance(n,list):n[:len(src)]=src;self.o.append(n[:len(src)])
   else:n.update(src);self.o.append(n)
 def op_index(self):n=self.pop();self.o.append(self.o[-1-n])
 def op_roll(self):
  n,j=self.pop(2)
  if n:j%=n;s=self.o[len(self.o)-n:];del self.o[len(self.o)-n:];self.o+=s[n-j:]+s[:n-j]
 def op_mark(self):self.o.append(MARK)
 def op_endarray(self):
  i=max(k for k,v in enumerate(self.o) if v is MARK);a=self.o[i+1:];del self.o[i:];self.o.append(a)
 def op_clear(self):self.o.clear()
 def op_count(self):self.o.append(len(self.o))
 def op_add(self):a,b=self.pop(2);self.o.append(a+b)
 def op_sub(self):a,b=self.pop(2);self.o.append(a-b)
 def op_mul(self):a,b=self.pop(2);self.o.append(a*b)
 def op_div(self):a,b=self.pop(2);self.o.append(a/b)
 def op_idiv(self):a,b=self.pop(2);self.o.append(int(a/b))
 def op_mod(self):a,b=self.pop(2);self.o.append(int(math.fmod(a,b)))
 def op_neg(self):self.o.append(-self.num())
 def op_abs(self):self.o.append(abs(self.num()))
 def op_ceiling(self):v=self.num();self.o.append(type(v)(math.ceil(v)))
 def op_floor(self):v=self.num();self.o.append(type(v)(math.floor(v)))
 def op_round(self):v=self.num();self.o.append(type(v)(math.floor(v+0.5)))
 def op_truncate(self):v=self.num();self.o.append(type(v)(math.trunc(v)))
 def op_cvi(self):self.o.append(int(self.num()))
 def op_cvr(self):self.o.append(float(self.num()))
 def op_sqrt(self):self.o.append(math.sqrt(self.num()))
 def op_eq(self):a,b=self.pop(2);self.o.append(a==b)
 def op_ne(self):a,b=self.pop(2);self.o.append(a!=b)
 def op_gt(self):a,b=self.pop(2);self.o.append(a>b)
 def op_ge(self):a,b=self.pop(2);self.o.append(a>=b)
 def op_lt(self):a,b=self.pop(2);self.o.append(a<b)
 def op_le(self):a,b=self.pop(2);self.o.append(a<=b)
 def op_not(self):v=self.pop();self.o.append(not v if isinstance(v,bool) else ~v)
 def op_and(self):a,b=self.pop(2);self.o.append(a and b if isinstance(a,bool) else a&b)
 def op_or(self):a,b=self.pop(2);self.o.append(a or b if isinstance(a,bool) else a|b)
 def op_if(self):
  c,p=self.pop(2)
  if c:self.call(p)
 def op_ifelse(self):c,a,b=self.pop(3);self.call(a if c else b)
 def op_for(self):
  i,step,end,p=self.pop(4)
  while (step>0 and i<=end) or (step<0 and i>=end):self.o.append(i);self.call(p);i+=step
 def op_repeat(self):
  n,p=self.pop(2)
  for _ in range(n):self.call(p)
 def op_forall(self):
  obj,p=self.pop(2)
  if isinstance(obj,dict):
   for k,v in list(obj.items()):self.o+=[k,v];self.call(p)
  else:
   for v in (obj.bytes() if isinstance(obj,PSString) else list(obj)):self.o.append(v);self.call(p)
 def op_exec(self):
  v=self.pop()
  if isinstance(v,Proc):self.call(v)
  else:self.execute(v)
 def op_stopped(self):
  p=self.pop()
  try:self.call(p);self.o.append(False)
  except Stop:self.o.append(True)
 def op_stop(self):raise Stop
 # Dictionaries, arrays, strings and names.
 def op_dict(self):self.pop();self.o.append({})
 def op_begin(self):d=self.pop();assert isinstance(d,dict);self.d.append(d)
 def op_end(self):assert len(self.d)>2;self.d.pop()
 def op_def(self):k,v=self.pop(2);self.d[-1][str(k) if isinstance(k,Name) else k]=v
 def op_load(self):self.o.append(self.lookup(self.pop()))
 def op_store(self):
  k,v=self.pop(2)
  for d in reversed(self.d):
   if k in d:d[k]=v;return
  self.d[-1][k]=v
 def op_known(self):d,k=self.pop(2);self.o.append(str(k) in d)
 def op_where(self):
  k=self.pop()
  for d in reversed(self.d):
   if k in d:self.o+=[d,True];return
  self.o.append(False)
 def op_currentdict(self):self.o.append(self.d[-1])
 def op_get(self):
  a,k=self.pop(2)
  self.o.append(a[str(k) if isinstance(k,Name) else k] if isinstance(a,dict) else a.buf[a.off+k] if isinstance(a,PSString) else a[k])
 def op_put(self):
  a,k,v=self.pop(3)
  if isinstance(a,dict):a[str(k) if isinstance(k,Name) else k]=v
  elif isinstance(a,PSString):a.buf[a.off+k]=v
  else:a[k]=v
 def op_length(self):a=self.pop();self.o.append(a.n if isinstance(a,PSString) else len(a))
 def op_array(self):self.o.append([None]*self.pop())
 def op_matrix(self):self.o.append([1.0,0.0,0.0,1.0,0.0,0.0])
 def op_astore(self):a=self.pop();n=len(a);a[:]=self.pop(n) if n>1 else [self.pop()];self.o.append(a)
 def op_aload(self):a=self.pop();self.o+=list(a)+[a]
 def op_string(self):self.o.append(PSString(bytearray(self.pop())))
 def op_getinterval(self):
  a,i,n=self.pop(3)
  if isinstance(a,PSString):assert i+n<=a.n;self.o.append(PSString(a.buf,a.off+i,n))
  else:self.o.append(a[i:i+n])
 def op_putinterval(self):
  a,i,b=self.pop(3)
  if isinstance(a,PSString):assert i+b.n<=a.n;a.buf[a.off+i:a.off+i+b.n]=b.bytes()
  else:a[i:i+len(b)]=b
 def op_cvn(self):s=self.pop();self.o.append(Name(s.bytes().decode('latin1'),False))
 def op_cvx(self):
  v=self.pop()
  if isinstance(v,Name):v=Name(v,True)
  elif isinstance(v,list):v=Proc(v)
  self.o.append(v)
 def op_cvlit(self):
  v=self.pop()
  if isinstance(v,Name):v=Name(v,False)
  self.o.append(v)
 def op_type(self):
  v=self.pop();t='booleantype' if isinstance(v,bool) else 'integertype' if isinstance(v,int) else 'realtype' if isinstance(v,float) else 'stringtype' if isinstance(v,PSString) else 'nametype' if isinstance(v,Name) else 'dicttype' if isinstance(v,dict) else 'arraytype' if isinstance(v,list) else 'operatortype' if isinstance(v,Op) else 'nulltype'
  self.o.append(Name(t,True))
 def op_bind(self):pass
 def op_currentfile(self):self.o.append(self.r)
 def op_readhexstring(self):
  f,s=self.pop(2);assert f is self.r;digits=[]
  while len(digits)<2*s.n and self.r.i<len(self.r.d):
   c=chr(self.r.d[self.r.i]);self.r.i+=1
   if c in '0123456789abcdefABCDEF':digits.append(c)
  s.buf[s.off:s.off+s.n]=bytes.fromhex(''.join(digits));self.o+=[s,len(digits)==2*s.n]
 # Device and job control: the operators a LaserWriter's prologue setup uses.
 def op_a4(self):self.page_size='a4'
 def op_save(self):self.gstack.append(('save',dict(self.g,ctm=list(self.g['ctm']),path=[list(p) for p in self.g['path']],clip=list(self.g['clip']))));self.o.append(Name('-save-',False))
 def op_restore(self):
  self.pop()
  while self.gstack[-1][0]!='save':self.gstack.pop()
  self.g=self.gstack.pop()[1]
 def op_gsave(self):self.gstack.append(('gsave',dict(self.g,ctm=list(self.g['ctm']),path=[list(p) for p in self.g['path']],clip=list(self.g['clip']))))
 def op_grestore(self):
  if self.gstack and self.gstack[-1][0]=='gsave':self.g=self.gstack.pop()[1]
 def op_showpage(self):
  copies=self.lookup('#copies');self.pages.append(dict(paint=self.paint,copies=copies));self.paint={}
  self.g.update(ctm=list(self.default),path=[],point=None,clip=[(0,0,self.size[0],self.size[1])])
 # Graphics state, paths and painting.
 def op_setgray(self):self.g['gray']=self.num()
 def op_setrgbcolor(self):r,g,b=self.pop(3);self.g['gray']=0.3*r+0.59*g+0.11*b
 def op_setlinewidth(self):self.g['lw']=self.num()
 def op_setlinecap(self):self.g['cap']=self.pop()
 def op_setlinejoin(self):self.pop()
 def op_setmiterlimit(self):self.pop()
 def op_setdash(self):a,o=self.pop(2);assert not a,'dashed lines';self.g['dash']=None
 def op_translate(self):x,y=self.pop(2);self.g['ctm']=mul([1,0,0,1,x,y],self.g['ctm'])
 def op_scale(self):x,y=self.pop(2);self.g['ctm']=mul([x,0,0,y,0,0],self.g['ctm'])
 def op_concat(self):m=self.pop();self.g['ctm']=mul(list(m),self.g['ctm'])
 def op_currentmatrix(self):m=self.pop();m[:]=self.g['ctm'];self.o.append(m)
 def op_setmatrix(self):self.g['ctm']=list(self.pop())
 def op_concatmatrix(self):a,b,c=self.pop(3);c[:]=mul(a,b);self.o.append(c)
 def op_newpath(self):self.g['path']=[];self.g['point']=None
 def op_moveto(self):x,y=self.pop(2);p=apply(self.g['ctm'],x,y);self.g['path'].append([p]);self.g['point']=p
 def op_rmoveto(self):
  dx,dy=self.pop(2);m=self.g['ctm'];x,y=self.g['point'];p=(x+m[0]*dx+m[2]*dy,y+m[1]*dx+m[3]*dy);self.g['path'].append([p]);self.g['point']=p
 def op_lineto(self):x,y=self.pop(2);p=apply(self.g['ctm'],x,y);self.g['path'][-1].append(p);self.g['point']=p
 def op_rlineto(self):
  dx,dy=self.pop(2);m=self.g['ctm'];x,y=self.g['point'];p=(x+m[0]*dx+m[2]*dy,y+m[1]*dx+m[3]*dy)
  self.g['path'][-1].append(p);self.g['point']=p
 def op_closepath(self):
  sp=self.g['path'][-1]
  if len(sp)>1 and sp[-1]!=sp[0]:sp.append(sp[0])
  self.g['point']=sp[0];self.g['path'].append([sp[0]])
 def op_clippath(self):
  x0,y0,x1,y1=self.cliprect();self.g['path']=[[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]];self.g['point']=(x0,y0)
 def rect(self,sp):
  """The axis-aligned box a closed four-sided subpath describes (all PDriverPS boxes are)."""
  pts=[p for i,p in enumerate(sp) if i==0 or p!=sp[i-1]]
  if pts[-1]==pts[0]:pts=pts[:-1]
  assert len(pts)==4 and all(a[0]==b[0] or a[1]==b[1] for a,b in zip(pts,pts[1:]+pts[:1])),('not an axis-aligned box',sp)
  xs=[p[0] for p in pts];ys=[p[1] for p in pts];return (min(xs),min(ys),max(xs),max(ys))
 def cliprect(self):
  c=self.g['clip'];return (max(r[0] for r in c),max(r[1] for r in c),min(r[2] for r in c),min(r[3] for r in c))
 def op_clip(self):
  boxes=[self.rect(sp) for sp in self.g['path'] if len(sp)>1];assert len(boxes)==1;self.g['clip']=self.g['clip']+boxes
 def fillrect(self,x0,y0,x1,y1):
  cx0,cy0,cx1,cy1=self.cliprect();x0,y0,x1,y1=max(x0,cx0),max(y0,cy0),min(x1,cx1),min(y1,cy1);g=self.g['gray']
  for py in range(math.ceil(y0-0.5),math.ceil(y1-0.5)):
   for px in range(math.ceil(x0-0.5),math.ceil(x1-0.5)):self.paint[(px,py)]=g
 def op_fill(self):
  for sp in self.g['path']:
   if len(sp)>1:self.fillrect(*self.rect(sp))
  self.g['path']=[];self.g['point']=None
 def op_stroke(self):
  # Square-capped (2) or butt-capped (0) straight segments; each is a box
  # around the segment (all PDriverPS's are horizontal or vertical).
  m=self.g['ctm'];w=self.g['lw']*math.hypot(m[0],m[1])/2;cap=w if self.g['cap']==2 else 0
  assert self.g['cap'] in (0,2) and abs(abs(m[0])-abs(m[3]))<1e-9 and m[1]==m[2]==0
  for sp in self.g['path']:
   for (ax,ay),(bx,by) in zip(sp,sp[1:]):
    assert ax==bx or ay==by,'diagonal stroke'
    if ay==by:self.fillrect(min(ax,bx)-cap,ay-w,max(ax,bx)+cap,ay+w)
    else:self.fillrect(ax-w,min(ay,by)-cap,ax+w,max(ay,by)+cap)
  self.g['path']=[];self.g['point']=None
 # Fonts: PDriverPS's VDU 5 text is a Type 3 font of 8 x 8 bitmaps.
 def op_definefont(self):k,f=self.pop(2);f['FID']=True;self.o.append(f)
 def op_makefont(self):f,m=self.pop(2);f=dict(f);f['FontMatrix']=mul(list(f['FontMatrix']),list(m));self.o.append(f)
 def op_scalefont(self):f,s=self.pop(2);f=dict(f);f['FontMatrix']=mul(list(f['FontMatrix']),[s,0,0,s,0,0]);self.o.append(f)
 def op_setfont(self):self.g['font']=self.pop()
 def op_currentfont(self):self.o.append(self.g['font'])
 def op_setcharwidth(self):self.width=self.pop(2)
 def op_show(self):
  s=self.pop();f=self.g['font'];assert f['FontType']==3
  for c in s.bytes():
   self.op_gsave();x,y=self.g['point'];self.g['ctm']=mul(list(f['FontMatrix']),[*self.g['ctm'][:4],x,y]);m=self.g['ctm']
   self.o+=[f,c];self.width=(0,0);self.call(f['BuildChar']);wx,wy=self.width;self.op_grestore()
   self.g['point']=(x+m[0]*wx+m[2]*wy,y+m[1]*wx+m[3]*wy)
 def op_imagemask(self):
  w,h,polarity,im,src=self.pop(5);data=src.bytes() if isinstance(src,PSString) else None
  assert data is not None and len(data)>=h*((w+7)//8),'imagemask data from a string'
  m=mul(invert(list(im)),self.g['ctm']);row=(w+7)//8
  for j in range(h):
   for i in range(w):
    if bool(data[j*row+i//8]&(0x80>>(i%8)))==bool(polarity):
     (ax,ay),(bx,by)=apply(m,i,j),apply(m,i+1,j+1);self.fillrect(min(ax,bx),min(ay,by),max(ax,bx),max(ay,by))

def render(data,dpi=300):
 """Run a PostScript job; return (pages, interpreter). Each page has its painted pixels and copy count."""
 ps=Interpreter(data,dpi).run();assert not ps.o,('operands left on the stack',ps.o[:5]);return ps.pages,ps
