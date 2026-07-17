# Batch Film Emulator

A modular, Dockerized command-line tool designed to emulate analog film stocks (like Kodak Gold or Portra) on digital photos. 

Instead of relying on subscription-based editing software, this tool uses Python (`Pillow` and `NumPy`) to programmatically apply `.cube` 3D Look-Up Tables (LUTs) across entire directories. It goes beyond simple color mapping by replicating physical film characteristics, including synthetic grain generation and optical softness.

## Features
* **Batch LUT Processing:** Map digital colors to specific film color spaces instantly.
* **Synthetic Grain Engine:** Procedurally generated noise blended over the image.
* **Optical Softness:** Automatic downscaling to emulate the resolution limits of lab-scanned film.
* **Fully Containerized:** Runs entirely within Docker — no local Python environment or dependency management required.

---

## Directory Structure
```
├── luts/                    # Directory for .cube files
│   └── kodak_gold.cube      # Identity test LUT
├── input/                   # Place raw JPEG images here
├── output/                  # Processed images output path
├── src/
│   ├── processor.py         # Image manipulation logic
│   └── grade.py             # CLI entrypoint
├── Dockerfile
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Getting Started

### Option A: Running with Docker (Recommended)

1. **Build the Docker Image:**
   ```bash
   docker build -t film-emulator .
   ```

2. **Run a Test Batch:**
   Create local `/input` and `/output` directories, then mount them as volumes:
   ```bash
   docker run --rm \
     -v "$(pwd)/input:/input" \
     -v "$(pwd)/output:/output" \
     -v "$(pwd)/luts:/luts" \
     film-emulator python src/grade.py \
       --style kodak_gold \
       --input /input \
       --output /output \
       --grain 0.15
   ```

### Option B: Running Locally

1. **Set Up a Virtual Environment & Install Dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the CLI Tool:**
   ```bash
   python src/grade.py --style kodak_gold --input ./input --output ./output --grain 0.15
   ```

---

## Managing 3D LUTs (Look-Up Tables)

This tool utilizes Adobe `.cube` 3D LUT files for film color grading.

1. **Add Custom LUTs:** Place your `.cube` files (e.g., `kodak_portra_400.cube`) inside the `luts/` directory.
2. **Apply Custom Styles:** Pass the filename without the `.cube` extension to the `--style` argument:
   ```bash
   python src/grade.py --style kodak_portra_400 --input ./input --output ./output
   ```

---

## Credits & Acknowledgements

Special thanks to the creators of the 3D LUT recipes used in this project:
* **lclassic_neo_gold_200.cube** (LClassic Neo Gold 200) by [u/windycitychi_](https://www.reddit.com/user/windycitychi_) on Reddit. The original recipe and discussion can be found in the [r/Lumix subreddit](https://www.reddit.com/r/Lumix/comments/18kx9on/gold_200_film_sim_w_realtime_lut_recipe_lut/).
* **rec709_fujifilm_3510_d65.cube**, **rec709_kodak_2383_d65.cube**, and **rec709_kodak_2393_d65.cube** (Print Film Emulations) by [Juan Melara](https://juanmelara.com.au/). The original downloads and details can be found on his [Print Film Emulation blog post](https://juanmelara.com.au/blog/print-film-emulation-luts-for-download).
* **cinecolor_fuji_f_log.cube** (Fujifilm F-Log Camera LUT) by [CINECOLOR](https://cinecolor.io/). The free LUT and details can be found on their [Fuji F-Log product page](https://cinecolor.io/collections/camera-luts/products/fuji-f-log).


---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

