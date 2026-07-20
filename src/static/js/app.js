// App State variables
let activeImage = null;
let activeLut = "";
let imgNaturalWidth = 0;
let imgNaturalHeight = 0;

// Debouncing for slider adjustments to prevent hammering the server
let previewTimeout = null;

// DOM Elements
const elements = {
    imageList: document.getElementById('image-list'),
    lutSelect: document.getElementById('lut-select'),
    blendSlider: document.getElementById('blend-slider'),
    blendVal: document.getElementById('blend-val'),
    grainSlider: document.getElementById('grain-slider'),
    grainVal: document.getElementById('grain-val'),
    brightnessSlider: document.getElementById('brightness-slider'),
    brightnessVal: document.getElementById('brightness-val'),
    contrastSlider: document.getElementById('contrast-slider'),
    contrastVal: document.getElementById('contrast-val'),
    saturationSlider: document.getElementById('saturation-slider'),
    saturationVal: document.getElementById('saturation-val'),
    resetBtn: document.getElementById('reset-btn'),
    saveBtn: document.getElementById('save-btn'),
    activeFilename: document.getElementById('active-filename'),
    placeholder: document.getElementById('placeholder'),
    loadingOverlay: document.getElementById('loading-overlay'),
    comparisonSlider: document.getElementById('comparison-slider'),
    beforeImg: document.getElementById('before-img'),
    afterImg: document.getElementById('after-img'),
    sliderHandle: document.getElementById('slider-handle'),
    previewContainer: document.getElementById('preview-container'),
    toast: document.getElementById('toast')
};

// 1. Initialize App Data
async function init() {
    try {
        await Promise.all([fetchImages(), fetchLuts()]);
        setupEventListeners();
        showToast("GUI Environment Loaded successfully.", "success");
    } catch (err) {
        showToast("Error loading GUI assets: " + err.message, "error");
    }
}

