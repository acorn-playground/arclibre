# Open Archimedes: read-only filing robustness

**PASS:** 42 scenarios across three cold-derived ARM2 runs, all retained regressions passing. The restored ROM remains unchanged. A demonstrated MacArch disc-change defect was fixed in an isolated patch, verified, and subsequently applied to the MacArch checkout at the user's request. Running application/server binaries still require rebuilding.

- [Results and limits](RESULTS.md)
- [Reproduction](BUILD.md)
- [RISC OS 3.11 checklist](COMPATIBILITY.md)
- [Licensing](LICENSING.md)
- Emulator patch
- Unchanged experimental ROM
- Generated media
- Verification

This is the original public cleaned 3.60 source cohort, not RO26. The ultimate target remains RISC OS 3.11 application/game compatibility. No desktop integration or guest disc writing is included.
