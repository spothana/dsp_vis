"""
Render sweep frames from dwt-simulator.html.

The DWT simulator is driven by clicking its segmented buttons and dispatching
input events on its sliders. This script does that programmatically (a real
headless browser, no visible window), screenshots after each step, and writes
PNG frames. Configure what to render in SEGMENTS below.
"""

import pathlib
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Each segment is one animation pass. Pick a fixed setup (signal / wavelet /
# levels / noise) and ONE thing to sweep. Segments render in order into the
# same frames/ folder, so a single MP4 can walk through several passes.
#
# signal : 'blocks' | 'chirp' | 'bumps' | 'ecg'
# wavelet: 'haar'   | 'db4'
# levels : 1..5
# noise  : 0..100   (percent; the slider's raw value)
#
# sweep  : what to animate across the pass. One of:
#            'threshold' -> denoise threshold 0 -> sweep_to     (melt noise away)
#            'levels'    -> level count 1 -> sweep_to           (deepen the pyramid)
#            'noise'     -> noise 0 -> sweep_to                 (add noise gradually)
#          'sweep_to' is the end value; the start is the natural minimum.

SEGMENTS = [
    # Pass 1: bumps signal, 4-level Haar, sweep the denoise threshold up.
    {"signal": "bumps", "wavelet": "haar", "levels": 4, "noise": 35,
     "sweep": "threshold", "sweep_to": 80},

    # Pass 2: blocks signal, Haar, sweep the pyramid depth 1 -> 5.
    {"signal": "blocks", "wavelet": "haar", "levels": 1, "noise": 0,
     "sweep": "levels", "sweep_to": 5},
]

# For a single pass, use a one-entry list, e.g.:
#   SEGMENTS = [{"signal":"ecg","wavelet":"haar","levels":4,"noise":40,
#                "sweep":"threshold","sweep_to":70}]

STEPS = 40                       # frames in the swept portion of each segment
HOLD_START, HOLD_END = 6, 12     # extra still frames at each end
SCALE = 2                        # device scale factor -> crisper pixels
STEP_WAIT_MS = 70                # settle time after each change before screenshot

# ---------------------------------------------------------------------------

HTML = pathlib.Path("dwt-simulator.html").resolve().as_uri()
OUT = pathlib.Path("frames")
OUT.mkdir(exist_ok=True)
for old in OUT.glob("f*.png"):
    old.unlink()

VALID_SIGNAL = {"blocks", "chirp", "bumps", "ecg"}
VALID_WAVELET = {"haar", "db4"}
VALID_SWEEP = {"threshold", "levels", "noise"}


def validate(seg):
    if seg.get("signal") not in VALID_SIGNAL:
        raise ValueError(f"{seg}: signal must be one of {sorted(VALID_SIGNAL)}")
    if seg.get("wavelet") not in VALID_WAVELET:
        raise ValueError(f"{seg}: wavelet must be one of {sorted(VALID_WAVELET)}")
    if not (1 <= seg.get("levels", 0) <= 5):
        raise ValueError(f"{seg}: levels must be 1..5")
    if not (0 <= seg.get("noise", -1) <= 100):
        raise ValueError(f"{seg}: noise must be 0..100")
    if seg.get("sweep") not in VALID_SWEEP:
        raise ValueError(f"{seg}: sweep must be one of {sorted(VALID_SWEEP)}")


for s in SEGMENTS:
    validate(s)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1160, "height": 1700},
        device_scale_factor=SCALE,
        color_scheme="dark",
    )
    page.goto(HTML)
    page.wait_for_selector("#decomp-stage svg")
    page.wait_for_timeout(400)

    frame = 0

    def shot():
        global frame
        # full-page screenshot of the dark .wrap container
        page.locator(".wrap").screenshot(path=str(OUT / f"f{frame:04d}.png"))
        frame += 1

    def click_seg(seg_id, value):
        page.click(f"#{seg_id} button[data-v='{value}']")
        page.wait_for_timeout(60)

    def set_slider(slider_id, value):
        page.eval_on_selector(
            f"#{slider_id}",
            "(el,v)=>{el.value=v;el.dispatchEvent(new Event('input'));}",
            value)
        page.wait_for_timeout(60)

    for seg in SEGMENTS:
        # apply the fixed setup
        click_seg("seg-signal", seg["signal"])
        click_seg("seg-wavelet", seg["wavelet"])
        click_seg("seg-levels", str(seg["levels"]))
        set_slider("noise", seg["noise"])
        set_slider("thr", 0)
        page.wait_for_timeout(200)

        sweep = seg["sweep"]
        print(f"  segment: {seg['signal']}/{seg['wavelet']} "
              f"L{seg['levels']} noise{seg['noise']} -- sweeping {sweep}")

        # establish the sweep start, hold
        if sweep == "threshold":
            set_slider("thr", 0)
        elif sweep == "noise":
            set_slider("noise", 0)
        elif sweep == "levels":
            click_seg("seg-levels", "1")
        page.wait_for_timeout(150)
        for _ in range(HOLD_START):
            shot()

        # the swept portion
        if sweep == "levels":
            for lvl in range(1, seg["sweep_to"] + 1):
                click_seg("seg-levels", str(lvl))
                page.wait_for_timeout(STEP_WAIT_MS)
                # hold a few frames per level so each is readable
                for _ in range(6):
                    shot()
        else:
            slider = "thr" if sweep == "threshold" else "noise"
            for i in range(STEPS + 1):
                val = round(seg["sweep_to"] * i / STEPS)
                set_slider(slider, val)
                page.wait_for_timeout(STEP_WAIT_MS)
                shot()

        for _ in range(HOLD_END):
            shot()

    browser.close()

print(f"rendered {frame} frames into {OUT}/ across {len(SEGMENTS)} segment(s)")
if frame:
    from PIL import Image
    im = Image.open(sorted(OUT.glob("f*.png"))[0])
    print(f"frame size: {im.size[0]}x{im.size[1]} px")