// 2. Fetch lists from endpoints
async function fetchImages() {
    const res = await fetch('/api/images');
    if (!res.ok) throw new Error("Could not fetch source images.");
    const data = await res.json();
    
    elements.imageList.innerHTML = "";
    if (data.images.length === 0) {
        elements.imageList.innerHTML = `<p class="empty-msg">No images found. Place JPEGs or HEIC files in the '/input' directory.</p>`;
        return;
    }
    
    data.images.forEach(filename => {
        const item = document.createElement('div');
        item.className = "image-item";
        item.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
            </svg>
            <span class="file-name">${filename}</span>
        `;
        item.addEventListener('click', () => selectImage(filename, item));
        elements.imageList.appendChild(item);
    });
}

async function fetchLuts() {
    const res = await fetch('/api/luts');
    if (!res.ok) throw new Error("Could not fetch film LUT looks.");
    const data = await res.json();
    
    data.luts.forEach(lut => {
        const opt = document.createElement('option');
        opt.value = lut;
        opt.textContent = formatStyleName(lut);
        elements.lutSelect.appendChild(opt);
    });
}

// 3. Selection Actions
async function selectImage(filename, element) {
    // Highlight item
    document.querySelectorAll('.image-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    
    activeImage = filename;
    elements.activeFilename.textContent = filename;
    elements.saveBtn.disabled = false;
    
    elements.loadingOverlay.classList.add('active');
    
    try {
        // Fetch original preview image
        const originalRes = await fetch(`/api/original/${filename}`);
        if (!originalRes.ok) throw new Error("Failed to load original preview.");
        const originalData = await originalRes.json();
        
        // Temporarily load image to extract natural aspect ratio
        const img = new Image();
        img.onload = () => {
            imgNaturalWidth = img.naturalWidth;
            imgNaturalHeight = img.naturalHeight;
            
            elements.beforeImg.src = originalData.base64;
            
            // Adjust layouts & triggers preview rendering
            resizeSlider();
            triggerPreviewUpdate();
        };
        img.src = originalData.base64;
        
    } catch (err) {
        showToast("Error loading image: " + err.message, "error");
        elements.loadingOverlay.classList.remove('active');
    }
}

// Aspect-ratio size constraints
function resizeSlider() {
    if (!imgNaturalWidth || !imgNaturalHeight) return;
    
    const containerWidth = elements.previewContainer.clientWidth;
    const containerHeight = elements.previewContainer.clientHeight;
    const containerRatio = containerWidth / containerHeight;
    const imgRatio = imgNaturalWidth / imgNaturalHeight;
    
    if (imgRatio > containerRatio) {
        // Width is bounding factor
        elements.comparisonSlider.style.width = '100%';
        elements.comparisonSlider.style.height = (containerWidth / imgRatio) + 'px';
    } else {
        // Height is bounding factor
        elements.comparisonSlider.style.height = '100%';
        elements.comparisonSlider.style.width = (containerHeight * imgRatio) + 'px';
    }
    
    // Reset drag handle to center
    setSliderSplit(50);
}

// 4. Preview Render Pipeline
function triggerPreviewUpdate() {
    if (!activeImage) return;
    
    elements.loadingOverlay.classList.add('active');
    
    // Debounce the call to prevent multiple quick slider calls hitting backend
    clearTimeout(previewTimeout);
    previewTimeout = setTimeout(async () => {
        try {
            const body = {
                filename: activeImage,
                style: activeLut || null,
                blend: parseFloat(elements.blendSlider.value) / 100.0,
                grain: parseFloat(elements.grainSlider.value) / 100.0,
                brightness: parseFloat(elements.brightnessSlider.value) / 100.0,
                contrast: parseFloat(elements.contrastSlider.value) / 100.0,
                saturation: parseFloat(elements.saturationSlider.value) / 100.0
            };
            
            const res = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            if (!res.ok) throw new Error("Preview generation failed.");
            
            const data = await res.json();
            elements.afterImg.src = data.image;
            
            // Uncover viewport elements
            elements.placeholder.style.display = "none";
            elements.comparisonSlider.style.display = "flex";
            
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            elements.loadingOverlay.classList.remove('active');
        }
    }, 150);
}

// 5. Save/Export Call
async function exportImage() {
    if (!activeImage) return;
    
    elements.loadingOverlay.classList.add('active');
    
    try {
        const body = {
            filename: activeImage,
            style: activeLut || null,
            blend: parseFloat(elements.blendSlider.value) / 100.0,
            grain: parseFloat(elements.grainSlider.value) / 100.0,
            brightness: parseFloat(elements.brightnessSlider.value) / 100.0,
            contrast: parseFloat(elements.contrastSlider.value) / 100.0,
            saturation: parseFloat(elements.saturationSlider.value) / 100.0
        };
        
        const res = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (!res.ok) throw new Error("Failed to export full resolution image.");
        const data = await res.json();
        
        showToast(`Saved graded file as: ${data.filename} inside /output`, "success");
    } catch (err) {
        showToast("Error exporting image: " + err.message, "error");
    } finally {
        elements.loadingOverlay.classList.remove('active');
    }
}

// 6. Before/After Split Drag Handling
let isDragging = false;

function setSliderSplit(percentage) {
    percentage = Math.max(0, Math.min(100, percentage));
    
    // Position slider line
    elements.sliderHandle.style.left = `${percentage}%`;
    
    // Clip the right-side (after) image accordingly
    elements.afterImg.style.clipPath = `polygon(0 0, ${percentage}% 0, ${percentage}% 100%, 0 100%)`;
}

function handlePointerMove(e) {
    if (!isDragging) return;
    
    const sliderRect = elements.comparisonSlider.getBoundingClientRect();
    const cursorX = (e.clientX || (e.touches ? e.touches[0].clientX : 0)) - sliderRect.left;
    const percentage = (cursorX / sliderRect.width) * 100;
    
    setSliderSplit(percentage);
}

// 7. Event Listeners Config
function setupEventListeners() {
    // Window Resizing fit
    window.addEventListener('resize', resizeSlider);
    
    // Presets Dropdown
    elements.lutSelect.addEventListener('change', (e) => {
        activeLut = e.target.value;
        triggerPreviewUpdate();
    });
    
    // Slider displays update
    elements.blendSlider.addEventListener('input', (e) => {
        elements.blendVal.textContent = `${e.target.value}%`;
        triggerPreviewUpdate();
    });
    
    elements.grainSlider.addEventListener('input', (e) => {
        elements.grainVal.textContent = (parseFloat(e.target.value) / 100.0).toFixed(2);
        triggerPreviewUpdate();
    });
    
    elements.brightnessSlider.addEventListener('input', (e) => {
        elements.brightnessVal.textContent = e.target.value;
        triggerPreviewUpdate();
    });
    
    elements.contrastSlider.addEventListener('input', (e) => {
        elements.contrastVal.textContent = e.target.value;
        triggerPreviewUpdate();
    });
    
    elements.saturationSlider.addEventListener('input', (e) => {
        elements.saturationVal.textContent = e.target.value;
        triggerPreviewUpdate();
    });
    
    // Action Buttons
    elements.resetBtn.addEventListener('click', resetSliders);
    elements.saveBtn.addEventListener('click', exportImage);
    
    // Interactive dragging coordinates binding
    const initDrag = () => { isDragging = true; };
    const endDrag = () => { isDragging = false; };
    
    elements.sliderHandle.addEventListener('pointerdown', initDrag);
    window.addEventListener('pointerup', endDrag);
    window.addEventListener('pointermove', handlePointerMove);
    
    // Support mobile touch actions
    elements.sliderHandle.addEventListener('touchstart', initDrag);
    window.addEventListener('touchend', endDrag);
    window.addEventListener('touchmove', handlePointerMove);
}

function resetSliders() {
    elements.blendSlider.value = 100;
    elements.blendVal.textContent = "100%";
    
    elements.grainSlider.value = 0;
    elements.grainVal.textContent = "0.00";
    
    elements.brightnessSlider.value = 0;
    elements.brightnessVal.textContent = "0";
    
    elements.contrastSlider.value = 0;
    elements.contrastVal.textContent = "0";
    
    elements.saturationSlider.value = 0;
    elements.saturationVal.textContent = "0";
    
    triggerPreviewUpdate();
}

// Helper formatting preset names
function formatStyleName(style) {
    return style
        .replace(/_/g, ' ')
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

// Notification Toast Alert
function showToast(message, type = "success") {
    elements.toast.textContent = message;
    elements.toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 4000);
}

// Initialize on execution
init();
