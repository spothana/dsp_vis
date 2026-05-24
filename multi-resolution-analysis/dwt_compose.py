"""
Composite DWT simulator frames onto a 3840x2160 (4K) canvas.

The simulator layout is portrait (taller than wide), so it is fitted by HEIGHT
and centered, leaving symmetric side margins on the 16:9 frame. The canvas
background matches the simulator's dark theme so the margins blend in.
"""

import pathlib
from PIL import Image

SRC = sorted(pathlib.Path("frames").glob("f*.png"))
OUT = pathlib.Path("canvas4k")
OUT.mkdir(exist_ok=True)
for old in OUT.glob("c*.png"):
    old.unlink()

CW, CH = 3840, 2160
BG = (14, 19, 32)     # matches --bg of the simulator's dark theme
MARGIN = 48           # vertical breathing room top+bottom

if not SRC:
    raise SystemExit("no frames found - run dwt_render_frames.py first")

for i, fp in enumerate(SRC):
    im = Image.open(fp).convert("RGB")
    # fit by height first
    target_h = CH - 2 * MARGIN
    scale = target_h / im.height
    target_w = int(round(im.width * scale))
    # if that overflows the width, fit by width instead
    if target_w > CW - 2 * MARGIN:
        scale = (CW - 2 * MARGIN) / im.width
        target_w = CW - 2 * MARGIN
        target_h = int(round(im.height * scale))
    im = im.resize((target_w, target_h), Image.LANCZOS)
    canvas = Image.new("RGB", (CW, CH), BG)
    canvas.paste(im, ((CW - target_w) // 2, (CH - target_h) // 2))
    canvas.save(OUT / f"c{i:04d}.png")

print(f"composited {len(SRC)} frames at {CW}x{CH} into {OUT}/")
