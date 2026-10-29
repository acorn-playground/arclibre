#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disc-loaded DOSFS on the current ROM, checked with an independent FAT parser.

The guest loads the module with *RMLoad from the distributable ADFS floppy
(build/dosfs/arclibre-dosfs.adf) in drive 0. Drive 1 holds a PC 720K disc
generated on the host by tests/fat12_fixture.py and recorded as MFM tracks
(tests/hfe_fixture.py). Everything is typed at the real F12 command line.
Afterwards the host parser reads the PC disc back: names and 8.3 mapping,
contents, sizes, EOF behaviour, directories, deletion, the boot sector /
BPB / FATs written by DOSFS_LayoutStructure and by *Format (which needs the
delivered FileCore: see tests/run_format.py). Errors (missing
file, non-empty directory) are checked, and a negative control runs the
same commands without loading DOSFS.
"""
import concurrent.futures,hashlib,json,os,pathlib,random,re,shutil,struct,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tests'))
import fat12_fixture,hfe_fixture,check_dosfs_boot
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/dosfs-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(b):return hashlib.sha256(b).hexdigest()
# The module and its floppy are built from source first (build/dosfs only;
# nothing shared). --no-build tests the existing build/dosfs outputs.
if '--no-build' not in sys.argv:run([sys.executable,R/'tools/build_dosfs.py'],'build-dosfs')
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-dosfs','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DOSFSProbe'],'harness')
exe=R/'build/harness-dosfs/release/DOSFSProbe'
module_disc=(R/'build/dosfs/arclibre-dosfs.adf').read_bytes()
verification=json.loads((R/'build/dosfs/verification.json').read_text())
module=(R/'build/dosfs/DOSFS,ffa').read_bytes();assert sha(module)==verification['module_sha256'] and verification['status']=='STATIC_PASS'
assert sha(module_disc)==json.loads((R/'build/dosfs/disc.json').read_text())['sha256'],'run tools/build_dosfs.py first'

# The PC disc: deterministic contents from the host writer.
rng=random.Random(1996)
DATA=bytes(rng.randrange(256) for _ in range(5000))
NESTED=bytes((i*13+7)&255 for i in range(1500))
HELLO=b'Hello from a host-made FAT12 disc\r\n'
FILES={'HELLO.TXT':HELLO,'DATA.BIN':DATA,'EMPTY.DAT':b'','OLD.TXT':b'delete me\r\n','SUBDIR':None,'SUBDIR/NESTED.TXT':NESTED}
pc_image=fat12_fixture.make(FILES,label='HOSTDISC')
before=fat12_fixture.Volume(pc_image)
assert before.files()=={k:v for k,v in FILES.items() if v is not None} and before.dirs()==['SUBDIR'] and before.label=='HOSTDISC'
pc_hfe=hfe_fixture.hfe(pc_image)
second_image=fat12_fixture.make({'KEEP.TXT':b'kept\r\n'},label='HOSTTWO');second_hfe=hfe_fixture.hfe(second_image)
(out/'pc-input.img').write_bytes(pc_image);(out/'pc-input.hfe').write_bytes(pc_hfe)
README=(R/'src/ArcLibre/dosfs/ReadMe').read_bytes()
WRITTEN=bytes((i*7+3)&255 for i in range(3000))+b'A'
from verify_filer_disc import read_directory
def adfs_files(b):return {n:b[e['address']*256:e['address']*256+e['length']] for n,e in read_directory(b,4).items()}
assert adfs_files(module_disc)['DOSFS']==module

LAYOUT='DIM bad% 4:!bad%=-1:F%=OPENOUT "ADFS::0.$.Layout":SYS "DOSFS_LayoutStructure",1,bad%,"ARCTEST",F%:CLOSE#F%:PRINT "LAYOUT DONE"'
COMMANDS=['*RMLoad ADFS::0.$.DOSFS','*Help DOSFS','*Help DOSMap','*Cat ADFS::1.$','*Ex ADFS::1.$.SUBDIR',
 '*Copy ADFS::1.$.DATA/BIN ADFS::0.$.DataCopy ~C~V','*Copy ADFS::1.$.SUBDIR.NESTED/TXT ADFS::0.$.NestCopy ~C~V',
 '*Copy ADFS::0.$.ReadMe ADFS::1.$.README/TXT ~C~V','BASIC',
 'F%=OPENIN "ADFS::1.$.HELLO/TXT":N%=0:REPEAT:B%=BGET#F%:N%+=1:UNTIL EOF#F%:PRINT "HELLO ";N%;" ";EXT#F%;" ";PTR#F%;" ";EOF#F%:CLOSE#F%',
 'F%=OPENOUT "ADFS::1.$.WRITTEN/DAT":FOR I%=0 TO 2999:BPUT#F%,(I%*7+3) AND 255:NEXT:CLOSE#F%',
 'F%=OPENOUT "ADFS::1.$.ZERO/DAT":CLOSE#F%',
 'F%=OPENIN "ADFS::1.$.EMPTY/DAT":PRINT "EMPTY ";EXT#F%;" ";EOF#F%:CLOSE#F%',
 'F%=OPENUP "ADFS::1.$.WRITTEN/DAT":PTR#F%=EXT#F%:BPUT#F%,65:PRINT "EXTENDED ";EXT#F%:CLOSE#F%',
 'F%=OPENOUT "ADFS::1.$.LongFileName/TXT":BPUT#F%,66:CLOSE#F%:PRINT "LONG DONE"',
 'F%=OPENOUT "ADFS::1.$.Bad/Text"',
 'F%=OPENIN "ADFS::1.$.MISSING/TXT":PRINT "MISSING ";F%',
 'SYS "OS_Module",18,"DOSFS" TO ,,,B%,W%:PRINT "BASE ";~B%;" ";~!B%;" ";~B%!4;" ";!W%','QUIT',
 '*CDir ADFS::1.$.NEWDIR','*Copy ADFS::0.$.ReadMe ADFS::1.$.NEWDIR.INNER/TXT ~C~V','*Delete ADFS::1.$.OLD/TXT',
 '*Rename ADFS::1.$.HELLO/TXT ADFS::1.$.GREET/TXT','*DOSMap TXT FFF','*DOSMap','*Info ADFS::1.$.*',
 '*Type ADFS::1.$.MISSING/TXT','*Delete ADFS::1.$.SUBDIR','*Type ADFS::1.$.GREET/TXT','DUMP:written',
 'BASIC',LAYOUT,
 'DIM fs% 64:SYS "DOSFS_DiscFormat",fs%,&40246,1,1:PRINT "DISCFORMAT ";fs%!0;" ";fs%?16;" ";fs%?17;" ";fs%?18;" ";fs%?19;" ";fs%!24',
 # The structure stage of *Format (ADFS s/MFormat): open the whole disc and lay it out.
 'SYS "OS_Find",&CF,"adfs::1" TO F%:SYS "DOSFS_LayoutStructure",1,bad%,"ARCFMT",F%:CLOSE#F%:PRINT "LAID OUT"',
 'QUIT','*Dismount :1','*Cat ADFS::1.$','*Copy ADFS::0.$.ReadMe ADFS::1.$.AFTER/TXT ~C~V','*Cat ADFS::1.$',
 '*RMKill DOSFS','*Cat ADFS::1.$','*Run ADFS::0.$.DOSFS','*Help DOSMap','*Cat ADFS::1.$','DUMP:laid',
 '*Format 1 DOS/M','KEYS:Y','WAIT:240','*Copy ADFS::0.$.ReadMe ADFS::1.$.FMT/TXT ~C~V','*Cat ADFS::1.$','DUMP:formatted',
 # *CopyBoot from the laid-out disc in drive 1 to a second host-made PC disc.
 'INSERT0:{dir}/second.hfe','*CopyBoot 1 0','*Cat ADFS::0.$','DUMP0:copyboot']
NEGATIVE=['*Help DOSMap','*Cat ADFS::1.$','BASIC',LAYOUT,'QUIT','DUMP:untouched']
def trial(n,commands=COMMANDS,name=None):
 p=out/(name or f'cold-{n}');shutil.rmtree(p,ignore_errors=True);p.mkdir()
 (p/'drive0.adf').write_bytes(module_disc);(p/'drive1.hfe').write_bytes(pc_hfe);(p/'second.hfe').write_bytes(second_hfe)
 run([exe,root/'arclibre.rom',root,p/'drive0.adf',p/'drive1.hfe',p,*[c.replace('{dir}',str(p)) for c in commands]],p.name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((root/'arclibre.rom').read_bytes()),r
 assert not r['drive1_faults'],r['drive1_faults'][:4]
 return p,r
def text_after(r,i,echo=None):
 """What followed the echo of command i (or of `echo`) on the screen taken
 after it: its most recent echo line starts with the * or > prompt and long
 echoes wrap at 80 columns."""
 cmd=echo or r['commands'][i];lines=r['screens'][i];head=cmd[:79]
 for j in range(len(lines)-1,-1,-1):
  if lines[j][:1] in '*>' and lines[j][1:].startswith(head):break
 else:raise AssertionError(('no echo',cmd))
 return '\n'.join(l.rstrip() for l in lines[j+(len(cmd)+80)//80:]).rstrip()
def index(r,cmd):return r['commands'].index(cmd)
def boot_matches_template(sector):
 template=(R/'build/dosfs/DOSFS,ffa').read_bytes()[verification['boot_sector']['offset']:verification['boot_sector']['offset']+512]
 return sector==template
def check(pr):
 p,r=pr;t=lambda c:text_after(r,index(r,c));obs={}
 # Module loads from disc; international help comes from its registered Messages.
 assert 'Module is: DOSFS' in t('*Help DOSFS') and '0.62' in t('*Help DOSFS') and 'DOSMap  CopyBoot' in t('*Help DOSFS')
 assert '*DOSMap specifies an MSDOS extension to RISC OS filetype mapping.' in t('*Help DOSMap') and 'Syntax: *DOSMap [<MSDOS extension> [<RISC OS filetype>]]' in t('*Help DOSMap')
 cat=t('*Cat ADFS::1.$');assert 'Dir. ADFS::HOSTDISC.$' in cat
 assert sorted(re.findall(r'(\S+)\s+(?:D/|WR/)',cat))==sorted(['SUBDIR','DATA/BIN','EMPTY/DAT','HELLO/TXT','OLD/TXT']),cat
 ex=t('*Ex ADFS::1.$.SUBDIR');assert re.search(r'^NESTED/TXT\s+WR/\s+DOS\s+12:30:00 01-Oct-2026 1500  bytes$',ex,re.M),ex
 assert re.search(r'^HELLO 35 35 35 -1$',t(COMMANDS[9]),re.M) and re.search(r'^EMPTY 0 -1$',t(COMMANDS[12]),re.M) and re.search(r'^EXTENDED 3001$',t(COMMANDS[13]),re.M)
 assert re.search(r'^LONG DONE$',t(COMMANDS[14]),re.M)
 assert "The name 'Bad/Text' contains characters that can not be converted" in t(COMMANDS[15]),t(COMMANDS[15])
 assert re.search(r'^MISSING 0$',t(COMMANDS[16]),re.M)
 # Loaded in the RMA, not at its &8000 link address: the header's first two
 # words (start 0, init offset) read back from there.
 base=re.search(r'^BASE ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]+) (\d+)$',t(COMMANDS[17]),re.M).groups()
 # The stubs' RMA block: its size word is the RW template plus 12 header bytes.
 assert int(base[3])==verification['rma_workspace_bytes'],base
 assert 0x1800000<=int(base[0],16)<0x1C00000 and int(base[1],16)==0 and int(base[2],16)==struct.unpack_from('<I',module,4)[0],base
 obs['module_base']=base[0]
 assert re.search(r'TXT\s+Text\s+FFF',t('*DOSMap')),t('*DOSMap')
 info={m[0]:(m[1],m[2]) for m in re.findall(r'^(\S+)\s+\S+\s+(\S+)\s+\S+ \S+\s+(\d+ +K?bytes?)$',t('*Info ADFS::1.$.*'),re.M)}
 assert info=={'SUBDIR':('Directory','0  bytes'),'DATA/BIN':('DOS','5 Kbytes'),'EMPTY/DAT':('DOS','0  bytes'),'GREET/TXT':('Text','35  bytes'),'README/TXT':('Text','%d  bytes'%len(README)),
  'WRITTEN/DAT':('Data','3001  bytes'),'ZERO/DAT':('Data','0  bytes'),'LONGFILE/TXT':('Data','1  byte'),'NEWDIR':('Directory','0  bytes')},info
 assert "File 'ADFS::1.$.MISSING/TXT' not found" in t('*Type ADFS::1.$.MISSING/TXT')
 assert "Directory 'SUBDIR' not empty" in t('*Delete ADFS::1.$.SUBDIR')
 assert 'Hello from a host-made FAT12 disc' in t('*Type ADFS::1.$.GREET/TXT')
 df=re.search(r'^DISCFORMAT (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',t(COMMANDS[COMMANDS.index(LAYOUT)+1]),re.M).groups()
 # 720K PC: 512-byte sectors, 9 per track, double density (MFM), index mark,
 # sides alternate, first sector ID 1, 80 cylinders x 2 sides.
 assert tuple(map(int,df))==(512,9,2,1,1,160),df
 assert re.search(r'^LAYOUT DONE$',t(LAYOUT),re.M) and 'LAID OUT' in t(COMMANDS[COMMANDS.index(LAYOUT)+2])
 cats=[i for i,c in enumerate(r['commands']) if c=='*Cat ADFS::1.$']
 assert 'Dir. ADFS::ARCFMT.$' in text_after(r,cats[1]) and not re.search(r'WR/',text_after(r,cats[1])),text_after(r,cats[1])
 assert re.search(r'AFTER/TXT\s+WR/',text_after(r,cats[2]))
 killed=text_after(r,cats[3]);assert 'ARCFMT' not in killed and 'AFTER/TXT' not in killed,killed
 assert 'Disc not understood - has it been formatted?' in killed,killed;obs['after_rmkill']='Disc not understood - has it been formatted?'
 helps=[i for i,c in enumerate(r['commands']) if c=='*Help DOSMap'];assert '*DOSMap specifies' in text_after(r,helps[1])
 assert re.search(r'AFTER/TXT\s+WR/',text_after(r,cats[4])),'reloaded module reads the disc again'
 # --- The PC disc as DOSFS left it, read by the independent host parser ---
 w=fat12_fixture.Volume((p/'written.img').read_bytes())
 expect={'DATA.BIN':DATA,'EMPTY.DAT':b'','GREET.TXT':HELLO,'README.TXT':README,'WRITTEN.DAT':WRITTEN,'ZERO.DAT':b'','LONGFILE.TXT':b'B',
  'SUBDIR/NESTED.TXT':NESTED,'NEWDIR/INNER.TXT':README}
 assert w.files()==expect,sorted(w.files())
 assert w.dirs()==['NEWDIR','SUBDIR'] and w.label=='HOSTDISC' and w.boot==pc_image[:512]
 assert w.free==w.clusters-sum(len(v['chain']) for v in w.tree.values()),'freed OLD.TXT and allocated exactly the new chains'
 for k in ['DATA.BIN','SUBDIR/NESTED.TXT','SUBDIR']:assert w.tree[k]['chain']==before.tree[{'GREET.TXT':'HELLO.TXT'}.get(k,k)]['chain'],k
 assert w.tree['GREET.TXT']['chain']==before.tree['HELLO.TXT']['chain'] and w.tree['GREET.TXT']['date']==before.tree['HELLO.TXT']['date']
 # Copies keep the RISC OS timestamp: 27 Oct 2026 00:00:00 as a DOS date/time.
 assert (w.tree['README.TXT']['date'],w.tree['README.TXT']['time'])==(((2026-1980)<<9)|(10<<5)|27,0)
 assert all(not v['attr']&0x10 or k in ('NEWDIR','SUBDIR') for k,v in w.tree.items())
 # --- Files DOSFS read, copied to the ADFS disc, and its layout file -------
 a=adfs_files((p/'disc0.adf').read_bytes())
 assert a['DataCopy']==DATA and a['NestCopy']==NESTED and a['DOSFS']==module and a['ReadMe']==README
 layout=a['Layout'];assert len(layout)==14*512,len(layout)
 assert boot_matches_template(layout[:512]),'DOS/M layout equals the ArcLibre template'
 for k in (0,1):assert layout[512*(1+3*k):512*(4+3*k)]==b'\xf9\xff\xff'+bytes(1533),'fresh FAT %d'%k
 root=layout[7*512:];assert root[0:11]==b'ARCTEST\0\0\0\0' and root[11]==0x28 and root[32:]==bytes(len(root)-32),root[:32]
 lv=fat12_fixture.Volume(layout+bytes(737280-len(layout)));assert lv.files()=={} and lv.free==lv.clusters==713
 # --- The drive laid out like *Format's structure stage -------------------
 laid=(p/'laid.img').read_bytes();lv=fat12_fixture.Volume(laid)
 assert boot_matches_template(laid[:512]) and laid[0:11]==b'\xeb\x3c\x90ARCLIBRE'
 assert lv.files()=={'AFTER.TXT':README} and lv.dirs()==[] and lv.label=='ARCFMT\0\0\0\0\0'
 boot=check_dosfs_boot.check(laid[:512],*check_dosfs_boot.tables(module[:verification['relocation_code_offset']],verification['symbols'],0x8000))
 # *Format: all 160 tracks written through the delivered FileCore (no FSLock
 # check), then the fresh disc takes a file and the host parser reads it.
 fmt=text_after(r,index(r,'WAIT:240'),'*Format 1 DOS/M')
 assert 'A total of 160 tracks need to be formatted' in fmt and 'Formatting track 160' in fmt and 'not known' not in fmt,fmt
 assert re.search(r'FMT/TXT\s+WR/',text_after(r,cats[5])),text_after(r,cats[5])
 formatted=(p/'formatted.img').read_bytes();fv=fat12_fixture.Volume(formatted)
 assert formatted[0:11]==b'\xeb\x3c\x90ARCLIBRE' and formatted[11:0x1E]==layout[11:0x1E] and formatted[0x1E:0x200]==layout[0x1E:0x200],'DOS/M BPB and ArcLibre boot code'
 assert fv.files()=={'FMT.TXT':README} and fv.dirs()==[],fv.files().keys()
 fboot=check_dosfs_boot.check(formatted[:512],*check_dosfs_boot.tables(module[:verification['relocation_code_offset']],verification['symbols'],0x8000))
 obs['format']=dict(tracks=160,files=sorted(fv.files()),free_clusters=fv.free,boot_check=fboot['status'],bpb_sha256=sha(formatted[11:0x1E]))
 # *CopyBoot: the jump, OEM name and 480 bytes of boot code come from the source;
 # the destination keeps its BPB, signature, FATs and files.
 cbt=text_after(r,index(r,'*CopyBoot 1 0'));assert cbt in ('*','*_'),cbt  # different drives: no prompt, no error
 assert 'Dir. ADFS::HOSTTWO.$' in text_after(r,index(r,'*Cat ADFS::0.$')) and re.search(r'KEEP/TXT\s+WR/',text_after(r,index(r,'*Cat ADFS::0.$')))
 cb=(p/'copyboot.img').read_bytes()
 assert cb[0:11]==formatted[0:11] and cb[0x1E:0x1FE]==formatted[0x1E:0x1FE],'jump, OEM name and boot code copied'
 assert cb[11:0x1E]==second_image[11:0x1E] and cb[0x1FE:]==second_image[0x1FE:],'destination BPB and contents kept'
 cv=fat12_fixture.Volume(cb);assert cv.files()=={'KEEP.TXT':b'kept\r\n'} and cv.label=='HOSTTWO'
 x=check_dosfs_boot.run_x86(cb);assert x['text']==check_dosfs_boot.MESSAGE and x['ended']=='INT 19h'
 obs['copyboot']=dict(code_from_source=True,bpb_kept=True,message_after_copy=True)
 obs.update(cat=cat.splitlines()[-2:],info=info,discformat=df,written=dict(free=w.free,files={k:len(v) for k,v in w.files().items()}),
  layout_sha256=sha(layout),laid_sha256=sha(laid[:7*1024]),boot_check=boot['status'],help_lines=len(t('*Help DOSMap').splitlines()))
 return obs
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=[check(x) for x in pool.map(trial,COLD)]
same(results)
(out/'observations.json').write_text(json.dumps(results[0],indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',results[0],'DOSFS')
# Negative control: the same disc and commands without loading DOSFS.
p,r=trial(0,NEGATIVE,'negative-no-dosfs');t=lambda c:text_after(r,index(r,c))
assert 'No help found.' in t('*Help DOSMap') and '*DOSMap specifies' not in t('*Help DOSMap'),t('*Help DOSMap')
cat=t('*Cat ADFS::1.$');assert 'HOSTDISC' not in cat and 'WR/' not in cat,cat
assert 'SWI name not known' in t(LAYOUT) and 'LAYOUT DONE' not in t(LAYOUT),t(LAYOUT)
assert (p/'untouched.img').read_bytes()==pc_image,'disc unchanged without DOSFS'
assert adfs_files((p/'disc0.adf').read_bytes())['Layout']==b'','the file opened for the layout stays empty'
assert 'Disc not understood - has it been formatted?' in cat
negative=dict(help='No help found.',cat='Disc not understood - has it been formatted?',layout='SWI name not known',pc_disc_unchanged=True,layout_file_empty=True)
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),module_sha256=verification['module_sha256'],module_disc_sha256=sha(module_disc),
 pc_disc_sha256=sha(pc_image),identical_repetitions=True,guest_code_injection=False,emulator_unchanged=True,independent_fat_parser='tests/fat12_fixture.py',
 observations=results[0],negative_control=negative,
 limits=['*Format DOS/M writes all 160 tracks of an HFE image under MacArch; real drive timing and other DOS formats are not exercised.']))
print('DOSFS PASS',flush=True)
