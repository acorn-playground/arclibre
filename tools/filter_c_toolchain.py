#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce the host source subset without unused, restricted CMunge sources."""
import gzip,hashlib,json,pathlib,sys,tarfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'manifests/c-toolchain.json').read_text())
source=pathlib.Path(sys.argv[1]);output=pathlib.Path(sys.argv[2])
assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['upstream_archive_sha256']
prefix='gccsdk-'+manifest['revision']+'/gcc/riscos-aof/cmunge'
removed=[]
with tarfile.open(source) as original,output.open('wb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as selected:
  for entry in sorted(original.getmembers(),key=lambda x:x.name):
   if entry.name==prefix or entry.name.startswith(prefix+'/'):
    if entry.isfile():removed.append(dict(path=entry.name,sha256=hashlib.sha256(original.extractfile(entry).read()).hexdigest(),bytes=entry.size))
    continue
   entry.uid=entry.gid=0;entry.uname=entry.gname='';entry.mtime=0
   selected.addfile(entry,original.extractfile(entry) if entry.isfile() else None)
record=dict(upstream_sha256=manifest['upstream_archive_sha256'],selected_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),excluded_prefix=prefix,excluded_files=removed,retained_payloads_unchanged=True)
output.with_suffix(output.suffix+'.selection.json').write_text(json.dumps(record,indent=2)+'\n')
print(record['selected_sha256'],len(removed),'excluded files')
