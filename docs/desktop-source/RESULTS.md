# Desktop source and assembly closure

> Historical assembly milestone. The full desktop and native Draw/Paint/Edit now run.
> Current appearance uses plain original furniture; see the [current roadmap](ROADMAP.md)
> and [standard-service audit](../system-audit/RESULTS.md) for remaining work.

The maintained tree now includes real Wimp, FontManager and ROMFonts runtime sources, selected public desktop assets and matching build dependencies. These are no longer header-only components. All three assemble reproducibly with no relocations or unresolved symbols. They now initialize together in the [isolated Wimp task gate](../wimp-stack/RESULTS.md); a full desktop has not been launched. This report retains the original assembly-closure evidence; later runtime findings and the message-list correction are recorded separately.

The compatibility target remains unmodified RISC OS 3.11 applications and games on original ARM2/ARM3 Archimedes hardware. The 3.60 implementation cohort, its selected 3D window furniture, and successful assembly do not establish that compatibility or visual identity.

## Source cohort

| Component | Exact public cleaned 3.60 import | Build result |
|---|---|---|
| Wimp | `530acd4a18ffa97ce7a6b5b20fdef0a4db3ef647` | 3.66; 81,544 bytes; 17,672 integer ARM2 instructions plus 21 real FPA instructions |
| FontManager | `f883f98662b95d16a03129835883f79a935910fd` | 3.33; 60,084 bytes; 13,868 integer ARM2 instructions |
| ROMFonts | `2aa781763cc8ee15b140f88b9e1ccc3e00b082b5` | 0.16; 250,000 bytes; 46 integer ARM2 instructions plus font resources |

The [cohort manifest](../../manifests/desktop-cohort.json) records repositories, all eleven exact revisions, notices and roles. Matching source candidates for ColourTrans, Draw, SuperSampler and Hourglass are retained. HostFS, PDriver, Switcher and FPEmulator headers close the missing public exports. The original FPASC wrapper/veneer is retained separately: that 3.60 snapshot does not contain ARM's core.

[desktop-inputs.json](../../manifests/desktop-inputs.json) records original and maintained hashes for 166 selected files. Existing source/header bytes were not replaced by unrelated desktop revisions. Shared headers still use the existing explicit kernel/module export map, including the previously documented later public registration definitions. The seven additional exports have their own [map](../../manifests/desktop-header-exports.json).

## Reviewable adaptations

The [desktop patch](../../patches/desktop-source/0001-assembly-contracts.patch) records changes to 29 files:

- Relocatable module areas preserve PC-relative addressing under AsAsm. No absolute origin is substituted.
- Old Entry macro calls use the maintained KernelEntry name, avoiding collision with the assembler directive.
- Backslash character/string literals preserve original bytes under AsAsm's escape rules. Original font-string assertions remain enabled.
- Wimp and Font SWI bases use the exported absolute base definitions. Assertions prevent double-adding the base to newer public registration numbers. The FPEmulator header uses the same correction.
- Explicit alignment keeps labels attached to instruction boundaries where original ObjAsm implicit padding differed.
- Explicit NOPs protect ARM2 processor-mode/banked-register transitions.
- The native host filename for the `.Base0` encoding is mapped without changing its ResourceFS name or payload.

No runtime service is stubbed and no FPA instruction is removed. The original Wimp default path can probe old/new kernels at runtime; its original `Medusa` build flag is not proof that an original-board path works. The subsequent Wimp gate verifies that the original MEMC path is selected.

## Assets and verification

[desktop-assets.json](../../manifests/desktop-assets.json) selects 39 files, 592,677 bytes, following the original UK build recipes: Wimp messages, templates and sprites, its WIMPSymbol font, FontManager messages and the Corpus/Homerton/Trinity ROM fonts and encodings. Each payload has an exact origin, hash, resource name, route and licence basis. The [licensing assessment](../../licenses/desktop/ASSESSMENT.md) distinguishes component-wide licence coverage from absent file-level notices and records exclusions.

The builder verifies every selected input and actual embedded ResourceFS payload, checks single-area resolved objects, independently decodes integer instructions, validates direct branch destinations, checks ARM2 settling and rejects absolute ADR materialization. The small zero alignment gap before Wimp's `vduinput` table is explicitly bounded, non-targetable by direct branches, and follows a return; it is not silently treated as code. Two ordinary assemblies and the observation-only assembler produce identical objects. Generated resource-copy timestamps are normalized to remove host mtime nondeterminism; source payloads are unchanged.

Wimp's 21 FPA instructions are explicitly reported as requiring software emulation on bare ARM2. Its conditional `WFSEQ` executes even when there is no saved FP block, so this dependency cannot be bypassed by merely avoiding FP-using applications. The separate [FPEmulator milestone](../fpemulator/RESULTS.md) implements and tests that prerequisite with the exact Wimp FPA encodings.

## Reproduction and boundaries

```sh
make desktop-components
make fpe-test
```

Candidates and audit evidence are in `build/desktop-components/`; the six external resources are in `external-resources.bin`. The baseline ROM and kernel remain byte-identical. The assembled candidates are not joined into the baseline ROM.

The [rendering providers](../renderers/RESULTS.md), [font stack](../font-stack/RESULTS.md) and [isolated Wimp task](../wimp-stack/RESULTS.md) now pass their runtime gates. Next, test multiple genuine application tasks and slots. Desktop, Filer, TaskManager and applications are subsequent milestones; neither assembled Wimp nor these font assets are a complete desktop distribution. See [the roadmap](ROADMAP.md).
