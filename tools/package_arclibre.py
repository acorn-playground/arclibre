#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package only the tested ArcLibre desktop ROM, public sources and evidence."""
import gzip,hashlib,json,pathlib,shutil,subprocess,sys,tarfile
from paths import REPO
from desktop_profile import desktop_task_count
root=REPO/'build/arclibre';out=REPO/'dist';out.mkdir(exist_ok=True)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text())
calendar=read(REPO/'build/desktop-c-runtime/identity-calendar.json')
assert calendar['status']=='PASS' and calendar['identical_to_normal_build'] and calendar['source_sha256']==sha(REPO/'src/RISC_OSLib/c/armsys')
report=read(root/'acceptance.json');layout=read(root/'rom-layout.json');assert report['status']=='PASS' and report['cold_boots']==3 and report['hardware_cursor_visible_and_moves'] and report['missing_spriteextend_negative_control'];assert sha(root/'arclibre.rom')==report['rom_sha256']==layout['rom_sha256']
assert report['negative_removes_only_spriteextend']
assert report['persistent_tasks']==desktop_task_count(root) and report['floppy_root_and_nested_directories_by_mouse'] and report['f12_catalogue_file_error_recovery_program_exit'] and report['shell_task_terminates_and_desktop_resumes']
assert report['desktop_application_double_click'] and report['nested_obey_and_application_exit'] and report['application_cold_boots']==3
assert report['wd1772_reads_and_fiq_observed'] and report['read_only_test_media']
assert sha(REPO/'build/desktop-baseline/artifacts/discs/DA.adf')==report['test_floppy_sha256']
checks=[REPO/'build/desktop-baseline/artifacts/acceptance.json']+[REPO/f'build/{n}/acceptance.json' for n in ['fpemulator','render-components','font-stack','wimp-stack','multitask','sound','desktop-actions','desktop-c-runtime']]
for p in checks:assert read(p)['status']=='PASS',p
assert all(read(REPO/('build/'+name+'/acceptance.json'))['rom_sha256']==report['rom_sha256'] for name in ['sound','desktop-actions','desktop-c-runtime'])
sprites=read(REPO/'build/sprite-commands/acceptance.json')
assert read(REPO/'build/sound/acceptance.json')['vidc_rate_and_dma_timing']
assert sprites['status']=='PASS' and sprites['cold_boots']==3 and sprites['rom_sha256']==report['rom_sha256']
tasks=read(REPO/'build/task-service-tests/acceptance.json')
assert tasks['status']=='PASS' and tasks['cold_machines']==6 and tasks['rom_sha256']==report['rom_sha256']
assert tasks['missing_modules_negative_control'] and tasks['eight_software_fpa_registers_preserved'] and tasks['original_edit_basic']
streams=read(REPO/'build/stream-tests/acceptance.json');sleep_negative=read(REPO/'build/stream-tests/sleep-negative.json')
assert streams['status']=='PASS' and streams['cold_boots']==3 and streams['rom_sha256']==report['rom_sha256']
assert streams['missing_modules_negative_control'] and streams['sleeping_word_removal_rejected_with_error_0xa84']
assert sleep_negative['status']=='PASS' and sleep_negative['positive_rom_sha256']==report['rom_sha256']
ram=read(REPO/'build/ram-filing-tests/acceptance.json')
assert ram['status']=='PASS' and ram['cold_boots']==3 and ram['rom_sha256']==report['rom_sha256']
assert ram['missing_modules_negative_control'] and ram['original_free_window_matches_filesystem']
assert ram['real_mouse_opens_ram_directory'] and ram['icon_task_removed_with_disk']
utilities=read(REPO/'build/utility-tests/acceptance.json')
assert utilities['status']=='PASS' and utilities['cold_boots']==3 and utilities['rom_sha256']==report['rom_sha256']
assert utilities['actual_vidc_and_frame_blanking'] and utilities['palette_restored_exactly']
assert utilities['real_mouse_and_keyboard_wake']
assert utilities['four_voices_execute_original_ram_code'] and utilities['four_voices_non_silent_dma']
assert utilities['missing_modules_negative_control']
squash=read(REPO/'build/squash-tests/acceptance.json')
assert squash['status']=='PASS' and squash['cold_boots']==3 and squash['rom_sha256']==report['rom_sha256']
assert squash['interleaved_workspaces'] and squash['empty_input_and_short_output'] and squash['missing_module_control']['status']=='EXPECTED_FAILURE'
basic=read(REPO/'build/basic-utility-tests/acceptance.json')
assert basic['status']=='PASS' and basic['cold_boots_per_application']==3 and basic['rom_sha256']==report['rom_sha256']
assert basic['chars_select_and_shift'] and basic['chars_outline_font_paint'] and basic['help_quit_and_restart']
menus=read(REPO/'build/menu-tests/acceptance.json');negative_menu=read(REPO/'build/menu-tests/negative-control.json')
assert menus['status']=='PASS' and menus['cold_boots']==3 and menus['rom_sha256']==report['rom_sha256']
assert negative_menu['status']=='PASS' and negative_menu['rom_sha256']==report['rom_sha256']
apps=read(REPO/'build/desktop-apps/acceptance/acceptance.json')
assert apps['status']=='PASS' and apps['trials']==3 and apps['rom_sha256']==report['rom_sha256']
workflows=read(REPO/'build/app-workflows/acceptance.json')
assert workflows['status']=='PASS' and workflows['independent_cold_boots']==18 and workflows['rom_sha256']==report['rom_sha256']
graphics=read(REPO/'build/graphics-apps/acceptance/acceptance.json')
assert graphics['status']=='PASS' and graphics['trials_per_app']==3 and graphics['rom_sha256']==report['rom_sha256']
palette=read(REPO/'build/palette/acceptance.json')
assert palette['status']=='PASS' and palette['cold_boots']==3 and palette['rom_sha256']==report['rom_sha256']
repro=read(REPO/'build/graphics-apps/reproducibility.json')
assert repro['status']=='PASS' and repro['hashes']['build/arclibre-graphics/arclibre.rom']==report['rom_sha256']
for row in read(REPO/'build/desktop-startup/result.json')['modules']:
 assert next(m['sha256'] for m in layout['modules'] if m['component']==row['component'])==row['sha256']
