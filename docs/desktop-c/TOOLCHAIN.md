# Historical C toolchain for ArcLibre

The host compiler is GCCSDK's public `release_3_4_6` cohort, revision
`f79cb59110e2d13566678d923dadba0f97a1321d` from
https://github.com/riscos-dot-info/gccsdk . The exact source archive, hash and
patch order are recorded in `manifests/c-toolchain.json`. No proprietary
Norcroft executable or prebuilt target library is required.

```
python3 tools/bootstrap.py
python3 tools/bootstrap_c.py
```

The second command produces `build/c-toolchain-release/install/bin/gcc` and
`drlink`. Its log and binary hashes are retained beside the install directory.
A changed source/patch manifest invalidates the preparation stamp. The tested
host is Apple Silicon macOS with Apple Clang and the project's pinned GNU M4
and Autoconf 2.72. Other hosts have not been validated.

## Host adaptations

`third_party/patches/gccsdk-3.4.6-host.patch`:

- Recognises the ARM64 host and regenerates configuration with the pinned
  Autoconf and config.guess/config.sub.
- Changes old fixed-arity instruction generator callbacks from an incorrect
  variadic function pointer to the C89 unprototyped pointer used for this vintage
  compiler. Apple ARM64 passes variadic arguments differently; the old casts
  caused compiler crashes. The block-copy callbacks need the same correction.
- Prevents an out-of-bounds language-prefix probe in gengtype.
- Declares `aof_rodata_section` with its actual pointer return type; an implicit
  integer declaration truncated the pointer on a 64-bit host.
- Tolerates warnings in the legacy assembler and excludes the unused CMunge
  utility from the SDK's supporting-tool targets.

C89 host compilation and `-fno-strict-aliasing` are intentional. Only the compiler
and Drlink are used for the guest C build; the legacy GCCSDK assembler is not.
Compiler `-S` output is assembled by the existing checked AsAsm toolchain.
Unused SDK utilities are not claimed to work on a 64-bit host.

`third_party/patches/gccsdk-3.4.6-case-insensitive.patch` lets the
preprocessor open an `#include` on a case-sensitive host. The staged include
directory holds lowercased RISC OS names (`h.editintern.txt1`), and sources
spell them as RISC OS allows (`h.EditIntern.txt1`); the macOS volumes resolved
the difference. When an exact name is missing, each missing path component
takes its unique case-insensitive match, as there. The path the source wrote is
kept for `__FILE__` and line markers. On macOS the exact open already succeeds,
so nothing changes. The x86-64 Linux build of this compiler produces the same
ROM bytes as the Apple Silicon one.

## Signed frame offsets on a 64-bit host

`third_party/patches/gccsdk-3.4.6-signed-frame-offset.patch` preserves the signed
result of `arm_compute_initial_elimination_offset`. A frameless APCS leaf has
an argument-pointer-to-stack offset of -4. The old unsigned 32-bit return value
became +4,294,967,292 when widened to reload's 64-bit host integer; adding the
first stacked argument's +4 produced an invalid +4,294,967,296 address.
Size optimisation exposed this with Draw's seven-argument path-style function.
The compiler now calculates and returns a signed `HOST_WIDE_INT`; it does not
rewrite invalid assembly text or change the APCS stack layout.

`tests/fixtures/CStackArgs.c` isolates leaf and framed seven-argument functions
in a separate translation unit. The public C ABI client calls both `-O2` and
`-Os` versions, checks stacked values and buffer guards, and exercises a real
1,200-byte local frame. The existing disk-loaded ABI gate also retains recursive
stack growth, setjmp/longjmp, varargs, allocation, division and software FPA.
The [isolated cold-run evidence](reports/signed-frame-offset.json) passes on the
unchanged prior ROM; subsequent full filing gates repeat this public client.

## Signed prologue offsets on a 64-bit host

