#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Import and pin the selected original DOSFS 0.62 sources (maintainer tool).

  baseline  write the selected pinned bytes to build/dosfs-upstream/ (and to
            src/DOSFS/ for files not yet imported)
  manifest  regenerate manifests/dosfs-inputs.json from src/DOSFS
  check     re-derive every pinned file from the reference repository and
            compare it with the manifest

This is the only DOSFS tool that reads references/. Normal builds use src/,
the manifest and patches/dosfs only. Files are read with `git show REV:path`
from the pinned revision, never from the reference checkout's worktree.

s/StaticDefs embeds a default boot-sector template (OEM text and opaque x86
boot code) whose provenance is unresolved. ArcLibre does not redistribute
those lines: the import baseline excises exactly that block and records the
hashes of the complete upstream file and of the excised bytes. The
replacement boot sector is ArcLibre's own src/ArcLibre/s/DOSFSBoot.
c/BOOTblock (another copy, unused by the build) is not imported at all.
"""
import hashlib,json,pathlib,subprocess,sys
from paths import REPO
REV='ec870faf21127aba600c58b3571115ac164e40f3'
URL='https://gitlab.4corn.co.uk/RiscOS/Sources/FileSys/ImageFS/DOSFS.git'
REF=REPO/'references/RiscOS/Sources/FileSys/ImageFS/DOSFS'
if not REF.exists():REF=REPO.parents[2]/'references/RiscOS/Sources/FileSys/ImageFS/DOSFS' if REPO.parent.name=='worktrees' else REF
SELECTED=['LICENSE','Makefile','Doc/!ReadMe','cmhg/DOSFShdr','hdr/DOSFS','Resources/UK/Messages',
 'c/DOSFS','c/DOSFSops','c/DOSnaming','c/FSerrors','c/MsgTrans','c/Statics','c/TIMEconv','c/debug','c/wcompare',
 'h/ADFSshape','h/ASCII','h/BOOTblock','h/DOSFS','h/DOSFSctl','h/DOSFSops','h/DOSmapping','h/DOSnaming','h/DOSshape',
 'h/FSerrors','h/MsgTrans','h/MultiFS','h/Statics','h/TIMEconv','h/debug','h/wcompare',
 's/DOSFSctl','s/MFSmacros','s/StaticDefs']
# Upstream files deliberately not imported, with the reason.
EXCLUDED={'c/BOOTblock':'second copy of the opaque MSDOS3.3 boot-sector template; not part of the build',
 's/init':'ROM-only guard that refuses RAM loading; the disc module uses ArcLibre s/DOSFSHdr instead',
 'c/DOSfsiface':'marked "THIS FILE IS NO LONGER USED"; not in the Makefile objects',
 'Help':'pre-internationalisation help text, superseded by Resources/UK/Messages',
 'Syntax':'pre-internationalisation syntax text, superseded by Resources/UK/Messages'}
EXCISE_START=b'; The following is the default boot block.\n'
EXCISE_END=b'        END\n'
MARKER=(b'; [ArcLibre import: the default boot-block template that stood here (BPB\n'
 b'; values, "MSDOS3.3" OEM text and opaque x86 boot code) is not\n'
 b'; redistributed. manifests/dosfs-inputs.json records the hashes of the\n'
 b'; complete upstream file and of the excised lines.]\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def show(path):return subprocess.run(['git','show',REV+':'+path],cwd=REF,capture_output=True,check=True).stdout
def baseline(path,data):
 """The imported baseline: upstream bytes, with the opaque block excised."""
 if path!='s/StaticDefs':return data,None
 start=data.index(EXCISE_START);end=data.rindex(EXCISE_END);assert start<end
 cut=data[start:end]
 return data[:start]+MARKER+data[end:],dict(first_line=data[:start].count(b'\n')+1,last_line=data[:end].count(b'\n'),bytes=len(cut),sha256=sha(cut))
def rows():
 manifest=REPO/'manifests/dosfs-inputs.json'
 return json.loads(manifest.read_text()) if manifest.exists() else []
def main(mode):
 out=REPO/'build/dosfs-upstream'
 if mode=='baseline':
  listing=subprocess.run(['git','ls-tree','-r','--name-only',REV],cwd=REF,capture_output=True,text=True,check=True).stdout.split()
  assert set(SELECTED)<=set(listing) and set(EXCLUDED)<=set(listing)
  for path in SELECTED:
   data,_=baseline(path,show(path));p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   s=REPO/'src/DOSFS'/path
   if not s.exists():s.parent.mkdir(parents=True,exist_ok=True);s.write_bytes(data)
  print('baseline written to',out)
 elif mode=='manifest':
  result=[]
  for path in SELECTED:
   up=show(path);base,excised=baseline(path,up);cur=(REPO/'src/DOSFS'/path).read_bytes()
   row=dict(component='DOSFS',path=path,revision=REV,repository=URL,upstream_sha256=sha(up),sha256=sha(cur),bytes=len(cur),modified=sha(cur)!=sha(base))
   if excised:row.update(baseline_sha256=sha(base),baseline_bytes=len(base),excised=excised,
     note='Import baseline excises the default boot-sector template; see tools/import_dosfs.py')
   result.append(row)
  (REPO/'manifests/dosfs-inputs.json').write_text(json.dumps(result,indent=2)+'\n')
  print(len(result),'rows;',sum(r['modified'] for r in result),'modified')
 elif mode=='patch':
  # Regenerate the reviewable patch from the import baseline (run 'baseline'
  # first) to the maintained src/DOSFS files.
  import difflib
  text=''
  for path in SELECTED:
   a=(out/path).read_bytes().decode('latin1');b=(REPO/'src/DOSFS'/path).read_bytes().decode('latin1')
   if a!=b:
    assert a.endswith('\n') and b.endswith('\n')
    text+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),'a/src/DOSFS/'+path,'b/src/DOSFS/'+path,n=3))
  p=REPO/'patches/dosfs/0001-disc-module-build.patch';p.parent.mkdir(exist_ok=True);p.write_bytes(text.encode('latin1'))
  (p.parent/'series').write_text(p.name+'\n');print(p)
 elif mode=='check':
  for row in rows():
   up=show(row['path']);base,excised=baseline(row['path'],up)
   assert sha(up)==row['upstream_sha256'],row['path']
   if excised:assert sha(base)==row['baseline_sha256'] and excised==row['excised'],row['path']
  print('DOSFS manifest matches the pinned upstream revision')
 else:sys.exit(__doc__)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else '')
