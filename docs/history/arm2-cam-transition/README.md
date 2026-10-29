# Legacy CAM transition repair

**PASS:** the repaired ARM2 kernel passes the former CAM failure and reaches a clean `RISC OS 4MB / Supervisor` prompt. Three cold boots and three repeated page-transfer test suites agree.

- Repaired experimental ROM
- Supervisor display
- [Results, memory contract and remaining dependencies](RESULTS.md)
- [Build and reproduction instructions](BUILD.md)
- Source patch 13
- Combined acceptance report

ROM SHA-256: `3d8bce380345b4a0dc5117e09c8f5de2d3dfd62f7cbe7c5e75cf1b578622f250`.

This is a kernel/Utility-module Supervisor milestone. FileSwitch, filing-system drivers and other runtime modules are absent. Reaching the prompt does not establish a complete OS or RISC OS **3.11** application/game compatibility. No desktop integration was attempted.
