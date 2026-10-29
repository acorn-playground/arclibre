# Host source dependencies

These dependencies build and test the ROM; they are not guest modules. `manifests/toolchain.json` records upstream URLs/revisions and SHA-256 values of the supplied source archives. Their original copyright/licence files remain inside the archives. No precompiled host executable is supplied.

- `archives/gccsdk-tools.tar.gz`: unmodified tracked AsAsm, decaof and current ELF-toolchain sources from GCCSDK `212d4567f007e7d30f4af3d6e1919a3d8a115b1c`. The archive was exported with worktree attributes to avoid an unavailable unrelated promisor attribute blob; the included tracked source bytes are from the pin. The original relative symlinks are retained.
- `archives/m4-1.4.20.tar.xz`, `autoconf-2.72.tar.xz`, `automake-1.17.tar.xz`: original official GNU archives, checked against the previously recorded upstream hashes.
- `tokenise/`: public tokenise source at `d6ea854482663935562dc4c1bc2cde4bf3b570aa`; two existing host C fixes are applied in the build directory.
- `compat/`: existing Darwin host-layout headers needed by the old object-file tooling.
- `archives/macarch-core.tar.gz`: public MacArch core at `550bee4842e45eafdf331f0d06e11df1368403e8`. Tests extract separate original and patched copies under `build/`, with the recorded original-machine disc-change repair applied only to the latter.
- `patches/`: existing observation-only assembler patches, tokeniser host fixes and emulator device repair. They retain their upstream license obligations.
- `patches/asasm-portable-host.patch`, `patches/gccsdk-3.4.6-case-insensitive.patch` and `patches/macarch-portable-host.patch`: host portability only. AsAsm and the C preprocessor fall back to a unique case-insensitive name match, and AsAsm counts Latin-1 no-break space as blank, as the macOS hosts did. The MacArch core gets portable stand-ins for Apple's Compression, CryptoKit, Keychain and SDK zlib module, and its unit tests build with swift-corelibs-xctest. Interrupt trace lines print their vector instead of an unchecked read past an empty register list. This patch is applied off macOS only. None changes assembled, compiled or emulated behaviour where the macOS host already worked.

GNU Libtool and pkg-config's aclocal macros, Apple developer tools (or, on Linux, Bison, flex, M4 and the zlib headers), Swift and Python are installed host prerequisites. Bootstrapping uses those existing installations without modifying them. Generated sources, object files and native binaries are confined to `build/`.

The original compiler/version/binary-hash fields retained in the toolchain manifest describe the historical bootstrap, not newly built executable hashes. A fresh build writes its actual hashes to `build/toolchain-build.json`. ROM/component bytes, rather than host executable hashes containing build metadata, are the reproducibility gate.

`archives/gccsdk-3.4.6-arclibre.tar.gz` is the selected public historical C
compiler/linker source cohort pinned by `manifests/c-toolchain.json`. The unused
CMunge directory is excluded because it has separate restrictive terms;
`manifests/c-toolchain-selection.json` records every exclusion and both archive
hashes. Retained payloads are unchanged and keep their individual notices. Its host and ROM-library
compiler patches and build instructions are described in
`docs/desktop-c/TOOLCHAIN.md`. The compiler/linker GPL notices and other components' notices remain in the archive.
Only host tools are used; no GCCSDK target runtime is included in the ROM.
