#!/usr/bin/env python3
"""Build maintained ARM2 sources; all generated inputs stay in build/rom."""
import hashlib,json,os,pathlib,shutil,struct,subprocess,sys
from paths import REPO,ROOT,SRC,HOST
import inspect_image,module_image
MODULES=['FileSwitch','ResourceFS','MsgTrans','Messages','TerritoryManager','UK','Inter','IntKey','FileCore','ADFS']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(ROOT/'artifacts'/name).write_text(json.dumps(value,indent=2)+'\n')
def run(cmd,cwd,log,env=None):
 with (ROOT/'logs'/log).open('w') as out:subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
for d in ['artifacts/modules','logs','build']:(ROOT/d).mkdir(parents=True,exist_ok=True)
(ROOT/'artifacts/acceptance.json').unlink(missing_ok=True)
if (ROOT/'work').exists():shutil.rmtree(ROOT/'work')
shutil.copytree(SRC,ROOT/'work')
if not (ROOT/'sources').exists():(ROOT/'sources').symlink_to(SRC,target_is_directory=True)
headers=json.loads((REPO/'manifests/header-exports.json').read_text());exports=ROOT/'build/Hdr'
if exports.exists():shutil.rmtree(exports)
exports.mkdir()
def export(mapping):
 for name,source in mapping.items():
  p=exports/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'work'/source,p)
export(headers['kernel'])
asm=HOST/'bin/asasm';observer=HOST/'bin/asasm-observer';tokenise=HOST/'bin/tokenise'
assert all(p.exists() for p in [asm,observer,tokenise]),'Run python3 tools/bootstrap.py first'
env=dict(os.environ,MACHINE='A440',IMAGESIZE='2048K',HDR_PATH=str(exports))
run([tokenise,exports/'Tokens','HelpStrs','s/TMOSHelp'],ROOT/'work/Kernel','kernel-help.log',env)
p=ROOT/'work/Kernel/s/TMOSHelp';p.write_bytes(b'; Generated 2026 from the pinned Kernel HelpStrs and HdrSrc Tokens.\n; Apache-2.0; upstream notices retained in those inputs and sources/Kernel/LICENSE.\n'+p.read_bytes())
# The delivered ROM's version and date (*FX 0, the kernel's *Help title,
# UtilityModule) come from manifests/release.json; the kernel's *Help version has
# two decimal places, as RISC OS's do (0.9 is 0.90, 0.9.1 is 0.91).
version=json.loads((REPO/'manifests/release.json').read_text());major,*minor=version['version'].split('.')
release=[f'-PreDefine=ArcLibreVersion SETS "{version["version"]}"',f'-PreDefine=ArcLibreHelpVersion SETS "{major}.{"".join(minor).ljust(2,"0")}"',f'-PreDefine=ArcLibreDate SETS "{version["date"]}"']
def assemble(source,cwd,out,absolute=False):
 hashes=[]
 for attempt in ['normal-1','normal-2','trace']:
  tracing=attempt=='trace';tool=observer if tracing else asm;output=out/('kernel-trace.aof' if tracing else 'kernel.aof') if out==ROOT/'artifacts' else out/('module-trace.aof' if tracing else 'module.aof')
  variables=dict(env)
  if tracing:
   for key,name in [('ASASM_TRACE','emissions.tsv'),('ASASM_SYMBOLS','symbols.tsv'),('ASASM_REFS','symbol-lookups.tsv')]:
    p=out/name;p.unlink(missing_ok=True);variables[key]=str(p)
  # ArcLibreDelivered marks fixes made for the delivered ROM (for example
  # FileCore without FSLock); the --baseline build stays the exact frozen one.
  cmd=[tool]+(['-PreDefine=ArcLibreDesktopDefaults SETL {TRUE}'] if absolute and '--desktop-defaults' in sys.argv else [])+(['-PreDefine=ArcLibreDelivered SETL {TRUE}']+release if '--desktop-defaults' in sys.argv else [])+(['-ABSolute'] if absolute else [])+['-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','-Verbose',source,output]
  log=cwd.name+'-'+attempt+'.log';run(cmd,cwd,log,variables);hashes.append(sha(output))
  if absolute:save('trace-assembly-result.json' if tracing else 'assembly-result.json',dict(returncode=0,log='logs/'+log,command=[str(x) for x in cmd],assembler_sha256=sha(tool)))
 assert len(set(hashes))==1,(cwd,hashes)
 return hashes
