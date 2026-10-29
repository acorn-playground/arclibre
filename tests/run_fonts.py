#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cold-boot font gate with independent original-metrics and pixel checks."""
import hashlib,json,os,pathlib,shutil,struct,subprocess,sys
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from paths import ROOT
out=REPO/'build/font-stack';logs=out/'logs';logs.mkdir(exist_ok=True);(out/'acceptance.json').unlink(missing_ok=True)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
def run(cmd,name):
 print('Running',name,flush=True)
 with (logs/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def metric_width(name,text):
 # IntMetrics format: 52-byte header, optional mapping, bounding boxes,
 # horizontal/vertical advances and miscellaneous default advances.
 path=REPO/'src/ROMFonts/Fonts'/pathlib.Path(*name.split('.'))/'IntMetric0,ff6';b=path.read_bytes()
 n=b[48]+256*b[51];flags=b[50];p=52
 maplen=struct.unpack_from('<H',b,p)[0] if flags&32 else 256
 if flags&32:p+=2
 mapping=b[p:p+maplen];p+=maplen
 if not flags&1:p+=8*n
 widths=struct.unpack_from('<'+'h'*n,b,p) if not flags&2 else []
 if not flags&2:p+=2*n
 if not flags&4:p+=2*n
 assert flags&8
 misc=p+struct.unpack_from('<H',b,p)[0];default=struct.unpack_from('<h',b,misc+8)[0]
 width=sum(widths[mapping[c]] if widths else default for c in text.encode('ascii'))*12
 return dict(path=str(path.relative_to(REPO)),sha256=hashlib.sha256(b).hexdigest(),width=width)
def pixels(b):return [v for byte in b for v in (byte&15,byte>>4)]
run([sys.executable,REPO/'tools/prepare_emulator.py'],'emulator')
run(['swift','build','--package-path',REPO/'tests/harness','--scratch-path',REPO/'build/harness-patched','--cache-path',REPO/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release'],'harness')
bin=REPO/'build/harness-patched/release';a=ROOT/'artifacts';rom=a/'floppy.rom'
run([bin/'BootProbe',rom,out/'cold-boots',3],'cold-boots')
results=[];evidence=[];hashes=[]
for i in [1,2,3]:
 natural=out/f'natural-{i}';probe=out/f'run-{i}'
 if probe.exists():shutil.rmtree(probe)
 run([bin/'CamProbe',rom,out/f'cold-boots/cold-{i}/pre-module.macarch-state',a/'symbols.json',natural,'natural'],f'natural-{i}')
 run([bin/'FontProbe',rom,natural/'supervisor-entry.macarch-state',out,probe],f'fonts-{i}')
 r=json.loads((probe/'result.json').read_text());assert r['status']=='PASS' and len(r['loaded'])==6 and len(r['fonts'])==12
 assert all(r['exceptions'][n]==0 for n in [1,3,4,5,7]);assert r['line_length']==320
 framehash=[]
 for j,font in enumerate(r['fonts']):
  metrics=metric_width(font['name'],'ArcLibre RISC OS 3.1');assert font['width']==metrics['width'] and font['characters']==20
  assert font['cache_base']==0x1e00000 and font['cache_bytes']==65536
  pages=font['cache_physical_pages'];assert len(pages)==len(set(pages))==2 and all(p%32768==0 and p<4*1024*1024 for p in pages)
  b=(probe/f'font-{j}.bin').read_bytes();assert len(b)==320*256
  px=pixels(b);assert set(px)=={0,7};ink=[(k%640,k//640) for k,v in enumerate(px) if v]
  bounds=[min(x for x,y in ink),min(y for x,y in ink),max(x for x,y in ink),max(y for x,y in ink)]
  # 12pt at 90x45 dpi and baseline (100,400) OS units. Allow the original
  # face bearings/rounding; all output must stay in this conservative region.
  assert 45<=bounds[0]<=55 and 140<=bounds[1]<=160 and bounds[2]<250 and 155<=bounds[3]<165,bounds
  framehash.append(hashlib.sha256(b).hexdigest())
  if i==1:evidence.append(dict(name=font['name'],metrics=metrics,pixel_bounds=bounds,ink_pixels=len(ink),framebuffer_sha256=framehash[-1]))
 aa=(probe/'antialias.bin').read_bytes();levels=sorted(set(pixels(aa)));assert len(levels)>2 and len(aa)==320*256
 framehash.append(hashlib.sha256(aa).hexdigest());hashes.append(framehash)
 # Real Draw processing and Super_Sample45 are reached inside Font_Paint.
 assert r['observed_swis'].get('60702',0)>0 and r['observed_swis'].get('60704',0)>0 and r['observed_swis'].get('60d81',0)>0
 results.append(r)
assert results[0]==results[1]==results[2] and hashes[0]==hashes[1]==hashes[2]
report=dict(status='PASS',cold_runs=3,identical_results=True,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),modules=json.loads((out/'inputs.json').read_text())['modules'],swi_calls_per_run=len(results[0]['calls']),font_faces=12,independent_widths=evidence,cache_base=0x1e00000,cache_bytes=65536,antialias_levels=levels,antialias_sha256=hashes[0][-1],cached_repaint_identical=True,baseline_rom_modified=False,emulator_modified=False,scope='ASCII sample at 12pt, mode 12, all selected faces; not full encoding, font-format or RISC OS 3.11 conformance')
assert report['rom_sha256']==json.loads((REPO/'manifests/baseline-rom.json').read_text())['rom_sha256']
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
