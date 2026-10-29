# Rebuilt headless MCP verification

The reconnected MacArch MCP server cold-booted the unchanged experimental ROM as A440/1, ARM2, 4 MiB, standard monitor, no hard discs and reset CMOS. The snapshot now includes `floppyDiscChanged`, confirming that the running process contains the device patch. The earlier connection lacked that field even though the on-disk executable had been rebuilt; reconnecting resolved it.

Through actual MCP commands and the guest command parser:

1. Mounted a disposable copy of generated DA.adf; `Load ADFS::0.$.RootText 20000` produced all 43 exact bytes of `DISC A -- same pathname, different media.\r\n` in guest RAM.
2. Ejected A, ran one emulated second, inserted DB.adf, ran one second, and repeated the same Load. RAM contained the complete B version. No dismount, reset, guest cache manipulation or success handler intervened.
3. Ejected B and repeated Load. ADFS returned `The disc drive is empty (Error number &108D3)`.
4. Reinserted A and repeated Load. All 43 A bytes returned correctly.
5. Ran `dir adfs::0.$` then `.`. The guest listed CheckFile, Docs, Hello, RootText and Zero. This is the state left in the connected headless instance.

`artifacts/transcript.json` records the complete successful sequence, including command output and memory peeks. Snapshots before/after the swap and at completion preserve machine state. The small native inspector independently restores those snapshots and verifies A/B/A bytes, the patched header field, zero write-overlay entries, and zero undefined-instruction/prefetch-abort/data-abort/address exceptions. `artifacts/verification.json` records its result. Both copied host disc files also remain byte-identical to the original generated fixtures.

The existing MCP `load_disc` API does not expose write protection, so these particular disposable mounts are **not write-protected**. Only read commands were issued, and snapshot inspection verifies no guest writes. The preceding 42-scenario native suite separately enforced write protection throughout. This live test is one additional cold boot and an MCP integration check, not a repeat of all 42 scenarios.

The ROM hash is unchanged: `bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791`. No emulator or ROM source changed during this follow-up. The implementation remains the restored public cleaned 3.60 cohort, with RISC OS 3.11 application/game compatibility as the eventual target. No proprietary ROM, desktop integration or guest write experiment was used.

To repeat manually with the same ROM/configuration, follow the five steps above using `artifacts/DA.adf` and `artifacts/DB.adf`; the transcript contains exact tool arguments. To recheck the saved states:

```sh
env MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore \
  swift run --package-path experiments/arm2-filing-mcp/harness \
  --scratch-path experiments/arm2-filing-mcp/build --disable-sandbox \
  --build-system native -c release Inspect \
  /absolute/path/to/riscos-oss/experiments/arm2-filing-mcp
```

The inspector is original Apache-2.0 code using the GPL-covered MacArch core as a host dependency; no native executable is distributed in this evidence directory. Earlier ROM, fixture and tool licensing remains documented in `../arm2-filing/LICENSING.md`.

The operational media-change milestone is complete. The next bounded ROM milestone is controlled file creation/writing and remount verification on disposable generated images, before desktop integration. It has not begun in this follow-up.
