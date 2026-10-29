#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Tokenise, compact and package a new ArcLibre BASIC application for the ROM.

  build_calc.py             !Calc (src/ArcCalc)
  build_calc.py configure   !Configure (src/ArcConfigure), with its section sprites

The BBC BASIC text source is tokenised by the ROM's own BASIC 1.14 (TEXTLOAD
then SAVE at the real F12 prompt, under the pinned MacArch core) on the ROM
built without the BASIC utilities. Its leading licence REM lines are given
line number 0, the convention of the published sources, so the squish tool
keeps them byte for byte. Two tokenisations must match. The squished program
and its Apps files become the ResourceFS block of the application's wrapper
module.
"""
import hashlib,json,os,pathlib,shutil,struct,subprocess,sys
from paths import REPO,SRC
sys.path.insert(0,str(REPO/'tests'))
from adfs_fixture import directory,entry,u24,oldcheck
from verify_filer_disc import read_directory
import basic_squish,check_basic_squish
def sha(b):return hashlib.sha256(b).hexdigest()
# The section icons of Configure 3.60's own Sprites file (Apache-2.0, pinned in
# manifests/configure-inputs.json) that the 3.11 Configuration window shows;
# renamed so that they cannot replace sprites already in the Wimp's pool.
# (pinned name, ROM name): cfg_ keeps them apart in the Wimp pool; 12 characters at most.
CONFIGURE_SPRITES=['discs','floppies','mouse','keyboard','memory','sound','screen','fonts','windows','n_net','n_fs',('n_spooler','n_spool')]
def sprite_subset(data,names,prefix):
 n,first,_=struct.unpack_from('<3I',data);o=first-4;found={}
 for _ in range(n):
  size,=struct.unpack_from('<I',data,o);found[data[o+4:o+16].split(b'\0')[0].decode()]=data[o:o+size];o+=size
 body=b''
 for name in names:
  src,dst=name if isinstance(name,tuple) else (name,name)
  s=bytearray(found[src]);new=(prefix+dst).encode();assert len(new)<=12;s[4:16]=new+bytes(12-len(new));body+=s
 return struct.pack('<3I',len(names),16,16+len(body))+body
APP=sys.argv[1] if len(sys.argv)>1 else 'calc'
if APP=='calc':
 COMPONENT,NAME='ArcCalc','Calc'
 run_file=b'| > !Run for the ArcLibre desk calculator\nWimpSlot -min 48K -max 48K\nRun Resources:$.Resources.Calc.!RunImage %*0\n'
 help_file=b'The Calculator is a simple four-function desk calculator.\nClick its icon on the icon bar to open the calculator window.\n'
 extra=[]
else:
 assert APP=='configure'
 COMPONENT,NAME='ArcConfigure','Configure'
 run_file=(b'| > !Run for the ArcLibre configuration editor\nIconSprites Resources:$.Resources.Configure.Sprites\n'
  b'Set File$Type_FF2 Config\nSet Alias$@RunType_FF2 Run Resources:$.Apps.!Configure %%*0\n'
  b'WimpSlot -min 96K -max 96K\nRun Resources:$.Resources.Configure.!RunImage %*0\n')
 help_file=(b'Configure sets the computer\'s configuration, held in its CMOS RAM.\n'
  b'Click its icon on the icon bar to open the Configuration window, then click a section.\n')
 extra=[('Resources.Configure.Sprites',sprite_subset((SRC/'ArcConfigure/Resources/Sprites,ff9').read_bytes(),CONFIGURE_SPRITES,'cfg_'),0xff9)]
OUT=REPO/('build/'+APP);OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name,**extra):
 with (OUT/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=REPO,env=dict(env,**extra),stdout=f,stderr=subprocess.STDOUT,check=True)
text=(SRC/COMPONENT/'bas'/NAME).read_bytes()
disc=bytearray(819200)
disc[12*256:12*256+2048]=directory('Resources',4,[],b'Hugo')
offset=8*1024;disc[offset:offset+len(text)]=text
disc[0x400:0xc00]=directory('$',4,[entry('Resources',12,directory=True),entry('AppSrc',offset//256,text,load=0xffffff00)],b'Hugo')
end=(offset+len(text)+1023)&~1023
u24(disc,0,end//256);u24(disc,256,(819200-end)//256);u24(disc,252,3200)
for i,ch in enumerate(b'APPBUILD  '):
 if i%2==0:disc[247+i//2]=ch
 else:disc[502+i//2]=ch
disc[507:509]=b'\x41\x42';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
rom_root=REPO/'build/arclibre-without-basic-utilities'
if not (rom_root/'arclibre.rom').exists():run([sys.executable,REPO/'tools/build_arclibre_rom.py','--without-basic-utilities'],'rom')
# As generate_alarm_code.py: a clean checkout has no extracted core yet, so
# prepare the pinned one into this build's own output directory.
(OUT/'emulator/artifacts').mkdir(parents=True,exist_ok=True)
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator',ARCLIBRE_OUTPUT=str(OUT/'emulator'))
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-alarm-code','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','BasicRunProbe'],'harness')
programs=[]
for n in [1,2]:
 p=OUT/f'run-{n}';shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(disc)
 run([REPO/'build/harness-alarm-code/release/BasicRunProbe',rom_root/'arclibre.rom',rom_root,p/'input.adf',p,
      '*Dir adfs::0.$','BASIC','TEXTLOAD "AppSrc"','SAVE "Resources.Prog"','QUIT'],f'run-{n}')
 b=(p/'disc.adf').read_bytes();rows=read_directory(b,read_directory(b,4)['Resources']['address'])
 assert set(rows)=={'Prog'},rows;row=rows['Prog'];programs.append(b[row['address']*256:row['address']*256+row['length']])
assert programs[0]==programs[1],'two tokenisations differ'
# Leading REM-only lines are the licence and attribution: number them 0.
rows=list(basic_squish.lines(programs[0]));n=0
while n<len(rows) and rows[n][1][:1]==bytes([basic_squish.TREM]):n+=1
assert n>=15,'licence header not found'
tokenised=basic_squish.program([(0,b) for _,b in rows[:n]]+rows[n:])
squished,mapping=basic_squish.squish(tokenised)
evidence=check_basic_squish.check(COMPONENT+'/bas/'+NAME,tokenised)
assert evidence['sha256']==sha(squished)
(OUT/(NAME+',ffb')).write_bytes(tokenised);(OUT/'!RunImage,ffb').write_bytes(squished)
files=[(f'Apps.!{NAME}.!Run',run_file,0xfeb),(f'Apps.!{NAME}.!Help',help_file,0xfff),(f'Resources.{NAME}.!RunImage',squished,0xffb)]+extra
block=bytearray()
for name,data,ft in files:
 nm=name.encode()+b'\0';nm+=bytes(-len(nm)%4)
 block+=struct.pack('<5I',24+len(nm)+((len(data)+3)&~3),0xfff00000|(ft<<8),0,len(data),3)+nm+struct.pack('<I',len(data)+4)+data+bytes(-len(data)%4)
gen=OUT/'generated';gen.mkdir(exist_ok=True)
# A leading DCD starts the data mapping region, as the Chars wrapper does.
(gen/(NAME+'Files')).write_bytes(bytes(block[4:]))
(gen/(NAME+'Files.s')).write_text('        DCD '+str(struct.unpack_from('<I',block)[0])+f'\n        INCBIN {NAME}Files\n        END\n')
(OUT/'result.json').write_text(json.dumps(dict(status='PASS',source=f'src/{COMPONENT}/bas/{NAME}',source_sha256=sha(text),interpreter='ROM BASIC 1.14 under MacArch',
 rom_sha256=sha((rom_root/'arclibre.rom').read_bytes()),tokenised_bytes=len(tokenised),tokenised_sha256=sha(tokenised),squished_bytes=len(squished),
 squished_sha256=sha(squished),licence_lines=n,names=len(mapping),identical_tokenisations=2,files=[dict(name=f,bytes=len(d),filetype=t,sha256=sha(d)) for f,d,t in files],
 resource_block_sha256=sha(bytes(block))),indent=2)+'\n')
print(NAME,len(tokenised),'->',len(squished),'bytes')
