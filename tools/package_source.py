#!/usr/bin/env python3
"""Export the repository's tracked tree (no build output, local settings or references/)."""
import argparse,gzip,hashlib,pathlib,subprocess,tarfile
from paths import REPO
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--arclibre',action='store_true')
parser.add_argument('--output-dir',type=pathlib.Path,default=REPO/'dist')
args=parser.parse_args()
names=['Makefile','README.md','BUILD.md','CONTRIBUTING.md','LICENSING.md','.gitignore','.gitattributes','src','tools','tests','third_party','manifests','patches','licenses','docs']
files=[]
for name in names:
 p=REPO/name
 assert p.exists(),p
 files.extend([p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and not any(x in ['__pycache__','.build','.swiftpm','.DS_Store','.git'] for x in f.relative_to(p).parts)])
# Submodules contribute their committed files only, not their .git link or
# anything built inside them.
for sub in subprocess.run(['git','config','-f','.gitmodules','--get-regexp','path'],cwd=REPO,capture_output=True,text=True).stdout.split():
 if '/' not in sub or sub.startswith('submodule.'):continue
 kept={REPO/sub/f for f in subprocess.check_output(['git','-C',str(REPO/sub),'ls-files'],text=True).split('\n') if f}
 files=[f for f in files if not f.is_relative_to(REPO/sub) or f in kept]
files=sorted(set(files));out=args.output_dir;out.mkdir(parents=True,exist_ok=True);archive=out/'arclibre-source.tar.gz'
with archive.open('wb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
 for p in files:
  assert not p.is_symlink(),p
  info=tar.gettarinfo(str(p),arcname='arclibre/'+str(p.relative_to(REPO)));info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with p.open('rb') as data:tar.addfile(info,data)
with tarfile.open(archive) as tar:
 for member,p in zip(tar.getmembers(),files):assert tar.extractfile(member).read()==p.read_bytes()
h=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest();(out/(archive.name+'.sha256')).write_text(h+'  '+archive.name+'\n');print(archive,len(files),'files',archive.stat().st_size,'bytes',h)
