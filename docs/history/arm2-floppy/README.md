# Original-machine read-only floppy milestone

**PASS.** Matching public FileCore and ADFS modules now catalogue and read a generated D-format floppy through the original WD1772/FIQ path. The ROM loads and executes an original ARM2 program in USR26, then returns to Supervisor. Three independent cold boots produce identical checked results.

The implementation baseline is the publicly released **cleaned RISC OS 3.60 source cohort**, with the documented original-machine restoration patches. **It is not based on RO26.** The compatibility target remains unmodified RISC OS **3.11** applications, desktop utilities and games; this milestone does not establish that wider compatibility.

- ROM: `artifacts/floppy.rom` (2 MiB; 381,128 bytes occupied).
- Original generated test disc: `artifacts/disc/arm2-test.adf` (800 KiB).
- Build: [BUILD.md](BUILD.md), `scripts/run.sh`.
- Results, limitations and next milestone: [RESULTS.md](RESULTS.md).
- Source changes: `patches/series`, patches 24–28; earlier patches retained.
- Gates: `artifacts/acceptance.json`, `artifacts/floppy-verification.json`.
- Traces and saved memory: `artifacts/floppy-{1,2,3}/`, `artifacts/repeats/` and the retained regression suites.
- Source pins and hashes: `manifests/cohort.json`, `manifests/source-files.json`.
- Licensing: [LICENSING.md](LICENSING.md).

Kernel SHA-256 remains `cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30`. MacArch core is unchanged at `550bee4842e45eafdf331f0d06e11df1368403e8`. No proprietary ROM material, substitute service handlers, desktop integration or disc-writing tests were introduced.
