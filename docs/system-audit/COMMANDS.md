# Actual ArcLibre command-table inventory

Generated from final ROM bytes by `python3 tools/audit_system.py`. All module header titles match the build layout; every string and command record is bounded to its containing image. Kernel system commands are inventoried separately because their pseudo-module is not in ROMModules. This is registration evidence, not successful execution of every command. Configuration keywords and help callbacks are separate. Aliases, UKCommand services and disk programs are outside this inventory.

## UtilityModule

| Entry | Kind |
|---|---|
| `Break` | help-only |
| `Configure` | command |
| `Commands` | help-code-entry |
| `Echo` | command |
| `Error` | command |
| `Eval` | command |
| `FileCommands` | help-code-entry |
| `GOS` | command |
| `IF` | command |
| `Ignore` | command |
| `Modules` | command |
| `PowerOn` | help-only |
| `Reset` | help-only |
| `RMClear` | command |
| `RMEnsure` | command |
| `RMFaster` | command |
| `RMInsert` | command |
| `RMKill` | command |
| `RMLoad` | command |
| `RMReInit` | command |
| `RMRun` | command |
| `RMTidy` | command |
| `ROMModules` | command |
| `Set` | command |
| `SetEval` | command |
| `SetMacro` | command |
| `Show` | command |
| `Status` | command |
| `Syntax` | help-only |
| `Time` | command |
| `Unplug` | command |
| `Unset` | command |

## FileSwitch

| Entry | Kind |
|---|---|
| `Access` | command |
| `Cat` | command |
| `CDir` | command |
| `Copy` | command |
| `Count` | command |
| `Dir` | command |
| `EnumDir` | command |
| `Ex` | command |
| `FileInfo` | command |
| `Info` | command |
| `LCat` | command |
| `LEx` | command |
| `Lib` | command |
| `Rename` | command |
| `Run` | command |
| `SetType` | command |
| `Shut` | command |
| `ShutDown` | command |
| `Stamp` | command |
| `Up` | command |
| `Wipe` | command |
| `Back` | command |
| `URD` | command |
| `NoDir` | command |
| `NoURD` | command |
| `NoLib` | command |
| `FileSystem` | configuration |
| `Truncate` | configuration |

## ResourceFS

| Entry | Kind |
|---|---|
| `ResourceFS` | command |

## TerritoryManager

| Entry | Kind |
|---|---|
| `Territories` | command |
| `Territory` | configuration |
| `DST` | configuration |
| `NODST` | configuration |
| `TimeZone` | configuration |

## International

| Entry | Kind |
|---|---|
| `Alphabet` | command |
| `Country` | command |
| `Keyboard` | command |
| `Country` | configuration |
| `Alphabets` | command |
| `Countries` | command |

## Desktop

| Entry | Kind |
|---|---|
| `Desktop` | command |

## FileCore

| Entry | Kind |
|---|---|
| `Backup` | filing-command |
| `Bye` | filing-command |
| `CheckMap` | filing-command |
| `Compact` | filing-command |
| `Defect` | filing-command |
| `Dismount` | filing-command |
| `Drive` | filing-command |
| `Free` | filing-command |
| `Map` | filing-command |
| `Mount` | filing-command |
| `NameDisc` | filing-command |
| `NameDisk` | filing-command |
| `Verify` | filing-command |

## ADFS

| Entry | Kind |
|---|---|
| `ADFS` | command |
| `Format` | filing-command |
| `ADFSbuffers` | configuration |
| `ADFSDirCache` | configuration |
| `Drive` | configuration |
| `Floppies` | configuration |
| `HardDiscs` | configuration |
| `IDEDiscs` | configuration |
| `Step` | configuration |

## ColourTrans

| Entry | Kind |
|---|---|
| `ColourTransMapSize` | command |
| `ColourTransMap` | command |
| `ColourTransLoadings` | command |

## FontManager

| Entry | Kind |
|---|---|
| `FontList` | command |
| `FontCat` | command |
| `FontMax1` | configuration |
| `FontMax2` | configuration |
| `FontMax3` | configuration |
| `FontMax4` | configuration |
| `FontMax5` | configuration |
| `FontMax` | configuration |
| `LoadFontCache` | command |
| `SaveFontCache` | command |
| `FontInstall` | command |
| `FontLibrary` | command |
| `FontRemove` | command |

