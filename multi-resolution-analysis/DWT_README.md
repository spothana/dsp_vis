# Discrete Wavelet Transform — Interactive Simulator

An interactive explainer for the Discrete Wavelet Transform (DWT). Run the
Mallat pyramid level by level — each stage splits a signal into a smooth
**approximation** and a fine **detail** band — then threshold the detail
coefficients to denoise and reconstruct. Built as a single self-contained HTML
file, with an optional pipeline to render sweep animations as a 4K MP4.

## Contents

| File | What it is |
|------|-----------|
| `dwt-simulator.html` | The interactive simulator. Open it in a browser — nothing to build. |
| `dwt_render_frames.py` | Captures animation frames from the simulator. |
| `dwt_compose.py` | Composites the captured frames onto a 3840×2160 canvas. |
| `dwt-simulator-4k.mp4` | Pre-rendered 4K video (threshold sweep + level sweep). |

## Part 1 — Running the interactive simulator

No installation, no build step, no server.

1. Download `dwt-simulator.html`.
2. Double-click it, or open it in any modern browser.

The only network request is for a display font; if offline, it falls back to a
system serif and everything else works unchanged.

### Using it

- **Signal** — four presets: Blocks, Chirp, Bumps + noise, ECG-like.
- **Wavelet** — Haar (piecewise-constant, sharp on edges) or Daubechies-4
  (smoother, better on gradual signals). Defaults to Haar.
- **Levels (J)** — how many times the pyramid recurses, 1 to 5.
- **Denoise threshold** — soft-thresholds the detail coefficients: small ones
  are zeroed, the rest shrunk. Reconstruction follows via the inverse DWT.
- **Noise on signal** — how much noise is mixed into the input.
- **New noise** — reseeds the random noise.

With the threshold at zero the reconstruction is exact to machine precision —
orthonormal filters guarantee perfect reconstruction.

## Part 2 — Rendering sweep animations as a 4K MP4

This pipeline drives the simulator's controls programmatically — clicking its
buttons and moving its sliders inside a headless browser — screenshots each
step, and encodes the result. It is deterministic: no cursor, no window
chrome, identical every run.

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

The second command downloads a private copy of Chromium that Playwright
drives; it does not affect any browser already installed.

### Choosing what to render

Open `dwt_render_frames.py` and edit the `SEGMENTS` list near the top. Each
entry is one animation pass: a fixed setup plus ONE thing to sweep.

```python
SEGMENTS = [
    {"signal": "bumps", "wavelet": "haar", "levels": 4, "noise": 35,
     "sweep": "threshold", "sweep_to": 80},
    {"signal": "blocks", "wavelet": "haar", "levels": 1, "noise": 0,
     "sweep": "levels", "sweep_to": 5},
]
```

Segments render in order into the same `frames/` folder, so one MP4 can walk
through several passes. For a single pass, use a one-entry list.

Allowed values:

| Field | Values | Meaning |
|-------|--------|---------|
| `signal` | `blocks` `chirp` `bumps` `ecg` | which input signal |
| `wavelet` | `haar` `db4` | Haar or Daubechies-4 |
| `levels` | `1`–`5` | pyramid depth (fixed setup value) |
| `noise` | `0`–`100` | noise slider value, percent |
| `sweep` | `threshold` | animate the denoise threshold 0 → `sweep_to` |
| | `levels` | animate pyramid depth 1 → `sweep_to` |
| | `noise` | animate noise 0 → `sweep_to` |
| `sweep_to` | end value | where the swept control finishes |

The most illustrative pass is `sweep: "threshold"` on a noisy signal — the
reconstruction visibly sheds its noise as the threshold rises.

Invalid values are caught with a clear error before any rendering starts.

### Run the pipeline

Run all commands from the folder that contains `dwt-simulator.html`.

```bash
python dwt_render_frames.py     # writes PNG frames into ./frames/
python dwt_compose.py           # writes 4K frames into ./canvas4k/
ffmpeg -y -framerate 12 -i canvas4k/c%04d.png \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 16 \
  -r 30 -movflags +faststart dwt-simulator-4k.mp4
```

The result is `dwt-simulator-4k.mp4`: 3840×2160, H.264, 30 fps, silent —
ready to drop into a 4K editing timeline for audio.

`dwt_render_frames.py` clears stale frames automatically, so you can re-edit
`SEGMENTS` and re-run without cleaning up by hand.

### Tuning

**Sweep speed** — the `-framerate` value sets how many source frames play per
second. Lower it for a slower animation:

| `-framerate` | Feel |
|--------------|------|
| 12 | default |
| 6 | calm, room to narrate |
| 24 | quick montage |

**Frames and holds** — in `dwt_render_frames.py`:
- `STEPS` — number of frames in the swept portion of a `threshold`/`noise` pass.
- `HOLD_START`, `HOLD_END` — extra still frames at each end of a segment.
- `STEP_WAIT_MS` — settle time after each control change before the screenshot.
- `SCALE` — Chromium device scale factor; higher = crisper pixels, larger PNGs.

**Canvas** — in `dwt_compose.py`:
- `MARGIN` — vertical breathing room around the simulator.
- `BG` — canvas background `(R, G, B)`; default matches the dark theme.

**Encoding quality** — in the ffmpeg command, `-crf` controls quality: lower is
better (16 is high quality; 0 is lossless and very large; 23 is the default).

## Troubleshooting

**`ffmpeg: command not found`** — install ffmpeg (see Prerequisites) and
re-open your terminal.

**Playwright cannot find a browser** — run `python -m playwright install
chromium` once after installing the `playwright` package.

**Frames look wrong or clipped** — delete the `frames/` and `canvas4k/`
folders and re-run both scripts from scratch.

**A `levels` sweep looks jumpy** — that is expected; level count is discrete,
so the pyramid depth steps rather than glides. Each level is held for several
frames so it stays readable.

## Notes on the math

- The transform uses periodic boundary handling and orthonormal filters, so
  with a zero threshold the reconstruction is exact to machine precision.
- The output coefficients `{A_J, D_J, …, D1}` total the same length as the
  input — the DWT reorganizes the signal across scales, it does not add data.
- Soft thresholding zeros detail coefficients below the threshold and shrinks
  the rest. Raising it improves denoising up to a point; pushed too far it
  erodes the signal itself — the SNR readout rises, then falls.
