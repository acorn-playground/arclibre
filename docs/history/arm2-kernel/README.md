# A440/1 ARM2 kernel assembly experiment

**Result: FAIL — architectural/source integration blocker at the pinned revision. No valid kernel binary was produced.**

The March 2000 kernel was recovered, its public dependencies reconstructed, and a native open-source assembler built and exercised. Assembly reaches the second pass after configuration and dialect repairs, but the original MEMC workspace does not satisfy unconditional later-machine code. This is a negative result for the proposed source combination, **not proof that an open ARM2 ROM is impossible**.

Read [RESULTS.md](RESULTS.md) for the evidence and next milestone, [MODIFICATIONS.md](MODIFICATIONS.md) for every adaptation, and [BUILD.md](BUILD.md) for reproduction. [LICENSING.md](LICENSING.md) records source and tool terms.

The complete attempt is isolated in this directory. MacArch was not read or modified during this phase. No ROM image, proprietary ROM code, extracted ROM resource, application or desktop integration was used.

Key artifacts:

- Final assembly status and exact command, diagnostics and reproduction log.
- 134 actual assembly inputs, 352 recovered source/reference files, header export map and toolchain versions/hashes.
- Original-machine configuration, configuration glue, kernel changes, AAsm macro adaptation and tokeniser port.
- Assembler validation results. These tiny original test objects are tool tests, **not kernel components**.

The intended product remains a freely redistributable ROM with high **RISC OS 3.11** application, desktop, game and utility compatibility. The later version strings and interfaces in this source candidate do not replace that requirement.
