# Result and recommendation

## Decision

**Historical source closure: FAIL within the examined public history. ARM2 emitted-code gate: NOT REACHED.** There is no defensible “newest coherent A440/1 configuration” to name from these repositories. Pinning an earlier kernel reduces the work but does not recover a complete original-machine build.

This investigation follows [the previous result](../arm2-kernel/RESULTS.md) and the scope of FIRST_BOOT_EXPERIMENT. It stops at the documented source/interface gap and supplies a restoration design, as requested.

## What was established

1. The unconditional `L1L2PTenhancements` and `AMBControl_Init` reset calls and the AMB include are first visible in the **3.70 import, `fd98e2a10aa9986fc7baaa5375bc4f53a231d49d`, dated 6 November 1996**. They enter merged trunk at **`10073caf45e22ddb3fd3a637762a9e78ddb0bc31`, 21 January 1997**. Their original development predates the available import; Git cannot date that original edit precisely.
2. The IOMD-specific `OS_ReadSysInfo 8` implementation first appears on **Ursula at `b2c0554784089095310b7a0b92ffc94f96b4d804`, 24 September 1998**, then enters trunk with reasons 6/7 at **`b85d7d81d8d76e95440b6db1c39399eaa6a8945b`, 2 February 2000**. February 2000 is the trunk integration date, not its first appearance anywhere in history.
3. The earlier **3.60 import, `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc`**, avoids AMB and the L1/L2 reset call. But it already references `PageFlags_Unavailable` outside the `NewCDA` selection that defines it, and `RawMachineID` without a definition in the selected original workspace. These faults therefore predate the available kernel history.
4. Across **890 reachable Kernel commits**, the recovered `hdr/Old/NewSpace` has **one blob identity**, present in 645 commits. A lexical screen found 197 revisions selecting it, of which 194 actually retain it. All 73 screened revisions without the two later reset calls still reference the page flag and machine ID. The screen is a candidate filter, not a substitute for evaluating every assembly conditional. Manual inspection of the import and branch representatives confirms the relevant mismatches. See candidate summary.
5. The **matching cleaned-3.60 cohort** supplies kernel and module header sources, but not nine required global interface headers. The HdrSrc Makefile names those exports and, for several, absent `Register`/generator inputs. The public registration files first appear in the **2008 cleaned import**; its commit explicitly states that their earlier revision history was not included. The examined BuildSys history also begins with a 2008 clean reimport. These are publication gaps, not evidence that original Acorn builds lacked these inputs.

The [history report](HISTORY.md) distinguishes real code changes, branch manufacture, import dates, and the limits of the evidence.

## Assembly result

The source-coherence screen found no candidate that justified another hybrid kernel assembly. As a bounded check of the strongest matched cohort, the working AsAsm was nevertheless invoked on **unmodified 3.60 sources and matching import headers**, without filling the publication gap using 2008 globals.

The recovery produced **201 source/reference/licence files from 13 components** and **79 isolated header exports**. Wimp, FontManager and other module contributions are interface headers/recipes/licences only; their executable payloads are not part of the experiment. The explicit global-header inventory lacks `SWIs`, `CMOS`, `Services`, `FSNumbers`, `NewErrors`, `UpCall`, `Pointer`, `DevNos` and `PaletteV`; it is not an exhaustive inventory of every possible later transitive failure.

AsAsm was run with `-cpu=ARM2 -apcs 3/26bit -ABSolute -Uppercase -aof`. Its trace selects A440, ARM2/Generic26, IOC-A1, MEMC1a/MEMC1, VIDC1a and `Old/NewSpace`. It first reports missing `Hdr:SWIs`, then additional missing interfaces and consequent symbol/macro errors. It ultimately aborts with an assertion in `Decode`, **return code -6 / SIGABRT**. The unmodified A440 profile also lacks `MorrisSupport`, an ordinary explicit-configuration issue to resolve during restoration; it is not the reason for rejecting the historical source set.

The crash is an assembler error-recovery limitation. It neither establishes a new architectural impossibility nor excuses supplying unrelated headers without review. The source-tree omissions and unselected definitions are independently inspectable. No failed or partial object is retained. Command, environment and tool hash; diagnostics.

There is **no emitted kernel code to certify**, no instruction listing or trustworthy component size, and no boot result. The prior tool smoke checks remain relevant, including the warning that AsAsm's ARM2 option can warn and still accept later instructions. No kernel opcode audit is claimed here.

## Remaining issues and next milestone

Recommend a **kernel-only restoration of the cleaned 3.60 cohort**, starting with a reviewed public interface manifest and original-machine workspace/CAM contract. It is a deliberate restoration, not a recovered historical release. This avoids importing AMB and then trying to adapt its ARM600 memory model to MEMC1.

The [restoration plan](RESTORATION_PLAN.md) identifies routines, interfaces, evidence, acceptance checks and an estimated **12–24 engineer-days**, plus **5–10 days contingency**, for source/interface restoration through static assembly and instruction validation. These are planning estimates, not a claim that all faults are enumerated. Missing lawful interface evidence or contradictory workspace requirements are stop conditions.

Do not advance to ROM joining, MacArch boot testing or desktop integration from this result. The next milestone should end with a fully resolved kernel component, provenance manifest, listing, executable-range map and ARM2/26-bit audit. Subsequent compatibility work must still target RISC OS **3.11**, not merely successful use of later RISC OS APIs or a later desktop.

## Investigation boundary

All advertised branches/tags of the available Kernel and HdrSrc mirror were fetched; both repositories are non-shallow, with 890 and 377 reachable commits respectively. Twelve related repositories were also fetched to compare import cohorts. Coverage and ref hashes preserve the actual scope.

The official Kernel endpoint redirected Git to a 503 page during verification (log). Completeness relative to unavailable upstream refs, unpublished archives or unadvertised objects is unproven. “No coherent set found” is bounded by this evidence; it is not a universal claim about every public archive.
