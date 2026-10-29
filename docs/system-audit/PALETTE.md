# Palette mode labels

ArcPalette 0.03 labels the existing presets `12 (16 colours)`,
`15 (256 colours)` and `16 (16 colours)`. The submenu is widened to 320 OS
units and uses indirect strings, retaining the editable mode-number field and
the existing mode-selection behaviour. It does not add unsupported modes or
change the preset numbers. [Actual menu capture](reports/palette-mode-menu.png).

Build and verification:

```sh
python3 tools/build_palette.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py
python3 tests/run_palette.py
python3 tools/install_macarch_rom.py
```

The assembler's two normal builds and observer build agree. Independent ARM2
instruction checks, relocation/symbol closure and the final ROM static checks
pass. The existing Palette gate passes on three identical cold boots, including
real mode 12/15/16 changes, typed mode selection, rejected text-mode recovery,
palette hardware changes, pointer-leave behaviour, dragging, closing and quitting.
The captured labels were also checked visually for clipping.

Evidence: [assembly](reports/palette-assembly.json),
[cold-boot acceptance](reports/palette-acceptance.json).

The resulting `build/arclibre/arclibre.rom` is 2 MiB, with 1,893,244 bytes used
and 203,908 free; the change adds 84 bytes. Its SHA-256 is
`294d5aec83438e1aad9a69bbf5b5c562f6187aa21f7fac246d0a0e79be2beacc`.
The kernel remains `71b0c301ed58f7f60d84899ca80acdef3d6cb9c9f6d82182f441e66676c35c80`.
The tested ROM was installed into the configured MacArch ROM folder. Reopen the
machine to load it; Power Cycle retains the machine's previously loaded ROM.

This is a targeted Palette verification. The full release archive and its
existing regression reports remain the earlier `2e0fda2c…` release; they have
not been relabelled as verification of this new image. The change is original
ArcLibre Apache-2.0 code and introduces no assets or dependencies.
