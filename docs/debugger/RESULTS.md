# Original Debugger

The default ROM includes the original cleaned-3.60 Debugger 1.45
(`Programmer/Debugger` @ `973b1967d8ff1c48dcd138d1d27f1721217228b8`): `*Memory`,
`*MemoryA`, `*MemoryI`, `*InitStore`, `*BreakSet`, `*BreakClr`, `*BreakList`,
`*Continue`, `*ShowRegs` and `*Debug`. Its 26-bit address-wrapping variant is
selected (`CPU_Type` is not ARM600). It is 8,852 bytes with 1,862 decoded ARM2
instructions and no FPA code; with its messages the ROM grows by 11,312 bytes.

[`patches/debugger/0001-arm2-build.patch`](../../patches/debugger/0001-arm2-build.patch)
adds a relocatable AREA, removes `LEADR`, uses the maintained `KernelEntry`
spelling and takes the exported `DebuggerSWI_Base` (the maintained header
defines `DebuggerSWI` as a full chunk index). The original tokenised help is
used unchanged.

```sh
python3 tools/build_system_modules.py debugger
python3 tests/run_debugger.py
```

`tests/run_debugger.py` types at the real F12 command line (`BasicRunProbe`):
`*MemoryI` words equal the ROM's and their operands equal an independent
decode; `*Memory` matches the ROM; a breakpoint in a BASIC-assembled routine
stops with the expected registers, and `*Continue` (executing out of line)
returns to BASIC. A ROM without Debugger reports `File 'MemoryI' not found`.

Not tested: `*MemoryA` editing, `*InitStore`, breakpoints in ROM, and
interaction with unusual exception states.
