#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Optional visual preview; Pillow is not required by the acceptance gate."""
import json
from PIL import Image,ImageDraw
from paths import REPO
root=REPO/'build/font-stack';r=json.loads((root/'run-1/result.json').read_text())
canvas=Image.new('RGB',(1000,13*80+35),'#181b22');draw=ImageDraw.Draw(canvas)
for i,font in enumerate(r['fonts']+[dict(name='Homerton.Medium (antialiased)')]):
 name='antialias' if i==12 else f'font-{i}';b=(root/f'run-1/{name}.bin').read_bytes()
 values=[v for byte in b for v in (byte&15,byte>>4)]
 im=Image.new('L',(640,256));im.putdata([v*17 if i==12 else (255 if v else 0) for v in values])
 im=im.crop((40,145,260,165)).resize((440,80),Image.Resampling.NEAREST)
 canvas.paste(im,(335,30+i*80));draw.text((15,62+i*80),font['name'],fill='white')
canvas.save(root/'atlas.png');print(root/'atlas.png')
