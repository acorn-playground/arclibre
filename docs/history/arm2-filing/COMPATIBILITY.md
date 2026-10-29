# RISC OS 3.11 compatibility checklist

The target remains existing, unmodified RISC OS 3.11 desktop applications and games on ARM2/ARM3 original Archimedes hardware. A restored 3.60 kernel/module cohort is an implementation baseline, not a substitute compatibility target.

| Interface or behavior | Evidence in this milestone | Limit |
|---|---|---|
| OS_File 5 / 255 | Case-folded metadata and exact whole-file loads | Generated files only |
| OS_Find 0 / &40 | Read handles and close; closed handle gives &DE | No output/update handles |
| OS_Args 0 / 2 | Closed-handle error and exact extent | No resizing or flush/write semantics |
| OS_GBPB 3 / 4 | Positioned/sequential reads, residual counts, EOF carry, buffer boundaries | Read paths only |
| OS_GBPB 9 | One-entry pagination, wildcard and nested directory enumeration | Two directory levels, D/E only |
| OS_BGet | EOF carry on zero/nonzero files | No OS_BPut |
| FileSwitch paths | Lowercase lookup, `@`, `^`, explicit ADFS drive 0 | No path variables or other filing systems |
| D/E disc layout | Real old/new maps, shared-object offsets and three noncontiguous extents | One-zone 800 KiB E fixture; not arbitrary E/F/L media |
| Read error recovery | Missing sector, ID/data CRC, directory/map damage; remount recovery | Synthetic controller faults; no physical-drive timing claim |
| Media change / removal | Baseline stale-data regression; patched IRQB4/latch reset behavior | Original A440 model; checkout patched; installed binary not rebuilt |
| ARM2 application entry | Original 280-byte client loaded by OS_CLI at &10000, USR26, real file SWIs, checksum and OS_Exit | Diagnostic source written for this project; not a third-party app compatibility claim |
| Desktop, games, sound, graphics modules | Not exercised | Still required for the ultimate target |

Historical presence of an interface and passing these calls are evidence toward compatibility. They do not establish every 3.11 flag, error, timing or workspace contract. The absence of a legally sourced 3.11 reference run is explicitly retained; no commercial reference ROM was used.
