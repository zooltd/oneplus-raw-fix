---
name: oneplus-raw-fix
description: Use when a user wants to find and fix horizontally stretched phone RAW or DNG files in a photos or gallery folder, especially OnePlus 12 and OnePlus 13 images that need DefaultScale metadata corrected.
---

# OnePlus RAW Fix

Use this skill to repair stretched `.dng` files in a gallery or photos folder with the `oneplus_raw_fix.py` script in this repository.

## Use this skill when

- A gallery folder contains stretched RAW or DNG photos
- OnePlus 12 or OnePlus 13 `.dng` files render at the wrong aspect ratio
- The user wants to batch-fix a folder of affected photos
- The user wants a safe output-folder workflow before overwriting originals

## Workflow

1. Read `README.md` and `oneplus_raw_fix.py` if behavior needs confirmation.
2. Identify target `.dng` files in the user-provided folder.
3. Prefer writing fixed files to a separate output directory first.
4. Use `--in-place` only when the user explicitly wants originals overwritten.
5. Report which files were fixed, skipped, or failed.

## Commands

Use the script directly:

```bash
python3 oneplus_raw_fix.py photo.dng
python3 oneplus_raw_fix.py photos/*.dng --output-dir fixed/
python3 oneplus_raw_fix.py photos/*.dng --in-place
```

If the user points to a gallery directory and wants affected DNGs located first, prefer `fd -e dng` when available. Fall back to `find` if needed.

## Defaults

- Default output is `<original>_4x3.dng` next to the source file.
- Prefer `--output-dir` for bulk runs unless the user requests in-place edits.
- Keep the fix scoped to metadata only. Do not alter pixel data or unrelated EXIF fields.

## Validation

Run lightweight checks when changing or relying on the script behavior:

```bash
python3 oneplus_raw_fix.py --help
python3 -m py_compile oneplus_raw_fix.py
```

## Avoid

- Adding extra CLI flags unless the user explicitly needs them
- Converting the tool into a larger package when the script is enough
- Using in-place edits by default for bulk gallery work
- Letting the README drift from the script behavior