wimp=read(REPO/'build/wimp-stack/acceptance.json')
for c,digest in wimp['inputs']['modules'].items():
 assert next(m['sha256'] for m in layout['modules'] if m['component']==c)==digest
subprocess.run([sys.executable,REPO/'tools/verify_candidate_patches.py'],check=True)
subprocess.run([sys.executable,REPO/'tools/package_source.py','--arclibre'],check=True)
# Verify the exact archive that will be shipped. The report is outside the
# source archive, avoiding a self-referential archive-hash dependency.
source_digest=sha(out/'arclibre-source.tar.gz');proof_path=out/'arclibre-source-build.json'
# The 4 MB ROM and the extras disc are rebuilt from the same archive and compared.
rom_4m=REPO/'build/arclibre-4m/arclibre.rom';extras=REPO/'build/extras-disc/arclibre-extras.adf'
rom_4m_report=read(REPO/'build/rom-4m-tests/acceptance.json');extras_report=read(REPO/'build/extras-tests/acceptance.json')
assert rom_4m_report['status']=='PASS' and rom_4m_report['cold_boots']==3 and rom_4m_report['rom_sha256']==sha(rom_4m),'run make release-test first'
assert extras_report['status']=='PASS' and extras_report['cold_boots']==3 and extras_report['rom_sha256']==report['rom_sha256'] and extras_report['disc_sha256']==sha(extras)
proof=read(proof_path) if proof_path.exists() else {}
if proof.get('status')!='PASS' or proof.get('source_archive_sha256')!=source_digest or proof.get('rom_sha256')!=report['rom_sha256'] or proof.get('rom_4m_sha256')!=sha(rom_4m) or proof.get('extras_disc_sha256')!=sha(extras):
 parent=REPO/'build/source-verification';parent.mkdir(exist_ok=True)
 n=0
 while (parent/(source_digest[:16]+'-'+str(n))).exists():n+=1
 destination=parent/(source_digest[:16]+'-'+str(n))
 subprocess.run([sys.executable,REPO/'tests/check_source_export.py',out/'arclibre-source.tar.gz',destination,'--expected-rom',root/'arclibre.rom','--expected-rom-4m',rom_4m,'--expected-extras',extras],check=True)
 shutil.copy2(destination/'acceptance.json',proof_path)
