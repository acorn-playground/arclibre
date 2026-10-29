# MessageTrans and ROM resources milestone

**PASS:** full `*Help` output and readable error lookup now work on the A440/1 ARM2 configuration. Three cold boots pass the retained keyboard, reset, workspace, CAM and font tests, plus direct MessageTrans client tests.

- Experimental ROM
- Help screenshot
- [Results and remaining issues](RESULTS.md)
- [Build instructions](BUILD.md)
- Patch series
- Acceptance report

ROM SHA-256: `0f0313ba250d83879206fc979dd40de5846b4516f98beed86e3c4156412ac653`.

This adds genuine FileSwitch, ResourceFS, MessageTrans and Messages implementations from the matching public 3.60 import. The keyboard milestone's kernel code and source remain unchanged. This is not a complete OS or proof of RISC OS **3.11** application/game compatibility. No desktop work or emulator changes were made.
