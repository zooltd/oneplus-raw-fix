# fix-dng-aspect

Fix OnePlus (and similar phone) DNG raw files that appear **horizontally stretched** when opened in Lightroom, RawTherapee, Windows Photos, or any other raw editor.

## The Problem

OnePlus phones (and potentially others) write DNG files where the `DefaultScale` tag is incorrectly set to `1.0 × 1.0` (square pixels), even though the sensor readout uses non-square pixels. This causes every DNG-aware application to render the image at the wrong aspect ratio — typically around **2.2:1 instead of 4:3** — making subjects look unnaturally wide and squished.

The embedded JPEG preview inside the DNG is unaffected, so the image looks correct for the first second while the preview loads, then snaps to the stretched version once the raw data finishes decoding.

## The Fix

The script patches a single metadata tag (`DefaultScale`, tag `0xC61E`) in the DNG file, setting the vertical scale factor so the rendered output matches a correct 4:3 aspect ratio. No pixel data is modified — it is a metadata-only change of 8 bytes.

Before → After:

| | Raw pixels | Rendered |
|---|---|---|
| **Before** | 4096 × 1864 | 4096 × 1864 (2.2:1, stretched) |
| **After** | 4096 × 1864 | 4096 × 3072 (4:3, correct) |

## Requirements

- Python 3.7+
- [tifffile](https://pypi.org/project/tifffile/)

```bash
pip install tifffile
```

## Usage

```bash
# Output saved as <original>_4x3.dng next to the source file
python fix_dng_aspect.py photo.dng

# Or specify an output path
python fix_dng_aspect.py photo.dng fixed_photo.dng
```

### Example output

```
Source:         IMG20250524142353.dng
Raw dimensions: 4096 x 1864  (ratio 2.1974)
DefaultScale:   H=1.0000  V=1.0000

Target DefaultScale V: 1.648069  →  384/233 = 1.648069
Rendered size will be: 4096 x 3072  (ratio 1.3333)

Written: IMG20250524142353_4x3.dng
DefaultScale V confirmed: 1.648069
```

## Tested with

- OnePlus 12 (CPH2583)
- Lightroom, RawTherapee, Windows Photos, Gwenview

## Notes

- The script only modifies the `DefaultScale` TIFF tag. All raw pixel data, color profiles, lens corrections, and EXIF metadata are preserved.
- If the file already has a 4:3 aspect ratio, the script exits without making any changes.
- The fix applies to any DNG where `DefaultScale` is incorrectly set to `1.0` — not limited to OnePlus devices.
