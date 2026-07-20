import os
import numpy as np
# pyrefly: ignore [missing-import]
from PIL import Image, ImageFilter

def load_cube_file(cube_path: str) -> ImageFilter.Color3DLUT:
    """
    Parses an Adobe .cube 3D LUT file and returns a PIL ImageFilter.Color3DLUT.
    
    This function parses the metadata and 3D data grid from a .cube file and
    scales values to the [0.0, 1.0] range expected by Pillow.
    """
    if not os.path.exists(cube_path):
        raise FileNotFoundError(f"LUT file not found: {cube_path}")

    size = None
    table = []

    with open(cube_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse LUT size
            if line.startswith("LUT_3D_SIZE"):
                parts = line.split()
                if len(parts) >= 2:
                    size = int(parts[1])
                continue

            # Ignore typical metadata headers
            if line.startswith(("TITLE", "DOMAIN_MIN", "DOMAIN_MAX", "LUT_1D_SIZE", "LUT_1D_INPUT_RANGE")):
                continue

            # Parse color data line (3 floats)
            parts = line.split()
            if len(parts) == 3:
                try:
                    r, g, b = map(float, parts)
                    # Clip to [0.0, 1.0] as expected by Pillow's Color3DLUT
                    r = max(0.0, min(1.0, r))
                    g = max(0.0, min(1.0, g))
                    b = max(0.0, min(1.0, b))
                    table.append((r, g, b))
                except ValueError:
                    # Ignore lines that cannot be parsed as floats
                    continue

    if size is None:
        raise ValueError(f"Could not find LUT_3D_SIZE in {cube_path}")

    expected_entries = size ** 3
    if len(table) != expected_entries:
        raise ValueError(
            f"LUT entry mismatch in {cube_path}: Expected {expected_entries} data lines for size {size}, but parsed {len(table)} lines."
        )

    return ImageFilter.Color3DLUT(size, table)


def resize_longest_edge(image: Image.Image, target_size: int = 2000) -> Image.Image:
    """
    Resizes the image so that the longest edge matches target_size (default 2000px),
    maintaining the aspect ratio.
    
    This helps emulate the natural softness of lab-scanned analog film.
    """
    width, height = image.size
    longest_edge = max(width, height)

    if longest_edge == target_size:
        return image

    ratio = target_size / longest_edge
    new_width = int(round(width * ratio))
    new_height = int(round(height * ratio))

    # Determine resampling filter based on Pillow version
    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:
        resample_filter = Image.LANCZOS

    return image.resize((new_width, new_height), resample=resample_filter)


def add_synthetic_grain(image: Image.Image, grain_intensity: float) -> Image.Image:
    """
    Generates monochrome Gaussian noise using NumPy and blends it over the image.
    
    Args:
        image: A PIL Image in RGB mode.
        grain_intensity: Float scaling the noise intensity (typically 0.0 to 0.5).
    """
    if grain_intensity <= 0.0:
        return image

    # Convert image to numpy array of float32
    img_arr = np.array(image, dtype=np.float32)
    height, width, _ = img_arr.shape

    # Generate monochrome noise (height, width, 1) and broadcast it
    # This prevents colored pixel noise, creating a natural silver halide grain appearance
    noise = np.random.normal(loc=0.0, scale=grain_intensity * 255.0, size=(height, width, 1))

    # Add noise to image array
    grainy_arr = img_arr + noise

    # Clip values to valid range and cast back to uint8
    grainy_arr = np.clip(grainy_arr, 0.0, 255.0).astype(np.uint8)

    return Image.fromarray(grainy_arr, mode="RGB")


def process_image(
    input_path: str,
    output_path: str,
    lut_path: str = None,
    lut_blend: float = 1.0,
    grain_intensity: float = None,
    target_size: int = 2000
) -> None:
    """
    Modular execution pipeline for a single image:
    1. Loads the image and converts to RGB.
    2. Applies a 3D LUT and blends it with original (if provided).
    3. Resizes the image to the specified longest edge limit.
    4. Applies synthetic film grain (if intensity > 0).
    5. Saves the output file as a JPEG with 80% quality.
    """
    with Image.open(input_path) as img:
        # Convert to RGB to ensure compatibility with JPEG saving and LUT filtering
        img = img.convert("RGB")

        # Apply LUT if requested
        if lut_path:
            lut = load_cube_file(lut_path)
            graded_img = img.filter(lut)
            if lut_blend < 1.0:
                img = Image.blend(img, graded_img, lut_blend)
            else:
                img = graded_img


        # Resize to emulate lab-scan optical softness
        if target_size:
            img = resize_longest_edge(img, target_size)

        # Apply synthetic grain
        if grain_intensity is not None and grain_intensity > 0.0:
            img = add_synthetic_grain(img, grain_intensity)

        # Ensure directory path for output exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save image as JPEG at 80% quality
        img.save(output_path, format="JPEG", quality=80)
