#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package the formal release: dist/arclibre-VERSION/ (make release).

The release has two variants, named with manifests/release.json's version:

  arclibre-VERSION-2mb.rom, arclibre-VERSION-2mb-extras.adf   any Archimedes
  arclibre-VERSION-4mb.rom                                    the A5000 family

with the source archive, the proof that it rebuilds all three, the evidence
archive, MacArch machine files in machines/, a README.txt and SHA256SUMS.

It packages only what make release-test passed, after the release was
recorded (tools/record_desktop_release.py) and committed: package_arclibre.py
checks every 2 MB gate, the extras disc's and the 4 MB ROM's, exports and
rebuilds the source, and tests/check_release_archives.py compares the
archives with the commit. Each file here is then a byte-identical copy of
one of those checked files.
"""
import hashlib,json,shutil,subprocess,sys
from paths import REPO
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text())
release=read(REPO/'manifests/release.json');version=release['version'];stem=f'arclibre-{version}'
recorded=read(REPO/'manifests/arclibre-desktop-release.json')
assert recorded.get('version')==version,'record the release first (tools/record_desktop_release.py)'
assert not subprocess.run(['git','status','--porcelain','--untracked-files=no'],cwd=REPO,capture_output=True,text=True,check=True).stdout,'commit the recorded release first'
for tool in ['tools/package_arclibre.py','tools/package_rom_4m.py','tests/check_release_archives.py']:subprocess.run([sys.executable,REPO/tool],check=True)
dist=REPO/'dist';out=dist/stem;machines=out/'machines'
assert sha(dist/'arclibre.rom')==recorded['rom_sha256'] and sha(dist/'arclibre-4m.rom')==recorded['rom_4m_sha256']
extras=REPO/'build/extras-disc/arclibre-extras.adf';assert sha(extras)==recorded['extras_disc_sha256']
proof=read(dist/'arclibre-source-build.json')
assert proof['rom_sha256']==recorded['rom_sha256'] and proof['rom_4m_sha256']==recorded['rom_4m_sha256'] and proof['extras_disc_sha256']==recorded['extras_disc_sha256']
shutil.rmtree(out,ignore_errors=True);machines.mkdir(parents=True)
copies={f'{stem}-2mb.rom':dist/'arclibre.rom',f'{stem}-2mb-extras.adf':extras,f'{stem}-4mb.rom':dist/'arclibre-4m.rom',
 f'{stem}-source.tar.gz':dist/'arclibre-source.tar.gz',f'{stem}-source-build.json':dist/'arclibre-source-build.json',f'{stem}-evidence.tar.gz':dist/'arclibre-evidence.tar.gz',
 f'machines/{stem}.cmos':dist/'arclibre.cmos',f'machines/{stem}-demo.hdf':dist/'arclibre-demo.hdf',f'machines/{stem}-draw-demo.hdf':dist/'arclibre-draw-demo.hdf',f'machines/{stem}-paint-demo.hdf':dist/'arclibre-paint-demo.hdf'}
for name,source in copies.items():shutil.copy2(source,out/name);assert sha(out/name)==sha(source),name
# Machine files: the tested A440/1 configuration, with paths relative to machines/.
base=read(dist/'arclibre.machine.json')
def machine(rom,discs=()):return dict(base,romPaths=[f'../{stem}-{rom}.rom'],cmosPath=f'{stem}.cmos',hardDiscs=list(discs))
for name,config in {'2mb':machine('2mb'),'2mb-hard-disc':machine('2mb',[f'{stem}-demo.hdf']),'2mb-draw':machine('2mb',[f'{stem}-draw-demo.hdf']),
  '2mb-paint':machine('2mb',[f'{stem}-paint-demo.hdf']),'4mb':machine('4mb')}.items():
 (machines/f'{stem}-{name}.machine.json').write_text(json.dumps(config,indent=2)+'\n')
template=(REPO/'docs/release/README.txt').read_text()
(out/'README.txt').write_text(template.replace('{underline}','='*len(version)).replace('{version}',version))
files=sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file())
(out/'SHA256SUMS').write_text(''.join(f'{sha(out/n)}  {n}\n' for n in files))
print(out)
for n in files:print(f'  {n:44} {(out/n).stat().st_size:>10,} bytes  {sha(out/n)[:16]}')
