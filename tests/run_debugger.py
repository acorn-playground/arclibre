#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original Debugger: memory display, disassembly, breakpoints and register reports."""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,struct,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tests'))
import inspect_image
from adfs_fixture import directory,u24,oldcheck
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/debugger-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-alarm-code','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','BasicRunProbe'],'harness')
exe=R/'build/harness-alarm-code/release/BasicRunProbe'
# An empty formatted floppy: the probe needs a disc, the commands do not use it.
disc=bytearray(819200);disc[0x400:0xc00]=directory('$',4,[],b'Hugo')
u24(disc,0,0x1400//256);u24(disc,256,(819200-0x1400)//256);u24(disc,252,3200)
for i,ch in enumerate(b'DEBUGTEST '[:10]):disc[247+i//2 if i%2==0 else 502+i//2]=ch
disc[507:509]=b'\x41\x42';disc[510]=3;disc[255]=oldcheck(disc[:255]);disc[511]=oldcheck(disc[256:511])
(out/'blank.adf').write_bytes(disc)
COMMANDS=['*MemoryI 3800000 +10','*Memory 3800000 +10','BASIC',
 'DIM c% 64:P%=c%:[OPT 0:MOV R0,#42:MOV R1,#7:MOV R2,#0:MOV PC,R14:]',
 'OSCLI("BreakSet "+STR$~(c%+8)):PRINT "CODE ";~c%','CALL c%','Continue','Y',
 'PRINT "BACK":OSCLI("BreakClr"):OSCLI("BreakList")','QUIT']
rom=(root/'arclibre.rom').read_bytes()
def romword(a):return struct.unpack_from('<I',rom,a-0x3800000)[0]
def trial(n,rom_root=root,name=None):
 p=out/(name or f'cold-{n}');shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'input.adf').write_bytes(disc)
 run([exe,rom_root/'arclibre.rom',rom_root,p/'input.adf',p,*COMMANDS],p.name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha(rom_root/'arclibre.rom')
 return r
def check(r):
 text='\n'.join(line for screen in r['screens'] for line in screen)
 # Disassembly: each word is the ROM's, and the operand matches an independent decode.
 rows=re.findall(r'^(038000[0-9A-F]{2}) : .{4} : ([0-9A-F]{8}) : (\S+)\s+(.*)$',text,re.M)
 seen={};[seen.setdefault(int(a,16),(int(w,16),op,rest.strip())) for a,w,op,rest in rows]
 assert sorted(seen)==[0x3800000,0x3800004,0x3800008,0x380000C],sorted(seen)
 for a,(w,op,rest) in seen.items():
  assert w==romword(a),(hex(a),'word')
  d=inspect_image.decode(w,a)
  target=d['branch'] if d['branch'] is not None else d.get('literal')
  assert target is not None and rest.endswith('&%08X'%target),(hex(a),op,rest,hex(target or 0))
 dump=re.search(r'^03800000 :\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+([0-9A-F]{8})',text,re.M)
 assert dump and [int(x,16) for x in dump.groups()]==[romword(0x3800000+4*i) for i in range(4)],'memory dump'
 code=int(re.search(r'^CODE\s+([0-9A-F]+)',text,re.M).group(1),16)
 assert ('Stopped at break point set at &%08X'%(code+8)) in text,'breakpoint stop'
 regs=re.search(r'R0  = ([0-9A-F]{8}) R1  = ([0-9A-F]{8})',text[text.index('Stopped at break point'):])
 assert regs and regs.groups()==('0000002A','00000007'),'registers at the breakpoint'
 assert 'Continue from breakpoint set at &%08X'%(code+8) in text and re.search(r'^BACK$',text,re.M),'continue returns to BASIC'
 return dict(disassembly={hex(a):list(v) for a,v in seen.items()},breakpoint=code+8,registers=regs.groups())
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=[check(r) for r in pool.map(trial,COLD)]
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Debugger')
run([sys.executable,R/'tools/build_arclibre_rom.py','--without-debugger'],'negative-rom')
neg=R/'build/arclibre-without-debugger'
positive=json.loads((root/'rom-layout.json').read_text());negative=json.loads((neg/'rom-layout.json').read_text())
assert {m['component'] for m in positive['modules']}-{m['component'] for m in negative['modules']}=={'Debugger'}
r=trial(0,neg,'negative-missing-module');text='\n'.join(l for s in r['screens'] for l in s)
assert "File 'MemoryI' not found" in text and 'Stopped at break point' not in text,'missing Debugger control'
finish(out,dict(status='PASS',rom_sha256=sha(root/'arclibre.rom'),negative_rom_sha256=sha(neg/'arclibre.rom'),identical_repetitions=True,
 kernel_and_emulator_unchanged=True,guest_code_injection=False,disassembly_matches_rom_and_independent_decode=True,memory_dump_matches_rom=True,
 breakpoint_stop_and_register_report=True,continue_returns=True,missing_module_negative_control=True,observations=results[0]))
print('Debugger PASS',flush=True)