## WindowManager

| Entry | Kind |
|---|---|
| `IconSprites` | command |
| `Pointer` | command |
| `ToolSprites` | command |
| `WimpFlags` | configuration |
| `WimpMode` | command |
| `WimpPalette` | command |
| `WimpSlot` | command |
| `WimpTask` | command |
| `WimpWriteDir` | command |
| `WimpDragDelay` | configuration |
| `WimpFont` | configuration |
| `WimpDragMove` | configuration |
| `WimpDoubleClickDelay` | configuration |
| `WimpDoubleClickMove` | configuration |
| `WimpAutoMenuDelay` | configuration |
| `WimpMenuDragDelay` | configuration |
| `WimpKillSprite` | command |

## Filer

| Entry | Kind |
|---|---|
| `Filer_OpenDir` | command |
| `Filer_CloseDir` | command |
| `Filer_Run` | command |
| `Filer_Boot` | command |
| `Desktop_Filer` | command |

## TaskManager

| Entry | Kind |
|---|---|
| `Desktop_TaskManager` | command |
| `ChangeDynamicArea` | command |

## Pinboard

| Entry | Kind |
|---|---|
| `Desktop_Pinboard` | command |
| `AddTinyDir` | command |
| `RemoveTinyDir` | command |
| `Pinboard` | command |
| `Pin` | command |
| `BackDrop` | command |

## ADFSFiler

| Entry | Kind |
|---|---|
| `Desktop_ADFSFiler` | command |

## ShellCLI

| Entry | Kind |
|---|---|
| `ShellCLI` | command |

## Obey

| Entry | Kind |
|---|---|
| `Obey` | command |

## SoundDMA

| Entry | Kind |
|---|---|
| `Audio` | command |
| `Speaker` | command |
| `Stereo` | command |
| `SoundSystem` | configuration |

## SoundChannels

| Entry | Kind |
|---|---|
| `Volume` | command |
| `Voices` | command |
| `ChannelVoice` | command |
| `Sound` | command |
| `Tuning` | command |
| `SoundDefault` | configuration |

## SoundScheduler

| Entry | Kind |
|---|---|
| `Tempo` | command |
| `QSound` | command |

## SpriteUtils

| Entry | Kind |
|---|---|
| `SChoose` | command |
| `SGet` | command |
| `SFlipX` | command |
| `SFlipY` | command |
| `SDelete` | command |
| `SList` | command |
| `SLoad` | command |
| `SMerge` | command |
| `SNew` | command |
| `SSave` | command |
| `SInfo` | command |
| `SRename` | command |
| `SCopy` | command |
| `ScreenSave` | command |
| `ScreenLoad` | command |

## BASIC

| Entry | Kind |
|---|---|
| `BASIC` | command |

## ResourceFiler

| Entry | Kind |
|---|---|
| `Desktop_ResourceFiler` | command |

## ArcPalette

| Entry | Kind |
|---|---|
| `Desktop_ArcPalette` | command |

## Filer_Action

| Entry | Kind |
|---|---|
| `Filer_Action` | command |

## !Edit

| Entry | Kind |
|---|---|
| `Desktop_Edit` | command |

## !Draw

| Entry | Kind |
|---|---|
| `Desktop_Draw` | command |

## !Paint

| Entry | Kind |
|---|---|
| `Desktop_Paint` | command |

## Kernel system command table

| Entry | Kind |
|---|---|
| `Append` | command |
| `Build` | command |
| `Close` | command |
| `Create` | command |
| `Delete` | command |
| `Dump` | command |
| `Exec` | command |
| `FX` | command |
| `GO` | command |
| `Help` | command |
| `Key` | command |
| `Load` | command |
| `List` | command |
| `Opt` | command |
| `Print` | command |
| `Quit` | command |
| `Remove` | command |
| `Save` | command |
| `Shadow` | command |
| `Spool` | command |
| `SpoolOn` | command |
| `TV` | command |
| `Type` | command |
