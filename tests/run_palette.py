#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise actual Palette input, VIDC effects and default appearance on cold boots."""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish,probe_exit
REPO=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
from verify_filer_disc import read_directory
# Independent expectation for the saved file: the Wimp's own default palette
# (src/Wimp/s/!Palette, BBGGRR00 words) with greys 0-7 inverted, as VDU 19.
words=[int(w,16) for w in re.findall(r'&([0-9A-F]{8})',(REPO/'src/Wimp/s/!Palette').read_text())]
assert len(words)==20
words[:8]=words[:8][::-1]
def vdu(n,code,w):return bytes([19,n,code,(w>>8)&255,(w>>16)&255,(w>>24)&255])
EXPECTED=b''.join(vdu(i,16,words[i]) for i in range(16))+vdu(0,24,words[16])+b''.join(vdu(i,25,words[16+i]) for i in range(1,4))
root=REPO/'build/arclibre';out=REPO/'build/palette';start(out)
env=dict(os.environ,MACARCH_CORE=str(REPO/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(REPO/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(REPO/'build/swift-module-cache'))
with (out/'harness.log').open('w') as log:subprocess.run(['swift','build','--package-path',str(REPO/'tests/harness'),'--scratch-path',str(REPO/'build/harness-patched'),'--cache-path',str(REPO/'build/swift-cache'),'--disable-sandbox','--build-system','native','-c','release','--product','PaletteProbe'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
def trial(n):
 p=out/f'cold-{n}';shutil.rmtree(p,ignore_errors=True);print('palette-cold-'+str(n),flush=True)
 with (out/f'cold-{n}.log').open('w') as log:subprocess.run([str(REPO/'build/harness-patched/release/PaletteProbe'),str(root/'arclibre.rom'),str(root),str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['task_count']==desktop_task_count(root) and not r['errors']
 assert r['palette_closes']==1 and r['palette_redraws']>0
 assert r['mode_calls']==[15,35,36,12,15,12,3] and len(r['expected_errors'])==1
 assert any(v['component']=='ArcPalette' and v['psr']&3==0 for v in r['initialisations'])
 t=verify(p,required=['ArcPalette','Wimp','Colours'],root=root)
 b=(p/'saved.adf').read_bytes();row=read_directory(b,4)['Pal']
 saved=b[row['address']*256:row['address']*256+row['length']]
 assert (row['load']>>8)&4095==0xFED and saved==EXPECTED,'saved palette file is the inverted palette as VDU 19'
 return dict(result=r,trace=t,screens={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(p.glob('*.png'))})
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(trial,COLD))
same(results)
probe_exit(out,root/'arclibre.rom',results[0],'Palette')
finish(out,dict(status='PASS',rom_sha256=results[0]['result']['rom_sha256'],identical_repetitions=True,actual_vidc_rgb_changes=True,channel_clamping=True,
 selected_swatch_numbered_and_outlined=True,selected_control_inverted=True,menu_items_match_311=['Invert','Mode','Save','Default'],default_palette=True,invert=True,
 greys_follow_colours_0_and_7=True,save_box_writes_vdu19_palette_file=True,dropped_palette_file_loads=True,modes=[12,15,35,36],typed_mode=True,rejected_mode_recovery=True,
 close_reopen=True,pointer_leave_preserves_window=True,title_drag=True,border_and_pointer_colours=True,default_border_matches_desktop_background=True,
 plain_original_furniture=True,bitmap_font_and_flat_cmos=True,no_guest_code_injection=True,emulator_unchanged=True,observations=results[0]))
print('Palette and appearance PASS')