proof_path.with_name(proof_path.name+'.sha256').write_text(sha(proof_path)+'  '+proof_path.name+'\n')
shutil.copy2(root/'arclibre.rom',out/'arclibre.rom');shutil.copy2(root/'cold-1/cmos.bin',out/'arclibre.cmos')
config=read(root/'cold-1/result.json')['configuration'];config['romPaths']=['arclibre.rom'];config['cmosPath']='arclibre.cmos';config['powerOnKeys']=[];config['cmosSettings']=[]
(out/'arclibre.machine.json').write_text(json.dumps(config,indent=2)+'\n')
shutil.copy2(REPO/'build/app-workflows/edit-cold-1/test.hdf',out/'arclibre-demo.hdf')
demo=dict(config,hardDiscs=['arclibre-demo.hdf'])
(out/'arclibre-hard-disc.machine.json').write_text(json.dumps(demo,indent=2)+'\n')
# DOSFS is delivered on its own floppy, not in the ROM.
shutil.copy2(REPO/'build/dosfs/arclibre-dosfs.adf',out/'arclibre-dosfs.adf')
# So is Alarm, to leave ROM space for networking.
shutil.copy2(REPO/'build/alarm-disc/arclibre-alarm.adf',out/'arclibre-alarm.adf')
# And printing (!Printers and its modules), by owner decision.
printing=read(REPO/'build/printing-tests/acceptance.json');assert printing['status']=='PASS' and printing['rom_sha256']==report['rom_sha256']
assert sha(REPO/'build/printing-disc/arclibre-printing.adf')==printing['disc_sha256']
shutil.copy2(REPO/'build/printing-disc/arclibre-printing.adf',out/'arclibre-printing.adf')
for app in ['draw','paint']:
 shutil.copy2(REPO/f'build/app-workflows/{app}-cold-1/test.hdf',out/f'arclibre-{app}-demo.hdf')
 (out/f'arclibre-{app}.machine.json').write_text(json.dumps(dict(config,hardDiscs=[f'arclibre-{app}-demo.hdf']),indent=2)+'\n')
for name in [f'arclibre-{app}{suffix}' for app in ['draw','paint'] for suffix in ['-demo.hdf','.machine.json']]+['arclibre-dosfs.adf','arclibre-alarm.adf','arclibre-printing.adf','arclibre.rom','arclibre.cmos','arclibre.machine.json','arclibre-demo.hdf','arclibre-hard-disc.machine.json']:(out/(name+'.sha256')).write_text(sha(out/name)+'  '+name+'\n')
source=dict(source_archive='arclibre-source.tar.gz',sha256=sha(out/'arclibre-source.tar.gz'),rom_sha256=report['rom_sha256'],module_layout=layout,acceptance=report)
(root/'SOURCE.json').write_text(json.dumps(source,indent=2)+'\n')
files=[(n,out/n) for n in ['arclibre-dosfs.adf','arclibre-dosfs.adf.sha256','arclibre-alarm.adf','arclibre-alarm.adf.sha256','arclibre-printing.adf','arclibre-printing.adf.sha256','arclibre.rom','arclibre.rom.sha256','arclibre.cmos','arclibre.cmos.sha256','arclibre.machine.json','arclibre-demo.hdf','arclibre-demo.hdf.sha256','arclibre-hard-disc.machine.json']]+[('SOURCE.json',root/'SOURCE.json')]
files += [(f'arclibre-{app}{suffix}',out/f'arclibre-{app}{suffix}') for app in ['draw','paint'] for suffix in ['-demo.hdf','-demo.hdf.sha256','.machine.json','.machine.json.sha256']]
files += [(n,out/n) for n in ['arclibre-source.tar.gz','arclibre-source.tar.gz.sha256','arclibre-source-build.json','arclibre-source-build.json.sha256']]
# Every document (component results, provenance, history) and the licences.
files.extend((str(p.relative_to(REPO)),p) for p in (REPO/'docs').rglob('*') if p.is_file() and p.name!='.DS_Store')
files.append(('LICENSING.md',REPO/'LICENSING.md'))
# The release's gate reports, as recorded (tools/record_desktop_release.py).
recorded=read(REPO/'manifests/arclibre-desktop-release.json')
for name,path in recorded['evidence_reports'].items():
 assert sha(REPO/path)==recorded['evidence_report_sha256'][name],(name,'record the release again');files.append((name,REPO/path))
