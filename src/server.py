import os
import base64
import sys
from io import BytesIO
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PIL import Image, ImageEnhance

# Ensure the parent folder is on path so we can import processor and grade modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from processor import process_image, load_cube_file, add_synthetic_grain, resize_longest_edge
from grade import resolve_lut_path

app = FastAPI(title="Batch Film Emulator GUI")

# Setup directories relative to grade.py
static_dir = os.path.join(script_dir, "static")
templates_dir = os.path.join(script_dir, "templates")

# Ensure folders exist
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# Mount static files and setup Jinja template support
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Absolute workspace paths
INPUT_DIR = os.path.abspath(os.path.join(script_dir, "..", "input"))
OUTPUT_DIR = os.path.abspath(os.path.join(script_dir, "..", "output"))
LUTS_DIR = os.path.abspath(os.path.join(script_dir, "..", "luts"))

# Input schemas for endpoints
class PreviewRequest(BaseModel):
    filename: str
    style: str = None
    blend: float = 1.0
    grain: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    saturation: float = 0.0

class SaveRequest(BaseModel):
    filename: str
    style: str = None
    blend: float = 1.0
    grain: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    saturation: float = 0.0

def generate_base64_preview(
    input_path: str,
    lut_path: str = None,
    lut_blend: float = 1.0,
    grain_intensity: float = 0.0,
    brightness: float = 0.0,
    contrast: float = 0.0,
    saturation: float = 0.0
) -> str:
    """
    Generates a low-resolution thumbnail (max 800px) with requested edits
    and returns a base64 string for quick real-time preview updating.
    """
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        
        # 1. Resize to preview thumbnail (800px on longest edge) for high performance
        img = resize_longest_edge(img, 800)
        
        # 2. Apply enhancements in standardized order (Brightness, Contrast, Color/Saturation)
        if brightness != 0.0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + brightness)
        if contrast != 0.0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + contrast)
        if saturation != 0.0:
            img = ImageEnhance.Color(img).enhance(1.0 + saturation)
            
        # 3. Apply film style (LUT)
        if lut_path:
            lut = load_cube_file(lut_path)
            graded = img.filter(lut)
            if lut_blend < 1.0:
                img = Image.blend(img, graded, lut_blend)
            else:
                img = graded
                
        # 4. Apply grain
        if grain_intensity > 0.0:
            img = add_synthetic_grain(img, grain_intensity)
            
        # 5. Output to buffer as low-quality preview JPEG
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"


@app.get("/", response_class=HTMLResponse)
def get_gui_index(request: Request):
    """Serve the single-page editor interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/images")
def get_input_images():
    """List all available JPEG/HEIC images in the input directory."""
    valid_extensions = (".jpg", ".jpeg", ".heic", ".heif")
    try:
        if not os.path.exists(INPUT_DIR):
            os.makedirs(INPUT_DIR, exist_ok=True)
            return {"images": []}
            
        files = os.listdir(INPUT_DIR)
        images = [
            f for f in files 
            if f.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(INPUT_DIR, f))
        ]
        return {"images": sorted(images)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/luts")
def get_available_luts():
    """List all available .cube LUT configurations."""
    try:
        if not os.path.exists(LUTS_DIR):
            os.makedirs(LUTS_DIR, exist_ok=True)
            return {"luts": []}
            
        files = os.listdir(LUTS_DIR)
        luts = [
            f[:-5] for f in files 
            if f.lower().endswith(".cube") and os.path.isfile(os.path.join(LUTS_DIR, f))
        ]
        return {"luts": sorted(luts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/original/{filename}")
def get_original_thumbnail(filename: str):
    """
    Returns a fast-loading base64-encoded thumbnail of the original image
    to power the Split Screen before-comparison.
    """
    file_path = os.path.join(INPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original file not found")
        
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img = resize_longest_edge(img, 800)
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=80)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return JSONResponse({"base64": f"data:image/jpeg;base64,{img_str}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview")
def get_realtime_preview(req: PreviewRequest):
    """Processes adjustments in real-time on a preview thumbnail."""
    input_path = os.path.join(INPUT_DIR, req.filename)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Input file not found: {req.filename}")
        
    lut_path = None
    if req.style:
        resolved_lut = resolve_lut_path(req.style)
        if resolved_lut and os.path.exists(resolved_lut):
            lut_path = resolved_lut
            
    try:
        base64_image = generate_base64_preview(
            input_path=input_path,
            lut_path=lut_path,
            lut_blend=req.blend,
            grain_intensity=req.grain,
            brightness=req.brightness,
            contrast=req.contrast,
            saturation=req.saturation
        )
        return {"image": base64_image}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save")
def save_full_resolution_image(req: SaveRequest):
    """Runs the full-res emulation and saves the output file."""
    input_path = os.path.join(INPUT_DIR, req.filename)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Input file not found: {req.filename}")
        
    lut_path = None
    if req.style:
        resolved_lut = resolve_lut_path(req.style)
        if resolved_lut and os.path.exists(resolved_lut):
            lut_path = resolved_lut
            
    # Derive output filename as a JPG
    basename, _ = os.path.splitext(req.filename)
    output_filename = f"{basename}_graded.jpg"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        process_image(
            input_path=input_path,
            output_path=output_path,
            lut_path=lut_path,
            lut_blend=req.blend,
            grain_intensity=req.grain,
            target_size=2000,
            brightness=req.brightness,
            contrast=req.contrast,
            saturation=req.saturation
        )
        return {"status": "success", "filename": output_filename, "path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
