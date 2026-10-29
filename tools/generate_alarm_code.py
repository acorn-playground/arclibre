#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate Alarm's Resources.Code by running its original AlarmSrc assembler.

The original Makefile builds Code by running bas.AlarmSrc in BBC BASIC. This
does the same, in the ROM's own BASIC 1.14 under the pinned MacArch core: a
generated floppy holds AlarmSrc and an empty Resources directory, AlarmSrc is
run at the real F12 command line, and the file it saves is extracted. Two
independent runs must produce identical bytes. The ROM used is the profile
without the BASIC utilities, so building it never needs this output.
"""
import hashlib,json,os,pathlib,shutil,subprocess,sys
from paths import REPO,SRC
sys.path.insert(0,str(REPO/'tests'))
from adfs_fixture import directory,entry,u24,oldcheck
from verify_filer_disc import read_directory
OUT=REPO/'build/alarm-code';OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 with (OUT/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=REPO,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
source=(SRC/'Alarm/bas/AlarmSrc,ffb').read_bytes()
# 1 KiB-aligned files on an old-map ADFS D floppy, with an empty Resources directory.
disc=bytearray(819200)
disc[12*256:12*256+2048]=directory('Resources',4,[],b'Hugo')
offset=8*1024;disc[offset:offset+len(source)]=source
disc[0x400:0xc00]=directory('$',4,[entry('Resources',12,directory=True),entry('AlarmSrc',offset//256,source,load=0xfffffb00)],b'Hugo')
end=(offset+len(source)+1023)&~1023
u24(disc,0,end//256);u24(disc,256,(819200-end)//256);u24(disc,252,3200)
name=b'ALARMBUILD'
for i in range(5):disc[247+i]=name[2*i];disc[502+i]=name[2*i+1]
disc[507:509]=b'\x41\x42';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
rom_root=REPO/'build/arclibre-without-basic-utilities'
run([sys.executable,REPO/'tools/build_arclibre_rom.py','--without-basic-utilities'],'rom')
# A clean checkout has no extracted core yet; prepare the pinned one as the tests do.
(OUT/'emulator/artifacts').mkdir(parents=True,exist_ok=True)
with (OUT/'emulator.log').open('w') as f:subprocess.run([sys.executable,str(REPO/'tools/prepare_emulator.py')],cwd=REPO,env=dict(os.environ,OPEN_ARCHIMEDES_OUTPUT=str(OUT/'emulator')),stdout=f,stderr=subprocess.STDOUT,check=True)
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-alarm-code','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','BasicRunProbe'],'harness')
codes=[]
for n in [1,2]:
 p=OUT/f'run-{n}';shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(disc)
 run([REPO/'build/harness-alarm-code/release/BasicRunProbe',rom_root/'arclibre.rom',rom_root,p/'input.adf',p,'*Dir adfs::0.$','/AlarmSrc'],f'run-{n}')
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS'
 b=(p/'disc.adf').read_bytes();assert b[255]==oldcheck(b[:255]) and b[511]==oldcheck(b[256:511])
 rows=read_directory(b,read_directory(b,4)['Resources']['address']);assert set(rows)=={'Code'},rows
 row=rows['Code'];codes.append(b[row['address']*256:row['address']*256+row['length']])
assert codes[0]==codes[1],'two independent assemblies differ'
(OUT/'Code').write_bytes(codes[0])
(OUT/'result.json').write_text(json.dumps(dict(status='PASS',source='src/Alarm/bas/AlarmSrc,ffb',source_sha256=sha(source),interpreter='ROM BASIC 1.14 under MacArch',rom_sha256=sha((rom_root/'arclibre.rom').read_bytes()),bytes=len(codes[0]),sha256=sha(codes[0]),identical_runs=2),indent=2)+'\n')
print('Alarm Code',len(codes[0]),'bytes',sha(codes[0]))
