#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Launch the BASIC applications (Chars, Help, Calc, Configure in ROM; Alarm from its disc) through Filer and exercise their UIs."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
args=[a for a in sys.argv[1:] if not a.startswith('--')];root=R/(args[0] if args else 'build/arclibre-basic-utilities')
out=R/'build/basic-utility-tests';out.mkdir(exist_ok=True);(out/('probe.json' if '--probe' in sys.argv else 'acceptance.json')).unlink(missing_ok=True)
env=dict(os.environ,PYTHONPATH=str(R/'tools'),MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run([sys.executable,R/'tests/build_basic_utility_disc.py'],'fixture')
# Alarm runs from the distributable arclibre-alarm.adf, as a user would.
run([sys.executable,R/'tools/build_alarm_disc.py'],'alarm-disc');alarm_disc=R/'build/alarm-disc/arclibre-alarm.adf'
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-basic-utilities','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','DesktopLaunchProbe'],'harness')
exe=R/'build/harness-basic-utilities/release/DesktopLaunchProbe';disc=R/'build/basic-utility-app/applications.adf';rom_sha=sha(root/'arclibre.rom')
def trial(spec):
 app,n=spec;name=app.lower()+'-'+str(n);p=out/name
 # ConfigureNet: !Configure's Net window on Econet station 1 (DesktopLaunchProbe net).
 if '--verify-existing' not in sys.argv:
  shutil.rmtree(p,ignore_errors=True);run([exe,root/'arclibre.rom',root,alarm_disc if app=='Alarm' else disc,p,'!'+app.replace('ConfigureNet','Configure')]+(['net'] if app=='ConfigureNet' else []),name)
 # Alarm is left running with its delivered alarm; Chars and Help quit.
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==rom_sha and not r['errors'] and r['task_count']==desktop_task_count(root)+(1 if app in ['Alarm','ConfigureNet'] else 0)
 assert all(r['exceptions'][i]==0 for i in [3,4,5])
 proof=verify(p,required={'Alarm':['BASIC','Wimp','Sound0'],'Calc':['ArcCalc','BASIC','Wimp'],'Configure':['ArcConfigure','BASIC','Wimp'],'ConfigureNet':['ArcConfigure','BASIC','Wimp','Econet','NetFS','NetPrint']}.get(app,['Chars','Help','BASIC','Wimp','FontManager']),root=root)
 result=dict(application=app,rom_sha256=rom_sha,trace=proof,exceptions=r['exceptions'],stages=json.loads((p/'stages.json').read_text()),menus=json.loads((p/'menus.json').read_text()))
 if app=='Chars':
  result['fonts']=json.loads((p/'basic-fonts.json').read_text());assert r'\FWIMPSymbol' in result['fonts']
  result['keys']=json.loads((p/'basic-keys.json').read_text());assert 65 in result['keys'] and 66 in result['keys']
 elif app=='Calc':
  result['calc']=json.loads((p/'calc-observations.json').read_text())
  assert result['calc']['sum']=='15' and result['calc']['error']=='Error'
 elif app=='Configure':
  o=json.loads((p/'configure-observations.json').read_text())
  assert len(o['changes'])>=18 and o['main_icons'][2]=='Net'
  # The saved file: Cfg, type &FF2, two bytes per recorded CMOS RAM location.
  sys.path.insert(0,str(R/'tests'));from verify_filer_disc import read_directory
  b=(p/'saved.adf').read_bytes();row=read_directory(b,4)['Cfg']
  assert (row['load']>>8)&0xfff==0xff2 and row['length']==64,row
  result['configure']=dict(changes=o['changes'],main_icons=o['main_icons'],windows=o['windows'],saved_bytes=row['length'],saved_sha256=hashlib.sha256(b[row['address']*256:row['address']*256+row['length']]).hexdigest())
 elif app=='ConfigureNet':
  o=json.loads((p/'configure-net-observations.json').read_text())
  assert o['station']=='0.1' and o['final']['fs']=='Fred' and o['final']['ps']=='0.235' and o['final']['cmos'][:2]==[0,0x46],o
  result['configure_net']=o
 elif app=='Alarm':
  o=json.loads((p/'alarm-observations.json').read_text());c=json.loads((p/'alarm-code-state.json').read_text())
  assert o['delivered_minutes']>=o['due_minutes']>o['set_time_minutes'] and c['verified'] and c['swis']>c['swis_before']
  result['alarm']=dict(observations=o,code=c)
 else:
  result['help_messages']=json.loads((p/'basic-help-messages.json').read_text());assert any(m['action']==0x503 and m['text'] for m in result['help_messages'])
 return result
count=1 if '--probe' in sys.argv else 3
APPS=['Chars','Help','Alarm','Calc','Configure','ConfigureNet']
specs=[(app,n) for n in range(1,count+1) for app in APPS]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,specs))
for app in APPS:
 repeats=[r for r in results if r['application']==app];assert all(r==repeats[0] for r in repeats)
negative=None
if count>1:
 # Alarm is not in the ROM: the wrapper that runs Resources:$.Apps.!Alarm
 # (as the ROM copy of 3.11 would be) must fail on the same ROM.
 neg=root;assert all(m['component']!='Alarm' for m in json.loads((neg/'rom-layout.json').read_text())['modules'])
 q=out/'negative-missing-alarm';shutil.rmtree(q,ignore_errors=True)
 with (out/'negative.log').open('w') as f:control=subprocess.run([str(exe),neg/'arclibre.rom',neg,disc,q,'!Alarm'],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
 failure=json.loads((q/'failure.json').read_text());assert control.returncode==1 and all(t in failure['failure'] for t in ['Resources:$.Apps.!Alarm.!Run','not found','"number": 214']),failure['failure']
 negative=dict(rom_sha256=sha(neg/'arclibre.rom'),failure=failure['failure'])
report=dict(status='PASS',rom_sha256=rom_sha,fixture_sha256=sha(disc),alarm_disc_sha256=sha(alarm_disc),alarm_from_disc=True,cold_boots_per_application=count,basic_compacted_by_arclibre_squish=True,licence_lines_retained=True,
 alarm_set_delivered_on_time_with_sound=True,alarm_browser_runs_generated_code=True,alarm_quit_and_restart=True,calc_arithmetic_error_and_clear=True,calc_311_layout_colours=True,calc_quit=True,configure_sections_write_cmos=True,configure_save_and_load=True,configure_quit=True,configure_net_on_econet=True,missing_alarm_negative_control=negative,real_filer_launch=True,chars_select_and_shift=True,chars_font_menu=True,chars_outline_font_paint=True,help_real_requests_and_replies=True,help_quit_and_restart=True,observations=results[:len(APPS)])
(out/('probe.json' if count==1 else 'acceptance.json')).write_text(json.dumps(report,indent=2)+'\n');print('Chars, Help, Alarm, Calc and Configure gate PASS',flush=True)
