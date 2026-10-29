#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify distributed bytes, committed sources and excluded private inputs."""
import hashlib,io,json,pathlib,subprocess,tarfile
R=pathlib.Path(__file__).resolve().parents[1];out=R/'dist'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
objects=subprocess.check_output(['git','ls-tree','-rz','--full-tree','HEAD'],cwd=R).decode().split('\0')
tracked={row.split('\t',1)[1]:row.split('\t',1)[0].split()[2] for row in objects if row}
algorithm=subprocess.check_output(['git','rev-parse','--show-object-format'],cwd=R).decode().strip()
source=out/'arclibre-source.tar.gz';source_count=0
with tarfile.open(source) as tar:
 for m in tar:
  assert m.isfile() and m.name.startswith('arclibre/')
  name=m.name.removeprefix('arclibre/');assert name in tracked,name
  b=tar.extractfile(m).read();assert hashlib.new(algorithm,b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==tracked[name],name
  assert not any(p in ['references','build','.git'] for p in pathlib.PurePosixPath(name).parts),name
  if name=='third_party/archives/gccsdk-3.4.6-arclibre.tar.gz':
   with tarfile.open(fileobj=io.BytesIO(b)) as sdk:assert not any('cmunge' in x.name.lower() for x in sdk)
  source_count+=1
required=['arclibre.rom','arclibre-source.tar.gz','arclibre-source-build.json','arclibre.machine.json','arclibre-hard-disc.machine.json']
archive=out/'arclibre-evidence.tar.gz';seen=set();files=0
with tarfile.open(archive,mode='r|gz') as tar:
 for m in tar:
  assert m.isfile() and m.name.startswith('arclibre-evidence/');name=m.name.removeprefix('arclibre-evidence/')
  assert not any(p.lower()=='references' or p.lower().startswith('private-') for p in pathlib.PurePosixPath(name).parts),name
  if name in required:
   assert hashlib.file_digest(tar.extractfile(m),'sha256').hexdigest()==sha(out/name),name
   seen.add(name)
  files+=1
assert seen==set(required)
for name in ['arclibre.rom','arclibre-source.tar.gz','arclibre-source-build.json','arclibre-evidence.tar.gz']:
 assert (out/(name+'.sha256')).read_text().split()[0]==sha(out/name)
proof=json.loads((out/'arclibre-source-build.json').read_text())
assert proof['status']=='PASS' and proof['source_archive_sha256']==sha(source) and proof['rom_sha256']==sha(out/'arclibre.rom')
report=dict(status='PASS',archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,files=files,source_files=source_count,bundled_artifacts_match=required,private_media_and_reference_directories_absent=True,source_archive_matches_committed_files=True,restricted_cmunge_subtree_absent=True,published_source_rebuild_verified=True,rom_sha256=sha(out/'arclibre.rom'))
(out/'arclibre-package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
