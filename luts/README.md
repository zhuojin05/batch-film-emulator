# 3D LUTs (Look-Up Tables) Directory

This directory holds the `.cube` files representing different analog film stock emulations.

## How to use custom LUTs:
1. Place any Adobe `.cube` format file into this directory (e.g., `kodak_portra_400.cube`).
2. Run the command-line interface, referencing the filename without its extension:
   ```bash
   python src/grade.py --style kodak_portra_400 --input ./input --output ./output
   ```

## Included styles for testing:
* `kodak_gold`: A placeholder identity 3D LUT for pipeline testing and verification.