print('Assembling kernel',flush=True)
hashes=assemble('s/GetAll',ROOT/'work/Kernel',ROOT/'artifacts',True)
save('reproducibility.json',dict(status='PASS',normal_and_observer_aof_hashes=hashes))
import verify,routine_checks
verify.verify();routine_checks.checks()
subprocess.run([sys.executable,str(REPO/'tools/interface_manifest.py')],check=True)
symbols=inspect_image.load_symbols();values={n:v['value'] for n,v in symbols.items()};data=(ROOT/'artifacts/kernel.bin').read_bytes()
instructions=json.loads((ROOT/'artifacts/instructions.json').read_text())
calls=[x for x in instructions if x.get('branch')==values['ModuleInit']];assert len(calls)==1
values['PostSysHeapShrink']=calls[0]['rom_address']+16
values['SelectFSSWI']=min(x['rom_address'] for x in instructions if x['word']=='ef020029' and x['rom_address']>values['PostSysHeapShrink'])
save('symbols.json',values)
(ROOT/'artifacts/kernel.labels').write_text(''.join(f'{n} = &{v["value"]:08X}\n' for n,v in symbols.items() if v['tag']==128 and 0x3800000<=v['value']<0x3800000+len(data)))
export(headers['module_overrides'])
# Build the original public Squash compressor/decoder and round-trip the sprite.
squash=ROOT/'build/squash';squash.mkdir(exist_ok=True)
for p in (SRC/'Squash/h').iterdir():shutil.copyfile(p,squash/(p.name+'.h'))
run(['clang','-O2','-funsigned-char','-I'+str(squash),'-x','c',ROOT/'work/Squash/c/cssr',ROOT/'work/Squash/c/zssr',REPO/'tools/squash_asset.c','-o',squash/'squash-asset'],ROOT,'squash-build.log')
source=SRC/'TerritoryManager/SystemDisc,ff9';dest=ROOT/'work/TerritoryManager/SystemDiscSquashed'
run([squash/'squash-asset',source,dest],ROOT,'squash-first.log');run([squash/'squash-asset',source,squash/'repeat.bin'],ROOT,'squash-repeat.log')
assert dest.read_bytes()==(squash/'repeat.bin').read_bytes()
save('sprite-build.json',dict(status='PASS',source_sha256=sha(source),compressed_sha256=sha(dest),matching_public_decoder_roundtrip=True,reproducible=True))
# Original resources retain their bytes and public ScanRes record layout.
resources=[];blob=b''
rows=[('MsgTrans','Resources/UK/Messages','Resources.MsgTrans.Messages'),('FileSwitch','Resources/UK/Messages','Resources.FileSwitch.Messages'),('ResourceFS','Resources/UK/Messages','Resources.ResourceFS.Messages'),('Kernel','Resources/UK/Messages','Resources.Kernel.Messages'),('Messages','Global/UK/Messages','Resources.Global.Messages'),('Messages','Data/Dictionary','Resources.Kernel.Dictionary'),('Messages','Data/HelpTokens','Resources.Help.Messages'),('TerritoryManager','Resources/UK/Messages','Resources.TerrMgr.Messages'),('UK','Resources/UK/Messages','Resources.UK.Messages'),('Inter','Resources/UK/Messages','Resources.Internatio.Messages'),('FileCore','Resources/UK/Messages','Resources.FileCore.Messages'),('ADFS','Resources/UK/Messages','Resources.ADFS.Messages')]
for comp,path,name in rows:
 p=SRC/comp/path;b=p.read_bytes();filename=name.encode()+b'\0';filename+=bytes(-len(filename)%4)
 length=20+len(filename)+4+((len(b)+3)&~3)
 record=struct.pack('<5I',length,0xffffff00,0,len(b),3)+filename+struct.pack('<I',len(b)+4)+b+bytes(-len(b)%4)
 assert len(record)==length;blob+=record;resources.append(dict(name=name,source='sources/'+comp+'/'+path,length=len(b),sha256=sha(p),record_bytes=length))
