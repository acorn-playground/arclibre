#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The original NetFS, NetFiler and NetStatus against a file server.

NetFSProbe puts an A440/1 (Econet station 1) on an emulated line with a file
server at station 254 that runs on the host: the probe's own in-memory Acorn
file server, written from the documented file-server protocol (PRM, "File
server protocol interface") and the NetFS client source, attached through
MacArch's public EconetGateway. Its disc "Harness" holds ReadMe, Data (5000
bytes), Big (76,800 bytes of text) and Docs.Note; users SYST (no password)
and GUEST (password SECRET). Three cold boots each:

- F12 command line: the server's own errors for an unknown user, a wrong
  password and a non-empty directory; *ListFS finds the server by broadcast;
  *I Am; *Cat, *Ex, *Free, *Info; BASIC *Loads Data (its checksum matches the
  store's bytes), saves a file with OS_File 10, SAVEs and CHAINs a program,
  writes a file with OPENOUT/BPUT and reads it back with OPENIN/PTR/BGET/EXT/
  EOF; *CDir, *Rename into the new directory, *Access, *Dir and back, *Delete;
  *Bye, after which NetFS says it is not logged on. The server's store after
  the session is compared byte for byte with what the client wrote.
- Desktop: NetFiler's Net icon opens its logon box; logging on as SYST makes
  a "Harness" icon and a Filer viewer of the server's root; a subdirectory
  viewer; the icon's menu and its FS list (found by broadcast); Big
  double-clicked loads into Edit while NetStatus turns NetFS's upcalls into
  the hourglass percentage; Bye puts the Net icon back.

The negative control is the same logon with nothing answering for station
254: NetFS's own "cannot be found", and no server in *ListFS.
"""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1]
out=R/'build/netfs-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
root=R/'build/arclibre'
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-netfs','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','NetFSProbe'],'harness')
exe=R/'build/harness-netfs/release/NetFSProbe'
SUM='DIM b% 6000:OSCLI "Load Data "+STR$~b%:s%=0:FOR i%=0 TO 4999:s%=(s%*33+b%?i%) AND &FFFFFF:NEXT:PRINT "SUM ";s%'
SAVE='FOR i%=0 TO 2999:b%?i%=(i%*7+3) AND 255:NEXT:SYS "OS_File",10,"Saved",&FFD,,b%,b%+3000:PRINT "SAVED"'
OUT='c%=OPENOUT "Chan":FOR i%=1 TO 300:BPUT#c%,i% MOD 256:NEXT:PRINT "EXT ";EXT#c%:CLOSE#c%'
IN='c%=OPENIN "Chan":PTR#c%=100:PRINT "B ";BGET#c%;" PTR ";PTR#c%;" EXT ";EXT#c%;" EOF ";EOF#c%:CLOSE#c%'
MISSING='PRINT "IN ";OPENIN "Missing"'
CLI=['*I Am 0.254 Nobody','*I Am 0.254 Guest Wrong','*ListFS','*I Am 0.254 Syst','*Cat','*Ex','*Free','BASIC',SUM,SAVE,
 '10 PRINT "HELLO FROM THE FILE SERVER"','SAVE "Hello"','NEW','CHAIN "Hello"',OUT,IN,MISSING,'QUIT',
 '*CDir Sub','*Rename Hello Sub.Hello','*Access Chan LWR/R','*Info Chan','*Cat Sub','*Dir Sub','*Cat','*Dir $',
 '*Delete ReadMe','*Delete Docs','*Bye','*Cat']
NEGATIVE=['*I Am 0.254 Syst','*ListFS']
# OS coordinates (x=(px-96)*2, y=(272-py)*4 from the 832x288 frame): Net icon, the Harness icon,
# its menu's FS list/Free/Bye, the root viewer's Docs and Big, the Docs viewer's close icon.
NET,FS=(264,80),(272,80);FSLIST,FREE,BYE=(288,296),(288,164),(288,120);DOCS,BIG,CLOSE=(472,928),(96,928),(80,972)
p=lambda s,xy,*n:s+':'+','.join(map(str,xy+n))
DESKTOP=['SHOT:1-net-icon',p('CLICK',NET),'SHOT:2-logon','SYST','','WAIT:3','SHOT:3-logged-on',p('CLICK',DOCS,2),'WAIT:2','SHOT:4-docs',
 p('CLICK',CLOSE),p('MENU',FS),'SHOT:5-menu',p('CLICK',FSLIST),'WAIT:6','SHOT:6-fs-list',p('CLICK',BIG,2),'WATCH:7-netstatus','WAIT:5','SHOT:8-edit',
 p('MENU',FS),p('CLICK',FREE),'WAIT:2','SHOT:9-free',p('MENU',FS),p('CLICK',BYE),'WAIT:3','SHOT:10-bye']
def trial(server,mode,steps,name):
 d=out/name;shutil.rmtree(d,ignore_errors=True);run([exe,root/'arclibre.rom',root,d,server,mode,*steps],name)
 r=json.loads((d/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((root/'arclibre.rom').read_bytes())
 return r,d
def after(r,i):
 s=r['screens'][i];cmd=r['steps'][i][:70]
 j=max(k for k,l in enumerate(s) if cmd in l)
 return '\n'.join(l.rstrip() for l in s[j+1:] if l.strip() and not l.startswith('?') and l.strip() not in ['*','*_','>','>_'])
def node(tree,path):
 n=tree
 for c in path.split('.')[1:]:n=next((x for x in n.get('children',[]) if x['name']==c),None);assert n,path
 return n
def has(tree,path):
 try:node(tree,path);return True
 except AssertionError:return False
def data(tree,path):return bytes.fromhex(node(tree,path)['hex'])
def fns(r,f,**k):return [q for q in r['requests'] if q['function']==f and all(q.get(a)==b for a,b in k.items())]
def cli(n):
 r,_=trial('on','cli',CLI,f'cli-{n}');t=lambda x:after(r,CLI.index(x));before,after_=r['store_before'],r['store_after']
 assert t('*I Am 0.254 Nobody')=='User not known' and t('*I Am 0.254 Guest Wrong')=='Wrong password',(t('*I Am 0.254 Nobody'),t('*I Am 0.254 Guest Wrong'))
 assert fns(r,0,command='I am Nobody')[0]['result']=='&BC User not known' and fns(r,0,command='I am Guest')[0]['result']=='&BB Wrong password'
 assert re.search(r'^ +254 :0 Harness$',t('*ListFS'),re.M) and any(q.get('broadcast') and q['function']==14 for q in r['requests']),t('*ListFS')
 assert t('*I Am 0.254 Syst')=='' and fns(r,0,command='I am Syst')[0]['result']=='ok'
 cat=t('*Cat');assert 'Dir. Net::Harness.& Option 00 (Off) Owner' in cat and re.search(r'Big +WR/R +Data +WR/R +Docs +D/ +ReadMe +WR/R',cat),cat
 ex=t('*Ex')
 for l in ['Big          WR/r   Text      12:00:00 15-Oct-2026   75 Kbytes','Data         WR/r   Data      12:00:00 15-Oct-2026    5 Kbytes',
  'Docs         D/     Directory','ReadMe       WR/r   Text      12:00:00 15-Oct-2026   48  bytes']:assert l in ex,(l,ex)
 free=t('*Free');used=sum(1+(len(bytes.fromhex(x['hex']))+255)//256 for x in [node(before,'$.'+c) for c in ['ReadMe','Data','Big','Docs.Note']])+4
 assert re.search(r'Harness +0 +%s'%format((3200-used)*256,','),free) and 'User free space           %s'%format((3200-used)*256,',') in free,free
 s=0
 for b in data(before,'$.Data'):s=(s*33+b)&0xFFFFFF
 assert re.search(r'^SUM %d$'%s,t(SUM),re.M) and fns(r,10,count=5000),t(SUM)
 assert re.search(r'^SAVED$',t(SAVE),re.M) and data(after_,'$.Saved')==bytes((i*7+3)&255 for i in range(3000)) and node(after_,'$.Saved')['load'][:6]=='FFFFFD'
 hello=b'\r\x00\x0a\x23 \xf1 "HELLO FROM THE FILE SERVER"\r\xff'
 assert re.search(r'^HELLO FROM THE FILE SERVER$',t('CHAIN "Hello"'),re.M) and data(after_,'$.Sub.Hello')==hello and node(after_,'$.Sub.Hello')['load'][:6]=='FFFFFB'
 assert re.search(r'^EXT 300$',t(OUT),re.M) and re.search(r'^B 101 PTR 101 EXT 300 EOF 0$',t(IN),re.M) and re.search(r'^IN 0$',t(MISSING),re.M)
 assert data(after_,'$.Chan')==bytes(i%256 for i in range(1,301)) and node(after_,'$.Chan')['access']=='LWR/R' and fns(r,11) and fns(r,13)
 assert re.match(r'Chan +LWR/R +Data ',t('*Info Chan')),t('*Info Chan')
 assert 'Dir. Net::Harness.&.Sub' in t('*Cat Sub') and re.search(r'^Hello +WR/R$',t('*Cat Sub'),re.M)
 i=CLI.index('*Dir Sub')+1;assert 'CSD  Net::Harness.&.Sub' in after(r,i) and re.search(r'^Hello +WR/R$',after(r,i),re.M),after(r,i)
 assert node(after_,'$.Sub')['type']=='directory' and not has(after_,'$.Hello') and not has(after_,'$.ReadMe') and t('*Delete ReadMe')==''
 assert t('*Delete Docs')=='Dir not empty' and fns(r,20,name='Docs')[0]['result']=='&B4 Dir not empty' and data(after_,'$.Docs.Note')==data(before,'$.Docs.Note')
 assert data(after_,'$.Big')==data(before,'$.Big') and data(after_,'$.Data')==data(before,'$.Data')
 assert fns(r,23) and after(r,len(CLI)-1)=='Not logged on'
 assert not any(k.startswith('dropped') for k in r['transport']),r['transport']
 return dict(errors=dict(unknown_user='User not known',wrong_password='Wrong password',non_empty_directory='Dir not empty'),listfs='254 :0 Harness',
  data_checksum=s,saved=dict(length=3000,sha256=sha(data(after_,'$.Saved'))),basic_program=hello.hex(),chan=dict(extent=300,access='LWR/R'),
  functions=sorted({q['function'] for q in r['requests']}),requests=len(r['requests']),store_after=sha(json.dumps(after_,sort_keys=True).encode()))
def desktop(n):
 r,d=trial('on','desktop',DESKTOP,f'desktop-{n}')
 assert r['netfiler_icons']==['Net ','Harness','Net '],r['netfiler_icons']
 c=r['netfiler_commands'];assert 'Filer_OpenDir net::Harness.&' in c and 'net:%Bye :Harness' in c and any('Logon' in x for x in c),c
 assert [q['command'] for q in fns(r,0) if q['command'].startswith('I am')]==['I am SYST']
 ex=fns(r,3,argument=0);assert [q['entries'] for q in ex if q['entries']]==[['Big','Data','Docs','ReadMe'],['Note']],ex
 assert any(q.get('broadcast') for q in r['requests']) and fns(r,6,name='Big') and sum(q['count'] for q in fns(r,10))==76800 and fns(r,23)
 pc=r['netstatus_percentages'];assert pc and pc==sorted(pc) and pc[-1]==100 and any(0<x<100 for x in pc),pc
 # NetFiler's Free opens the Free module's window, which asks the server for its
 # disc's and the user's free space (functions 26 and 30), with no error.
 assert 'ShowFree -FS NET :Harness' in c and not r['reported_errors'],r['reported_errors']
 assert fns(r,26) and fns(r,30),[q['function'] for q in r['requests']]
 shots={k:sha((d/(k+'.png')).read_bytes()) for k in r['shots']}
 return dict(icons=r['netfiler_icons'],commands=[x for x in c if not x.startswith('%')],root_viewer=['Big','Data','Docs','ReadMe'],docs_viewer=['Note'],
  big_bytes=76800,netstatus_percentages=pc,free_window='ShowFree -FS NET :Harness, functions 26 and 30',screenshots=shots)
results=[dict(cli=cli(n),desktop=desktop(n)) for n in COLD];same(results)
(out/'observations.json').write_text(json.dumps(results[0],indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',results[0],'NetFS')
r,_=trial('off','cli',NEGATIVE,'negative-server-off')
assert 'The network station 254 cannot be found' in after(r,0).replace('\n',''),after(r,0)
assert 'Harness' not in after(r,1) and not r['requests'],after(r,1)
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),profile='delivered',observations=results[0],
 negative_control=dict(server='off',logon='The network station 254 cannot be found',listfs='no file servers'),
 limits=['The file server is this gate\'s own (one disc, two users, owner access only, 24-bit files), written from the public protocol; no Acorn server is run.',
  'One client station; no two clients sharing the server at once.',
  'NetStatus is seen through its Hourglass_Percentage calls and screenshots; its colour hourglass (broadcast load/save) is not exercised.',
  'Server functions 28, 31 and 33 onwards answer "Bad command"; NetFS does not use them.']))
print('NetFS PASS',flush=True)
