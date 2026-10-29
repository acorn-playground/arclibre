#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the public GCCSDK 3.4.6 AOF compiler, preserving ARM2/APCS-26 support."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,tarfile
from paths import REPO,HOST,TOOLS
m=json.loads((REPO/'manifests/c-toolchain.json').read_text())
a=REPO/'third_party/archives'/m['archive'];assert hashlib.sha256(a.read_bytes()).hexdigest()==m['sha256']
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build-root',type=pathlib.Path,default=REPO/'build/c-toolchain-release')
root=p.parse_args().build_root.resolve();root.mkdir(parents=True,exist_ok=True);log=root/'bootstrap.log'
source=root/('gccsdk-'+m['revision']);gcc=source/'gcc';prefix=root/'install'
# A prior bootstrap may have installed this unused SDK utility. It is not a
# dependency of ArcLibre and is no longer in the selected source archive.
(prefix/'bin/cmunge').unlink(missing_ok=True)
env=dict(os.environ,PATH=str(HOST/'bin')+os.pathsep+os.environ['PATH'],CC='clang',CXX='clang++',CFLAGS='-O2 -fno-strict-aliasing -std=gnu89 -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-pointer-types',CXXFLAGS='-O2 -std=gnu++98',ac_cv_prog_MAKEINFO='echo')
def run(cmd,cwd):
 with log.open('a') as f:subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
stamp=hashlib.sha256((REPO/'manifests/c-toolchain.json').read_bytes()+b''.join((REPO/p).read_bytes() for p in m['patches'])).hexdigest()
if not (source/'.prepared').exists() or (source/'.prepared').read_text().strip()!=stamp:
 if source.exists():shutil.rmtree(source)
 with tarfile.open(a) as t:t.extractall(root,filter='data')
 for patch in m['patches']:run(['patch','--batch','-p1','--fuzz=0','-i',REPO/patch],source)
 for f in ['config.guess','config.sub']:shutil.copy2(TOOLS/'autoconf-2.72/build-aux'/f,gcc/f)
 run(['autoconf'],gcc);run(['autoheader'],gcc)
 run(['./configure','--prefix='+str(prefix),'--enable-checking=no'],gcc)
 (source/'.prepared').write_text(stamp+'\n')
 (root/'build.json').unlink(missing_ok=True)
if not (root/'build.json').exists():
 for target in ['setup','libiberty-stg1','riscos-aof-stg1','gcc-stg1']:
  print('GCCSDK',target,flush=True);run(['make','-j4',target],gcc)
 report=dict(status='BUILT',manifest=m,binaries={str(p.relative_to(prefix)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [prefix/'bin/gcc',prefix/'bin/drlink',prefix/'bin/arm-riscos-aof/3_4/as']})
 (root/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(prefix,flush=True)
