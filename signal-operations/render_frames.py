"""
Render sweep frames from signal-operations.html.

The widget exposes its controls as global JS functions:
    setMode(m)   m = 'conv' | 'xcorr' | 'acorr'
    setData(d)   d = 'fir'  | 'match' | 'noise'
    setEdge(e)   e = 'zero' | 'circ'
    onShift(k)   k = integer shift

This script drives those directly (it never clicks the buttons), screenshots
each shift, and writes PNG frames. Configure what to render in SEGMENTS below.
"""

import pathlib
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Each segment is one continuous sweep with a chosen mode / signal / edge.
# List as many as you want; they render in order into the same frames/ folder,
# so a single MP4 can walk through several configurations.
#
# mode  : 'conv'  (convolution) | 'xcorr' (cross-correlation) | 'acorr' (auto-correlation)
# signal: 'fir'   (FIR filter)  | 'match' (template)          | 'noise' (in noise)
# edge  : 'zero'  (zero-pad)    | 'circ'  (circular)
#
# Note: in 'acorr' mode the widget sets h = x, so 'signal' still picks which
# signal is auto-correlated, but 'edge' still applies.

SEGMENTS = [
    {"mode": "conv",  "signal": "fir",   "edge": "zero"},
    {"mode": "xcorr", "signal": "match", "edge": "zero"},
    {"mode": "acorr", "signal": "noise", "edge": "zero"},
]

# To render just ONE configuration, replace SEGMENTS with a single entry, e.g.:
#   SEGMENTS = [{"mode": "conv", "signal": "noise", "edge": "circ"}]

K_MIN, K_MAX = -12, 24          # shift range swept in each segment
HOLD_START, HOLD_END = 6, 10    # extra still frames at each end of a segment
SCALE = 3                       # device scale factor -> crisper pixels
STEP_WAIT_MS = 90               # settle time after each shift before screenshot

# ---------------------------------------------------------------------------

HTML = pathlib.Path("signal-operations.html").resolve().as_uri()
OUT = pathlib.Path("frames")
OUT.mkdir(exist_ok=True)
for old in OUT.glob("f*.png"):   # clear stale frames from a previous run
    old.unlink()

MODE_NAMES = {"conv": "convolution", "xcorr": "cross-correlation",
              "acorr": "auto-correlation"}
SIGNAL_NAMES = {"fir": "FIR filter", "match": "template", "noise": "in noise"}
EDGE_NAMES = {"zero": "zero-pad", "circ": "circular"}

VALID = {"mode": MODE_NAMES, "signal": SIGNAL_NAMES, "edge": EDGE_NAMES}


def validate(seg):
    for key, table in VALID.items():
        if seg.get(key) not in table:
            raise ValueError(
                f"segment {seg}: '{key}' must be one of {list(table)}, "
                f"got {seg.get(key)!r}")


for s in SEGMENTS:
    validate(s)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 760, "height": 1100},
        device_scale_factor=SCALE,
        color_scheme="light",
    )
    page.goto(HTML)
    page.wait_for_selector("#widget-root")
    page.evaluate("document.body.style.background='#ffffff';"
                  "document.getElementById('widget-root').style.background='#ffffff';")
    page.wait_for_timeout(300)

    # measure the content region once (layout height does not change with shift)
    bbox = page.evaluate("""() => {
      const r = document.getElementById('widget-root');
      const note = document.getElementById('window-note');
      const top = r.getBoundingClientRect().top;
      const bottom = note.getBoundingClientRect().bottom;
      const rect = r.getBoundingClientRect();
      return {x: rect.x, y: top, w: rect.width, h: bottom - top + 24};
    }""")

    frame = 0

    def shot():
        global frame
        page.screenshot(path=str(OUT / f"f{frame:04d}.png"),
                        clip={"x": bbox["x"], "y": bbox["y"],
                              "width": bbox["w"], "height": bbox["h"]})
        frame += 1

    def set_shift(k):
        # move the visible slider thumb AND drive the widget
        page.evaluate(f"document.getElementById('shift').value={k};"
                      f"window.onShift({k});")

    for seg in SEGMENTS:
        # select mode / signal / edge via the widget's own functions.
        # order matters: setMode reads the current signal, so set signal first
        # when entering acorr; calling all three is safe and idempotent.
        page.evaluate(f"window.setData('{seg['signal']}')")
        page.evaluate(f"window.setMode('{seg['mode']}')")
        page.evaluate(f"window.setData('{seg['signal']}')")
        page.evaluate(f"window.setEdge('{seg['edge']}')")
        page.wait_for_timeout(150)

        label = (f"{MODE_NAMES[seg['mode']]} / {SIGNAL_NAMES[seg['signal']]} "
                 f"/ {EDGE_NAMES[seg['edge']]}")
        print(f"  segment: {label}")

        set_shift(K_MIN)
        page.wait_for_timeout(120)
        for _ in range(HOLD_START):
            shot()

        for k in range(K_MIN, K_MAX + 1):
            set_shift(k)
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