for n in ['manifests','licenses','patches']:
 files.extend((str(p.relative_to(REPO)),p) for p in (REPO/n).rglob('*') if p.is_file())
files.extend((str(p.relative_to(REPO)),p) for p in (REPO/'src').rglob('LICENSE'))
for n in ['acceptance.json','rom-layout.json','SOURCE.json','cold-1','cold-2','cold-3','launch-1','launch-2','launch-3','checker','negative-pointer']:
 p=root/n
 files.extend([('evidence/'+n,p)] if p.is_file() else [('evidence/'+str(f.relative_to(root)),f) for f in p.rglob('*') if f.is_file()])
for p in checks:files.append(('evidence/regressions/'+str(p.relative_to(REPO/'build')),p))
for n in ['result.json','headers.json','generated-help.json','resources.json']:
 p=REPO/'build/desktop-startup'/n;files.append(('evidence/startup/'+n,p))
for name in ['acceptance.json','workspace-contract.json','result.json','resources.json','cold-1','cold-2','cold-3']:
 p=REPO/'build/sound'/name
 files.extend([('evidence/sound/'+name,p)] if p.is_file() else [('evidence/sound/'+str(f.relative_to(REPO/'build/sound')),f) for f in p.rglob('*') if f.is_file()])
for name in ['acceptance.json','result.json','cold-1','cold-2','cold-3']:
 p=REPO/'build/desktop-actions'/name
 files.extend([('evidence/desktop-actions/'+name,p)] if p.is_file() else [('evidence/desktop-actions/'+str(f.relative_to(REPO/'build/desktop-actions')),f) for f in p.rglob('*') if f.is_file()])
for p in (root/'c-runtime').rglob('*'):
 if p.is_file():files.append(('evidence/c-runtime-link/'+str(p.relative_to(root/'c-runtime')),p))
for name in ['acceptance.json','identity-calendar.json']+[f'{mode}-cold-{n}' for mode in ['copy','move','delete','protected','abi'] for n in [1,2,3]]:
 p=REPO/'build/desktop-c-runtime'/name
 files.extend([('evidence/c-runtime/'+name,p)] if p.is_file() else [('evidence/c-runtime/'+str(f.relative_to(REPO/'build/desktop-c-runtime')),f) for f in p.rglob('*') if f.is_file()])
for name in ['app-runtime','graphics-runtime','palette-runtime','task-runtime','stream-runtime','ram-filing-runtime','utility-runtime','squash-runtime','basic-utility-runtime','clock-runtime','debugger-runtime','calc-runtime','configure-runtime','arm3-runtime','hardware']:
 for p in (root/name).rglob('*'):
  if p.is_file():files.append(('evidence/'+name+'/'+str(p.relative_to(root/name)),p))
for name in ['resources.json','acceptance']:
 p=REPO/'build/desktop-apps'/name
 files.extend([('evidence/desktop-apps/'+name,p)] if p.is_file() else [('evidence/desktop-apps/'+str(f.relative_to(REPO/'build/desktop-apps')),f) for f in p.rglob('*') if f.is_file()])
for name in ['reproducibility.json','resources.json','acceptance']:
 p=REPO/'build/graphics-apps'/name
 files.extend([('evidence/graphics-apps/'+name,p)] if p.is_file() else [('evidence/graphics-apps/'+str(f.relative_to(REPO/'build/graphics-apps')),f) for f in p.rglob('*') if f.is_file()])
for name in ['acceptance.json','fixtures']+[f'{app}-cold-{n}' for app in ['paint','draw','edit'] for n in [1,2,3]]:
 p=REPO/'build/app-workflows'/name
 files.extend([('evidence/app-workflows/'+name,p)] if p.is_file() else [('evidence/app-workflows/'+str(f.relative_to(REPO/'build/app-workflows')),f) for f in p.rglob('*') if f.is_file()])
for name in ['verification.json','workspace-contract.json','exception-paths.json','routine-tests.json','reproducibility.json','rom-layout.json']:
 p=REPO/'build/desktop-defaults/artifacts'/name
 if p.exists():files.append(('evidence/desktop-defaults/'+name,p))
