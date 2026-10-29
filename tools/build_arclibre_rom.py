#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Join the verified desktop stack without changing the pinned kernel or baseline."""
import fcntl,hashlib,json,os,shutil,struct,subprocess,sys
from paths import REPO,HOST
from module_image import load_aof
# Profiles share intermediate C linker outputs. Serialize joins so parallel
# regression negative controls cannot replace another profile's link evidence.
link_lock=(REPO/'build/arclibre-link.lock').open('a')
fcntl.flock(link_lock.fileno(),fcntl.LOCK_EX)
with_graphics='--with-graphics' in sys.argv or not any(v in sys.argv for v in ['--without-graphics','--with-apps','--without-apps','--with-hard-disc','--with-c-desktop','--without-c-desktop','--with-sound'])
with_tasks='--without-task-services' not in sys.argv and (with_graphics or '--with-task-services' in sys.argv)
with_streams='--without-streams' not in sys.argv and (with_graphics or '--with-streams' in sys.argv)
with_ram='--without-ram-filing' not in sys.argv and (with_graphics or '--with-ram-filing' in sys.argv)
with_utilities='--without-standard-utilities' not in sys.argv and (with_graphics or '--with-standard-utilities' in sys.argv)
# Original IIC_Control provider and the IOC timer calibration that uses it.
with_clock='--without-clock' not in sys.argv and with_graphics
with_debugger='--without-debugger' not in sys.argv and with_graphics
# The original networking modules (Econet, BBCEconet, NetFS, NetFiler,
# NetPrint, NetStatus), in ROM as in RISC OS 3.11; Alarm moved to disc to
# make room. Their profile without them is the networking negative control.
with_network='--without-network' not in sys.argv and with_graphics
with_graphics_apps=with_graphics
# The original Podule manager and serial and parallel device drivers, in ROM
# as in RISC OS 3.11. Their profile without them is the hardware negative
# control; the drivers are DeviceFS devices, so they also leave with streams.
with_hardware='--without-hardware' not in sys.argv and with_graphics
# The 4 MB ROM: everything the 2 MB ROM ships on discs is in ROM as well,
# !Alarm (as in RISC OS 3.11) and printing (!Printers in ResourceFS with its
# dot-matrix, LaserJet and PostScript classes, and PDriver, PDriverDP,
# PDriverPS, PDumperSupport, PDumperDM and PDumperLJ). It is never installed.
four_meg='--four-meg' in sys.argv
ROM_SIZE=4194304 if four_meg else 2097152
BASIC_UTILITIES=REPO/('build/basic-utilities-alarm' if four_meg else 'build/basic-utilities')
# The new ArcLibre ARM3Support (cache control; dormant on an ARM2).
with_arm3='--without-arm3' not in sys.argv and with_graphics
base=REPO/'build/desktop-baseline';out=REPO/('build/arclibre-ram-filing' if '--with-ram-filing' in sys.argv else 'build/arclibre-without-ram-filing' if '--without-ram-filing' in sys.argv else 'build/arclibre-streams' if '--with-streams' in sys.argv else 'build/arclibre-without-streams' if '--without-streams' in sys.argv else 'build/arclibre-tasks' if '--with-task-services' in sys.argv else 'build/arclibre-without-tasks' if '--without-task-services' in sys.argv else 'build/arclibre-graphics' if '--with-graphics' in sys.argv else 'build/arclibre-without-graphics' if '--without-graphics' in sys.argv else 'build/arclibre-without-apps' if '--without-apps' in sys.argv else 'build/arclibre-apps' if '--with-apps' in sys.argv else 'build/arclibre-hard-disc' if '--with-hard-disc' in sys.argv else 'build/arclibre-without-c-desktop' if '--without-c-desktop' in sys.argv else 'build/arclibre-c-desktop' if '--with-c-desktop' in sys.argv else 'build/arclibre-without-actions' if '--without-actions' in sys.argv else 'build/arclibre-without-sound' if '--without-sound' in sys.argv else 'build/arclibre-sound' if '--with-sound' in sys.argv else 'build/arclibre-without-spriteextend' if '--without-spriteextend' in sys.argv else 'build/arclibre');out.mkdir(exist_ok=True)
with_c='--without-c-desktop' not in sys.argv
with_basic_utilities='--with-basic-utilities' in sys.argv or (with_graphics and not any(v in sys.argv for v in ['--without-basic-utilities','--with-squash']))
with_squash='--without-squash' not in sys.argv and (with_graphics or '--with-squash' in sys.argv)
if '--with-squash' in sys.argv or '--without-squash' in sys.argv:
 out=REPO/('build/arclibre-squash' if '--with-squash' in sys.argv else 'build/arclibre-without-squash');out.mkdir(exist_ok=True)
