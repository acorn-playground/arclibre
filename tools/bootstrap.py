#!/usr/bin/env python3
"""Build pinned public host tools locally, from bundled unmodified sources."""
import hashlib,json,os,pathlib,shutil,subprocess,tarfile
from paths import REPO,ROOT,HOST,TOOLS
manifest=json.loads((REPO/'manifests/toolchain.json').read_text());logs=REPO/'build/logs';logs.mkdir(parents=True,exist_ok=True)
for name,digest in manifest['archives'].items():assert hashlib.sha256((REPO/'third_party/archives'/name).read_bytes()).hexdigest()==digest,name
TOOLS.mkdir(parents=True,exist_ok=True);HOST.mkdir(exist_ok=True)
# Homebrew names GNU libtoolize glibtoolize beside Apple's libtool; Linux keeps the GNU name.
libtool=shutil.which('glibtoolize') or shutil.which('libtoolize');assert libtool,'Install GNU libtool (glibtoolize or libtoolize) before bootstrapping.'
aclocal=os.pathsep.join([str(pathlib.Path(libtool).resolve().parents[1]/'share/aclocal'),str(pathlib.Path(libtool).parents[1]/'share/aclocal')])
# Clang, as on macOS: GCC 15's C23 default breaks gnulib's string.h on glibc 2.43.
env=dict(os.environ,CC='clang',PATH=str(HOST/'bin')+os.pathsep+os.environ['PATH'],M4=str(HOST/'bin/m4'),LIBTOOLIZE=libtool,ACLOCAL_PATH=str(aclocal),CPPFLAGS='-I'+str(REPO/'third_party/compat'))
def unpack(name,dest):
 dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(REPO/'third_party/archives'/name) as t:t.extractall(dest,filter='data')
def run(cmd,cwd,log):
 with (logs/log).open('a') as f:subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for name in ['m4-1.4.20','autoconf-2.72','automake-1.17']:
 dest=TOOLS/name
 if not (dest/'.built').exists():
  print('Building',name,flush=True);unpack(name+'.tar.xz',TOOLS)
  # M4 bootstrap must use the host's existing M4, not the not-yet-built path.
  saved=env.pop('M4') if name.startswith('m4-') else None
  run(['./configure','--prefix='+str(HOST)],dest,name+'.log')
  run(['make','-j4'],dest,name+'.log');run(['make','install'],dest,name+'.log')
  if saved:env['M4']=saved
  (dest/'.built').write_text('complete\n')
base=TOOLS/'gccsdk';normal=base/'tools/asasm'
if not (normal/'src/asasm').exists():
 print('Building pinned AsAsm',flush=True);unpack('gccsdk-tools.tar.gz',base)
 # Case-insensitive names and no-break-space blanks, as on the macOS hosts; the observer copy inherits it.
 run(['patch','-p1','-F','0','-i',str(REPO/'third_party/patches/asasm-portable-host.patch')],normal,'asasm.log')
 run(['autoreconf','-fiv'],normal,'asasm.log')
 run(['./configure','--target=arm-unknown-riscos','--disable-building-tools','--disable-shared','--prefix='+str(HOST)],normal,'asasm.log')
 run(['make','-j4','ASASM_VERSION=2010000','GIT_REV=212d4567f007e7d30f4af3d6e1919a3d8a115b1c','GIT_BUILD_REV=0'],normal,'asasm.log')
observer=TOOLS/'observer/tools/asasm'
if not (observer/'src/asasm').exists():
 print('Building observation-only AsAsm',flush=True)
 # Copy the configured tree in its sibling layout so relative elftoolchain links remain valid.
 shutil.copytree(base,TOOLS/'observer',dirs_exist_ok=True)
 for name in ['asasm-observation.patch','asasm-observation-eof.patch']:
  run(['patch','-p1','-F','0','-i',str(REPO/'third_party/patches'/name)],observer,'observer.log')
 (observer/'src/asasm').unlink()
 run(['make','-j4','ASASM_VERSION=2010000','GIT_REV=212d4567f007e7d30f4af3d6e1919a3d8a115b1c','GIT_BUILD_REV=0'],observer,'observer.log')
tokenise=HOST/'bin/tokenise'
if not tokenise.exists():
 dest=TOOLS/'tokenise';shutil.copytree(REPO/'third_party/tokenise',dest,dirs_exist_ok=True)
 run(['patch','-p1','-F','0','-i',str(REPO/'third_party/patches/tokenise-host.patch')],dest,'tokenise.log')
 run(['clang','-O2','-x','c',str(dest/'c/tokenise'),'-o',str(tokenise)],dest,'tokenise.log')
for name,path in [('asasm',normal/'src/asasm'),('asasm-observer',observer/'src/asasm')]:
 link=HOST/'bin'/name
 if link.is_symlink():link.unlink()
 link.symlink_to(path)
report={'status':'PASS','archives':manifest['archives'],'binaries':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HOST/'bin/asasm',HOST/'bin/asasm-observer',tokenise]},'libtoolize':libtool}
(REPO/'build/toolchain-build.json').write_text(json.dumps(report,indent=2)+'\n');print('Host tools ready',flush=True)
