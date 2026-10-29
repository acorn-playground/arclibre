# Source and tool provenance

This experiment used published Git sources and generated text. It did not use a proprietary reference ROM, extract ROM fonts/resources, borrow precompiled kernel/module data, or execute a proprietary RISC OS guest. Apple Clang and the installed macOS SDK were host build dependencies; no host runtime or SDK code is linked into the target assembly objects.

## Candidate kernel inputs

included-component-licenses.json records the 17 component/version/licence records for the selected assembly sources and the tokeniser. All have a root Apache-2.0 licence at the exact selected revision. The original licence texts are in `sources/<component>/LICENSE`, with copies under `licenses/`. Individual embedded notices remain in the source snapshots and modified build copies.

The complete input manifest maps original paths, revision, original and build hashes, modifications and the relevant licence file. Global public headers from Wimp, FileSwitch, FontManager, sound and other components are interfaces; their inclusion does not mean their module implementations or desktop assets were integrated.

The actual font selected by this kernel is **`s/vdu/vdufontl1`**, because `s/vdu/vdudriver` sets `BleedinDaveBell` true. That file carries an explicit Acorn copyright and Apache-2.0 notice and identifies a 1999 update from International 1.54. Its exact hash is in the input manifest. It was not extracted from a ROM. The older `vdufont` also exists in the recovered source, but is not the selected font in this run. Neither selection establishes fidelity to the 3.11 font.

`s/TMOSHelp` is generated from the Apache-covered Kernel `HelpStrs` and HdrSrc `Tokens` by the Apache-covered `tokenise` program. The algorithm is retained, with two host C type corrections. No generated library stub or proprietary message file supplies bytes.

The original local glue, scripts, test fixtures and host compatibility headers in this experiment are supplied under Apache-2.0; see `LICENSE`. This does not relicense upstream GNU/GCCSDK components. Derivative kernel and tokeniser changes preserve their original notices and identify modifications.

## Build tools

| Dependency | Source / terms | Used in target output? |
|---|---|---|
| GCCSDK AsAsm 2.01 | [Pinned public source](https://github.com/riscos-dot-info/gccsdk/tree/212d4567f007e7d30f4af3d6e1919a3d8a115b1c/tools/asasm); GPL-2.0-or-later per source headers, COPYING | Tool only; no runtime is linked |
| Bundled ELF toolchain / decaof | Same pinned GCCSDK tree; ELF library files retain their BSD-style per-file notices; decaof retains its own source notices | Host object-writing/inspection libraries only |
| GNU M4, Autoconf, Automake | Official GNU source archives and their supplied notices; versions/hashes recorded | Host bootstrap only |
| GNU Libtool | Existing local Homebrew installation, version recorded | Host bootstrap/link management only |
| Apple Clang / macOS SDK | Installed developer environment, version recorded | Host compilation only |
| tokenise | Audit pin `d6ea854482663935562dc4c1bc2cde4bf3b570aa`, Apache-2.0 | Produces text from identified Apache inputs; no linked runtime |

The local source checkouts retain the actual tool licence files and per-file notices. This evidence package is not a public binary-tool distribution. Its compact archive excludes tool executables, external source clones and bootstrap caches; source pins, hashes and local adapter code are included. If shipping native tool binaries later, supply the corresponding source and applicable notices rather than assuming their licences match the kernel.

## Distribution status

No kernel binary is cleared or released because none was successfully assembled. The available root/per-file licences support using these identified sources for this private experiment; this is not clearance of a future full ROM's final asset manifest, trademark use, fonts from other repositories or application content. The Phase-0 full-payload licence gate remains open. No DDE/aasm binary entitlement was needed for this attempt.
