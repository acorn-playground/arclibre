#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Import and pin the original networking sources (maintainer tool).

  baseline  copy the selected pinned files into src/<component>/ (files that
            already exist there are left alone and compared by `check`)
  manifest  regenerate manifests/network-inputs.json from src/
  check     re-derive every pinned file from the reference repositories and
            compare it with the manifest

This is the only networking tool that reads references/. Each file is read
with `git show REV:path` at the cleaned-3.60 import revision, never from a
reference worktree. Normal builds use src/, the manifest and patches/network.
"""
import hashlib,json,subprocess,sys
from paths import REPO
REFS=REPO/'references/RiscOS/Sources'
GITLAB='https://gitlab.4corn.co.uk/RiscOS/Sources/'
COMPONENTS={
 'Econet':('Networking/Econet','413ae41f105d8fa01f72ccb6c425cdc1ed0c4e0b',
  ['LICENSE','Makefile','NewOS','Time+Date','hdr/Econet','Resources/UK/Messages','s/Background','s/Commands','s/Interface','s/Macros','s/Memory','s/Module','s/Receive','s/Transmit']),
 'BBCEconet':('Networking/BBCEconet','5a1db236887c5c9da3f6176b49799b40c495f934',
  ['LICENSE','Makefile','Time+Date','s/Interface','s/Module']),
 'NetFS':('FileSys/NetFS/NetFS','3b392f000e60fdc44c885f4e05100349b15d3a38',
  ['LICENSE','Makefile','CurrentOS','HelpTexts','Time+Date','Resources/UK/Messages','s/Catalog','s/Commands','s/Configure','s/FileSystem','s/Functions','s/Interface','s/Memory','s/Module','s/OsFile','s/Random']),
 'NetFiler':('FileSys/NetFS/NetFiler','e0076648687f4cec1a685cee59b164164ab4f593',
  ['LICENSE','Makefile','Version','Resources/UK/Messages','Resources/UK/Templates,fec','s/NetFiler']),
 'NetPrint':('FileSys/NetPrint','c7aa0ed874824eb9d396d2c1a814e9f4cad2ffa7',
  ['LICENSE','Makefile','NewOS','HelpTexts','Time+Date','Resources/UK/Messages','s/Commands','s/FileSystem','s/Interface','s/Module']),
 # A public header the original Econet build reads (Hdr:PoduleReg), at the
 # HdrSrc revision already pinned for public allocation headers.
 'HdrSrc':('Programmer/HdrSrc','403c6dd8bce92d0629634cbf57f68f43b2f30d38',['hdr/PoduleReg']),
 'NetStatus':('Networking/NetStatus','3e8e96c5cbfff5a5824e9a1f0d3498a501d4ce11',
  ['LICENSE','Makefile','Time+Date','s/Module']),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def show(repo,rev,path):return subprocess.run(['git','show',rev+':'+path],cwd=REFS/repo,capture_output=True,check=True).stdout
def main(mode,components=COMPONENTS,manifest='network-inputs.json',label='network'):
 rows=[]
 for comp,(repo,rev,files) in components.items():
  for path in files:
   up=show(repo,rev,path) if mode!='manifest' or (REFS/repo).exists() else None
   dest=REPO/'src'/comp/path
   if mode=='baseline' and not dest.exists():
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(up)
   data=dest.read_bytes()
   row=dict(component=comp,path=path,revision=rev,repository=GITLAB+repo+'.git',upstream_sha256=sha(up) if up is not None else None,sha256=sha(data),bytes=len(data),modified=up is not None and data!=up)
   rows.append(row)
 if mode=='check':
  pinned=json.loads((REPO/'manifests'/manifest).read_text())
  assert [(r['component'],r['path'],r['upstream_sha256'],r['sha256']) for r in pinned]==[(r['component'],r['path'],r['upstream_sha256'],r['sha256']) for r in rows],'manifest differs'
  print(label,'pins re-derived:',len(rows),'files');return
 (REPO/'manifests'/manifest).write_text(json.dumps(rows,indent=2)+'\n')
 print(len(rows),'files;',sum(r['modified'] for r in rows),'modified')
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'check')
