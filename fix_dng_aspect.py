#!/usr/bin/env python3
"""
fix_dng_aspect.py — Fix non-square pixel DNG files from OnePlus (and similar phones)
that appear horizontally stretched by correcting the DefaultScale tag.

Usage:
    python fix_dng_aspect.py <input.dng> [output.dng]

If output is omitted, saves as <input>_4x3.dng next to the source file.
"""

import struct
import shutil
import sys
import os

try:
    import tifffile
except ImportError:
    sys.exit("Missing dependency: pip install tifffile")


def get_dng_info(path):
    """Return ((scale_h, scale_v), valueoffset, raw_width, raw_height)."""
    with tifffile.TiffFile(path) as tif:
        ifd0 = tif.pages[0]
        tag = ifd0.tags.get(50718)  # DefaultScale lives in IFD0
        if tag is None:
            return None, None, None, None
        v = tag.value  # (num_h, den_h, num_v, den_v)
        scales = (v[0] / v[1], v[2] / v[3])
        valueoffset = tag.valueoffset

        # Raw dimensions are in SubIFD[1] (raw CFA), not the 1×1 IFD0 thumbnail
        subifds = ifd0.pages or []
        raw_w = raw_h = None
        for sub in subifds:
            bps = sub.tags.get(258)
            if bps and getattr(bps, "value", None) == 16:  # raw = 16-bit
                raw_w = sub.tags[256].value
                raw_h = sub.tags[257].value
                break
        # Fall back to IFD0 if no SubIFD found
        if raw_w is None:
            raw_w = ifd0.tags[256].value
            raw_h = ifd0.tags[257].value

    return scales, valueoffset, raw_w, raw_h


def compute_scale_v(raw_width, raw_height, target_ratio=(4, 3)):
    """Return the vertical scale factor that brings raw_width x raw_height to target_ratio."""
    w, h = target_ratio
    scale_v = (raw_width * h) / (raw_height * w)
    return scale_v


def patch_default_scale(src, dst, scale_v_num, scale_v_den, valueoffset):
    shutil.copy2(src, dst)
    with open(dst, "r+b") as f:
        f.seek(valueoffset)
        # Write: scaleH = 1/1, scaleV = scale_v_num/scale_v_den (little-endian uint32 pairs)
        f.write(struct.pack("<IIII", 1, 1, scale_v_num, scale_v_den))


def rational_approx(value, max_denom=10000):
    """Return (numerator, denominator) approximating value with denominator <= max_denom."""
    best_n, best_d, best_err = 1, 1, abs(value - 1)
    for d in range(1, max_denom + 1):
        n = round(value * d)
        err = abs(value - n / d)
        if err < best_err:
            best_n, best_d, best_err = n, d, err
        if err < 1e-9:
            break
    return best_n, best_d


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isfile(src):
        sys.exit(f"File not found: {src}")

    base, ext = os.path.splitext(src)
    dst = sys.argv[2] if len(sys.argv) >= 3 else f"{base}_4x3{ext}"

    # Read current DefaultScale and raw dimensions
    (scale_h, scale_v), valueoffset, raw_w, raw_h = get_dng_info(src)
    if valueoffset is None:
        sys.exit("No DefaultScale tag found — not a standard DNG file.")

    current_ratio = raw_w / raw_h
    print(f"Source:        {os.path.basename(src)}")
    print(f"Raw dimensions: {raw_w} x {raw_h}  (ratio {current_ratio:.4f})")
    print(f"DefaultScale:  H={scale_h:.4f}  V={scale_v:.4f}")

    if abs(current_ratio - 4 / 3) < 0.01:
        print("Already 4:3 — nothing to do.")
        sys.exit(0)

    target_scale_v = compute_scale_v(raw_w, raw_h, target_ratio=(4, 3))
    num, den = rational_approx(target_scale_v)
    actual = num / den

    print(f"\nTarget DefaultScale V: {target_scale_v:.6f}  →  {num}/{den} = {actual:.6f}")
    print(f"Rendered size will be: {raw_w} x {round(raw_h * actual)}  "
          f"(ratio {raw_w / (raw_h * actual):.4f})")

    patch_default_scale(src, dst, num, den, valueoffset)

    # Verify
    (_, new_scale_v), _, _, _ = get_dng_info(dst)
    print(f"\nWritten: {dst}")
    print(f"DefaultScale V confirmed: {new_scale_v:.6f}")


if __name__ == "__main__":
    main()
