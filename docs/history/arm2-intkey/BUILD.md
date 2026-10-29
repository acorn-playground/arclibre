# Build and reproduce

Keep this experiment beside the earlier directories under `experiments/`. The original module sources, public resources, patches and test harnesses are included. No proprietary ROM image or network access is needed to rebuild.

From the project root:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-intkey/scripts/run.sh
```

Requirements: Python 3, Clang/make, macOS/Swift, the pinned normal AsAsm, the previous observer source/build tree and the public Tokenise executable. MacArch core must be unchanged at `550bee4842e45eafdf331f0d06e11df1368403e8`. The recorded host uses Swift 6.4 and the native SwiftPM backend. See `../arm2-restoration/BUILD.md` for host-tool reconstruction and the nested evidence chain for original sources/licenses.

Defaults are:

- Normal AsAsm: `../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm` (`ASASM` override supported).
- Observer: an isolated copy built from `../arm2-restoration/toolchain/asasm`, applying the territory milestone's observation-only EOF fix. `ASASM_OBSERVER`, if set, must point at an equivalent fixed observer.
- Tokenise: `../arm2-kernel/toolchain/host/bin/tokenise`, revision `d6ea854482663935562dc4c1bc2cde4bf3b570aa`; executable and dictionary hashes are recorded in `artifacts/help-build.json`.
- Kernel and reconstructed headers: immutable `../arm2-keyboard/work` and `artifacts` inputs, with original header-export checks retained.

The recipe copies original sources into `work/`, applies patches 16–23, rebuilds the original TerritoryManager sprite, generates International's help source with its original IntHelpSrc/IntHelpBod and tokenises it using the pinned public dictionary. It selects the existing UK A1 IntKey branch, packages the ten original ResourceFS files and assembles all eight modules twice normally and once with observation.

Module assembly uses `-Uppercase -cpu=ARM2 -apcs 3/26bit -aof` and relocatable read-only code areas. All references resolve within the module: no unresolved symbols or relocation records remain. Do not replace the module areas with `ORG 0`; that permits the absolute-address optimisation defect fixed in the preceding milestone. Only the host help-text generator uses an absolute zero origin.

The independent decoder checks instructions, branch targets, settling and ADR materialisation. Packaging retains every kernel byte before its original module-chain terminator, then writes the genuine length-prefixed module chain. The kernel component itself remains unchanged.

The full script builds native harnesses, executes three fresh reset-to-pre-module runs, and runs natural startup, CAM transfers, original keyboard tests, MessageTrans, territory and additional keyboard-selection suites from each boot. It also runs the two font/pixel fixtures and all independent verifiers. Development executed these recipe stages separately: `logs/cold-repeats.log`, `runtime-suites.log`, per-suite logs and `final-validation.log` contain the evidence. Initial verifier assumptions about resident-only KeyVec and post-module fonts were corrected to check the real installed contracts; the ROM hash did not change during those verifier corrections.

Expected SHA-256:

```text
kernel.bin  cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
intkey.rom  7dff5b428ba7c0a073d769c513a93c104c08b8ac1df0be7eca3de8ab5e943faa
```

For module/container-only rebuilding:

```sh
python3 experiments/arm2-intkey/scripts/build_observer.py
python3 experiments/arm2-intkey/scripts/build_modules.py
python3 experiments/arm2-intkey/scripts/audit_modules.py
python3 experiments/arm2-intkey/scripts/package_rom.py
python3 experiments/arm2-intkey/scripts/territory_expectations.py
```

For verification of the supplied saved execution evidence:

```sh
python3 experiments/arm2-intkey/scripts/verify_regressions.py
python3 experiments/arm2-intkey/scripts/verify_keyboard.py
python3 experiments/arm2-intkey/scripts/verify_messages.py
python3 experiments/arm2-intkey/scripts/verify_territory.py
python3 experiments/arm2-intkey/scripts/verify_selection.py
python3 experiments/arm2-intkey/scripts/finalize.py
```

For manual patch replay, copy `sources/` to a temporary directory and the keyboard milestone's `work/HdrSrc/hdr/CPU/Generic26` to `SharedHeaders/CPU/Generic26` inside it. Apply each `patches/series` entry with `patch -p1 -F 0`. The finalizer compares patched inputs byte-for-byte with the compiled work tree. Generated ResourcesData, SystemDiscSquashed and International help files are produced by the scripts rather than supplied as substitute binaries. The separate observer patch applies to the host observer tree.

Load `artifacts/intkey.rom` in MacArch as A440/1, ARM2, 4 MiB, standard monitor, no media, default CMOS/Delete at cold power-on. At Supervisor:

```text
keyboard uk
keyboard
help keyboard
```

The first returns to the prompt, the second displays `UK`, and the third displays the original help and syntax. `keyboard nonsense` returns the genuine Unknown keyboard error. Only the UK A1 configuration is validated; no desktop or disc filesystem is expected.

Package with:

```sh
python3 experiments/arm2-intkey/scripts/package_evidence.py
```

This creates `../arm2-intkey-evidence.tar.gz` and its SHA-256 sidecar and verifies every archive member. The previous territory archive is included with earlier prerequisites nested; extract the archives into a common parent to reconstruct sibling directories. Native build products, compiler caches and host tool binaries are excluded.
