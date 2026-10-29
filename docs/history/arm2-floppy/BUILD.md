# Build and reproduce

Keep this experiment alongside the prior `experiments/` directories. No proprietary ROM or network download is needed to reproduce the supplied sources.

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-floppy/scripts/run.sh
```

Dependencies are Python 3, Clang/make, macOS/Swift, the pinned normal AsAsm and observer source tree, and the pinned public Tokenise executable. The recorded host uses Swift 6.4. MacArch core must be unchanged at `550bee4842e45eafdf331f0d06e11df1368403e8`; its existing CPU, device, snapshot and debugger APIs are used by external harnesses. `run.sh` selects the native SwiftPM backend and temporary module caches. No emulator patch is required.

The host-tool reconstruction instructions and licenses are in the preceding evidence chain, starting with `../arm2-restoration/BUILD.md`. Defaults:

- AsAsm: `../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm`; override with `ASASM`.
- Observer: an isolated copy of `../arm2-restoration/toolchain/asasm`, rebuilt with the inherited observation-only EOF fix. `ASASM_OBSERVER` may select an equivalent fixed observer.
- Tokenise: `../arm2-kernel/toolchain/host/bin/tokenise`, revision `d6ea854482663935562dc4c1bc2cde4bf3b570aa`.
- Kernel/header reconstruction: immutable `../arm2-keyboard/work` and artifacts, retaining the original exported-header checks.

The recipe verifies source hashes, copies sources to `work/`, generates/replays patches 16–28, rebuilds the original compressed TerritoryManager sprite, generates International help with its original generator, tokenises the original FileCore/ADFS help, and packages twelve original message resources. Original source files are never edited. The new ADFS/FileCore headers are exported from their pinned snapshots.

Modules use relocatable read-only areas and:

```text
-Uppercase -cpu=ARM2 -apcs 3/26bit -aof
```

Each is assembled twice normally and once with observation; AOF hashes must agree, with zero relocations and unresolved symbols. Do not replace module areas with `ORG 0`: that permits incorrect absolute ADR materialisation. The independent decoder checks instructions, direct targets, ARM2 settling and ADR forms before packaging.

The packaged ROM retains every original kernel byte up to the module-chain terminator, followed by the ten real modules and a new zero-length terminator. `build_disc.py` creates the 800 KiB test disc solely from original generated files and the public FileCore format definitions. The native harness mounts it with `writeProtected: true` and verifies an empty overlay throughout.

For module/container/disc reconstruction only:

```sh
python3 experiments/arm2-floppy/scripts/build_observer.py
python3 experiments/arm2-floppy/scripts/build_modules.py
python3 experiments/arm2-floppy/scripts/audit_modules.py
python3 experiments/arm2-floppy/scripts/package_rom.py
python3 experiments/arm2-floppy/scripts/territory_expectations.py
python3 experiments/arm2-floppy/scripts/build_disc.py
```

For verification of supplied saved evidence:

```sh
python3 experiments/arm2-floppy/scripts/verify_regressions.py
python3 experiments/arm2-floppy/scripts/verify_keyboard.py
python3 experiments/arm2-floppy/scripts/verify_messages.py
python3 experiments/arm2-floppy/scripts/decode_hardware_log.py
python3 experiments/arm2-floppy/scripts/verify_territory.py
python3 experiments/arm2-floppy/scripts/verify_selection.py
python3 experiments/arm2-floppy/scripts/verify_floppy.py
python3 experiments/arm2-floppy/scripts/finalize.py
```

The full script builds and runs three independent cold boots, all inherited runtime suites, the display fixtures and the new floppy suite. Development ran these stages separately; logs and saved states are supplied. The finalizer replays patches with `patch -p1 -F 0` and compares every patched module input with the compiled work tree. It checks all prior component bytes except the expanded Messages resource pack, and checks the unchanged kernel and emulator provenance.

Expected SHA-256:

```text
floppy.rom   bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791
arm2-test.adf fe6da71633fe82c803b91d134fbacf6b5ab6b292a05325dfbf556cbef25d2d21
kernel.bin   cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
```

For manual MacArch use, load `artifacts/floppy.rom` as A440/1, ARM2, 4 MiB, standard monitor, no hard discs, default CMOS/Delete at cold power-on. Insert `artifacts/disc/arm2-test.adf` in drive 0, preferably write-protected. At Supervisor:

```text
dir adfs::0.$
cat
/adfs::0.$.Hello
```

The catalogue lists Hello, Pattern and ReadMe; Hello prints `ARM2 FLOPPY PROGRAM EXECUTED` and returns to the prompt. Without selecting drive 0, bare `cat` under the original reset defaults can report `Disc drive not known`. Explicit `cat adfs::0.$` also works.

For MCP with its current API, `load_disc` lacks the existing core write-protection flag. After loading the matching ROM, load `artifacts/floppy-1/mounted-supervisor.macarch-state` with `keep_debugger: false` to restore a protected mount at the natural Supervisor entry. Its media path refers to this checkout; use the native harness to regenerate it if the checkout moves. Do not interpret loading a saved state as another cold-boot test; those are separately recorded by BootProbe.

Package the verified result:

```sh
python3 experiments/arm2-floppy/scripts/package_evidence.py
```

The sibling archive includes this milestone and the preceding IntKey evidence archive; unpack nested archives into a common parent to reconstruct prerequisites. Native build products, compiler caches and host tool binaries are excluded. Every archive member is checked byte-for-byte, and `SHA256SUMS` plus an archive SHA-256 sidecar are written.