for name in ['acceptance.json','result.json','headers.json','cold-1','cold-2','cold-3']:
 p=REPO/'build/palette'/name
 files.extend([('evidence/palette/'+name,p)] if p.is_file() else [('evidence/palette/'+str(f.relative_to(REPO/'build/palette')),f) for f in p.rglob('*') if f.is_file()])
files.append(('evidence/desktop-resource-selection.json',root/'desktop-resource-selection.json'))
for base,names in [('sprite-commands',['acceptance.json','cold-1','cold-2','cold-3']),('sprite-command-app',['application.adf','input.sprite','client.aof','manifest.json']),('desktop-actions',['resources.json','headers.json','modules/SpriteUtil'])]:
 for name in names:
  p=REPO/'build'/base/name
  files.extend([('evidence/'+base+'/'+name,p)] if p.is_file() else [('evidence/'+base+'/'+str(f.relative_to(REPO/'build'/base)),f) for f in p.rglob('*') if f.is_file()])
# The release's other two artifacts: the 4 MB ROM's and the extras disc's gates and layouts.
for directory in ['rom-4m-tests','extras-tests']:
 files.extend(('evidence/'+directory+'/'+str(p.relative_to(REPO/'build'/directory)),p) for p in (REPO/'build'/directory).rglob('*.json') if p.is_file())
files+=[('evidence/rom-4m/rom-layout.json',REPO/'build/arclibre-4m/rom-layout.json'),('evidence/extras-disc/disc.json',REPO/'build/extras-disc/disc.json')]
for directory in ['task-service-tests','task-service-app','menu-tests','menu-app','stream-tests','stream-app','ram-filing-tests','ram-app','utility-tests','utility-app','squash-tests','squash-app','basic-utility-tests','basic-utility-app','clock-tests','debugger-tests']:
 files.extend(('evidence/'+directory+'/'+str(p.relative_to(REPO/'build'/directory)),p) for p in (REPO/'build'/directory).rglob('*') if p.is_file())
for name in ['rom-layout.json','probe/failure.json','probe/failure-trace.log','probe/launch-events.json']:
 files.append(('evidence/menu-negative/'+name,REPO/'build/arclibre-bad-menu'/name))
for name in ['result.json','headers.json','resources.json','workspace-contract.json']:
 files.append(('evidence/task-services/'+name,REPO/'build/task-services'/name))
for name in ['result.json','headers.json','resources.json','workspace-contract.json']:
 files.append(('evidence/streams/'+name,REPO/'build/streams'/name))
for name in ['result.json','headers.json','resources.json','workspace-contract.json']:
 files.append(('evidence/ram-filing/'+name,REPO/'build/ram-filing'/name))
for name in ['result.json','headers.json','resources.json']:
 files.append(('evidence/standard-utilities/'+name,REPO/'build/standard-utilities'/name))
for name in ['result.json','headers.json','resources.json']:
 files.append(('evidence/clock-services/'+name,REPO/'build/clock-services'/name))
for name in ['result.json','Code','run-1/result.json','run-2/result.json']:
 files.append(('evidence/alarm-code/'+name,REPO/'build/alarm-code'/name))
for name in ['disc.json','basic-1/result.json','basic-2/result.json']:
 files.append(('evidence/printing-disc/'+name,REPO/'build/printing-disc'/name))
for name in ['result.json','headers.json']:
 files.append(('evidence/printing/'+name,REPO/'build/printing'/name))
for name in ['result.json','Calc,ffb','!RunImage,ffb']:
 files.append(('evidence/calc/'+name,REPO/'build/calc'/name))
for name in ['result.json','Configure,ffb','!RunImage,ffb']:
 files.append(('evidence/configure/'+name,REPO/'build/configure'/name))
for name in ['rom-layout.json','probe/failure.json','probe/failure-trace.log','probe/launch-events.json']:
 files.append(('evidence/sleep-negative/'+name,REPO/'build/arclibre-bad-sleep'/name))
archive=out/'arclibre-evidence.tar.gz'
with archive.open('wb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
 for name,p in sorted(set(files)):
  assert p.is_file() and not p.is_symlink(),p
  info=tar.gettarinfo(str(p),arcname='arclibre-evidence/'+name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with p.open('rb') as data:tar.addfile(info,data)
archive.with_name(archive.name+'.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
print(out/'arclibre.rom',report['rom_sha256']);print(archive,archive.stat().st_size,'bytes')
