import pathlib
from PIL import Image

SRC = sorted(pathlib.Path("frames").glob("f*.png"))
OUT = pathlib.Path("canvas4k")
OUT.mkdir(exist_ok=True)

CW, CH = 3840, 2160
BG = (255, 255, 255)
MARGIN = 40   # minimal vertical breathing room

for i, fp in enumerate(SRC):
    im = Image.open(fp).convert("RGB")
    # scale widget to fit canvas height minus margins
    target_h = CH - 2 * MARGIN
    scale = target_h / im.height
    target_w = int(round(im.width * scale))
    # if too wide, constrain by width instead
    if target_w > CW - 2 * MARGIN:
        scale = (CW - 2 * MARGIN) / im.width
        target_w = CW - 2 * MARGIN
        target_h = int(round(im.height * scale))
    im = im.resize((target_w, target_h), Image.LANCZOS)
    canvas = Image.new("RGB", (CW, CH), BG)
    canvas.paste(im, ((CW - target_w) // 2, (CH - target_h) // 2))
    canvas.save(OUT / f"c{i:04d}.png")

print(f"composited {len(SRC)} frames at {CW}x{CH}")