(ROOT/'build/resources.bin').write_bytes(blob);(ROOT/'work/Messages/ResourcesData').write_bytes(blob);save('resources.json',resources)
run([asm,'-ABSolute','-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','IntHelpSrc',ROOT/'build/IntHelp.aof'],ROOT/'work/Inter','Inter-help.log',env)
(ROOT/'work/Inter/s/IntHelp').write_bytes(inspect_image.load_aof(ROOT/'build/IntHelp.aof')['data'])
for comp,inputfile,outputfile in [('Inter','s/IntHelp','s/IntHelpTok'),('FileCore','HelpText','s/TokenHelp'),('ADFS','HelpText','s/TokenHelp')]:run([tokenise,exports/'Tokens',inputfile,outputfile],ROOT/'work'/comp,comp+'-tokenise.log',env)
reports=[]
for comp in MODULES:
 print('Assembling',comp,flush=True);out=ROOT/'artifacts/modules'/comp;out.mkdir(exist_ok=True)
 source={'TerritoryManager':'s/TerrMgr','Inter':'s/InterMod','IntKey':'UK/Source/IntKeyMod'}.get(comp,'s/'+comp)
 hashes=assemble(source,ROOT/'work'/comp,out)
 obj=module_image.load_aof(out/'module.aof');(out/'module.bin').write_bytes(obj['data'])
 reports.append(dict(component=comp,bytes=obj['size'],sha256=sha(out/'module.bin'),object_hashes=hashes,unresolved_symbols=0,relocations=0))
save('module-build.json',dict(status='PASS',modules=reports))
subprocess.run([sys.executable,str(REPO/'tools/audit_modules.py')],check=True)
subprocess.run([sys.executable,str(REPO/'tools/territory_expectations.py')],check=True)
end=values['EndOfKernel']-0x3800000;assert end==len(data)-4 and data[end:]==bytes(4)
rom=bytearray(data[:end]);layout=[];labels=(ROOT/'artifacts/kernel.labels').read_text()
for comp in MODULES:
 b=(ROOT/'artifacts/modules'/comp/'module.bin').read_bytes();assert len(b)%4==0
 base=0x3800000+len(rom)+4;rom+=struct.pack('<I',len(b)+4)+b
 offset=struct.unpack_from('<I',b,16)[0];title=b[offset:b.index(0,offset)].decode()
 layout.append(dict(component=comp,title=title,base=base,length=len(b),size_word_address=base-4,size_word=len(b)+4,sha256=hashlib.sha256(b).hexdigest()))
 for name,value in json.loads((ROOT/'artifacts/modules'/comp/'symbols.json').read_text()).items():
  if value['tag']==128 and 0<=value['value']<len(b):labels+=f'{comp}_{name} = &{base+value["value"]:08X}\n'
rom+=bytes(4);used=len(rom);assert used<=2097152;rom+=bytes(2097152-used)
(ROOT/'artifacts/floppy.rom').write_bytes(rom);(ROOT/'artifacts/rom.labels').write_text(labels)
save('rom-layout.json',dict(status='PASS',rom_sha256=hashlib.sha256(rom).hexdigest(),kernel_sha256=sha(ROOT/'artifacts/kernel.bin'),kernel_code_and_data_preserved=True,chain_extension_offset=end,used_bytes=used,modules=layout))
if '--baseline' in sys.argv:
 expected=json.loads((REPO/'manifests/baseline-rom.json').read_text())
 assert hashlib.sha256(rom).hexdigest()==expected['rom_sha256'] and sha(ROOT/'artifacts/kernel.bin')==expected['kernel_sha256']
 assert layout==expected['modules'];print('PASS: exact baseline ROM, kernel and every module reproduced',flush=True)
save('build-result.json',dict(status='PASS',rom_sha256=hashlib.sha256(rom).hexdigest(),baseline_checked='--baseline' in sys.argv,source_files={str(p.relative_to(SRC)):sha(p) for p in sorted(SRC.rglob('*')) if p.is_file()}))
print(ROOT/'artifacts/floppy.rom',flush=True)
