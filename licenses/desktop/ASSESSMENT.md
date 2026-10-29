# Selected desktop source and asset assessment

This assessment covers the exact files in `manifests/desktop-inputs.json` and `manifests/desktop-assets.json`. It does not grant a new licence or clear arbitrary RISC OS desktop material.

## Source and permission

The selected sources come from public component Git histories on the [4corn RISC OS mirror](https://gitlab.4corn.co.uk/RiscOS/Sources), at the cleaned RISC OS 3.60 import revisions in [desktop-cohort.json](../../manifests/desktop-cohort.json). Every selected component's upstream LICENSE is retained under `src/<component>/LICENSE`. These are Apache License 2.0 texts; individual Acorn attribution and licence notices remain in the sources. Modified files are identified and the transformation is preserved in `patches/desktop-source/`.

The scope includes Wimp, FontManager, ROMFonts, Colours, DrawMod, Super, Hourglass and the four missing interface components HostFS, PDriver, Switcher and FPASC. Presence of source is distinguished from whether a runtime is built, tested or included in a ROM.

## Selected binary and text resources

The asset manifest identifies 39 source inputs, their exact hashes, original repository/revision, selected destination and licence evidence. They are public native source-tree resources, not bytes extracted from a ROM image.

| Selection | Files | Basis and qualification |
|---|---:|---|
| Wimp UK messages, Template3D, Sprites, Sprites22 and Tools3d | 5 | Pinned Wimp component LICENSE; native resources have no separate file-level licence notice |
| WIMPSymbol encoding, bitmap, metrics and outline | 4 | Same Wimp component LICENSE; original resource recipe embeds these files |
| FontManager UK messages | 1 | Pinned FontManager component LICENSE; no separate message-file notice |
| Corpus, Homerton and Trinity metrics/outlines plus five encodings | 29 | Pinned ROMFonts component LICENSE; original ROMFonts source explicitly embeds this selection; individual native resources lack separate licence notices |

The project's redistribution assessment relies on the licences attached to these exact public component distributions, not merely their public accessibility. A review of the selected resource contents found no additional conflicting embedded copyright/licence statements. This is evidence about this selection, not a representation that each asset contains an explicit individual Apache grant. The encoding glyph name `/copyright` is not a copyright notice. Four oblique outline inputs are original derived-font references to another selected font and a transform; they are not missing or corrupt outline data.

Sprites contain 147, 149 and 80 named sprites respectively. Original templates, sprites and font naming are preserved for compatibility; Apache-2.0 does not provide a general trademark licence or imply endorsement by Acorn or any later rights holder. The selected 3D templates and furniture follow the 3.60 recipe and do not establish 3.11 appearance.

Unused Wimp resources, experimental Darwin font aliases, private documentation, tests and additional desktop/application payloads are excluded. No commercial application, disc or ROM was used to recover assets. Further assets require an explicit selection and provenance review.

## Distribution obligations

Supply the applicable Apache-2.0 texts, preserve source copyright/attribution and any applicable NOTICE material, and identify modified files. The selected component trees supply LICENSE files; the recorded upstream notice inventory contains no separate selected NOTICE file. The [Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0) governs; this assessment is not a replacement licence.

The later complete software FPEmulator is a separate, explicitly recorded cohort exception. Its ARM core has BSD three-clause terms and must retain those terms in binary distribution materials. See [FPEmulator assessment](../FPEmulator-assessment.md); do not label the whole emulator Apache-only.
