#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The disc-loaded DOSFS beyond 720K floppies: 1.44M, 360K and FAT16 partitions.

tests/run_dosfs.py covers 720K FAT12 floppies on an A440's 1772. This gate
uses NewIOProbe (typing at the real F12 command line, DOSFS *RMLoaded from
its own disc in drive 0), three cold boots each, with PC media written on the
host by tests/fat12_fixture.py and tests/hfe_fixture.py and checked there
afterwards by the same strict parser:

- 1.44M (DOS/Q, 18 sectors, 500 kbit/s) on an A5000's 765: catalogue; a
  file copied to the ADFS disc; *Save from memory and *Copy within the PC
  disc.
- 360K (DOS/N, 40 tracks) on an A440's 1772, which DOSFS double-steps:
  catalogue and a copy each way.
- A FAT16 DOS partition (a 4 MB partitioned image, filetype &FC8) on an
  A5000's IDE disc, opened as an image directory: catalogue of it and a
  subdirectory, a 300,000-byte file copied out to ADFS and a file copied in
  from the floppy.

The negative control is the A5000 media without DOSFS loaded: the PC floppy
is not understood and the partition is only a file.
"""
import concurrent.futures,hashlib,json,os,pathlib,random,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tests'))
import fat12_fixture,hfe_fixture
from verify_filer_disc import read_directory
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/dosfs-format-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-newio','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','NewIOProbe'],'harness')
exe=R/'build/harness-newio/release/NewIOProbe'
module_disc=(R/'build/dosfs/arclibre-dosfs.adf').read_bytes();README=(R/'src/ArcLibre/dosfs/ReadMe').read_bytes()
rng=random.Random(1996);DATA=bytes(rng.randrange(256) for _ in range(5000));BIG=bytes(rng.randrange(256) for _ in range(300000))
MEM=bytes((i*7+3)&255 for i in range(3000))
media=out/'media';media.mkdir(exist_ok=True)
(media/'hd.hfe').write_bytes(hfe_fixture.hfe(fat12_fixture.make({'HELLO.TXT':b'High density\r\n','DATA.BIN':DATA},label='HDDISC',g=fat12_fixture.GEOMETRY_1440K),spt=18))
(media/'q.hfe').write_bytes(hfe_fixture.hfe(fat12_fixture.make({'OLD.TXT':b'Forty tracks\r\n'},label='DISC360',g=fat12_fixture.GEOMETRY_360K),double_step=True))
(media/'part.img').write_bytes(fat12_fixture.partitioned(fat12_fixture.make({'BIG.BIN':BIG,'SUB':None,'SUB/X.TXT':b'abc'},label='PCPART',g=fat12_fixture.GEOMETRY_FAT16_4M)))
LOAD='*RMLoad ADFS::0.$.DOSFS'
# Writes to the PC floppy stay on its drive: MacArch's 765 raises disc changed
# only while a drive is empty, so ADFS never learns that the line works and
# marks a drive maybe-changed at each motor start; FileCore then re-identifies
# the disc mid-copy, and a DOS disc's identity (its FAT's checksum) is already
# the new FAT's. Real drives also raise it from power-on until a step.
HD=['DISC1:{m}/hd.hfe',LOAD,'*Cat ADFS::1.$','*Copy ADFS::1.$.DATA/BIN ADFS::0.$.DataCopy ~C~V','BASIC','FOR i%=0 TO 2999:i%?&9000=(i%*7+3) AND 255:NEXT',
 '*Save ADFS::1.$.MEM/BIN 9000 +BB8','*Copy ADFS::1.$.DATA/BIN ADFS::1.$.COPY/BIN ~C~V','QUIT','WAIT:5','DUMP1:hd,18,80']
Q=['DISC1:{m}/q.hfe',LOAD,'*Cat ADFS::1.$','*Copy ADFS::0.$.ReadMe ADFS::1.$.README/TXT ~C~V','*Copy ADFS::1.$.OLD/TXT ADFS::0.$.Old ~C~V','WAIT:5','DUMP1:q,9,40,double']
PART=['IDE:PCDisc,FC8,{m}/part.img',LOAD,'*Cat ADFS::4.$.PCDisc','*Cat ADFS::4.$.PCDisc.SUB','*Copy ADFS::4.$.PCDisc.BIG/BIN ADFS::4.$.BigCopy ~C~V',
 '*Copy ADFS::0.$.ReadMe ADFS::4.$.PCDisc.SUB.README/TXT ~C~V','WAIT:5']
def trial(model,cmds,name):
 p=out/name;shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'disc0.in.adf').write_bytes(module_disc)
 run([exe,root/'arclibre.rom',root,model,'standard',p/'disc0.in.adf',p/'run',*[c.replace('{m}',str(media)) for c in cmds]],name)
 r=json.loads((p/'run/result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((root/'arclibre.rom').read_bytes()),r
 return p,r
def after(r,cmd):
 """The lines printed after a command's echo (the probe's commands exclude setup ones)."""
 i=r['commands'].index(cmd);s=r['screens'][i]
 j=max(k for k,l in enumerate(s) if cmd[:70] in l)+(len(cmd)+1+79)//80
 return '\n'.join(l.rstrip() for l in s[j:] if l.strip() and not l.startswith('?') and l.strip() not in ['*','>','*_','>_'])
def adfs(p,name):
 b=(p/'run/disc0.adf').read_bytes();e=read_directory(b,4)[name];return b[e['address']*256:e['address']*256+e['length']]
def files(cat):return sorted(re.findall(r'(\S+)\s+(?:WR/|D/)',cat))
def high_density(n):
 p,r=trial('A5000',HD,f'hd-{n}');assert not r['errors'] and not r['drive1_faults'],(r['errors'][:3],r['drive1_faults'][:3])
 cat=after(r,'*Cat ADFS::1.$');assert 'Dir. ADFS::HDDISC.$' in cat and files(cat)==['DATA/BIN','HELLO/TXT'],cat
 assert adfs(p,'DataCopy')==DATA
 v=fat12_fixture.Volume((p/'run/hd.img').read_bytes());fs=v.files()
 assert v.bits==12 and v.total==2880 and v.spt==18 and sorted(fs)==['COPY.BIN','DATA.BIN','HELLO.TXT','MEM.BIN'] and fs['MEM.BIN']==MEM and fs['COPY.BIN']==DATA,sorted(fs)
 return dict(format='1.44M DOS/Q on the A5000 765',catalogue=files(cat),written=sorted(fs),free_clusters=v.free)
def forty(n):
 p,r=trial('A440/1',Q,f'q-{n}');assert not r['errors'] and not r['drive1_faults'],(r['errors'][:3],r['drive1_faults'][:3])
 cat=after(r,'*Cat ADFS::1.$');assert 'Dir. ADFS::DISC360.$' in cat and files(cat)==['OLD/TXT'],cat
 assert adfs(p,'Old')==b'Forty tracks\r\n'
 v=fat12_fixture.Volume((p/'run/q.img').read_bytes());fs=v.files()
 assert v.total==720 and v.media==0xFD and sorted(fs)==['OLD.TXT','README.TXT'] and fs['README.TXT']==README,sorted(fs)
 return dict(format='360K DOS/N on the A440 1772, double-stepped',catalogue=files(cat),written=sorted(fs))
def fat16(n):
 p,r=trial('A5000',PART,f'fat16-{n}');assert not r['errors'],r['errors'][:3]
 cat=after(r,'*Cat ADFS::4.$.PCDisc');assert 'Dir. ADFS::IDEDisc.$.PCDisc' in cat and files(cat)==['BIG/BIN','SUB'],cat
 sub=after(r,'*Cat ADFS::4.$.PCDisc.SUB');assert files(sub)==['X/TXT'],sub
 assert (p/'run/ide/BigCopy').read_bytes()==BIG
 v=fat12_fixture.partition((p/'run/ide/PCDisc').read_bytes());fs=v.files()
 assert v.bits==16 and v.clusters>=4085 and sorted(fs)==['BIG.BIN','SUB/README.TXT','SUB/X.TXT'] and fs['SUB/README.TXT']==README and fs['BIG.BIN']==BIG,sorted(fs)
 return dict(format='FAT16 partition image (&FC8) on the A5000 IDE disc',fat_bits=16,clusters=v.clusters,catalogue=files(cat),written=sorted(fs),copied_out=len(BIG))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 h=list(pool.map(high_density,COLD));q=list(pool.map(forty,COLD));f16=list(pool.map(fat16,COLD))
same(h,q,f16)
obs=dict(high_density=h[0],forty_track=q[0],fat16=f16[0])
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'DOSFS formats')
# Negative control: the same A5000 media without DOSFS.
p,r=trial('A5000',['DISC1:{m}/hd.hfe','IDE:PCDisc,FC8,{m}/part.img','*Cat ADFS::1.$','*Cat ADFS::4.$.PCDisc'],'negative-without-dosfs')
floppy=after(r,'*Cat ADFS::1.$');part=after(r,'*Cat ADFS::4.$.PCDisc')
assert 'Dir. ADFS::HDDISC' not in floppy and 'Dir. ADFS::IDEDisc.$.PCDisc' not in part,(floppy,part)
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_control=dict(dosfs_loaded=False,floppy=floppy.splitlines()[-1] if floppy else '',partition=part.splitlines()[-1] if part else ''),
 limits=['Copies between a PC floppy and another drive on the 765 machines are not run: MacArch raises the 765 disc-changed line only while a drive is empty (real drives also from power-on until a step), so ADFS treats each motor start as maybe changed and FileCore re-identifies a DOS disc mid-copy.',
  'DOS/H (1.2M), DOS/P, DOS/T, DOS/U and the Atari formats, *Format of them, and physical drives are not exercised.']))
print('DOSFS formats PASS',flush=True)
