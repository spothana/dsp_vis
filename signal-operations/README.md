# Convolution & Correlation Explorer

An interactive explainer for the two core DSP signal operations — convolution
and correlation. Drag a shift slider to slide one signal over another and watch
the product terms, the running sum, and the full output sequence update in real
time. Built as a single self-contained HTML file, with an optional pipeline to
render the sweep animation as a 4K MP4.

## Contents

| File | What it is |
|------|-----------|
| `signal-operations.html` | The interactive widget. Open it in a browser — nothing to build. |
| `render_frames.py` | Captures each frame of the sweep animation from the HTML. |
| `compose.py` | Composites the captured frames onto a 3840×2160 canvas. |
| `signal-operations-4k.mp4` | Pre-rendered 4K video of one convolution sweep (silent). |

## Part 1 — Running the interactive widget

No installation, no build step, no server.

1. Download `signal-operations.html`.
2. Double-click it, or open it in any modern browser (Chrome, Firefox, Safari, Edge).

The only thing it fetches from the network is the play/pause icon font (from a
CDN). Everything else — the math, the sample arrays, the slider, the output
curve — works fully offline.

### Using it

- **Mode buttons** — switch between Convolution, Cross-correlation, and
  Auto-correlation. The only real difference is whether the kernel is flipped.
- **Shift k slider** — slides the kernel over the signal. The highlighted cells
  in the `x[n]` and `h[n]` arrays show exactly which samples enter the sum.
- **Sweep** — auto-advances the shift through the full range.
- **Signals** — three preset signal pairs (FIR filter, Template, In noise).
- **Edges** — zero-pad (linear convolution) vs circular (modulo wrap-around,
  what a raw FFT-based convolution computes).

## Part 2 — Rendering the sweep as a 4K MP4

This pipeline drives the widget's own `onShift(k)` function frame by frame,
screenshots each step, and encodes the result. It is deterministic — no cursor,
no window chrome, identical every run.

### Prerequisites

- **Python 3.8+**
- **ffmpeg** on your PATH — verify with `ffmpeg -version`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from ffmpeg.org, or `winget install ffmpeg`

### Install the Python dependencies

```bash
pip install playwright pillow
python -m playwright install chromium
```

Tested with `playwright` 1.56 and a recent `pillow`. The second command
downloads a private copy of Chromium that Playwright drives — this does not
affect any browser already installed on your machine.

### Choosing what to render

Open `render_frames.py` and edit the `SEGMENTS` list near the top. Each entry
is one continuous sweep with a chosen operation, signal, and edge mode:

```python
SEGMENTS = [
    {"mode": "conv",  "signal": "fir",   "edge": "zero"},
    {"mode": "xcorr", "signal": "match", "edge": "zero"},
    {"mode": "acorr", "signal": "noise", "edge": "zero"},
]
```

Segments render in order into the same `frames/` folder, so a single MP4 can
walk through several configurations back to back. For just one configuration,
use a single-entry list:

```python
SEGMENTS = [{"mode": "conv", "signal": "noise", "edge": "circ"}]
```

Allowed values for each field:

| Field | Values | Meaning |
|-------|--------|---------|
| `mode` | `conv` | Convolution |
| | `xcorr` | Cross-correlation |
| | `acorr` | Auto-correlation (the widget sets h = x) |
| `signal` | `fir` | FIR filter preset |
| | `match` | Template preset |
| | `noise` | In-noise preset |
| `edge` | `zero` | Zero-pad (linear convolution) |
| | `circ` | Circular (modulo wrap-around) |

Invalid values are caught with a clear error before any rendering starts.

### Run the pipeline

Run all commands from the folder that contains `signal-operations.html`.

```bash
python render_frames.py        # writes PNG frames into ./frames/
python compose.py              # writes 4K frames into ./canvas4k/
ffmpeg -y -framerate 6 -i canvas4k/c%04d.png \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 16 \
  -r 30 -movflags +faststart signal-operations-4k.mp4

  ffmpeg -y -framerate 0.1 -i canvas4k/c%04d.png \
  -c:v h264_nvenc -profile:v high -pix_fmt yuv420p -crf 16 \
  -r 30 -movflags +faststart signal-operations-4k.mp4
  #h264_nvenc
```

`render_frames.py` clears stale frames from any previous run automatically, so
you can re-edit `SEGMENTS` and re-run without cleaning up by hand.

The result is `signal-operations-4k.mp4`: 3840×2160, H.264, 30 fps, silent —
ready to drop into a 4K editing timeline for audio.

### Tuning

**Sweep speed.** The `-framerate` value in the ffmpeg command sets how many
source frames play per second. Lower it for a slower sweep:

| `-framerate` | Approx. duration | Good for |
|--------------|------------------|----------|
| 6 | ~9 s | default |
| 3–4 | ~15–18 s | narrating each shift |
| 12 | ~4 s | quick montage |

**Segments, shift range, and holds** — in `render_frames.py`:
- `SEGMENTS` — the list of operation / signal / edge configurations to render.
- `K_MIN`, `K_MAX` — the range of shifts swept in each segment.
- `HOLD_START`, `HOLD_END` — extra still frames held at each end of a segment.
- `STEP_WAIT_MS` — settle time after each shift before the screenshot.
- `SCALE` — Chromium device scale factor; higher = crisper pixels, larger PNGs.

**Canvas padding and background** — in `compose.py`:
- `MARGIN` — vertical breathing room around the widget.
- `BG` — canvas background color as an `(R, G, B)` tuple.

**Encoding quality** — in the ffmpeg command, `-crf` controls quality: lower is
better (16 is high quality; 0 is lossless and very large; 23 is the default).

## Troubleshooting

**`ffmpeg: command not found`** — ffmpeg is not installed or not on your PATH.
Install it (see Prerequisites) and re-open your terminal.

**Playwright cannot find a browser** — run `python -m playwright install chromium`
again; it must be run once after installing the `playwright` package.

**The slider icon (play/pause) is blank** — the icon font failed to load from the
CDN. The widget still works; only the glyph is missing. An internet connection
on first open fixes it.

**Frames look wrong or clipped** — delete the `frames/` and `canvas4k/` folders
and re-run `render_frames.py` then `compose.py` from scratch.

## Notes on the math

- The widget computes the output over the **full index range**, not just the
  13 visible sample slots. Terms from samples outside the window are still
  summed; they are marked with ◀ / ▶ indicators.
- Linear convolution of two length-N signals produces 2N−1 nonzero output
  values — which is why the output curve extends past the input window.
- The FFT-based convolution path produces the same numbers as the direct sum;
  it is a speed optimization, not a different result. The circular edge mode is
  the honest stand-in for the wrap-around behavior an unpadded FFT exhibits.
