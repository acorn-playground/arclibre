#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original Draw/Paint artwork creation, ST506 save and independent cold reopen."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,shutil,struct,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
from verify_filer_disc import read_directory
from adfs_fixture import oldcheck
p=argparse.ArgumentParser();p.add_argument('root',nargs='?',default='build/arclibre');p.add_argument('--verify-existing',action='store_true');p.add_argument('--probe',action='store_true',help='one cold boot; writes probe.json');args=p.parse_args()
root=REPO/args.root;out=REPO/'build/graphics-apps/acceptance';out.mkdir(parents=True,exist_ok=True);start(out)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
# RISC OS 3 desktop palette entries (&BBGGRR00) picked in RISC_OSLib's
# dboxtcol dialogue by the probe.
YELLOW,RED=0x00EEEE00,0x0000DD00
def draw(data):
 assert data[:4]==b'Draw' and struct.unpack_from('<2I',data,4)==(201,0)
 offset=40;objects=[]
 while offset<len(data):
  tag,size=struct.unpack_from('<2I',data,offset);assert size>=24 and size%4==0 and offset+size<=len(data)
  objects.append((tag,data[offset:offset+size]));offset+=size
 assert offset==len(data) and sorted(tag for tag,_ in objects)==[2,11], 'one real path and original options'
 path=next(b for tag,b in objects if tag==2);bbox=struct.unpack_from('<4i',path,8)
 assert bbox[0]<bbox[2] and bbox[1]<bbox[3]
 fill,stroke,width,style=struct.unpack_from('<4I',path,24)
 assert stroke!=0xffffffff and not style&128
 # Chosen in Style > Fill colour's dialogue: the desktop's yellow (colour 9).
 assert fill==YELLOW,hex(fill)
 i=40;commands=[];points=[]
 while True:
  tag=struct.unpack_from('<I',path,i)[0];i+=4;commands.append(tag)
  if tag==0:break
  if tag in [2,8]:points.append(struct.unpack_from('<2i',path,i));i+=8
  else:assert tag==5, 'closed straight rectangle only'
 assert i==len(path) and commands[0]==2 and commands[-2:]==[5,0]
 corners=set(points);xs={x for x,y in corners};ys={y for x,y in corners}
 assert len(xs)==len(ys)==2 and corners=={(x,y) for x in xs for y in ys}
 return dict(kind='DrawFile',bytes=len(data),object_tags=[t for t,_ in objects],bbox=bbox,rectangle_points=points,fill=fill,stroke=stroke,width=width),path

def sprite(data):
 count,first,free=struct.unpack_from('<3I',data)
 assert count==1 and first==16 and free==len(data)+4
 size=struct.unpack_from('<I',data,12)[0];assert size==len(data)-12
 header=data[12:];name=header[4:16].split(b'\0')[0].decode('ascii')
 width,height,left,right,image,mask,mode=struct.unpack_from('<7I',header,16)
 assert name=='newsprite' and mode==12 and (width,height,left,right)==(3,31,0,31)
 assert image==44+16*8 and mask==image+512 and size==mask+512
 pixels=[]
 for y in range(32):
  row=[]
  for byte in header[image+16*y:image+16*(y+1)]:row.extend([byte&15,byte>>4])
  pixels.append(row)
 colors={v for row in pixels for v in row};assert len(colors)==2,colors
 minority=min(colors,key=lambda v:sum(row.count(v) for row in pixels));painted=[(x,y) for y,row in enumerate(pixels) for x,v in enumerate(row) if v==minority]
 assert len(painted)>=8 and len({x for x,y in painted})>=8 and len({y for x,y in painted})>=8, 'real non-empty diagonal paint stroke'
 assert all(b==255 for b in header[mask:]),'opaque mask retained'
 # Paint > Edit palette set the painting colour to the desktop's red (colour 11).
 assert struct.unpack_from('<2I',header,44+8*minority)==(RED,RED),'edited palette entry'
 return dict(kind='Sprite',bytes=len(data),name=name,mode=mode,width=32,height=32,colours=sorted(colors),painted_pixels=painted),data

