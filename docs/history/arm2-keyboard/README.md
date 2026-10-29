# Resident A1 keyboard milestone

**PASS for bounded keyboard input.** The experimental ARM2 ROM accepts typing at Supervisor, editing, modifiers, Escape and autorepeat. Three cold boots produce identical input results. Full `*Help` output remains blocked by the absent MessageTrans module; command dispatch itself is verified.

- Experimental ROM
- [Results and remaining dependencies](RESULTS.md)
- [Build instructions](BUILD.md)
- Source patch series
- Acceptance report
- Keyboard verification
- Captured command display

ROM SHA-256: `c8128177ca866eda984c920eb543f6f1320f9e9a23d149187de164ee5c3a1745`.

This is the pinned restored 3.60 kernel cohort, with its original resident A1 handler enabled. The ultimate target remains RISC OS **3.11** applications and games. This milestone does not establish that compatibility or provide a desktop, file services or a complete OS.
