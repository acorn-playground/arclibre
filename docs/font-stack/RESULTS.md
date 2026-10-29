# Original-machine font stack

**PASS:** the pinned FontManager 3.33 and ROMFonts 0.16 execute with the real ColourTrans, Draw, SuperSampler and Hourglass providers on the restored ARM2 kernel. Three independent cold boots produce identical results and framebuffer hashes. No additional guest source patch, kernel change, emulator change or ROM joining was necessary.

## What is verified

Each run loads all six modules through `OS_Module`, compares the installed bytes with the statically audited artifacts, and registers the original message resources. ROMFonts registers its own 29 embedded font resources. All twelve selected Corpus, Homerton and Trinity faces are found, measured, painted, repainted from cache and released. Module finalizers and ResourceFS deregistration also execute normally. There are 175 explicit harness SWI calls per run, with no undefined instruction, abort, address exception or unexpected FIQ.

For the 20-character string `Open Archimedes 3.11`, an independent host parser reads each original `IntMetric0` mapping, advance array and default advance. Its 12-point widths match the guest `Font_StringWidth` results for all faces. This includes the four oblique faces whose outline files reference and shear their base faces. The parser does not use FontManager's reported widths as expected values.

Mode 12 framebuffer checks confirm bounded glyph output, exact two-colour monochrome pixels, and identical cached repaint bytes. A Homerton antialiased sample produces all sixteen levels after programming a real grayscale palette and calling ColourTrans. Observed SWIs include real `Draw_Fill`, `Draw_Stroke` and `Super_Sample45` calls inside the font routines. The text cursor is disabled through VDU 23 so its timer cannot contaminate framebuffer comparisons.

The original font cache occupies dynamic area 4 at `&01E00000`, with 65,536 bytes mapped to two distinct aligned 32 KiB physical RAM pages. The test checks the actual MEMC translations after every face. FontManager creates this area through the kernel's real dynamic-area interface; the harness does not invent or prepopulate a font workspace.

[Acceptance and independent metrics](reports/acceptance.json), [runtime calls and observations](reports/runtime.json) and [exact module inputs](reports/inputs.json) are retained. Full instruction traces, framebuffers and cold snapshots remain in `build/font-stack/`.

## Reproduce

```sh
make font-stack
make font-test
```

`font-test` rebuilds the baseline ROM and candidates, verifies the recorded source patches, obtains three fresh cold boots, and runs the native probe plus independent metrics/pixel verifier. It preserves all earlier `make test`, `make fpe-test` and `make renderer-test` gates.

For a visual contact sheet, with Pillow installed:

```sh
python3 tools/font_atlas.py
```

The image doubles vertical pixels to account for mode 12's 90x45 dpi aspect. It is a diagnostic preview, not an original desktop asset.

## Provenance and limits

All guest bytes and resources remain those recorded in the [desktop cohort](../../manifests/desktop-cohort.json), [asset manifest](../../manifests/desktop-assets.json) and [licensing assessment](../../licenses/desktop/ASSESSMENT.md). This milestone adds only original test/build code and evidence, under the project's Apache-2.0 terms.

Coverage is deliberately bounded: one ASCII string, twelve selected faces at 12 points, mode 12, monochrome and one antialias configuration. It does not establish arbitrary encoding, kerning, transformed text, large cache pressure, every font format or application compatibility. The 3.60 sources remain implementation inputs; **RISC OS 3.11 remains the compatibility target**. The subsequent [isolated Wimp task](../wimp-stack/RESULTS.md) now passes window redraw, events and floating-point state. Multiple Wimp tasks and slots remain before desktop startup.
