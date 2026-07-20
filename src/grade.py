#!/usr/bin/env python3
import os
import sys

import time
import argparse
from processor import process_image

# Safely import and register pillow-heif for optional HEIC/HEIF support
try:
    # pyrefly: ignore [missing-import]
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False

def resolve_lut_path(style: str) -> str:
    """
    Resolves a style name (e.g., 'kodak_gold') to the actual .cube filepath.
    Looks in current working directory and relative to script file directory.
    """
    if not style:
        return None

    # Append extension if not already present
    filename = style if style.lower().endswith(".cube") else f"{style}.cube"

    # Search location 1: luts/ relative to the current working directory
    cwd_lut = os.path.join("luts", filename)
    if os.path.exists(cwd_lut):
        return os.path.abspath(cwd_lut)

    # Search location 2: luts/ relative to the src/ folder location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    relative_lut = os.path.join(script_dir, "..", "luts", filename)
    if os.path.exists(relative_lut):
        return os.path.abspath(relative_lut)

    # Check if the style is a direct path to a file
    if os.path.exists(style):
        return os.path.abspath(style)

    # Return standard path for error reporting
    return os.path.abspath(cwd_lut)


def main():
    parser = argparse.ArgumentParser(
        description="Batch process digital photos to emulate analog film stocks using 3D LUTs and grain."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Start the interactive Web GUI for real-time photo editing."
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Name of the film stock style LUT (e.g., 'kodak_gold' maps to 'luts/kodak_gold.cube')."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=False,
        help="Path to the input directory containing raw/original JPEG/HEIC images."
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to the output directory where processed images will be stored."
    )
    parser.add_argument(
        "--grain",
        type=float,
        default=0.0,
        help="Optional noise level for synthetic grain (float, e.g. 0.15 for medium film grain)."
    )
    parser.add_argument(
        "--blend",
        type=float,
        default=1.0,
        help="LUT blend strength/opacity (float between 0.0 and 1.0, default 1.0)."
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=0.0,
        help="Exposure/brightness adjustment (float between -1.0 and 1.0, default 0.0)."
    )
    parser.add_argument(
        "--contrast",
        type=float,
        default=0.0,
        help="Contrast adjustment (float between -1.0 and 1.0, default 0.0)."
    )
    parser.add_argument(
        "--saturation",
        type=float,
        default=0.0,
        help="Saturation/color adjustment (float between -1.0 and 1.0, default 0.0)."
    )


    args = parser.parse_args()

    # If GUI is requested, launch the FastAPI server using Uvicorn
    if args.gui:
        import uvicorn
        # Ensure the script directory is in the path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from server import app
        print("=" * 60)
        print("Starting Interactive Film Emulator GUI...")
        print("Open your browser and navigate to: http://127.0.0.1:8000")
        print("=" * 60)
        uvicorn.run(app, host="127.0.0.1", port=8000)
        sys.exit(0)


    # Validate input/output parameters when running in standard CLI mode
    if not args.input or not args.output:
        parser.error("the following arguments are required when not running in GUI mode: --input, --output")

    # 1. Validate Input Directory
    if not os.path.isdir(args.input):
        print(f"Error: Input directory does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 2. Resolve LUT path if style is specified
    lut_path = None
    if args.style:
        resolved_lut = resolve_lut_path(args.style)
        if not os.path.exists(resolved_lut):
            print(f"Error: LUT file not found at: {resolved_lut}", file=sys.stderr)
            print("Please ensure the .cube file exists in the 'luts/' directory.", file=sys.stderr)
            sys.exit(1)
        lut_path = resolved_lut
        print(f"[INFO] Using 3D LUT style: {args.style} ({lut_path})")
    else:
        print("[INFO] No style specified. Processing without LUT color mapping.")

    # 3. Locate files to process
    valid_extensions = (".jpg", ".jpeg", ".heic", ".heif") if HAS_HEIF else (".jpg", ".jpeg")
    all_files = os.listdir(args.input)
    images_to_process = [
        f for f in all_files 
        if f.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(args.input, f))
    ]

    if not images_to_process:
        ext_desc = ".jpg, .jpeg, .heic, .heif" if HAS_HEIF else ".jpg, .jpeg"
        print(f"[INFO] No images ({ext_desc}) found in input directory: {args.input}")
        if not HAS_HEIF:
            print("[INFO] Install 'pillow-heif' to enable processing of HEIC/HEIF images.")
        sys.exit(0)

    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)

    print(f"[INFO] Found {len(images_to_process)} image(s) to process. Starting batch run...")
    start_time = time.time()
    success_count = 0
    failure_count = 0

    for i, filename in enumerate(images_to_process, 1):
        in_file_path = os.path.join(args.input, filename)
        out_file_path = os.path.join(args.output, filename)

        print(f"[{i}/{len(images_to_process)}] Processing: {filename}...", end="", flush=True)
        try:
            item_start = time.time()
            process_image(
                input_path=in_file_path,
                output_path=out_file_path,
                lut_path=lut_path,
                lut_blend=args.blend,
                grain_intensity=args.grain,
                target_size=2000,
                brightness=args.brightness,
                contrast=args.contrast,
                saturation=args.saturation
            )

            item_elapsed = time.time() - item_start
            print(f" Success ({item_elapsed:.2f}s)")
            success_count += 1
        except Exception as e:
            print(" Failed!")
            print(f"  [ERROR] {str(e)}", file=sys.stderr)
            failure_count += 1

    total_elapsed = time.time() - start_time
    print("\n" + "=" * 40)
    print("Batch processing complete.")
    print(f"  Success: {success_count}")
    print(f"  Failures: {failure_count}")
    print(f"  Time Elapsed: {total_elapsed:.2f} seconds")
    print("=" * 40)

    # Exit with code 1 if there were any failures
    if failure_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
