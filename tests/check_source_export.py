#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rebuild a published source archive in a new directory and compare its ROMs and disc.

The release's 2 MB ROM is required; the 4 MB ROM and the 2 MB ROM's extras
disc, when given, are built in the same make run and compared too."""
import argparse,hashlib,json,os,pathlib,re,subprocess,tarfile

def sha(path):return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('archive',type=pathlib.Path)
p.add_argument('destination',type=pathlib.Path,help='New directory; must not already exist')
p.add_argument('--expected-rom',type=pathlib.Path,required=True)
p.add_argument('--expected-rom-4m',type=pathlib.Path)
p.add_argument('--expected-extras',type=pathlib.Path)
a=p.parse_args();archive=a.archive.resolve();destination=a.destination.resolve()
assert not destination.exists(),destination
expected=sha(a.expected_rom);destination.mkdir(parents=True)
with tarfile.open(archive) as tar:
 members=tar.getmembers()
 assert all(m.name.startswith('arclibre/') and m.isfile() for m in members)
 assert not any('/references/' in m.name or '/build/' in m.name for m in members)
 tar.extractall(destination,filter='data')
 for member in members:
  with tar.extractfile(member) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==sha(destination/member.name)
source=destination/'arclibre';log=destination/'build.log'
targets=['arclibre-rom']+(['arclibre-rom-4m'] if a.expected_rom_4m else [])+(['extras-disc'] if a.expected_extras else [])
with log.open('w') as f:
 result=subprocess.run(['make',*targets],cwd=source,env=dict(os.environ,ARCLIBRE_INSTALL_ROM='0'),stdout=f,stderr=subprocess.STDOUT)
assert result.returncode==0,log
rom=source/'build/arclibre/arclibre.rom';actual=sha(rom)
assert actual==expected,(expected,actual)
others={}
for option,built in [(a.expected_rom_4m,'build/arclibre-4m/arclibre.rom'),(a.expected_extras,'build/extras-disc/arclibre-extras.adf')]:
 if option:
  others[built]=sha(source/built);assert others[built]==sha(option),(built,sha(option),others[built])
# Detect the original __FILE__ failure independently of the expected hash.
for built in [rom]+([source/'build/arclibre-4m/arclibre.rom'] if a.expected_rom_4m else []):
 assert not any(b'/Users/' in s or str(source).encode() in s for s in re.findall(rb'[ -~]{12,}',built.read_bytes())),built
report=dict(status='PASS',source_archive_sha256=sha(archive),source_files_verified=len(members),
 rom_sha256=actual,rom_bytes=rom.stat().st_size,empty_destination=True,host_tools_built_from_bundled_sources=True,
 command='ARCLIBRE_INSTALL_ROM=0 make '+' '.join(targets),
 rom_4m_sha256=others.get('build/arclibre-4m/arclibre.rom'),extras_disc_sha256=others.get('build/extras-disc/arclibre-extras.adf'),checkout_paths_absent_from_rom=True)
(destination/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
