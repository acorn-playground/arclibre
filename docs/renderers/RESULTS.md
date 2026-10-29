# Original-machine rendering providers

**PASS:** ColourTrans, Draw, SuperSampler and Hourglass assemble reproducibly and execute through genuine module/SWI/vector paths on ARM2. Three fresh cold boots produce identical results. The baseline ROM/kernel and emulator are unchanged. This is the rendering-provider milestone before FontManager and Wimp integration.

## Components

The source revisions remain those in [desktop-cohort.json](../../manifests/desktop-cohort.json), all cleaned-3.60 imports. Each module has zero unresolved symbols/relocations and matching ordinary/repeated/observer objects.

| Component | Module bytes | Independently decoded ARM2 instructions |
|---|---:|---:|
| Colours / ColourTrans | 16,376 | 3,644 |
| DrawMod / Draw | 10,104 | 2,372 |
| Super / SuperSample | 2,320 | 255 |
| Hourglass | 2,148 | 368 |

[Assembly hashes](reports/assembly.json) and [runtime acceptance](reports/acceptance.json) are retained. The strict integer decoder is unchanged: no coprocessor instructions, later ARM instructions, absolute module-address ADR folding or unresolved code/data discrepancies are accepted. Direct branches target emitted instructions and mode changes have ARM2 settling instructions.

## Source changes and generated tables

[0002-renderer-contracts.patch](../../patches/desktop-source/0002-renderer-contracts.patch) follows the earlier desktop patch. It changes ten source files:

- Real relocatable areas replace LEADR/implicit module origins.
- Entry macros use KernelEntry; ColourTrans and Hourglass use the public absolute SWI base definitions.
- Three processor-state transitions receive explicit settling NOPs.
- ColourTrans's PC-byte store used to force a nonzero cache-invalidation flag becomes an explicit `MOV R0,#1; STRB R0`. The real cache-flush routine is retained and exercised.
- Draw's three fixed public workspace-address loads explicitly use MOV instead of ADR: IRQsema at `&108`, ScratchSpace at `&4000`. These are existing kernel contracts, not relocatable module labels or fabricated storage. Emitted values are unchanged.

The original SuperSampler source requires `s.Matrix1` and `s.Matrix2`. Its preserved tokenised BASIC generators are complete. [generate_super_tables.py](../../tools/generate_super_tables.py) parses their actual weighted-bit formulas and loop bounds, produces the same tables, and replaces only the timestamp comment with deterministic text. It checks original input hashes, formula shape, complement symmetry and bounds. The version >=5 reverse 511..1 table is deliberately preserved. Runtime results are checked against a separate direct two-dimensional convolution, not against those generated lookup tables.

The [patch verifier](../../tools/verify_candidate_patches.py) reverses the complete desktop series to all original pinned hashes and reapplies it without fuzz. Raw public sources, notices and generated-input algorithms remain identifiable.

## Runtime evidence

Each run dynamically loads the four real modules through `OS_Module`, verifies their installed bytes, registers the two public message resources and performs **61 SWI calls**:

- RGB/HSV round trips include exact primary-colour hue/saturation/value checks and a mixed colour.
- Palette conversion, cached conversion and invalidation agree for five colours in original mode 12.
- Draw transforms a path using a real fixed-point affine matrix. An invalid element returns the translated `Bad path element` error.
- A Draw-filled rectangle changes exactly 5,000 pixels, at the expected 100-by-50 pixel coordinates for mode 12's eigen factors. The independent verifier checks every framebuffer pixel, including unchanged surrounding memory.
- Both SuperSampler algorithms process four original input patterns. All fourteen output pixels per case match an independent 7x7 or 9x7 convolution, including rounding, clipping and the original low-intensity threshold. Output sentinels remain untouched.
- Hourglass claims TickerV, executes its real periodic handler, generates pointer data, updates its displayed percentage to 42 and releases its active depth. The harness waits for return to its own SVC idle loop before issuing another call; it does not interrupt an active handler to inject a test. The original first pointer setup resets percentage state, so percentage is set after initial display setup.
- All modules unload through their real finalizers. No undefined instruction, abort, address or unexpected FIQ exception occurs.

[Runtime calls/results](reports/runtime.json) and [generator evidence](reports/generated-tables.json) are retained; complete traces, framebuffer bytes, pointer data and cold snapshots remain under `build/render-components/`.

## Licensing and reproduction

```sh
make renderer-components
make renderer-test
```

The modules and their source patches retain the pinned component Apache-2.0 licences. The two original UK message files are recorded [separately](reports/resources.json); neither has its own file-level licence notice, so their basis is the attached component licence. The generator port retains Acorn attribution and uses the original Apache-covered algorithms. No proprietary ROM or asset extraction is involved.

The maintained source export includes these components, generators, tests and notices. No installed MacArch application is changed. `make test` retains the full earlier boot/filing/write regressions and `make fpe-test` retains the software-FP gate.

## Scope and next work

These sampled APIs and pixel checks do not cover every Draw path, clipping mode, sprite depth, colour calibration, palette change, hourglass appearance, interrupt interaction or numerical boundary. Super is SuperSampler, not SpriteExtend. Any additional sprite-extension dependency must be established explicitly during Wimp bring-up.

The subsequent [font-stack gate](../font-stack/RESULTS.md) and [isolated Wimp task](../wimp-stack/RESULTS.md) now pass with these providers. Multi-task scheduling and desktop startup remain. Neither this milestone nor the 3.60 source choice establishes RISC OS 3.11 application compatibility.