`third_party/patches/gccsdk-3.4.6-signed-prologue-offset.patch` makes the
prologue's `args_to_push` a signed `HOST_WIDE_INT`. It was `unsigned int`, and
`-(4 + args_to_push + fp_offset)` went into `GEN_INT` as +4294967292 rather
than -4, so every function with an APCS frame was emitted as
`sub fp, ip, #-4294967292` (and a variadic one with a frame as
`#-4294967276`) instead of `sub fp, ip, #4` (`#20`). AsAsm wraps immediates
to 32 bits and encoded the intended instruction, so no ROM byte was wrong: the
patched compiler's output for the test cases assembles to identical objects,
and the ROM rebuilt with it is unchanged. The assembly text is now correct for
any assembler. The same patch and its compile-only regression tests are
published separately as
[gccsdk-apcs26](https://github.com/acorn-playground/gccsdk-apcs26).

## Original ROM-library data contract

`third_party/patches/gccsdk-3.4.6-rom-library.patch` is a separate target-code
adaptation. With `-mlibrary-static-data-offset`, it keeps read-only constants in
ROM and refrains from adding a RAM data relocation to their addresses. The old
GCC module profile forced literals into writable data; that exceeded the real
historic SharedCLibrary private reservations.

The ordinary RAM-module profile keeps its previous behaviour. Compilation uses
ARM2, APCS-26 and the SharedCLibrary ABI. The real original library, including
its public data prefixes, is retained. No enlarged invented workspace or
replacement C runtime is used. Link-time data and instruction checks are in
`tools/link_c_desktop.py` and `tools/verify_c_desktop.py`.

## Licensing boundary

The archived GCCSDK compiler and Drlink retain their GPL notices and COPYING
files. The compiler patches are modifications to those GPL host tools.
Their selected source archive and patch files are distributed as source,
retaining the other included SDK components' own per-file notices. They are not
linked into the guest ROM. No GCC target runtime object is used: small
ArcLibre-authored ABI adapters call the original library's real division
routines, including its divide-by-zero handling. This is not a claim that
arbitrary GCCSDK target libraries can be included under ArcLibre's guest terms.

## Selected host archive

The earlier whole-SDK archive also contained CMunge 0.76. Its own
`gcc/riscos-aof/cmunge/Docs/Copyright` restricts commercial bundling and charges;
it is not covered by the compiler's GPL notice. CMunge was built incidentally
by the old SDK make target but its output is not used by any ArcLibre ROM
component. Earlier descriptions of the entire archive as GPL were too broad.

`gccsdk-3.4.6-arclibre.tar.gz` excludes that complete unused directory (57
files). Every retained payload is unchanged from the pinned upstream archive.
[Selection metadata](../../manifests/c-toolchain-selection.json) records the
upstream and selected hashes plus excluded paths/hashes. The former archive
is no longer included in new source packages; its provenance remains recorded
in the manifest and version history. This is source selection, not relicensing.

To reproduce the selection from the pinned upstream download:

```sh
python3 tools/filter_c_toolchain.py upstream-gccsdk.tar.gz selected.tar.gz
```

The bootstrap no longer builds or requires CMunge. Its original restricted
source or modified binary is not included in the new bundle. A future component
requiring generated CMHG veneers needs a separately reviewed solution.

## Checkout-independent diagnostics

A clean export initially differed by 40 bytes when built in a deeper directory.
The compiler had embedded Draw's absolute source pathname through `__FILE__`.
[The before report](reports/checkout-path-before.json) records both ROM hashes.
All ROM C compilation now uses repository-relative source paths with the
repository as its working directory. Draw keeps the real diagnostic filename;
no assertion or runtime functionality is removed. The release process also
rebuilds the source archive in an empty directory, including its host tools,
and compares the complete ROM bytes.

The next comparison exposed a separate five-byte difference in Draw's embedded
ResourceFS catalogue: `:FLOAD:`/`:FEXEC:` inherited Unix mtimes, and the unsuffixed
build copy defaulted to Text. `patches/graphics-apps/0002-deterministic-sprite-catalogue.patch`
uses the source asset's actual Sprite type (&FF9), a fixed zero datestamp, and
its actual file size. The complete sprite payload remains unchanged. The linker
checks the emitted catalogue fields, record bounds and every original asset
byte. This follows the existing deterministic resource packaging contract and
does not change Draw's application code or replace artwork.

The corrected [empty-directory source build](reports/clean-source-build.json)
reproduces ROM `1059cfb0b5b4b87ca1828a428a5cf8f0fa01c9b1f305ec6f1f395fbf813624ee`
with freshly built bundled host tools. The report identifies the tested source
snapshot; later documentation and release-report updates do not change ROM
inputs. `tests/check_source_export.py` repeats this check for a published archive.
