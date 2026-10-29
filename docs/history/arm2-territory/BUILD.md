# Build and reproduce

Keep the experiment directories as siblings under `experiments/`. All module sources and original resource bytes are included. No network access, existing ROM image or proprietary build dependency is required by this recipe.

From the project root:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-territory/scripts/run.sh
```

Prerequisites are Python 3, Clang/make, macOS/Swift and the previously built AsAsm tools. MacArch core must match commit `550bee4842e45eafdf331f0d06e11df1368403e8` without changes. The recorded machine uses Swift 6.4 and the native SwiftPM backend. See `../arm2-restoration/BUILD.md` for reconstruction of the pinned host toolchain. The default normal assembler is `../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm`; `ASASM` may override its path. The script copies the earlier observer source/build tree to this experiment's `toolchain/asasm`, applies the observation-only EOF fix and rebuilds it. `ASASM_OBSERVER`, if set, must identify a tool with that fix. No prior tool tree is modified.

The keyboard experiment supplies the exact pinned kernel, public workspace and restored headers. The builder checks their original header-export hashes, copies sources to an isolated work tree, applies patches 16–21 and builds the compressed sprite from the public source asset. Its host-only Squash adapter uses the matching portable compressor and decoder, unsigned-char semantics and two byte-identical round trips. This is a single-shot asset build, not validation of the compressor's unused restart modes.

Each module is assembled twice normally and once with the observer using `-cpu=ARM2 -apcs 3/26bit -aof -Uppercase`. Modules use a single **relocatable read-only code area**, with all internal references resolved. Do not reinstate `-ABSolute`/`ORG 0`: it permits incorrect absolute-address optimisations when moving modules into ROM. `module_image.py` requires a single code area, no unresolved symbols and no relocation records; `audit_modules.py` independently decodes the emitted words, checks branch destinations, ARM2 settling and absence of ADR-to-absolute-MOV folding.

The full recipe then packages the ROM and executes three fresh cold boots, natural continuations, CAM transfer fixtures, keyboard/Help, MessageTrans and territory client suites, plus the font/pixel tests. Independent verifiers inspect saved results and memory contracts. The successful runtime captures were produced by the full recipe; a patch-diff line-count issue in the final replay check was subsequently fixed without changing the ROM. `logs/final-validation.log` records the final complete verification. Original 8-bit source bytes require newline-only patch splitting: Unicode `splitlines()` incorrectly counts embedded character-table bytes as line breaks.

For module/container-only rebuilding:

```sh
python3 experiments/arm2-territory/scripts/build_observer.py
python3 experiments/arm2-territory/scripts/build_modules.py
python3 experiments/arm2-territory/scripts/audit_modules.py
python3 experiments/arm2-territory/scripts/package_rom.py
python3 experiments/arm2-territory/scripts/territory_expectations.py
```

Expected SHA-256 values:

```text
kernel.bin     cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
territory.rom  e5d6697f0825a9016c0c961c261f4fc8041334ef9ae74eaa14f7c0623ae398d3
```

To verify supplied execution evidence without claiming new boots:

```sh
python3 experiments/arm2-territory/scripts/verify_regressions.py
python3 experiments/arm2-territory/scripts/verify_keyboard.py
python3 experiments/arm2-territory/scripts/verify_messages.py
python3 experiments/arm2-territory/scripts/verify_territory.py
python3 experiments/arm2-territory/scripts/finalize.py
```

For manual patch review/replay, copy `sources/` to a temporary directory and the keyboard milestone's `work/HdrSrc/hdr/CPU/Generic26` to `SharedHeaders/CPU/Generic26` inside it. Apply `patches/series` in order with `patch -p1 -F 0`. The finalizer compares every patched module/header/Squash source with the actual build inputs. `Messages/ResourcesData` and `TerritoryManager/SystemDiscSquashed` are generated data, not manually supplied binaries. The separate observer patch applies to the previous observer tree, not module sources.

Load `artifacts/territory.rom` into MacArch: A440/1, ARM2, 4 MiB, standard monitor, no media, default CMOS/Delete at cold power-on. At Supervisor, type `Territories`, `Help`, or `Type Resources:$.rEsOuRcEs.uK.mEsSaGeS`. ResourceFS is read-only; no desktop is expected.

To create the source/ROM/evidence bundle:

```sh
python3 experiments/arm2-territory/scripts/package_evidence.py
```

This writes `../arm2-territory-evidence.tar.gz` and its SHA-256 sidecar, verifying every member against its source file. The previous MessageTrans evidence archive is included, with earlier prerequisites nested. Extract the nested archives into a common parent to reconstruct sibling directories. Host tool binaries, native harness build products and caches are excluded; tool sources and reconstruction instructions remain in the earlier evidence chain.
