#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The original networking modules on two emulated Econet stations.

The modules are in the delivered ROM (Alarm moved to disc to make room).
NetProbe puts two A440s on one emulated line (stations 1 and 2) and types at
their F12 command lines:

- Econet: station 2 opens a receive block on port &50 for station 1; station 1
  transmits; station 2 reads status Received, port, sender, length and the
  exact bytes. A broadcast from station 2 reaches station 1's wildcard
  receive. Econet_ReadLocalStationAndNet gives each station its number.
- NetFS: its tokenised *Help, *Configure FS / *Status FS, and *I Am to an
  absent file server, which gives NetFS's own "cannot be found" error.
- NetPrint and BBCEconet answer *Help.

The negative control is the same ROM built without the networking modules
(`build_arclibre_rom.py --without-network`): the commands and SWIs are
unknown. NetFS against a file server, NetFiler and NetStatus are in
tests/run_netfs.py.
"""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1]
out=R/'build/network-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
# The delivered ROM (make arclibre-rom) already built and joined the modules;
# rebuilding them here would race other gates' negative-control ROM joins.
root=R/'build/arclibre'
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-net','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','NetProbe'],'harness')
exe=R/'build/harness-net/release/NetProbe'
RX='DIM b% 64:SYS "Econet_CreateReceive",&50,1,0,b%,64 TO h%:PRINT "RX ";h%'
TX='DIM t% 64:$t%="HELLO ARCLIBRE"+CHR$13:SYS "Econet_DoTransmit",0,&50,2,0,t%,15,5,20 TO s%:PRINT "TX ";s%'
READ='SYS "Econet_ExamineReceive",h% TO s%:SYS "Econet_ReadReceive",h% TO r0%,f%,p%,st%,n%,bb%,l%:PRINT "ST ";s%;" P ";p%;" FROM ";st%;" LEN ";l%;" ";$b%'
BRX='DIM c% 64:SYS "Econet_CreateReceive",&51,255,255,c%,64 TO g%:PRINT "BRX ";g%'
BTX='DIM u% 16:$u%="ALL"+CHR$13:SYS "Econet_DoTransmit",0,&51,255,255,u%,4,5,20 TO s%:PRINT "BTX ";s%'
BREAD='SYS "Econet_ExamineReceive",g% TO s%:SYS "Econet_ReadReceive",g% TO r0%,f%,p%,st%,n%,bb%,l%:PRINT "BST ";s%;" P ";p%;" FROM ";st%;" LEN ";l%;" ";$c%'
ME='SYS "Econet_ReadLocalStationAndNet" TO st%,n%:PRINT "ME ";st%;" ";n%'
COMMANDS=['A:*Help Econet','A:*Help NetFS','A:*Configure FS 0.254','A:*Status FS','A:*I Am Syst','A:*Help NetPrint','A:*Help BBCEconet',
 'B:BASIC',f'B:{RX}','A:BASIC',f'A:{TX}',f'B:{READ}',f'A:{BRX}',f'B:{BTX}',f'A:{BREAD}',f'A:{ME}',f'B:{ME}']
NEGATIVE=['A:*Help Econet','A:BASIC',f'A:{ME}']
def trial(rom_root,cmds,name):
 p=out/name;shutil.rmtree(p,ignore_errors=True);run([exe,rom_root/'arclibre.rom',rom_root,p,*cmds],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((rom_root/'arclibre.rom').read_bytes())
 return r
def after(r,i):
 c=r['commands'][i];m=c[0];s=r['screens'][i][m];cmd=c[2:][:70]
 j=max(k for k,l in enumerate(s) if cmd in l)
 return '\n'.join(l.rstrip() for l in s[j+1:] if l.strip() and not l.startswith('?'))
def check(n):
 r=trial(root,COMMANDS,f'cold-{n}');c=r['commands'];t=lambda x:after(r,c.index(x))
 assert 'Module is: Econet' in t('A:*Help Econet') and '5.70' in t('A:*Help Econet')
 assert re.search(r'AddFS\s+Bye\s+Free\s+FS\s+ListFS\s+Logon',t('A:*Help NetFS')),t('A:*Help NetFS')
 assert 'File server 254' in t('A:*Status FS')
 assert 'The network station 254 cannot be found' in t('A:*I Am Syst').replace('\n','')
 assert 'SetPS' in t('A:*Help NetPrint') and 'Module is: BBCEconet' in t('A:*Help BBCEconet')
 assert re.search(r'^RX \d+$',t(f'B:{RX}'),re.M) and re.search(r'^TX 0$',t(f'A:{TX}'),re.M)
 assert re.search(r'^ST 9 P 80 FROM 1 LEN 15 HELLO ARCLIBRE$',t(f'B:{READ}'),re.M),t(f'B:{READ}')
 assert re.search(r'^BST 9 P 81 FROM 2 LEN 4 ALL$',t(f'A:{BREAD}'),re.M),t(f'A:{BREAD}')
 assert re.search(r'^ME 1 0$',t(f'A:{ME}'),re.M) and re.search(r'^ME 2 0$',t(f'B:{ME}'),re.M)
 return dict(econet_version='5.70',station_to_station=dict(status='Received',port=0x50,sender=1,bytes=15,data='HELLO ARCLIBRE'),
  broadcast=dict(status='Received',port=0x51,sender=2,bytes=4),netfs_absent_server="The network station 254 cannot be found",netprint_help=True,bbceconet_help=True,stations=[1,2])
results=[check(n) for n in COLD];same(results)
(out/'observations.json').write_text(json.dumps(results[0],indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',results[0],'Network')
run([sys.executable,R/'tools/build_arclibre_rom.py','--without-network'],'negative-rom')
neg=R/'build/arclibre-without-network';assert not {'Econet','NetFS'}&{m['component'] for m in json.loads((neg/'rom-layout.json').read_text())['modules']}
r=trial(neg,NEGATIVE,'negative-without-network')
assert 'No help found' in after(r,0) and 'SWI name not known' in after(r,2),(after(r,0),after(r,2))
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),profile='delivered',observations=results[0],
 negative_control=dict(rom_sha256=sha((neg/'arclibre.rom').read_bytes()),help='No help found',swi='SWI name not known'),
 limits=['No file server here: NetFS logon, catalogue, load and save, NetFiler and NetStatus are in tests/run_netfs.py.']))
print('Network PASS',flush=True)
