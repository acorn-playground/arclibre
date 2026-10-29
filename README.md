# ArcLibre

ArcLibre is a freely redistributable ROM for the Acorn Archimedes, compatible
with **RISC OS 3.11**. It is built from the public, Apache-licensed RISC OS
sources: the cleaned RISC OS 3.60 source import, restored to the ARM2 and ARM3
machines and to 3.11's behaviour. No code, resources or fonts
are taken from Acorn's ROM images.

It starts the original desktop with its Filer, Task Manager, Pinboard, Edit,
Draw, Paint, BBC BASIC, sound, fonts, Econet networking, expansion cards,
serial and parallel ports, and the floppy and hard-disc filing systems.

## Downloads

Each release has two variants:

| File | For |
|---|---|
| `arclibre-VERSION-2mb.rom` | any Archimedes: the A300 and A400 series, A3000, A5000, A3010, A3020 and A4000 |
| `arclibre-VERSION-2mb-extras.adf` | the 2 MB ROM's floppy: DOSFS (PC discs), !Alarm and !Printers, which the 2 MB ROM has no room for |
| `arclibre-VERSION-4mb.rom` | the A5000, A3010, A3020 and A4000, whose ROM sockets take 4 MB: everything in ROM, no disc needed |

with the source archive, the record of rebuilding it from scratch into the
same ROMs, the test evidence and `SHA256SUMS`. Like RISC OS 3.11, one ROM
serves the whole range: at reset it detects the A5000 family's I/O chips
([new I/O](docs/new-io/RESULTS.md)).

ArcLibre has been tested only on emulated machines (MacArch); no physical
ROM has been made from it yet. See [the status page](docs/STATUS.md) for what
works, what has been tested and what hasn't.

## Building

On macOS or Linux, with the prerequisites in [BUILD.md](BUILD.md):

```sh
make arclibre-rom        # build/arclibre/arclibre.rom, the 2 MB ROM
make release-test        # both ROMs and the disc, and every test gate on them
make release             # dist/arclibre-VERSION/ (after recording the release)
```

The build needs no network access: every host tool (AsAsm, GCC 3.4.6 for the
C modules, Autoconf, M4, the MacArch emulator core the tests run on) is built
from pinned source archives in `third_party/`. It reproduces each release
byte for byte from a clean checkout on either host.

## How it is tested

Each part of the ROM has a gate that boots it in the MacArch emulator,
usually three times from cold, and drives the real desktop with the
emulated mouse and keyboard or the real command line: no test code is
injected into the guest. Results are checked on the host by independent
means: disc images are parsed, printed pages decoded, sound DMA timed. Most
gates have a negative control, a deliberately broken ROM or disc that must
fail. [BUILD.md](BUILD.md) lists the tiers and the gates;
[docs/](docs/README.md) has each component's results.

## Repository

| Path | Contents |
|---|---|
| `src/` | the RISC OS sources the ROM is built from, with ArcLibre's changes applied; edit here |
| `patches/` | every change to the upstream sources, as reviewable patches |
| `manifests/` | upstream repositories and revisions, file hashes, component roles, the release record |
| `tools/` | the build: toolchain bootstrap, assembly, linking, ROM joining, disc building, packaging |
| `tests/` | the gates and their emulator harness (`tests/harness`, Swift) |
| `third_party/` | pinned source archives of the host tools, and their patches |
| `licenses/` | licence texts and assessments |
| `docs/` | component results, provenance, and the restoration history |

## Licensing and provenance

ArcLibre is distributed under the Apache License 2.0. The sources come from
the public RISC OS source repositories at pinned revisions, each recorded with
its upstream hash in `manifests/`; every change is a patch in `patches/` and
every modified file carries a modification notice. [LICENSING.md](LICENSING.md)
gives the full provenance, the licences of the host tools, and what is
excluded and why. [docs/history](docs/history/README.md) records how the
3.60 sources were restored to the ARM2 machines, and the original
feasibility audit.

[CONTRIBUTING.md](CONTRIBUTING.md) describes how to make changes.
