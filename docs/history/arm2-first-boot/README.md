# First real ARM2 kernel ROM boot

**PASS: the unchanged restored kernel cold-boots in MacArch to the entry of `ModuleInit`, before module initialisation executes.** The MCP-driven run and three independent fresh-machine harness runs reached the same boundary. Their cold-start checkpoint registers and captured state match exactly.

The experimental ROM is a 2 MiB container containing the exact pinned 142,148-byte kernel followed by zeros. No kernel or emulator patch, additional module or success stub was needed. It is an experimental pre-module image, **not a complete RISC OS ROM or usable desktop**.

- [Results and remaining issues](RESULTS.md)
- [Exact build and execution instructions](BUILD.md)
- [Verification, traces and memory effects](VERIFICATION.md)
- [Packaging and licensing](PACKAGING_AND_LICENSING.md)
- [Recommended next phase](NEXT_PHASE.md)

ROM SHA-256: `651ad2015c8c3f427ab070c124c6282c2e1d717d421f518545a04710d152c2bb`.

The ultimate target remains **RISC OS 3.11 compatibility** for unmodified desktop applications, games and utilities on original ARM2/ARM3 hardware. This run tests ARM2 reset and kernel initialisation only. No desktop or general application compatibility work was performed.
