# Contributing to ArcLibre

## The aim

ArcLibre's target is **RISC OS 3.11 compatibility on the original
machines**: unmodified 3.11 applications, games and utilities should run.
Behaving like the 3.60 sources it is built from is not enough; where 3.60
differs from 3.11, ArcLibre follows 3.11.

Some rules follow from being freely redistributable:

- No code, resources, fonts or sprites from Acorn ROM images or other
  proprietary sources, and nothing derived by disassembling them. Comparing
  behaviour with RISC OS 3.11 running in an emulator is fine; copying its
  bytes is not.
- No stand-ins that only pretend to work: a SWI that returns success without
  doing its job is worse than one that is missing.
- No commercial software or media in the repository, including test inputs.

## Changing the sources

Edit `src/`. It holds the upstream sources with every ArcLibre change already
applied; the build copies it and never writes into it.

For each change to an upstream file:

1. Add a modification notice near the top of the file (for example
   `; Modified 2026 by ArcLibre: ...`), keeping every existing notice.
2. Record the change as a patch in the component's group in `patches/` and
   update the file's maintained `sha256` in its manifest in `manifests/`
   (the `upstream_sha256` stays). For a group with one patch,
   `tools/regen_patch.py` does both: run it with `capture` before editing
   and `write` after. The kernel and the first restored modules (the files
   in `manifests/restoration-inputs.json`) keep a numbered series instead:
   `python3 tools/regen_patch.py restoration NNNN-what-it-does.patch`
   records your uncommitted changes to them as the next patch. `tools/verify_candidate_patches.py`, run on every
   build, checks that each patch takes the upstream file to the maintained
   one exactly.
3. Where a change is for the delivered ROM only, put it under
   `[ :DEF: ArcLibreDelivered`, so the frozen baseline still builds exactly.

New components are imported at a pinned upstream revision with a tool like
`tools/import_hardware.py`, which records each file's repository, revision and
hash. Those tools read an optional local collection of upstream sources in
`references/`; nothing else does.

Keep reformatting separate from behaviour changes, and don't run formatters
over imported assembly, resources or patches: their bytes are recorded.

## Tests

Every behaviour ArcLibre provides should have a gate that boots the ROM and
checks it from outside: drive the real desktop or command line, check the
result on the host by independent means, repeat from cold, and include a
negative control that must fail. See [BUILD.md](BUILD.md) for the tiers.
Don't weaken a test to make it pass; if an expectation was wrong, change it
deliberately and say why.

Run `make check` for every change. It builds the ROM and runs the gates for
what you changed. A release runs everything (`make release-test`).

## The emulator

The tests run on the pinned MacArch core. Treat it as fixed: when something
fails, look for the fault in ArcLibre first. A genuine emulator defect gets a
reviewable patch in `third_party/patches/` with a test that demonstrates it.

## Commits

Commit reviewed changes with the tests they need. Build output, ROMs, test
captures and packages stay in the ignored `build/` and `dist/`.
`.gitattributes` turns off line-ending conversion, because file bytes are
recorded in manifests. Two upstream `.gitignore` files, in
`src/Colours/Palettes` and `src/Colours/Tables`, hide files the build needs;
those are tracked with `git add -f`.
