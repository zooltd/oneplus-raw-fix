#!/usr/bin/env python3
"""Fix horizontally stretched DNG files from OnePlus 12/13 (and similar phones).

Patches the DefaultScale metadata tag so DNG-compliant software renders
the image at the correct 4:3 aspect ratio. No pixel data is modified.

See: https://community.adobe.com/bug-reports-679/p-oneplus13-and-oneplus12-raw-photos-are-stretched-662257
"""

import argparse
import glob
import os
import re
import shutil
import struct
import sys
from fractions import Fraction

try:
    import tifffile
except ImportError:
    sys.exit("Error: missing dependency 'tifffile'. Install with: pip install tifffile")

TARGET_RATIO = Fraction(4, 3)
DEFAULT_SCALE_TAG = 50718  # TIFF tag 0xC61E
MIN_ANDROID_VERSION = 15


def parse_android_version(software):
    """Extract the Android major version from the Software tag if present."""
    if not software:
        return None
    match = re.search(r"/[^/]+:(\d+)/", software)
    if match:
        return int(match.group(1))
    return None


def detect_byte_order(path):
    """Return '<' for little-endian (II) or '>' for big-endian (MM) TIFF."""
    with open(path, "rb") as f:
        magic = f.read(2)
    if magic == b"II":
        return "<"
    if magic == b"MM":
        return ">"
    raise ValueError(f"Not a TIFF/DNG file: {path}")


def get_dng_info(path):
    """Read DefaultScale and raw dimensions from a DNG file.

    Returns (scale_h, scale_v, valueoffset, raw_width, raw_height, make, software).
    Raises ValueError if the file lacks the expected DNG tags.
    """
    with tifffile.TiffFile(path) as tif:
        ifd0 = tif.pages[0]
        tag = ifd0.tags.get(DEFAULT_SCALE_TAG)
        if tag is None:
            raise ValueError("No DefaultScale tag — not a valid DNG file")
        v = tag.value  # (num_h, den_h, num_v, den_v)
        scale_h = Fraction(int(v[0]), int(v[1]))
        scale_v = Fraction(int(v[2]), int(v[3]))
        make = ifd0.tags.get(271)
        software = ifd0.tags.get(305)
        make_value = make.value if make else None
        software_value = software.value if software else None

        # Raw dimensions live in a SubIFD (raw CFA), not the IFD0 thumbnail.
        raw_w = raw_h = None
        for sub in ifd0.pages or []:
            bps = sub.tags.get(258)  # BitsPerSample
            if bps is None:
                continue
            val = bps.value
            depth = val[0] if isinstance(val, tuple) else val
            if depth == 16:
                raw_w = sub.tags[256].value
                raw_h = sub.tags[257].value
                break

        # Fall back to IFD0 (some DNGs store raw data directly there)
        if raw_w is None:
            raw_w = ifd0.tags[256].value
            raw_h = ifd0.tags[257].value

    return (
        scale_h,
        scale_v,
        tag.valueoffset,
        raw_w,
        raw_h,
        make_value,
        software_value,
    )


def fix_file(src, dst, target=TARGET_RATIO):
    """Patch DefaultScale in a single DNG file.

    Returns "fixed", "already-correct", or "unsupported-build".
    """
    byte_order = detect_byte_order(src)
    scale_h, scale_v, offset, raw_w, raw_h, make, software = get_dng_info(src)
    pixel_ratio = Fraction(raw_w, raw_h)

    # Already correct — either pixels are 4:3 or DefaultScale already compensates
    rendered_ratio = pixel_ratio * scale_h / scale_v
    if rendered_ratio == target:
        return "already-correct"

    android_version = parse_android_version(software)
    if make != "OnePlus" or android_version is None or android_version < MIN_ANDROID_VERSION:
        return "unsupported-build"

    new_scale_v = pixel_ratio / target * scale_h
    frac = Fraction(new_scale_v).limit_denominator(10000)

    if src != dst:
        shutil.copy2(src, dst)

    fmt = f"{byte_order}IIII"
    with open(dst, "r+b") as f:
        f.seek(offset)
        f.write(struct.pack(
            fmt,
            scale_h.numerator,
            scale_h.denominator,
            frac.numerator,
            frac.denominator,
        ))
    return "fixed"


def main():
    parser = argparse.ArgumentParser(
        description="Fix horizontally stretched DNG files from OnePlus phones.",
        epilog="Examples:\n"
               "  %(prog)s IMG_001.dng\n"
               "  %(prog)s *.dng --in-place\n"
               "  %(prog)s photos/*.dng -o fixed/\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files", nargs="+", metavar="FILE",
        help="one or more .dng files (globs are expanded on Windows)",
    )
    parser.add_argument(
        "-o", "--output-dir", metavar="DIR",
        help="write fixed files to DIR (created if needed)",
    )
    parser.add_argument(
        "-i", "--in-place", action="store_true",
        help="overwrite input files instead of creating *_4x3.dng copies",
    )
    args = parser.parse_args()

    if args.in_place and args.output_dir:
        parser.error("--in-place and --output-dir are mutually exclusive")

    # Expand globs (Windows cmd.exe doesn't expand them automatically)
    paths = []
    for pattern in args.files:
        expanded = glob.glob(pattern)
        if expanded:
            paths.extend(expanded)
        else:
            paths.append(pattern)  # let it fail with "file not found" later

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    fixed = 0
    skipped = 0
    unsupported = 0
    errors = 0
    for src in paths:
        if not os.path.isfile(src):
            print(f"ERROR   {src}: file not found", file=sys.stderr)
            errors += 1
            continue

        if args.in_place:
            dst = src
        elif args.output_dir:
            dst = os.path.join(args.output_dir, os.path.basename(src))
        else:
            base, ext = os.path.splitext(src)
            dst = f"{base}_4x3{ext}"

        try:
            result = fix_file(src, dst)
            if result == "fixed":
                fixed += 1
                if dst == src:
                    print(f"FIXED   {src}")
                else:
                    print(f"FIXED   {src} -> {dst}")
            elif result == "already-correct":
                skipped += 1
                print(f"SKIPPED {src} (already correct)")
            else:
                unsupported += 1
                print(
                    f"SKIPPED {src} "
                    f"(not a newer affected OnePlus build; default behavior only fixes Android {MIN_ANDROID_VERSION}+ captures)"
                )
        except (ValueError, OSError) as e:
            print(f"ERROR   {src}: {e}", file=sys.stderr)
            errors += 1

    if len(paths) > 1:
        print(
            f"\nSummary: {fixed} fixed, {skipped} already-correct, "
            f"{unsupported} unsupported-build, {errors} errors"
        )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