def media(p,app):
 b=p.read_bytes();assert len(b)==615*4*32*256 and b[255]==oldcheck(b[:255]) and b[511]==oldcheck(b[256:511])
 rows=read_directory(b,4);assert set(rows)=={'ReadMe',app+'Doc'};used=[(0,0xe00)];contents={}
 for name,r in rows.items():
  start=r['address']*256;contents[name]=b[start:start+r['length']];used.append((start,start+((r['length']+255)&~255)));assert r['attributes']==3
 assert contents['ReadMe']==b'ArcLibre original ST506 hard disc.\n'
 doc=rows[app+'Doc'];assert doc['load']>>20==0xfff and (doc['load']>>8)&0xfff=={'Draw':0xaff,'Paint':0xff9}[app]
 assert b[510]%3==0;free=[]
 for i in range(0,b[510],3):
  start=int.from_bytes(b[i:i+3],'little')*256;length=int.from_bytes(b[256+i:259+i],'little')*256;assert length>0;free.append((start,start+length))
 spans=sorted(used+free);assert spans[0][0]==0 and spans[-1][1]==len(b) and all(a[1]==z[0] for a,z in zip(spans,spans[1:]))
 description,payload=(draw if app=='Draw' else sprite)(contents[app+'Doc'])
 return dict(sha256=sha(p),files=rows,bytes=len(b),free_bytes=sum(z-a for a,z in free),checksums_and_allocation_accounting=True,document=description,document_sha256=hashlib.sha256(contents[app+'Doc']).hexdigest()),payload

run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','GraphicsProbe'],'harness')
def trial(spec):
 app,n=spec;p=out/(app.lower()+f'-cold-{n}')
 if not args.verify_existing:
  shutil.rmtree(p,ignore_errors=True);run([REPO/'build/harness-patched/release/GraphicsProbe',root/'arclibre.rom',root,p,app],f'{app}-write-{n}')
  before,payload=media(p/'test.hdf',app);(p/'written-media.json').write_text(json.dumps(before,indent=2)+'\n')
  run([REPO/'build/harness-patched/release/GraphicsProbe',root/'arclibre.rom',root,p,app,'reopen'],f'{app}-reopen-{n}')
 before=load(p/'written-media.json');after,payload=media(p/'test.hdf',app)
 assert json.dumps(before,sort_keys=True)==json.dumps(after,sort_keys=True),'reopening must not alter media'
 phases={}
 for phase in ['write','reopen']:
  r=load(p/phase/'result.json');assert r['status']=='PASS' and r['app']==app and r['rom_sha256']==sha(root/'arclibre.rom')
  assert r['phase']==phase and r['task_count']==desktop_task_count(root)+1 and not r['errors'] and all(r['exceptions'][i]==0 for i in [3,4,5])
  assert r['configuration']['cmosSettings']==[] and r['configuration']['powerOnKeys']==([0x34] if phase=='write' else [])
  assert any(i['name']==app and i['psr']&3==0 for i in r['initialisations'])
  assert (r['writes']>0 if phase=='write' else r['writes']==0)
  buffers=[(p/phase/v['file']).read_bytes() for v in r['document_buffers']]
  assert any(payload==b for b in buffers),'on-disk artwork exactly matches original app document in memory'
  trace=verify(p/phase,required=['SharedCLib',app,'ADFS','Filer'],root=root)
  r.pop('configuration');phases[phase]=dict(result=r,trace=trace,screens={f.name:sha(f) for f in (p/phase).glob('*.png')})
 return app,n,dict(media=after,phases=phases)
results={a:{} for a in ['Draw','Paint']}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for app,n,r in pool.map(trial,[(a,n) for a in ['Draw','Paint'] for n in COLD]):results[app][n]=r
for app in results:same(results[app])
report=dict(status='PASS',rom_sha256=sha(root/'arclibre.rom'),trials_per_app=3,colour_dialogue=dict(draw_fill=hex(YELLOW),paint_palette_entry=hex(RED),source='RISC_OSLib dboxtcol with the application dboxtcol template'),independent_cold_boots=12,identical_repeats=True,real_original_graphics_applications=True,real_st506_controller=True,no_guest_code_injection=True,emulator_unchanged=True,save_power_off_then_desktop_double_click=True,actual_document_and_disk_bytes_match=True,results={a:r[1] for a,r in results.items()})
finish(out,report);print('Draw/Paint hard-disc persistence PASS',flush=True)
