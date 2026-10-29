#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regenerate a component group's patch after editing its files in src/.

  python3 tools/regen_patch.py GROUP MANIFEST capture   before editing
  python3 tools/regen_patch.py GROUP MANIFEST write     after editing

GROUP is a directory in patches/ holding one 0001-*.patch for the files listed
in MANIFEST (for example patches/hardware and manifests/hardware-inputs.json).
capture reverse-applies the patch to copies of the listed files in
build/regen-GROUP/ and checks they match each row's upstream_sha256. write
diffs those upstream copies against src/, rewrites the patch, and updates each
row's maintained sha256 (never upstream_sha256 or bytes, the upstream size).
"""
import hashlib,json,shutil,subprocess,sys
from paths import REPO
group,manifest,mode=sys.argv[1:4]
rows=json.loads((REPO/manifest).read_text());patch=sorted((REPO/'patches'/group).glob('0001-*.patch'))[0]
up=REPO/'build'/('regen-'+group)
if mode=='capture':
 shutil.rmtree(up,ignore_errors=True)
 for r in rows:
  p=up/'src'/r['component']/r['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/'src'/r['component']/r['path'],p)
 subprocess.run(['patch','--batch','-p1','--fuzz=0','-R','-i',str(patch)],cwd=up,check=True,capture_output=True)
 for r in rows:assert hashlib.sha256((up/'src'/r['component']/r['path']).read_bytes()).hexdigest()==r['upstream_sha256'],r
 print('captured',len(rows),'upstream files in',up)
elif mode=='write':
 out=b''
 for r in rows:
  rel=f"src/{r['component']}/{r['path']}"
  d=subprocess.run(['diff','-a','-u','--label','a/'+rel,'--label','b/'+rel,str(up/rel),str(REPO/rel)],capture_output=True)
  assert d.returncode in (0,1),d.stderr;out+=d.stdout
  r['sha256']=hashlib.sha256((REPO/rel).read_bytes()).hexdigest()
 patch.write_bytes(out);(REPO/manifest).write_text(json.dumps(rows,indent=2)+'\n');print('wrote',patch.name,len(out),'bytes')
else:sys.exit(__doc__)
