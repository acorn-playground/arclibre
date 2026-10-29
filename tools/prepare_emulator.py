#!/usr/bin/env python3
"""Prepare reproducible host dependencies, outside the maintained guest source."""
import hashlib,json,shutil,subprocess,sys,tarfile
from paths import REPO,ROOT
manifest=json.loads((REPO/'manifests/emulator-patch.json').read_text())
base=REPO/'build/macarch-baseline/ArchimedesCore';patched=REPO/'build/macarch/ArchimedesCore'
archive=REPO/'third_party/archives/macarch-core.tar.gz'
expected=json.loads((REPO/'manifests/toolchain.json').read_text())['archives'][archive.name]
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
if not base.exists():
 base.mkdir(parents=True)
 with tarfile.open(archive) as t:t.extractall(base,filter='data')
 # Other hosts lack Apple's Compression, CryptoKit, Security, SDK zlib module
 # and XCTest initialiser; this host-only patch supplies equivalents and
 # changes no emulation.
 if sys.platform!='darwin':subprocess.run(['patch','-p1','-F','0','-i',str(REPO/'third_party/patches/macarch-portable-host.patch')],cwd=base,check=True)
if not patched.exists():
 shutil.copytree(base,patched)
 subprocess.run(['patch','-p1','-F','0','-i',str(REPO/'third_party/patches/macarch-original-disc-change.patch')],cwd=patched,check=True)
for row in manifest['files']:assert hashlib.sha256((patched/row['path']).read_bytes()).hexdigest()==row['after']
# A clean build tree has no output directory yet.
(ROOT/'artifacts').mkdir(parents=True,exist_ok=True)
(ROOT/'artifacts/core-replay.json').write_text(json.dumps(dict(status='PASS',base=manifest['base'],files=manifest['files']),indent=2)+'\n')
print(patched)
