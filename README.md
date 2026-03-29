# oneplus-raw-fix

Fix horizontally stretched RAW (`.dng`) photos from OnePlus 12 and OnePlus 13 phones.

> **Reported issue:** [OnePlus 13 and OnePlus 12 RAW photos are stretched — Adobe Community](https://community.adobe.com/bug-reports-679/p-oneplus13-and-oneplus12-raw-photos-are-stretched-662257)

---

## The Problem

OnePlus 12 and OnePlus 13 users report that RAW (`.dng`) photos appear **horizontally stretched and unusable** when opened in any app outside the phone's own gallery — including Lightroom Mobile, Lightroom Desktop, Photoshop, RawTherapee, Windows Photos, and Gwenview.

JPEGs from the same phone are unaffected. The issue only occurs with RAW files shot in non-4:3 aspect ratios (16:9, 1:1, etc.).

Community findings: the phone stores the full 4:3 sensor image in the `.dng` regardless of the selected aspect ratio, but encodes the intended crop in metadata. Apps like Lightroom ignore the crop hint and squish the full 4:3 data into the selected aspect ratio instead. Photos shot in **4:3 mode are unaffected**.

---

## The Fix

The script patches a single metadata tag — `DefaultScale` (TIFF tag `0xC61E`) — in the `.dng` file. OnePlus incorrectly writes this as `1.0 × 1.0` (square pixels). Setting the vertical scale factor to the correct value tells all DNG-compliant software to render the image at the proper 4:3 aspect ratio.

**No pixel data is modified.** It is an 8-byte metadata-only change.

| | Raw pixels | Rendered |
|---|---|---|
| **Before** | 4096 × 1864 | 4096 × 1864 (2.2:1, stretched) |
| **After** | 4096 × 1864 | 4096 × 3072 (4:3, correct) |

---

## Requirements

- Python 3.7+
- [tifffile](https://pypi.org/project/tifffile/)

```bash
pip install tifffile
```

---

## Agent Skill

This repository also includes a reusable Codex-compatible skill at `skills/oneplus-raw-fix/`.

Once this repo is published on GitHub, users can install it with the skills CLI:

```bash
npx skills add <owner>/oneplus-raw-fix --skill oneplus-raw-fix
```

The skill is meant for agents helping users scan a photos or gallery folder, find affected `.dng` files, and run this fixer with either a safe output directory or `--in-place` when explicitly requested.

---

## Usage

```bash
# Output saved as <original>_4x3.dng next to the source file
python oneplus_raw_fix.py photo.dng

# Write fixed files into a directory
python oneplus_raw_fix.py photos/*.dng --output-dir fixed/

# Overwrite the originals
python oneplus_raw_fix.py photos/*.dng --in-place
```

### Example output

```
FIXED   IMG20250524142353.dng -> IMG20250524142353_4x3.dng
```

---

## Tested with

- OnePlus 12 (CPH2583)
- Lightroom, RawTherapee, Windows Photos, Gwenview

---

## Notes

- All raw pixel data, color profiles, lens corrections, and EXIF metadata are preserved.
- If the file is already correct, the script reports it as skipped and does not modify it.
- May work on other devices with the same `DefaultScale` metadata bug.
