#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Tiered development checks for the default ArcLibre ROM.

  check       build and statically verify the ROM, then run the gates for the
              paths that changed, each with one cold boot (--probe).
  check-full  every runtime gate with three cold boots and negative controls.

Neither replaces `make arclibre-test`: only that complete suite produces the
acceptance records required for a release. The release suite runs every
check-full gate with three cold boots, so a release batch needs only the suite.
Don't run check-full after it: its ROM build rebuilds the frozen baseline and
shared stacks, deleting acceptance records that packaging needs. Changed paths are uncommitted and
untracked files, plus commits since --since REF if given.
"""
import argparse,fnmatch,os,pathlib,subprocess,sys,time
REPO=pathlib.Path(__file__).resolve().parents[1]

# Gate name -> (command, paths whose changes select it). The desktop ROM gate
# is the smoke test and always runs.
GATES={
 'desktop-rom':(['tests/run_desktop_rom.py'],['src/Desktop/*','src/Filer/*','src/Switcher/*','src/Pinboard/*','src/ADFSFiler/*','src/ShellCLI/*','src/Obey/*','src/Buffers/*','src/SprExtend/*','src/ArcLibre/*']),
 'squash':(['tests/run_squash.py','build/arclibre'],['src/Squash/*','tools/build_squash.py','tools/link_squash.py']),
 'basic-utilities':(['tests/run_basic_utilities.py','build/arclibre'],['src/Chars/*','src/Help/*','src/Alarm/*','src/ArcCalc/*','src/ArcConfigure/*','tools/build_calc.py','tests/build_basic_utility_disc.py','tools/generate_alarm_code.py','tests/harness/Sources/BasicRunProbe/*','src/BASIC/*','tools/build_basic_utilities.py','tools/basic_squish.py','tools/build_alarm_disc.py','src/ArcLibre/alarm/*']),
 'standard-utilities':(['tests/run_standard_utilities.py'],['src/ScrBlank/*','src/StringLib/*','tools/build_standard_utilities.py']),
 'clock':(['tests/run_clock.py'],['src/IIC/*','src/RTCAdjust/*','tools/build_system_modules.py','tests/harness/Sources/ClockProbe/*']),
 'debugger':(['tests/run_debugger.py'],['src/Debugger/*','tests/harness/Sources/BasicRunProbe/*']),
 # Disc-loaded module, not in the ROM; the gate builds build/dosfs first.
 # Test-only profile until the modules fit in the delivered ROM.
 'network':(['tests/run_network.py'],['src/Econet/*','src/BBCEconet/*','src/NetFS/*','src/NetFiler/*','src/NetPrint/*','src/NetStatus/*','manifests/network-inputs.json','patches/network/*','tests/run_network.py','tests/harness/Sources/NetProbe/*']),
 'printing':(['tests/run_printing.py'],['src/PDriver/*','src/PDModules/*','src/PDumperSpt/*','src/PDumpers/*','src/PrinterManager/*','src/PrintDefs/*','src/MakePSFont/*','src/ArcLibre/printing/*','src/ArcLibre/hdr/SprExtend','src/Kernel/s/vdu/vdufontl1','manifests/printing-inputs.json','manifests/printing-headers.json','patches/printing/*','tools/build_printing_disc.py','tools/adfs_image.py','tests/run_printing.py','tests/epson_fixture.py','tests/pcl_fixture.py','tests/postscript_fixture.py','tests/sysfont_fixture.py','tests/fixtures/PrintTest.bas','tests/harness/Sources/PrintProbe/*','tests/harness/Sources/BasicRunProbe/*']),
 'netfs':(['tests/run_netfs.py'],['src/NetFS/*','src/NetFiler/*','src/NetStatus/*','src/Free/*','src/Econet/*','tests/run_netfs.py','tests/harness/Sources/NetFSProbe/*']),
 # The A5000 family's IOEB/82C711 probe and the drivers that use it.
 'new-io':(['tests/run_new_io.py'],['src/HdrSrc/hdr/Machine/*','src/Kernel/s/PMF/osinit','src/Kernel/s/Middle','src/ADFS/*','src/Serial/*','src/Parallel/*','tools/verify.py','tests/run_new_io.py','tests/harness/Sources/NewIOProbe/*']),
 'dosfs-formats':(['tests/run_dosfs_formats.py'],['src/DOSFS/*','src/ADFS/*','src/FileCore/*','tools/build_dosfs.py','tests/run_dosfs_formats.py','tests/fat12_fixture.py','tests/hfe_fixture.py','tests/harness/Sources/NewIOProbe/*']),
 # The 2 MB ROM's shipped floppy, rebuilt from the DOSFS, Alarm and printing discs first.
 'extras':(['tests/run_extras.py','--build'],['src/ArcLibre/extras/*','src/ArcLibre/system/*','tools/system_apps.py','tools/build_extras_disc.py','tools/adfs_image.py','manifests/release.json','tests/run_extras.py','tests/harness/Sources/PrintProbe/*']),
 'hardware':(['tests/run_hardware.py'],['src/Podule/*','src/Serial/*','src/SerialSpt/*','src/Parallel/*','manifests/hardware-inputs.json','manifests/hardware-headers.json','patches/hardware/*','tests/run_hardware.py','tests/harness/Sources/HardwareProbe/*']),
 'arm3':(['tests/run_arm3.py'],['src/ARM3Support/*','manifests/arm3-inputs.json','tools/inspect_image.py','tests/run_arm3.py','tests/harness/Sources/ARM3Probe/*']),
 # The delivered FileCore (ArcLibreDelivered) and its *Format / DiscOp writes.
 'format':(['tests/run_format.py'],['src/FileCore/*','tools/build.py','tests/run_format.py','tests/adfs_newmap.py','tests/harness/Sources/FormatProbe/*','patches/restoration/*']),
 'dosfs':(['tests/run_dosfs.py'],['src/DOSFS/*','src/ArcLibre/s/DOSFS*','src/ArcLibre/h/DOSFShdr','src/ArcLibre/dosfs/*','tools/build_dosfs.py','tools/check_dosfs_boot.py','tools/import_dosfs.py',
  'manifests/dosfs-inputs.json','patches/dosfs/*','tests/run_dosfs.py','tests/fat12_fixture.py','tests/hfe_fixture.py','tests/harness/Sources/DOSFSProbe/*']),
 'ram-filing':(['tests/run_ram_filing.py'],['src/RamFS/*','src/RAMFSFiler/*','src/Free/*','tools/build_ram_filing.py']),
 'streams':(['tests/run_streams.py'],['src/DeviceFS/*','src/SystemDevs/*','src/PipeFS/*','tools/build_streams.py']),
 'task-services':(['tests/run_task_services.py'],['src/TaskWindow/*','src/Filter/*','tools/build_task_services.py']),
 'menus':(['tests/run_menus.py'],['src/Wimp/s/Menu*','tests/build_menu_app.py']),
 'sprite-commands':(['tests/run_sprite_commands.py'],['src/SpriteUtil/*','src/SprExtend/*']),
 'palette':(['tests/run_palette.py'],['src/ArcPalette/*','src/Colours/*','src/Wimp/s/!Palette','tools/build_palette.py','tests/harness/Sources/PaletteProbe/*']),
 'sound':(['tests/run_sound.py'],['src/Sound0/*','src/Sound1/*','src/Sound2/*','src/WaveSynth/*','src/Percussion/*','tools/build_sound.py']),
 'desktop-actions':(['tests/run_desktop_actions.py'],['src/DragASprit/*','src/Pinboard/*','tools/build_desktop_actions.py']),
 'filer-actions':(['tests/run_filer_actions.py'],['src/FilerAct/*','src/FilerSWIs/*','src/RISC_OSLib/*','tools/build_c_desktop.py','tools/link_c_desktop.py']),
 'desktop-apps':(['tests/run_desktop_apps.py'],['src/EditApp/*','src/RISC_OSLib/*','tools/build_desktop_apps.py','tools/link_desktop_apps.py']),
 'graphics-apps':(['tests/run_graphics_apps.py'],['src/Draw/*','src/Paint/*','src/DrawMod/*','tools/build_graphics_apps.py','tools/link_graphics_apps.py']),
 'app-workflows':(['tests/run_app_workflows.py'],['src/Draw/*','src/Paint/*','src/EditApp/*','src/FontManager/*','src/ROMFonts/*']),
}
# Shared foundations: any change here selects every gate.
HIGH_RISK=['src/Kernel/*','src/Wimp/*','src/FileSwitch/*','src/FileCore/*','src/ADFS/*','src/ResourceFS/*','src/MsgTrans/*','src/Messages/*',
 'src/HdrSrc/*','src/PublicInterfaces/*','src/SharedHeaders/*','src/FPEmulator/*','src/FPASC/*','src/TerritoryManager/*','src/UK/*','src/Inter/*','src/IntKey/*',
 'tools/build_arclibre_rom.py','tools/build_desktop.py','tools/build_startup.py','tools/module_image.py','tools/inspect_image.py','tools/archimedes_resources.py',
 'manifests/header-exports.json','manifests/desktop-header-exports.json','manifests/desktop-startup-headers.json','third_party/*',
 'tests/harness/Package.swift','tests/harness/Sources/DesktopLaunchProbe/*','tests/harness/Sources/DesktopROMProbe/*','tests/gate_mode.py','tools/verify_desktop_rom_trace.py']

def changed(since):
 def git(*a):return subprocess.run(['git',*a],cwd=REPO,capture_output=True,text=True,check=True).stdout.split('\n')
 paths=set(git('diff','--name-only','HEAD'))|set(git('ls-files','--others','--exclude-standard'))
 if since:paths|=set(git('diff','--name-only',since,'HEAD'))
 return sorted(p for p in paths if p)

def matches(path,patterns):return any(fnmatch.fnmatch(path,p) for p in patterns)

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('tier',choices=['check','check-full'])
 ap.add_argument('--since',help='also include paths changed since this commit')
 ap.add_argument('--gate',action='append',default=[],help='run this gate as well (repeatable)')
 ap.add_argument('--no-build',action='store_true',help='use the existing build/arclibre ROM')
 a=ap.parse_args()
 paths=changed(a.since)
 claimed=[pat for _,pats in GATES.values() for pat in pats]
 # A source change no gate claims has unknown reach, so it is treated as high risk.
 risky=[p for p in paths if matches(p,HIGH_RISK) or (p.startswith('src/') and not matches(p,claimed))]
 if a.tier=='check-full' or risky:selected=list(GATES)
 else:selected=[g for g,(_,pats) in GATES.items() if g=='desktop-rom' or g in a.gate or any(matches(p,pats) for p in paths)]
 print(f'{len(paths)} changed paths; high risk: {", ".join(risky[:6]) or "none"}{" ..." if len(risky)>6 else ""}')
 print('gates:',', '.join(selected),flush=True)
 timings=[];env=dict(os.environ,ARCLIBRE_INSTALL_ROM='0')
 def step(name,cmd):
  t=time.monotonic();print(f'== {name}',flush=True)
  r=subprocess.run(cmd,cwd=REPO,env=env);timings.append((name,time.monotonic()-t,r.returncode))
  if r.returncode:summary();sys.exit(f'{name} failed')
 def summary():
  for name,secs,rc in timings:print(f'  {name:22} {secs/60:5.1f} min  {"PASS" if rc==0 else "FAIL"}')
 if not a.no_build:step('build and static checks',['make','arclibre-rom'])
 step('basic squish check',[sys.executable,'tests/check_basic_squish.py','Chars/bas/!RunImage,ffb','Help/bas/!RunImage,ffb','Alarm/bas/!RunImage,ffb'])
 for g in selected:
  cmd,_=GATES[g];step(g,[sys.executable,*cmd]+(['--probe'] if a.tier=='check' else []))
  if a.tier=='check-full' and g=='streams':step('stream sleep negative',[sys.executable,'tests/check_stream_sleep_negative.py'])
 summary()
 if risky and a.tier=='check':print('High-risk paths changed: run `make check-full`, or the release suite (which covers it), before relying on this result.')
 print(f'{a.tier} PASS (not release evidence: run `make arclibre-test` before recording a release)')

if __name__=='__main__':main()
