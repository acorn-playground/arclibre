# Reproducing the restored kernel

## Existing workspace

From the project root, using the working AsAsm and tokenise built by the previous experiment:

```sh
python3 experiments/arm2-restoration/scripts/run-restoration.py
```

This restores sources twice, assembles twice, compares object bytes, builds an isolated observation tool, assembles with that tool, checks the emitted instructions, exercises bounded MEMC/query routines, inventories public interfaces, verifies input hashes, and replays all saved source patches without fuzz. A successful run ends with `All kernel-only restoration acceptance gates passed.` Its combined result is acceptance.json. A failed rerun removes that combined acceptance file rather than leaving a stale success report.

To assemble only:

```sh
python3 experiments/arm2-restoration/scripts/build.py
```

The script exports headers into `build/Hdr`, regenerates help, and invokes AsAsm from `work/Kernel` with:

```text
MACHINE=A440 IMAGESIZE=2048K HDR_PATH=<absolute build/Hdr>
asasm -ABSolute -Uppercase -cpu=ARM2 -apcs 3/26bit -aof -Verbose \
  -Depend=<absolute artifacts/kernel.d> s/GetAll <absolute artifacts/kernel.aof>
```

`2048K` selects the existing source image-size configuration; it does not create a 2 MiB ROM image. No linker or ROM joiner runs. The independent AOF reader in `verify.py` extracts `kernel.bin` at origin `&03800000`; it does not prepend a container, fill a ROM, append modules or change the entry code.

The default tools are in the sibling `arm2-kernel/toolchain`. Set `ASASM` and `TOKENISE` to absolute executable paths to override them. Set `ASASM_SOURCE` to a **prepared, successfully built tree of the pinned AsAsm source** for the isolated observer rebuild. The observer copies that tree into this experiment; it never patches the original normal tool. Reusing an observer tree from a different host configuration requires removing only this experiment's generated `toolchain/asasm` copy before rebuilding.

## Sources and patch-only reconstruction

All target sources required for this run are supplied. Build and verification need no ROM, DDE, proprietary assembler or network. The cohort manifest, original hashes and public interface hashes identify upstream recovery locations. If the old `/tmp/archimedes-rom-audit/HdrSrc` cache is available, provenance verification additionally compares the later headers with `git show` at the pin. Otherwise it verifies the delivered, previously Git-checked hashes offline.

To inspect the source changes independently of the restoration generator, copy `sources/` to a fresh directory and apply every filename from `patches/series` in order with `patch -p1 -F 0 -i <absolute patch path>`. The generated help file is regenerated after patching. No source commit or newer workspace definition is silently selected.

## Host tool reconstruction

The measured host is Apple Silicon macOS 27.0.1 (26A434), Apple Clang 21.0.0, Python 3.14.0 and GNU Make 3.81. Exact versions and official archive hashes are preserved in toolchain.json. This is same-host reproducibility; another compiler/host's native executable hashes are not promised to match.

The evidence package excludes native tools and downloaded build caches. evidence/host-bootstrap contains the original Darwin compatibility headers, bootstrap script, layout check, tokeniser source and host patch. For a fresh Darwin tool build, choose that directory as the absolute `host_root` and:

1. Create its `toolchain/host/bin` and `logs` directories. Fetch and hash-check GNU M4 1.4.20, Autoconf 2.72 and Automake 1.17 using the URLs and SHA-256 values in the manifest. Build each with `./configure --prefix="$host_root/toolchain/host"`, `make -j4`, `make install`, in that order. Put that prefix's `bin` first in `PATH`; set `M4` to its M4. These are local installations.
2. Supply installed Clang/macOS SDK and GNU Libtool (`glibtoolize`), with its macros under `/opt/homebrew/share/aclocal` as recorded by the bootstrap. No package manager operation is performed by this experiment.
3. Obtain the pinned public GCCSDK tree and prepare the sparse tool dependencies:

```sh
git clone --filter=blob:none --sparse https://github.com/riscos-dot-info/gccsdk.git "$host_root/toolchain/gccsdk"
git -C "$host_root/toolchain/gccsdk" checkout 212d4567f007e7d30f4af3d6e1919a3d8a115b1c
git -C "$host_root/toolchain/gccsdk" sparse-checkout set tools/asasm tools/decaof tools/elftoolchain
sh "$host_root/scripts/bootstrap-tools.sh"
clang -I"$host_root/toolchain/compat" "$host_root/scripts/check-host-layout.c" -o "$host_root/toolchain/host/bin/check-host-layout"
"$host_root/toolchain/host/bin/check-host-layout"
```

The repository symlink from AsAsm to `tools/elftoolchain/current-trunk` must remain valid. The bootstrap preserves the real Git identity, configures the ARM target, and uses the Darwin headers only for host library layouts. No host library is linked into the kernel.

4. Build tokenise from the delivered source and its two host C fixes:

```sh
cp -R "$host_root/sources/tokenise" "$host_root/toolchain/tokenise-src"
patch -d "$host_root/toolchain/tokenise-src" -p1 -F 0 -i "$host_root/patches/tokenise-host.patch"
clang -O2 -x c "$host_root/toolchain/tokenise-src/c/tokenise" -o "$host_root/toolchain/host/bin/tokenise"
export ASASM="$host_root/toolchain/gccsdk/tools/asasm/src/asasm"
export TOKENISE="$host_root/toolchain/host/bin/tokenise"
export ASASM_SOURCE="$host_root/toolchain/gccsdk/tools/asasm"
python3 experiments/arm2-restoration/scripts/run-restoration.py
```

When reproducing outside the original workspace, invoke the script at the extracted experiment's actual location. The host bootstrap recipe was exercised in the preceding experiment and its tools reused here; this phase did not independently redownload and rebuild all GNU prerequisites. The observer tool was rebuilt here.

## Expected outputs

| File | SHA-256 / property |
|---|---|
| `artifacts/kernel.bin` | `6fb97a29134f6cea155d4b1ec0e9ca80f3c9f8e61672dd238eea32585a6851f1`, 142,148 bytes |
| `artifacts/kernel.aof` | `9878071f0fed64608297615860074c8455ed2a76e33886ccddd4710aae6b15f3` |
| `artifacts/kernel-trace.aof` | Identical to normal AOF |
| `artifacts/kernel-instructions.txt` | Independent decoded listing with ROM address, execution address and source origin |
| `artifacts/code-data-ranges.json` | Complete, non-overlapping byte-range classification |
| `artifacts/assembly-result.json` | Actual command, environment, log and tool hashes |

Absolute paths and timestamps in evidence logs may differ between runs. The target component bytes must not. All 43 final warnings are reviewed in diagnostics-review.json; unknown diagnostic categories fail the gate.
