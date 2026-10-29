# ArcLibre documentation

[STATUS.md](STATUS.md) summarises what works, what has been tested, and
what is missing. Each component's `RESULTS.md` says what was built, from
which sources, how it was tested, and its limits.

## The system

- [Status](STATUS.md)
- [RISC OS 3.11 gaps](system-audit/GAPS.md), [commands](system-audit/COMMANDS.md) and [system audit](system-audit/RESULTS.md)
- [Compatibility checklist](maintained-tree/COMPATIBILITY.md)
- [The maintained tree and frozen baseline](maintained-tree/RESULTS.md)
- [Desktop sources and roadmap](desktop-source/RESULTS.md), [roadmap](desktop-source/ROADMAP.md)
- [The 4 MB ROM](rom-4m/RESULTS.md)
- [ROM size](archimedes-desktop/SIZE.md)

## Components

| Area | Results |
|---|---|
| Desktop and appearance | [startup](desktop-startup/RESULTS.md), [appearance and !Palette](archimedes-desktop/RESULTS.md), [actions](desktop-actions/RESULTS.md), [menus](menu-messages/RESULTS.md) |
| Graphics and fonts | [renderers](renderers/RESULTS.md), [fonts](font-stack/RESULTS.md), [Wimp](wimp-stack/RESULTS.md), [SpriteUtils](spriteutils/RESULTS.md) |
| Tasks | [multitasking](multitask/RESULTS.md), [TaskWindow and FilterManager](task-services/RESULTS.md), [FPEmulator](fpemulator/RESULTS.md) |
| Applications | [Edit](desktop-apps/RESULTS.md), [Draw and Paint](graphics-apps/RESULTS.md), [editing workflows](graphics-apps/EDITING.md), [Calc](calc/RESULTS.md), [Configure](configure/RESULTS.md), [Chars, Help, Squash, Alarm](desktop-utilities/RESULTS.md) |
| Filing | [FileCore](filecore/RESULTS.md), [filing writes](filing-writes/RESULTS.md), [hard disc](hard-disc/RESULTS.md), [C runtime and FilerAct](desktop-c/RESULTS.md), [RAM filing](ram-filing/RESULTS.md), [streams](streams/RESULTS.md), [DOSFS](dosfs/RESULTS.md) |
| Sound | [sound](sound/RESULTS.md), [rate fix](sound/RATE_FIX.md) |
| Hardware | [expansion cards, serial, parallel](hardware/RESULTS.md), [A5000 family I/O](new-io/RESULTS.md), [IIC and clock](clock/RESULTS.md), [ARM3](arm3/RESULTS.md), [Debugger](debugger/RESULTS.md) |
| Network and printing | [Econet and NetFS](network/RESULTS.md), [printing](printing/RESULTS.md) |
| Utilities | [ScreenBlanker and StringLib](standard-utilities/RESULTS.md) |

## Releases and history

- [What a release contains](release/README.txt)
- [How the 3.60 sources were restored to the ARM2 machines](history/README.md),
  with the original feasibility audit
- [Licensing and provenance](../LICENSING.md)
