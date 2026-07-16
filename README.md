# Batch Film Emulator

A modular, Dockerized command-line tool designed to emulate analog film stocks (like Kodak Gold or Portra) on digital photos. 

Instead of relying on subscription-based editing software, this tool uses Python (`Pillow` and `NumPy`) to programmatically apply `.cube` 3D Look-Up Tables (LUTs) across entire directories. It goes beyond simple color mapping by replicating physical film characteristics, including synthetic grain generation and optical softness.

## Features
* **Batch LUT Processing:** Map digital colors to specific film color spaces instantly.
* **Synthetic Grain Engine:** Procedurally generated noise blended over the image.
* **Optical Softness:** Automatic downscaling to emulate the resolution limits of lab-scanned film.
* **Fully Containerized:** Runs entirely within Docker — no local Python environment or dependency management required.
