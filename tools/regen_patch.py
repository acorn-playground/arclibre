#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Record edits to src/ in the patches and manifests.

  python3 tools/regen_patch.py GROUP MANIFEST capture   before editing
  python3 tools/regen_patch.py GROUP MANIFEST write     after editing

GROUP is a directory in patches/ holding one 0001-*.patch for the files listed
in MANIFEST (for example patches/hardware and manifests/hardware-inputs.json).
capture reverse-applies the patch to copies of the listed files in
build/regen-GROUP/ and checks they match each row's upstream_sha256. write
diffs those upstream copies against src/, rewrites the patch, and updates each
row's maintained sha256 (never upstream_sha256 or bytes, the upstream size).

  python3 tools/regen_patch.py restoration NNNN-what-it-does.patch

The kernel and the first restored modules (manifests/restoration-inputs.json)
keep a numbered series instead. This records the uncommitted changes to those
files, against the committed ones, as a new patch at the end of
patches/restoration/series, adds it to each component's restoration_patches in
manifests/components.json, and updates the files' sha256.
"""
import hashlib,json,shutil,subprocess,sys
from paths import REPO
def sha(b):return hashlib.sha256(b).hexdigest()
if sys.argv[1:2]==['restoration'] and len(sys.argv)==3:
 name=sys.argv[2];series=REPO/'patches/restoration/series';names=series.read_text().split()
 assert name.endswith('.patch') and name not in names and not (series.parent/name).exists(),name
 manifest=REPO/'manifests/restoration-inputs.json';record=json.loads(manifest.read_text());out=b'';changed=set()
 for r in record['files']:
  rel=f"src/{r['component']}/{r['path']}";now=(REPO/rel).read_bytes()
  if sha(now)==r['sha256']:continue
  before=subprocess.run(['git','show','HEAD:'+rel],cwd=REPO,capture_output=True,check=True).stdout
  assert sha(before)==r['sha256'],(rel,'the committed file is not the recorded one')
  tmp=REPO/'build/regen-restoration';tmp.mkdir(parents=True,exist_ok=True);(tmp/'before').write_bytes(before)
  d=subprocess.run(['diff','-a','-u','--label','a/'+rel,'--label','b/'+rel,str(tmp/'before'),str(REPO/rel)],capture_output=True)
  assert d.returncode==1,d.stderr;out+=d.stdout;r['sha256']=sha(now);changed.add(r['component'])
 assert out,'no restoration file has changed'
 (series.parent/name).write_bytes(out);series.write_text('\n'.join(names+[name])+'\n')
 manifest.write_text(json.dumps(record,indent=2)+'\n')
 components=json.loads((REPO/'manifests/components.json').read_text())
 for c in components:
  if c['component'] in changed:c.setdefault('restoration_patches',[]).append(name)
 (REPO/'manifests/components.json').write_text(json.dumps(components,indent=2)+'\n')
 print('wrote',name,len(out),'bytes for',', '.join(sorted(changed)));sys.exit()
group,manifest,mode=sys.argv[1:4]
rows=json.loads((REPO/manifest).read_text());patch=sorted((REPO/'patches'/group).glob('0001-*.patch'))[0]
up=REPO/'build'/('regen-'+group)
if mode=='capture':
 shutil.rmtree(up,ignore_errors=True)
 for r in rows:
  p=up/'src'/r['component']/r['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/'src'/r['component']/r['path'],p)
 subprocess.run(['patch','--batch','-p1','--fuzz=0','-R','-i',str(patch)],cwd=up,check=True,capture_output=True)
 for r in rows:assert sha((up/'src'/r['component']/r['path']).read_bytes())==r['upstream_sha256'],r
 print('captured',len(rows),'upstream files in',up)
elif mode=='write':
 out=b''
 for r in rows:
  rel=f"src/{r['component']}/{r['path']}"
  d=subprocess.run(['diff','-a','-u','--label','a/'+rel,'--label','b/'+rel,str(up/rel),str(REPO/rel)],capture_output=True)
  assert d.returncode in (0,1),d.stderr;out+=d.stdout
  r['sha256']=sha((REPO/rel).read_bytes())
 patch.write_bytes(out);(REPO/manifest).write_text(json.dumps(rows,indent=2)+'\n');print('wrote',patch.name,len(out),'bytes')
else:sys.exit(__doc__)
