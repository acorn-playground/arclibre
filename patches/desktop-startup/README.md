# Desktop startup restoration

The exact cleaned public 3.60 inputs and retained hashes are listed in
`manifests/desktop-startup-inputs.json`. These are original implementation sources,
not replacements written from interface descriptions. The original historical
experiments remain untouched.

`0001-arm2-assembly.patch` introduces relocatable AOF areas, removes obsolete
fixed module load directives, uses the maintained `KernelEntry` spelling to avoid
AsAsm's case-insensitive ENTRY directive, corrects the logical NOT operator in
Filer, and uses the exported Switcher SWI base directly (without adding the OS
base a second time). NOPs after processor-state changes in Desktop, Filer and
TaskManager satisfy ARM2 pipeline settling. No routine is replaced with a stub.

Filer's help source is tokenised at build time with the existing public host tool
and pinned HdrSrc Tokens, following its original Makefile. The generated result
and retained historical tokenised source are hashed separately. Two ordinary
assemblies and the observer build must match byte for byte. Independent decoding
checks integer ARM2 opcodes, branch targets, code/data coverage and settling;
resolved AOF extraction rejects external symbols and relocations.

`python3 tools/verify_candidate_patches.py` reverses the patch to every original
hash and reapplies it with zero fuzz. Additional public Econet, FilerAct and
DragASprit imports are interface headers only, not runtime services.

`0002-project-name.patch` changes the welcome title to ArcLibre. The original
Acorn copyright line and source notices remain intact.

`0003-pinboard.patch` applies the same relocatable-area and macro spelling
adaptations to the matching Pinboard source. The real Pinboard background
window removes the splash screen after Service_StartedWimp; no artificial
screen-clear or startup-service handler is used.

`0004-taskmanager-memc-accounting.patch` selects the existing physical-page map
accounting path (`readareas = FALSE`). With the later-machine readareas path,
the MEMC machine reported total/free application RAM as zero: that branch fills
those fields only for a Medusa free pool. The original alternative enumerates
MEMC pages through OS_ReadMemMapInfo/Entries. The natural ROM test requires the
TaskManager total-memory icon's backing record to equal 4,194,304 bytes.

`0005-spriteextend-arm2.patch` restores the genuine sprite-to-hardware-pointer
provider missing from the first desktop ROM. The kernel's original SpriteOp 36
entry is DoesNowt because SpriteExtend is expected to claim SpriteV. Consequently
the previous click test passed even though no hardware cursor had been defined.

SpriteExtend is pinned to the same cleaned-3.60 cohort (version 0.99). This profile
selects its retained assembly sprite compiler (`ccompiler`, `remoldcompiler`,
`jpeg`, `dynamicarea` false). JPEG SWIs and their implementation are excluded
together; no unsupported JPEG service is advertised or replaced by success.
The C-generated plotting engine and JPEG compiler/build dependencies are not
needed by this profile. The original pointer conversion, sprite operations,
scaling and assembly code generator remain real upstream implementations.

The newer SpriteOp_CheckSpriteArea dispatch still calls the C routine even with
those flags off. Its complete public `c/SpriteOp` validation algorithm is
translated to ARM2 assembly in `Sources/SprExtend`, retaining its old/new mask
rules, bounds/alignment checks, return convention and mode-variable query. The
unmodified C source is retained and compiled on the host as an independent
oracle for bounded valid/corrupt fixtures; no always-success validator is used.
The translation is not a claim to fix all pre-existing malformed-input issues.

Other changes are a relocatable AOF area, removal of LEADR, unambiguous macro
spelling, explicit shift syntax, one PSR-settling NOP, and an equivalent MOVNV
r0,r0 template replacing MOVNV r14,r14. The code generator copies this NOP
unchanged. Static instruction auditing remains strict. The runtime observer also checks any instructions executed from the assembly
compiler buffer. The original startup/pointer-only runs recorded no instructions from that
buffer. The subsequent ADFSFiler/ShellCLI filing gate exercises and independently
decodes generated instructions too; unobserved variants remain outside coverage.

`0006-derived-attribution.patch` makes the splash's origin explicit:
“Derived from RISC OS - © Acorn Computers Ltd, 1995”, below the ArcLibre title.
It retains the original copyright notice and RISC OS glyph byte. Only the
Desktop Messages resource changes; no kernel or application interface changes.

`0007-desktop-filing-providers.patch` imports ADFSFiler 0.83 and ShellCLI 0.28
from their cleaned-360-CD commits. Both are original assembly implementations.
The patch adds relocatable AOF areas, removes LEADR, makes ENTRY macro use
unambiguous, aligns the backup routine following its dismount string, and uses
an explicit NOP for ShellCLI's two ARM2 processor-mode settling instructions.
The backup branch previously targeted padding before the implicitly aligned
instruction; independent branch-to-code validation caught it.

The original ShareD header is absent from the public collection. The two used
SWIs are declared in `src/ArcLibre/hdr/ShareD`, using the existing public
`ShareDSWI_Base` allocation (&47AC0) and the published CreateShare/StopShare
operation offsets (0 and 1). Those offsets are independently recorded in
OSLib's ShareFS header at `3eeb69d103defa42dc77999d9fcecb4af89d05d6`,
`Dist/OSLib/Computer/oslib/Hdr/ShareFS`, in
https://gitlab.4corn.co.uk/RiscOS/Sources/Lib/OSLib . These are authored interface
aliases, not imported OSLib code or an implementation of sharing. ADFSFiler keeps
its original ShareFS module-presence check and menu disabling.

`0008-open-source-splash.patch` makes the public-source origin explicit without
changing the Acorn copyright text. It adds a separate “Derived from the RISC OS
open-source release” line, measures it using the existing 18-point welcome font,
includes its width in the panel bounds and centres it beneath the original
notice. The build manifest records the message and Desktop source changes.
