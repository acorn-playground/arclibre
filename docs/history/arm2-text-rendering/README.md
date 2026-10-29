# System text rendering repair

**Fixed:** the kernel's system font was not word-aligned. ARM2's unaligned `LDR` behavior corrupted the font during its copy into VDU workspace. Explicit alignment makes the text legible without changing MacArch.

- Repaired experimental ROM
- Readable display after repair
- Printable ASCII test
- [Results and separate runtime failure](RESULTS.md)
- [Exact build and verification instructions](BUILD.md)
- Source patch
- Acceptance report

ROM SHA-256: `7d7835feaf0b31f5ea6ebdaf8a2798079c270979ac931ede7420e273315e2859`.

The repaired display reads `Error: !!!! CAM Map Corrupt !!!! (Error Number &0)`, followed by the kernel's command prompt. **This is an existing later-startup error, not a successful complete OS boot.** Both old and repaired ROMs encounter the same CAM lookup failure after the preceding experiment's pre-module stopping point. That separate defect is recorded, not hidden or bypassed.

The ultimate target remains RISC OS **3.11** compatibility on original ARM2/ARM3 hardware. This change certifies the specific font-copy/rendering path tested here; it adds no runtime module, desktop, application support or proprietary ROM content.
