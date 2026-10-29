# Source changes

No kernel, assembler, header or emulator patches were needed for this boot milestone.
The packaging operation retains every kernel byte and appends zero padding to the configured 2 MiB size.
New host harness/build/verification code is contained in `../harness/` and `../scripts/`.
The original restoration patch series remains in the accompanying restoration evidence package.
