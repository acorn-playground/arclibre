#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Optional native-pixel preview, including mode 12's two-to-one aspect."""
import json
from PIL import Image
from paths import REPO
root=REPO/'build/wimp-stack';r=json.loads((root/'run-1/result.json').read_text())
for name in ['window','moved','closed']:
 palette=[tuple(((v>>shift)&15)*17 for shift in [0,4,8]) for v in r['frame_palettes'][name]]
 b=(root/f'run-1/{name}.bin').read_bytes();im=Image.new('RGB',(640,256));im.putdata([palette[v] for byte in b for v in (byte&15,byte>>4)])
 im.resize((640,512),Image.Resampling.NEAREST).save(root/(name+'.png'))
print(root/'window.png')