if '--with-standard-utilities' in sys.argv:
 out=REPO/'build/arclibre-utilities';out.mkdir(exist_ok=True)
elif '--without-standard-utilities' in sys.argv:
 out=REPO/'build/arclibre-without-utilities';out.mkdir(exist_ok=True)
if '--without-clock' in sys.argv:
 out=REPO/'build/arclibre-without-clock';out.mkdir(exist_ok=True)
if '--without-debugger' in sys.argv:
 out=REPO/'build/arclibre-without-debugger';out.mkdir(exist_ok=True)
if '--without-arm3' in sys.argv:
 out=REPO/'build/arclibre-without-arm3';out.mkdir(exist_ok=True)
if '--without-network' in sys.argv:
 out=REPO/'build/arclibre-without-network';out.mkdir(exist_ok=True)
if '--without-hardware' in sys.argv:
 out=REPO/'build/arclibre-without-hardware';out.mkdir(exist_ok=True)
if four_meg:
 out=REPO/'build/arclibre-4m';out.mkdir(exist_ok=True)
# Negative control for the delivered FileCore: the frozen baseline FileCore.
if '--baseline-filecore' in sys.argv:
 out=REPO/'build/arclibre-baseline-filecore';out.mkdir(exist_ok=True)
# The new ArcLibre !Calc is built with the ROM's BASIC, so it joins only with
# the BASIC utilities (whose profile without them tokenises it).
with_calc='--without-calc' not in sys.argv
if not with_calc:
 out=REPO/'build/arclibre-without-calc';out.mkdir(exist_ok=True)
# The new ArcLibre !Configure is built the same way as !Calc.
with_configure='--without-configure' not in sys.argv
if not with_configure:
 out=REPO/'build/arclibre-without-configure';out.mkdir(exist_ok=True)
if '--with-basic-utilities' in sys.argv or '--without-basic-utilities' in sys.argv:
 out=REPO/('build/arclibre-basic-utilities' if '--with-basic-utilities' in sys.argv else 'build/arclibre-without-basic-utilities');out.mkdir(exist_ok=True)
with_apps='--with-apps' in sys.argv or not any(v in sys.argv for v in ['--without-apps','--with-hard-disc','--with-c-desktop','--without-c-desktop','--with-sound'])
assert not with_apps or with_c
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
expected=json.loads((REPO/'manifests/baseline-rom.json').read_text());kernel=(base/'artifacts/kernel.bin').read_bytes()
assert sha(kernel)==expected['kernel_sha256'];assert sha((base/'artifacts/floppy.rom').read_bytes())==expected['rom_sha256']
kernel_unchanged=True
if with_apps:
 kernel=(REPO/'build/desktop-defaults/artifacts/kernel.bin').read_bytes()
 proof=json.loads((REPO/'build/desktop-defaults/artifacts/build-result.json').read_text())
 assert proof['status']=='PASS'
 kernel_unchanged=False
# Extend the real Messages resource container; its executable prefix is unchanged.
work=out/'Messages'
if work.exists():shutil.rmtree(work)
shutil.copytree(REPO/'src/Messages',work)
resources=(base/'build/resources.bin').read_bytes()+(REPO/'build/desktop-startup/resources.bin').read_bytes()[:-4]
if '--without-sound' not in sys.argv:resources+=(REPO/'build/sound/resources.bin').read_bytes()[:-4]
if with_c:resources+=(REPO/'build/desktop-c-runtime/resources.bin').read_bytes()[:-4]
if with_apps:resources+=(REPO/'build/desktop-apps/resources.bin').read_bytes()[:-4]
if with_graphics_apps:resources+=(REPO/'build/graphics-apps/resources.bin').read_bytes()[:-4]
if with_network:
 network_proof=json.loads((REPO/'build/network/result.json').read_text());assert network_proof['status']=='PASS'
 resources+=(REPO/'build/network/resources.bin').read_bytes()[:-4]
