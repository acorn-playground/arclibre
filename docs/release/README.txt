ArcLibre {version}
========={underline}

ArcLibre is a freely redistributable ROM for Acorn Archimedes computers,
compatible with RISC OS 3.11, built from the Apache-licensed RISC OS
sources. This release has two variants.

2 MB: for any Archimedes
------------------------

arclibre-{version}-2mb.rom
    The ROM.
arclibre-{version}-2mb-extras.adf
    An 800K floppy with the parts of RISC OS 3.11 that the 2 MB ROM has
    no room for: DOSFS, !Alarm and !Printers. It also has !System and
    !Scrap, which every machine needs on its hard disc (RISC OS 3.11's
    came on the Applications disc). Its ReadMe explains each.

4 MB: for the A5000, A3010, A3020 and A4000
-------------------------------------------

arclibre-{version}-4mb.rom
    The ROM, with DOSFS, Alarm and printing built in. Copy !System and
    !Scrap from the extras disc to your hard disc.
    It needs a machine whose ROM sockets take 4 MB. The A3000, A300 and
    A400 series take at most 2 MB.

Also in this release
--------------------

arclibre-{version}-source.tar.gz
    The complete source. "make release-test" rebuilds and tests both ROMs
    and the disc; BUILD.md lists what the build needs.
arclibre-{version}-source-build.json
    The record of rebuilding this source archive from scratch into the
    same ROMs and disc, byte for byte.
arclibre-{version}-evidence.tar.gz
    The release's test records and documentation.
machines/
    MacArch machine files, CMOS settings and demonstration hard discs.
    Paths in the machine files are relative to that folder.
SHA256SUMS
    Checksums of every file here (check them with
    "shasum -a 256 -c SHA256SUMS").

Only emulated machines have been tested; no physical ROM has been made
from this release. ArcLibre is distributed under the Apache License 2.0;
the source archive's LICENSING.md has the full notices.
