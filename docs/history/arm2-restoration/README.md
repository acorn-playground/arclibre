# ARM2 kernel restoration

The approved kernel-only milestone passes: a reproducible **142,148-byte ARM2 kernel component**, with no unresolved symbols or relocations, has been assembled from the pinned public RISC OS 3.60 cohort plus explicitly reviewed public interface definitions.

This is a component at `&03800000`, not a joined ROM or a boot result. RISC OS **3.11** desktop, application, game and utility compatibility remains the ultimate requirement and is not established by this milestone. MacArch was not modified or used for boot testing.

- [Results and remaining issues](RESULTS.md)
- [Build and verification instructions](BUILD.md)
- [Source patch explanations](MODIFICATIONS.md) and ordered patch series
- [Workspace and memory contract](MEMORY_CONTRACT.md)
- [Independent verification and exception-path review](VERIFICATION.md)
- [Interfaces, provenance and licensing](INTERFACES_AND_LICENSING.md)
- [Recommended first ROM boot experiment](FIRST_ROM_BOOT.md)

The delivered component is kernel.bin; the corresponding absolute object is kernel.aof. The combined machine-readable gate is acceptance.json. Immutable original snapshots are in `sources/`, restored sources in `work/`, and all target changes in `patches/`. Host-tool observation changes are separate.

Kernel SHA-256: `6fb97a29134f6cea155d4b1ec0e9ca80f3c9f8e61672dd238eea32585a6851f1`.