if with_hardware:
 hardware_proof=json.loads((REPO/'build/hardware/result.json').read_text());assert hardware_proof['status']=='PASS'
 resources+=(REPO/'build/hardware/resources.bin').read_bytes()[:-4]
if '--without-actions' not in sys.argv:resources+=(REPO/'build/desktop-actions/resources.bin').read_bytes()[:-4]
if with_tasks:
 task_proof=json.loads((REPO/'build/task-services/result.json').read_text())
 assert task_proof['status']=='PASS'
 task_resources=(REPO/'build/task-services/resources.bin').read_bytes()
 assert sha(task_resources)==task_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/task-services-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=task_resources[:-4]
if with_streams:
 stream_proof=json.loads((REPO/'build/streams/result.json').read_text())
 assert stream_proof['status']=='PASS'
 stream_resources=(REPO/'build/streams/resources.bin').read_bytes()
 assert sha(stream_resources)==stream_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/stream-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=stream_resources[:-4]
if with_ram:
 ram_proof=json.loads((REPO/'build/ram-filing/result.json').read_text())
 assert ram_proof['status']=='PASS'
 ram_resources=(REPO/'build/ram-filing/resources.bin').read_bytes()
 assert sha(ram_resources)==ram_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/ram-filing-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=ram_resources[:-4]
if with_utilities:
 utility_proof=json.loads((REPO/'build/standard-utilities/result.json').read_text())
 assert utility_proof['status']=='PASS'
 utility_resources=(REPO/'build/standard-utilities/resources.bin').read_bytes()
 assert sha(utility_resources)==utility_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/standard-utility-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=utility_resources[:-4]
if with_clock:
 clock_proof=json.loads((REPO/'build/clock-services/result.json').read_text())
 assert clock_proof['status']=='PASS'
 clock_resources=(REPO/'build/clock-services/resources.bin').read_bytes()
 assert sha(clock_resources)==clock_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/clock-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=clock_resources[:-4]
if with_debugger:
 debugger_proof=json.loads((REPO/'build/debugger/result.json').read_text())
 assert debugger_proof['status']=='PASS'
 debugger_resources=(REPO/'build/debugger/resources.bin').read_bytes()
 assert sha(debugger_resources)==debugger_proof['resources_sha256']
 for row in json.loads((REPO/'manifests/debugger-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 resources+=debugger_resources[:-4]
if with_basic_utilities:
 # Original Messages Makefile appends HelpTokens to the application's file.
 # Replace the earlier tokens-only record with that complete file, once.
 p=0;kept=bytearray();removed=0
 while p<len(resources):
  length=struct.unpack_from('<I',resources,p)[0];assert length>0
  rec=resources[p:p+length];end=rec.index(0,20);name=rec[20:end].decode()
  if name=='Resources.Help.Messages':
   dataoff=((end+4)&~3)+4;size=struct.unpack_from('<I',rec,12)[0]
   assert rec[dataoff:dataoff+size]==(REPO/'src/Messages/Data/HelpTokens').read_bytes();removed+=1
  else:kept+=rec
  p+=length
 assert removed==1;resources=bytes(kept)
 resources+=(BASIC_UTILITIES/'resources.bin').read_bytes()[:-4]
if with_squash:
 resources+=(REPO/'build/squash-runtime/resources.bin').read_bytes()[:-4]
if four_meg:
 printing_disc=json.loads((REPO/'build/printing-disc/disc.json').read_text());assert printing_disc['status']=='PASS'
 printing_resources=(REPO/'build/printing-disc/rom-resources.bin').read_bytes();assert sha(printing_resources)==printing_disc['rom_resources_sha256']
 resources+=printing_resources[:-4]
if with_apps:
 from archimedes_resources import filter_resources
 resources,selection=filter_resources(resources)
 save(out/'desktop-resource-selection.json',selection)
(work/'ResourcesData').write_bytes(resources)
env=dict(os.environ,HDR_PATH=str(base/'build/Hdr'),MACHINE='A440',LOCALE='UK',IMAGESIZE='2048K')
objects=[]
for n in [1,2]:
 with (out/f'messages-{n}.log').open('w') as f:subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','s/Messages',str(out/f'messages-{n}.aof')],cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 objects.append((out/f'messages-{n}.aof').read_bytes())
assert objects[0]==objects[1];obj=load_aof(out/'messages-1.aof');messages=obj['data'];(out/'messages.bin').write_bytes(messages)
resource_offset=json.loads((base/'artifacts/modules/Messages/symbols.json').read_text())['Messages']['value'];old=(base/'artifacts/modules/Messages/module.bin').read_bytes()
assert messages[:resource_offset]==old[:resource_offset]
modules={r['component']:(base/'artifacts/modules'/r['component']/'module.bin').read_bytes() for r in expected['modules']};modules['Messages']=messages
if with_apps or '--with-hard-disc' in sys.argv:modules['ADFS']=(REPO/'build/hard-disc/artifacts/modules/ADFS/module.bin').read_bytes()
# The delivered FileCore (ArcLibreDelivered: no FSLock in RISC OS 3.11) comes
# from the same desktop-defaults build as the delivered kernel.
if with_apps and '--baseline-filecore' not in sys.argv:
 modules['FileCore']=(REPO/'build/desktop-defaults/artifacts/modules/FileCore/module.bin').read_bytes()
 shutil.copytree(REPO/'build/desktop-defaults/artifacts/modules/FileCore',out/'delivered/modules/FileCore',dirs_exist_ok=True)
for c in ['FPEmulator','Colours','DrawMod','Super','Hourglass','FontManager','ROMFonts','Wimp']:modules[c]=(REPO/'build/wimp-stack/modules'/c/'module.bin').read_bytes()
for c in ['Desktop','Filer','Switcher','Pinboard','SprExtend','ADFSFiler','ShellCLI','Obey','Buffers']:modules[c]=(REPO/'build/desktop-startup/modules'/c/'module.bin').read_bytes()
# UtilityModule is the kernel's list entry 0. Configured language 10 selects
# loaded module 9, hence Desktop follows the first eight baseline providers.
order=['FileSwitch','ResourceFS','MsgTrans','Messages','TerritoryManager','UK','Inter','IntKey','Desktop','FileCore','ADFS','FPEmulator','Colours','DrawMod','Super','Hourglass','FontManager','ROMFonts','SprExtend','Wimp','Filer','Switcher','Pinboard','ADFSFiler','ShellCLI','Obey','Buffers']
# TaskManager must own workspace before Filer emits Service_StartFiler.
# It retains Filer's task handle for real RAMFSFiler resize/restart service calls.
order.remove('Switcher');order.insert(order.index('Filer'),'Switcher')
if with_hardware:
 for row in json.loads((REPO/'manifests/hardware-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 for report in hardware_proof['modules']:
  c=report['component']
  if c!='Podule' and not with_streams:continue
  modules[c]=(REPO/'build/hardware/modules'/c/'module.bin').read_bytes();assert sha(modules[c])==report['sha256']
 # 3.11 starts the Podule manager first; here it follows Desktop, which must
 # stay ninth (see above), and precedes every expansion card client.
 order.insert(order.index('Desktop')+1,'Podule')
 shutil.copytree(REPO/'build/hardware/modules',out/'hardware-runtime/modules',dirs_exist_ok=True)
if with_basic_utilities:
 for c in ['Chars','Help']+(['Alarm'] if four_meg else []):
  modules[c]=(BASIC_UTILITIES/'modules'/c/'module.bin').read_bytes();order.append(c)
 if with_calc:
  calc_proof=json.loads((REPO/'build/calc-module/result.json').read_text());assert calc_proof['status']=='PASS'
  assert json.loads((REPO/'build/calc/result.json').read_text())['status']=='PASS'
  for row in json.loads((REPO/'manifests/calc-inputs.json').read_text()):
   assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
  modules['ArcCalc']=(REPO/'build/calc-module/modules/ArcCalc/module.bin').read_bytes()
  assert sha(modules['ArcCalc'])==calc_proof['modules'][0]['sha256']
  order.append('ArcCalc')
  shutil.copytree(REPO/'build/calc-module/modules',out/'calc-runtime/modules',dirs_exist_ok=True)
 if with_configure:
  configure_proof=json.loads((REPO/'build/configure-module/result.json').read_text());assert configure_proof['status']=='PASS'
  assert json.loads((REPO/'build/configure/result.json').read_text())['status']=='PASS'
  for row in json.loads((REPO/'manifests/configure-inputs.json').read_text()):
   assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
  modules['ArcConfigure']=(REPO/'build/configure-module/modules/ArcConfigure/module.bin').read_bytes()
  assert sha(modules['ArcConfigure'])==configure_proof['modules'][0]['sha256']
  order.append('ArcConfigure')
  shutil.copytree(REPO/'build/configure-module/modules',out/'configure-runtime/modules',dirs_exist_ok=True)
 shutil.copytree(BASIC_UTILITIES/'modules',out/'basic-utility-runtime/modules',dirs_exist_ok=True)
if '--without-spriteextend' in sys.argv:order.remove('SprExtend')
if '--without-sound' not in sys.argv:
 for c in ['Sound0','Sound1','Sound2','WaveSynth','Percussion']:
  modules[c]=(REPO/'build/sound/modules'/c/'module.bin').read_bytes();order.append(c)
if '--without-actions' not in sys.argv:
 for c in ['DragASprit','SpriteUtil']:
  modules[c]=(REPO/'build/desktop-actions/modules'/c/'module.bin').read_bytes();order.append(c)
if with_c:
 modules['FilerSWIs']=(REPO/'build/desktop-actions/modules/FilerSWIs/module.bin').read_bytes();order.append('FilerSWIs')
if with_apps:
 for c in ['BASIC','BASICTrans','ResFiler']:
  modules[c]=(REPO/'build/desktop-apps/artifacts/modules'/c/'module.bin').read_bytes();order.append(c)
if with_apps:
 modules['ArcPalette']=(REPO/'build/palette/modules/ArcPalette/module.bin').read_bytes();order.append('ArcPalette')
 shutil.copytree(REPO/'build/palette/modules',out/'palette-runtime/modules',dirs_exist_ok=True)
if with_tasks:
 for c in ['Filter','TaskWindow']:
  modules[c]=(REPO/'build/task-services/modules'/c/'module.bin').read_bytes()
  assert sha(modules[c])==next(r['sha256'] for r in task_proof['modules'] if r['component']==c)
  order.append(c)
 shutil.copytree(REPO/'build/task-services/modules',out/'task-runtime/modules',dirs_exist_ok=True)
if with_streams:
 for c in ['DeviceFS','SystemDevs','PipeFS']:
  modules[c]=(REPO/'build/streams/modules'/c/'module.bin').read_bytes()
  assert sha(modules[c])==next(r['sha256'] for r in stream_proof['modules'] if r['component']==c)
  order.append(c)
 shutil.copytree(REPO/'build/streams/modules',out/'stream-runtime/modules',dirs_exist_ok=True)
 # The DeviceFS printer and serial devices, after DeviceFS as in 3.11.
 if with_hardware:order+=['Parallel','Serial','SerialSpt']
if with_ram:
 for c in ['RamFS','RAMFSFiler','Free']:
  modules[c]=(REPO/'build/ram-filing/modules'/c/'module.bin').read_bytes()
  assert sha(modules[c])==next(r['sha256'] for r in ram_proof['modules'] if r['component']==c)
  order.append(c)
 shutil.copytree(REPO/'build/ram-filing/modules',out/'ram-filing-runtime/modules',dirs_exist_ok=True)
if with_utilities:
 for c in ['ScrBlank','StringLib']:
  modules[c]=(REPO/'build/standard-utilities/modules'/c/'module.bin').read_bytes()
  assert sha(modules[c])==next(r['sha256'] for r in utility_proof['modules'] if r['component']==c)
  order.append(c)
 shutil.copytree(REPO/'build/standard-utilities/modules',out/'utility-runtime/modules',dirs_exist_ok=True)
if with_clock:
 for c in ['IIC','RTCAdjust']:
  modules[c]=(REPO/'build/clock-services/modules'/c/'module.bin').read_bytes()
  assert sha(modules[c])==next(r['sha256'] for r in clock_proof['modules'] if r['component']==c)
  order.append(c)
 shutil.copytree(REPO/'build/clock-services/modules',out/'clock-runtime/modules',dirs_exist_ok=True)
if with_debugger:
 modules['Debugger']=(REPO/'build/debugger/modules/Debugger/module.bin').read_bytes()
 assert sha(modules['Debugger'])==debugger_proof['modules'][0]['sha256']
 order.append('Debugger')
 shutil.copytree(REPO/'build/debugger/modules',out/'debugger-runtime/modules',dirs_exist_ok=True)
if with_network:
 for row in json.loads((REPO/'manifests/network-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 for report in network_proof['modules']:
  c=report['component'];modules[c]=(REPO/'build/network/modules'/c/'module.bin').read_bytes();assert sha(modules[c])==report['sha256'];order.append(c)
 shutil.copytree(REPO/'build/network/modules',out/'network-runtime/modules',dirs_exist_ok=True)
if four_meg:
 printing_proof=json.loads((REPO/'build/printing/result.json').read_text());assert printing_proof['status']=='PASS'
 for row in json.loads((REPO/'manifests/printing-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 for report in printing_proof['modules']:
  c=report['component']
  if c=='PrinterManager':continue                 # SetPrint is a file of !Printers, not a module
  modules[c]=(REPO/'build/printing/modules'/c/'module.bin').read_bytes();assert sha(modules[c])==report['sha256'];order.append(c)
 shutil.copytree(REPO/'build/printing/modules',out/'printing-runtime/modules',dirs_exist_ok=True)
if with_arm3:
 arm3_proof=json.loads((REPO/'build/arm3/result.json').read_text());assert arm3_proof['status']=='PASS'
 for row in json.loads((REPO/'manifests/arm3-inputs.json').read_text()):
  assert sha((REPO/'src'/row['component']/row['path']).read_bytes())==row['sha256']
 modules['ARM3Support']=(REPO/'build/arm3/modules/ARM3Support/module.bin').read_bytes()
 assert sha(modules['ARM3Support'])==arm3_proof['modules'][0]['sha256']
 order.append('ARM3Support')
 shutil.copytree(REPO/'build/arm3/modules',out/'arm3-runtime/modules',dirs_exist_ok=True)
rom=bytearray(kernel[:-4]);layout=[]
for c in order:
 b=modules[c];assert len(b)%4==0;offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode();address=0x3800000+len(rom)+4
 layout.append(dict(component=c,title=title,base=address,length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
if with_c:
 from link_c_desktop import link
 linked=link(0x3800000+len(rom)+4)
 from verify_c_desktop import verify
 verify()
 # Preserve link-specific evidence beside each ROM. Negative controls relink
 # at different bases and must not overwrite another ROM's audit inventory.
 evidence=out/'c-runtime';evidence.mkdir(exist_ok=True)
 for name in ['verification.json','workspace-contract.json','linked.json','link.log','filer-link.log','SharedCLib.symbols','FilerAct.symbols','resources.json','unchecked-stack-prologues.json']:
  shutil.copy2(REPO/'build/desktop-c-runtime'/name,evidence/name)
 shutil.copytree(REPO/'build/desktop-c-runtime/modules',evidence/'modules',dirs_exist_ok=True)
 for row in linked['modules']:
  c=row['component'];b=(REPO/'build/desktop-c-runtime'/(c+'.bin')).read_bytes();assert row['base']==0x3800000+len(rom)+4 and len(b)%4==0
  offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode()
  layout.append(dict(component=c,title=title,base=row['base'],length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
if with_apps:
 from link_desktop_apps import link as link_apps
 row=link_apps(0x3800000+len(rom)+4);b=(REPO/'build/desktop-apps/Edit.bin').read_bytes()
 offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode()
 layout.append(dict(component='Edit',title=title,base=row['base'],length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
 evidence=out/'app-runtime';evidence.mkdir(exist_ok=True)
 for name in ['verification.json','linked.json','edit-link.log','Edit.symbols','resources.json']:shutil.copy2(REPO/'build/desktop-apps'/name,evidence/name)
 shutil.copytree(REPO/'build/desktop-apps/modules',evidence/'modules',dirs_exist_ok=True)
if with_graphics_apps:
 from link_graphics_apps import link as link_graphics
 for row in link_graphics(0x3800000+len(rom)+4):
  c=row['component'];b=(REPO/'build/graphics-apps'/(c+'.bin')).read_bytes();assert row['base']==0x3800000+len(rom)+4 and len(b)%4==0
  offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode()
  layout.append(dict(component=c,title=title,base=row['base'],length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
 evidence=out/'graphics-runtime';evidence.mkdir(exist_ok=True)
 for name in ['verification.json','linked.json','Draw-link.log','Paint-link.log','Draw.symbols','Paint.symbols','resources.json']:shutil.copy2(REPO/'build/graphics-apps'/name,evidence/name)
 shutil.copytree(REPO/'build/graphics-apps/modules',evidence/'modules',dirs_exist_ok=True)
if with_apps or '--with-hard-disc' in sys.argv:
 shutil.copytree(REPO/'build/hard-disc/artifacts/modules/ADFS',out/'hardware/modules/ADFS',dirs_exist_ok=True)
if with_apps:
 for c in ['ResFiler','BASIC','BASICTrans']:
  shutil.copytree(REPO/'build/desktop-apps/artifacts/modules'/c,out/'app-runtime/modules'/c,dirs_exist_ok=True)
if with_squash:
 from link_squash import link as link_squash
 row=link_squash(0x3800000+len(rom)+4);b=(REPO/'build/squash-runtime/Squash.bin').read_bytes()
 layout.append(dict(component='Squash',title='Squash',base=row['base'],length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
 evidence=out/'squash-runtime';evidence.mkdir(exist_ok=True)
 for name in ['linked.json','verification.json','workspace-contract.json','Squash-link.log','Squash.symbols']:shutil.copy2(REPO/'build/squash-runtime'/name,evidence/name)
 shutil.copytree(REPO/'build/squash-runtime/modules',evidence/'modules',dirs_exist_ok=True)
if four_meg:
 # DOSFS in its original ROM form (see src/ArcLibre/s/DOSFSHdr): linked here,
 # at its ROM address, with the ROM C stubs and the absolute addresses of the
 # shared library this ROM was just linked with.
 import re
 from aof import read as read_aof
 dosfs_link=json.loads((REPO/'build/dosfs/rom-link.json').read_text());objs=[REPO/p for p in dosfs_link['objects']]
 lib={n:int(v,16) for v,n in re.findall(r'\b([0-9a-f]{7,8})\s+(\S+)',(REPO/'build/desktop-c-runtime/SharedCLib.symbols').read_text())}
 defined={x['name'] for o in objs for x in read_aof(o)['symbols'] if x['attributes']&1}
 wanted={x['name'] for o in objs for x in read_aof(o)['symbols'] if not x['attributes']&1}-defined
 bound={n:lib[n] for n in wanted if n in lib and not n.startswith('Image$$') and not n.endswith(('$$Base','$$Limit'))}
 d=out/'dosfs-rom';d.mkdir(exist_ok=True)
 (d/'library-exports.s').write_text('\n'.join('        EXPORT |'+n+'|\n|'+n+'| EQU &'+format(v,'X') for n,v in sorted(bound.items()))+'\n        END\n')
 subprocess.run([str(HOST/'bin/asasm'),'-Uppercase','-aof',str(d/'library-exports.s'),str(d/'library-exports.o')],check=True,stdout=subprocess.DEVNULL)
 dbase=0x3800000+len(rom)+4
 with (d/'link.log').open('w') as f:subprocess.run([str(REPO/'build/c-toolchain-release/install/bin/drlink'),'-bin','-base',hex(dbase),'-map','-symbols',str(d/'DOSFS.symbols'),'-output',str(d/'DOSFS.bin'),*map(str,objs),str(d/'library-exports.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
 b=(d/'DOSFS.bin').read_bytes();b+=bytes(-len(b)%4)
 offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode();assert title=='DOSFS',title
 assert '__RelocCode' not in (d/'DOSFS.symbols').read_text(),'no self-relocation in ROM'
 # Code words from the objects' mapping symbols, located by the link map, as
 # tools/build_dosfs.py does for the disc module; each decoded independently.
 import inspect_image,pathlib
 codewords={};covered=set()
 for address,size,kind,area,path in re.findall(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+(R/[OW] (?:code|data))\s+(\S+) from (.+)$',(d/'link.log').read_text(),re.M):
  address,size=int(address,16),int(size,16);obj=read_aof(pathlib.Path(path));ar=next(x for x in obj['areas'] if x['name']==area and x['size']==size)
  off=address-dbase;assert not covered.intersection(range(off,off+size));covered.update(range(off,off+size))
  marks=sorted((x['value'],x['name']) for x in obj['symbols'] if x['area']==area and x['name'] in ['$a','$d','$t'])
  if size:assert marks and marks[0][0]==0,(path,area,'unmapped bytes')
  for i,(start,tag) in enumerate(marks):
   end=marks[i+1][0] if i+1<len(marks) else size;assert tag!='$t'
   if tag=='$a':codewords.update({off+x:str(pathlib.Path(path).relative_to(REPO)) for x in range(start,end,4)})
 assert covered==set(range(len((d/'DOSFS.bin').read_bytes()))),'every linked byte from a mapped object area'
 decoded=[]
 for off in sorted(codewords):
  w=struct.unpack_from('<I',b,off)[0];info=inspect_image.decode(w,dbase+off)
  if info['psr'] or info.get('user_bank') and info['kind']=='LDM':assert struct.unpack_from('<I',b,off+4)[0]==0xe1a00000,(hex(off),'ARM2 settling')
  decoded.append(dict(offset=off,source=dict(word=w,object=codewords[off]),decoded=info))
 save(d/'instructions.json',decoded)
 save(d/'linked.json',dict(base=dbase,length=len(b),sha256=sha(b),objects=dosfs_link['objects'],bound_library_symbols=bound,instructions=len(decoded)))
 layout.append(dict(component='DOSFS',title=title,base=dbase,length=len(b),sha256=sha(b)));rom+=struct.pack('<I',len(b)+4)+b
rom+=bytes(4);used=len(rom);assert used<=ROM_SIZE;rom+=bytes(ROM_SIZE-used)
(out/'arclibre.rom').write_bytes(rom)
save(out/'rom-layout.json',dict(status='PASS',rom_sha256=sha(rom),kernel_sha256=sha(kernel),kernel_unchanged=kernel_unchanged,used_bytes=used,modules=layout,messages_code_unchanged=True,messages_resource_offset=resource_offset,resource_sha256=sha(resources),configured_language=10))
print(out/'arclibre.rom',used,'used bytes',sha(rom))
if not any(v in sys.argv for v in ['--without-basic-utilities','--without-squash','--with-basic-utilities','--with-squash','--with-standard-utilities','--without-standard-utilities','--with-streams','--without-streams','--with-ram-filing','--without-ram-filing','--without-task-services','--with-task-services','--with-graphics','--without-graphics','--without-apps','--with-apps','--with-hard-disc','--without-c-desktop','--with-c-desktop','--without-spriteextend','--with-sound','--without-sound','--without-actions','--without-clock','--without-debugger','--without-calc','--without-configure','--baseline-filecore','--without-arm3','--without-network','--without-hardware','--four-meg']):
 from install_macarch_rom import install
 install()
