const state = {
  imageUrl: null,
  imageWidth: 0,
  imageHeight: 0,
  mode: "idle",
  unitName: "px",
  unitsPerPixel: 1,
  scalePoints: [],
  pathPoints: [],
  pathClosed: false,
  measurement: null,
  measurementError: "",
  instructions: "Load an image to begin.",
  uploading: false,
  uploadError: "",
  measuring: false,
  lastFilename: "",
  totalDistance: 0,
};

const elements = {
  fileInput: document.getElementById("file-input"),
  uploadButton: document.getElementById("upload-button"),
  uploadStatus: document.getElementById("upload-status"),
  uploadError: document.getElementById("upload-error"),
  unitSelect: document.getElementById("unit-select"),
  scaleDistance: document.getElementById("scale-distance"),
  unitsPerPixel: document.getElementById("units-per-pixel"),
  measurementError: document.getElementById("measurement-error"),
  resetButton: document.getElementById("reset-button"),
  viewer: document.getElementById("viewer"),
  placeholder: document.getElementById("viewer-placeholder"),
  image: document.getElementById("viewer-image"),
  overlay: document.getElementById("viewer-overlay"),
  scaleButton: document.getElementById("scale-button"),
  pathButton: document.getElementById("path-button"),
  closeButton: document.getElementById("close-button"),
  endButton: document.getElementById("end-button"),
  scaleInfo: document.getElementById("scale-info"),
  measurementStatus: document.getElementById("measurement-status"),
  instructions: document.getElementById("instructions"),
  measurementTotal: document.getElementById("measurement-total"),
};

let measurementTimeout = null;

function setInstructions(message) {
  state.instructions = message;
  updateUI();
}

function clearMeasurement() {
  state.measurement = null;
  state.measurementError = "";
  state.measuring = false;
  state.totalDistance = 0;
  updateUI();
}

function formatDistance() {
  if (state.measurement && typeof state.measurement === "object") {
    const displayUnit =
      state.measurement.display_unit_name ||
      state.measurement.unit_name ||
      state.unitName;
    if (typeof state.measurement.total_units === "number") {
      return `${state.measurement.total_units.toFixed(2)} ${displayUnit}`;
    }
    if (typeof state.measurement.total_pixels === "number") {
      return `${state.measurement.total_pixels.toFixed(2)} px`;
    }
  }
  const unit = state.unitName || "px";
  const value = typeof state.totalDistance === "number" ? state.totalDistance : 0;
  return `${value.toFixed(2)} ${unit}`;
}

function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function updateOverlay() {
  const overlay = elements.overlay;
  overlay.innerHTML = "";
  if (!state.imageUrl || !state.imageWidth || !state.imageHeight) {
    overlay.style.display = "none";
    return;
  }
  overlay.style.display = "block";
  overlay.setAttribute("viewBox", `0 0 ${state.imageWidth} ${state.imageHeight}`);

  const scaleGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  scaleGroup.setAttribute("stroke", "#f87171");
  scaleGroup.setAttribute("stroke-width", "2");
  scaleGroup.setAttribute("fill", "none");

  if (state.scalePoints.length === 2) {
    const points = state.scalePoints
      .map((point) => `${point.x},${point.y}`)
      .join(" ");
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("points", points);
    line.setAttribute("stroke-dasharray", "6 4");
    scaleGroup.appendChild(line);
  }

  state.scalePoints.forEach((point) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point.x);
    circle.setAttribute("cy", point.y);
    circle.setAttribute("r", "6");
    circle.setAttribute("fill", "#f87171");
    circle.setAttribute("stroke", "white");
    circle.setAttribute("stroke-width", "1");
    scaleGroup.appendChild(circle);
  });

  overlay.appendChild(scaleGroup);

  const pathGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  pathGroup.setAttribute("stroke", "#34d399");
  pathGroup.setAttribute("stroke-width", "2");
  pathGroup.setAttribute("fill", state.pathClosed ? "rgba(34, 197, 94, 0.2)" : "none");

  if (state.pathPoints.length >= 2) {
    const coords = state.pathPoints
      .concat(state.pathClosed ? [state.pathPoints[0]] : [])
      .map((point) => `${point.x},${point.y}`)
      .join(" ");
    const pathLine = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    pathLine.setAttribute("points", coords);
    pathGroup.appendChild(pathLine);
  }

  state.pathPoints.forEach((point) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point.x);
    circle.setAttribute("cy", point.y);
    circle.setAttribute("r", "5");
    circle.setAttribute("fill", "#34d399");
    circle.setAttribute("stroke", "white");
    circle.setAttribute("stroke-width", "1");
    pathGroup.appendChild(circle);
  });

  overlay.appendChild(pathGroup);
}

function updateUI() {
  const hasImage = Boolean(state.imageUrl);

  elements.instructions.textContent = state.instructions;
  elements.measurementTotal.value = formatDistance();
  elements.measurementStatus.classList.toggle("loading", state.measuring);

  elements.scaleButton.classList.toggle("active", state.mode === "scale");
  elements.pathButton.classList.toggle("active", state.mode === "path");

  elements.scaleButton.disabled = !hasImage;
  elements.pathButton.disabled = !hasImage;
  elements.closeButton.disabled = !hasImage || state.pathPoints.length < 3 || state.pathClosed;
  elements.endButton.disabled = !hasImage || state.mode === "idle";
  elements.resetButton.disabled = !hasImage;

  elements.unitSelect.value = state.unitName;
  elements.unitSelect.disabled = !hasImage;

  const unitsValue = state.unitsPerPixel > 0 ? state.unitsPerPixel : "";
  if (unitsValue === "") {
    elements.unitsPerPixel.value = "";
  } else if (typeof unitsValue === "number") {
    elements.unitsPerPixel.value = unitsValue.toFixed(4);
  } else {
    elements.unitsPerPixel.value = String(unitsValue);
  }
  elements.unitsPerPixel.disabled = !hasImage;
  elements.scaleDistance.disabled = !hasImage;

  if (state.scalePoints.length === 2) {
    const length = distance(state.scalePoints[0], state.scalePoints[1]);
    elements.scaleInfo.textContent = `Scale length: ${length.toFixed(2)} px`;
  } else {
    elements.scaleInfo.textContent = "";
  }

  if (state.uploading) {
    elements.uploadStatus.textContent =
      state.lastFilename ? `Uploading ${state.lastFilename}...` : "Uploading...";
  } else {
    elements.uploadStatus.textContent = "";
  }

  elements.uploadButton.disabled = state.uploading;
  elements.fileInput.disabled = state.uploading;

  if (state.uploadError) {
    elements.uploadError.textContent = state.uploadError;
  } else {
    elements.uploadError.textContent = "";
  }

  if (state.measurementError) {
    elements.measurementError.textContent = state.measurementError;
  } else {
    elements.measurementError.textContent = "";
  }

  if (state.measuring) {
    elements.measurementStatus.textContent = "Calculating measurement...";
  } else if (state.measurementError) {
    elements.measurementStatus.textContent = "";
  } else if (state.measurement) {
    elements.measurementStatus.textContent = "Measurement ready.";
  } else {
    elements.measurementStatus.textContent = "";
  }

  if (hasImage) {
    elements.placeholder.style.display = "none";
    elements.image.style.display = "block";
  } else {
    elements.placeholder.style.display = "flex";
    elements.image.style.display = "none";
    elements.overlay.style.display = "none";
  }
}

function syncOverlaySize() {
  if (!state.imageUrl) {
    return;
  }
  const width = elements.image.clientWidth;
  const height = elements.image.clientHeight;
  if (!width || !height) {
    return;
  }
  elements.overlay.setAttribute("width", width);
  elements.overlay.setAttribute("height", height);
  elements.overlay.style.width = `${width}px`;
  elements.overlay.style.height = `${height}px`;
  updateOverlay();
}

function setMode(mode) {
  state.mode = mode;
  updateUI();
}

function resetMeasurements() {
  state.mode = "idle";
  state.scalePoints = [];
  state.pathPoints = [];
  state.pathClosed = false;
  state.unitsPerPixel = 1;
  state.measurement = null;
  state.measurementError = "";
  state.totalDistance = 0;
  state.instructions = "Select 'Set Scale' or 'Trace Path' to begin measuring.";
  elements.scaleDistance.value = "";
  updateUI();
  updateOverlay();
}

async function uploadImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  state.uploading = true;
  state.uploadError = "";
  state.lastFilename = file.name || "image";
  updateUI();

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error((data && data.detail) || "Failed to upload image.");
    }
    const payload = await response.json();
    if (!payload || typeof payload.url !== "string") {
      throw new Error("Upload succeeded but no image URL was returned.");
    }
    loadImage(payload.url);
    resetMeasurements();
    elements.fileInput.value = "";
  } catch (error) {
    console.error(error);
    state.uploadError = error.message || "Failed to upload image.";
  } finally {
    state.uploading = false;
    updateUI();
  }
}

function loadImage(url) {
  state.imageUrl = url;
  state.imageWidth = 0;
  state.imageHeight = 0;
  elements.overlay.innerHTML = "";
  elements.overlay.style.display = "none";
  elements.image.src = url;
}

elements.image.addEventListener("load", () => {
  state.imageWidth = elements.image.naturalWidth;
  state.imageHeight = elements.image.naturalHeight;
  syncOverlaySize();
  updateUI();
});

window.addEventListener("resize", () => {
  if (state.imageUrl) {
    syncOverlaySize();
  }
});

function addScalePoint(x, y) {
  if (state.scalePoints.length >= 2) {
    state.scalePoints = [];
  }
  state.scalePoints.push({ x, y });
  if (state.scalePoints.length === 2) {
    state.instructions = "Enter the real-world distance for the selected scale.";
  } else {
    state.instructions = "Select a second point to complete the scale.";
  }
  updateOverlay();
  updateUI();
}

function addPathPoint(x, y) {
  if (state.pathClosed) {
    state.pathClosed = false;
    state.pathPoints = [];
  }
  state.pathPoints.push({ x, y });
  state.measurementError = "";
  if (state.pathPoints.length === 1) {
    state.instructions = "Add more points to trace a path.";
  } else {
    state.instructions = "Continue adding points or close the loop.";
  }
  updateOverlay();
  scheduleMeasurement();
  updateUI();
}

function removeLastPathPoint() {
  if (!state.pathPoints.length) {
    return;
  }
  state.pathPoints.pop();
  state.measurementError = "";
  if (state.pathPoints.length < 3) {
    state.pathClosed = false;
  }
  if (!state.pathPoints.length) {
    state.instructions = "Path cleared. Add a new point to start.";
  } else {
    state.instructions = "Continue adding points or close the loop.";
  }
  updateOverlay();
  scheduleMeasurement();
  updateUI();
}

function closePath() {
  if (state.pathPoints.length >= 3 && !state.pathClosed) {
    state.pathClosed = true;
    state.measurementError = "";
    state.instructions = "Path closed. Add points to start a new path.";
    updateOverlay();
    scheduleMeasurement();
    updateUI();
  }
}

function endMode() {
  state.mode = "idle";
  if (state.pathPoints.length) {
    state.instructions = "Path active. Continue clicking to add points or close the loop.";
  } else {
    state.instructions = "Select a mode to begin measuring.";
  }
  updateUI();
}

function handleUnitsPerPixel(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    state.measurementError = "Units per pixel must be greater than zero.";
    updateUI();
    return;
  }
  state.measurementError = "";
  state.unitsPerPixel = parsed;
  scheduleMeasurement();
  updateUI();
}

function handleScaleMeasurement(value) {
  if (state.scalePoints.length !== 2) {
    return;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return;
  }
  const pixelDistance = distance(state.scalePoints[0], state.scalePoints[1]);
  if (pixelDistance <= 0) {
    return;
  }
  state.unitsPerPixel = parsed / pixelDistance;
  state.measurementError = "";
  elements.unitsPerPixel.value = state.unitsPerPixel.toFixed(4);
  state.instructions = "Scale set. Switch to path tracing to measure distances.";
  scheduleMeasurement();
  updateUI();
}

function handleCanvasEvent(event) {
  if (!state.imageUrl || !state.imageWidth || !state.imageHeight) {
    return;
  }
  const rect = elements.image.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    return;
  }
  const withinX = event.clientX >= rect.left && event.clientX <= rect.right;
  const withinY = event.clientY >= rect.top && event.clientY <= rect.bottom;
  if (!withinX || !withinY) {
    return;
  }
  event.preventDefault();
  const scaleX = state.imageWidth / rect.width;
  const scaleY = state.imageHeight / rect.height;
  const x = (event.clientX - rect.left) * scaleX;
  const y = (event.clientY - rect.top) * scaleY;

  if (event.button === 2) {
    removeLastPathPoint();
    return;
  }

  if (event.button !== 0) {
    return;
  }

  if (state.mode === "scale") {
    addScalePoint(x, y);
  } else {
    if (state.mode === "idle") {
      state.mode = "path";
    }
    addPathPoint(x, y);
  }
}

elements.viewer.addEventListener("mousedown", handleCanvasEvent);
elements.viewer.addEventListener("contextmenu", (event) => event.preventDefault());

elements.scaleButton.addEventListener("click", () => {
  state.mode = "scale";
  state.scalePoints = [];
  state.instructions = "Click two points to define the scale.";
  updateOverlay();
  updateUI();
});

elements.pathButton.addEventListener("click", () => {
  state.mode = "path";
  if (!state.pathPoints.length) {
    state.instructions =
      "Click on the image to create a path. Right-click to remove the last point.";
  } else {
    state.instructions = "Continue adding points or close the loop.";
  }
  updateUI();
});

elements.closeButton.addEventListener("click", closePath);
elements.endButton.addEventListener("click", endMode);
elements.resetButton.addEventListener("click", () => {
  if (state.imageUrl) {
    resetMeasurements();
  }
});

elements.unitSelect.addEventListener("change", (event) => {
  state.unitName = event.target.value;
  if (state.unitName === "px") {
    state.unitsPerPixel = 1;
    state.measurementError = "";
  }
  scheduleMeasurement();
  updateUI();
});

elements.unitsPerPixel.addEventListener("change", (event) => {
  handleUnitsPerPixel(event.target.value);
});

elements.scaleDistance.addEventListener("change", (event) => {
  handleScaleMeasurement(event.target.value);
});

elements.uploadButton.addEventListener("click", async () => {
  const file = elements.fileInput.files && elements.fileInput.files[0];
  if (!file) {
    state.uploadError = "Select an image to upload.";
    updateUI();
    return;
  }
  await uploadImage(file);
});

async function requestMeasurement() {
  if (state.pathPoints.length < 2) {
    state.measurement = null;
    state.totalDistance = 0;
    state.measuring = false;
    state.measurementError = "";
    updateUI();
    return;
  }

  if (state.unitName !== "px" && (!state.unitsPerPixel || state.unitsPerPixel <= 0)) {
    state.measurementError = "Units per pixel must be greater than zero.";
    updateUI();
    return;
  }

  const payload = {
    points: state.pathPoints.map((point) => ({ x: point.x, y: point.y })),
    closed: state.pathClosed,
    scale: {
      unit_name: state.unitName,
    },
  };

  if (state.unitName === "px") {
    payload.scale.units_per_pixel = 1;
  } else {
    payload.scale.units_per_pixel = state.unitsPerPixel;
  }

  state.measuring = true;
  state.measurementError = "";
  updateUI();

  try {
    const response = await fetch("/measure", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error((data && data.detail) || "Measurement request failed.");
    }
    const data = await response.json();
    if (!data || typeof data !== "object" || typeof data.measurement !== "object") {
      throw new Error("Measurement succeeded but returned invalid data.");
    }
    state.measurement = data.measurement;
    if (typeof data.measurement.total_units === "number") {
      state.totalDistance = data.measurement.total_units;
    } else if (typeof data.measurement.total_pixels === "number") {
      state.totalDistance = data.measurement.total_pixels;
    } else {
      state.totalDistance = 0;
    }
  } catch (error) {
    console.error(error);
    state.measurementError = error.message || "Measurement request failed.";
    state.measurement = null;
    state.totalDistance = 0;
  } finally {
    state.measuring = false;
    updateUI();
  }
}

function scheduleMeasurement() {
  if (measurementTimeout) {
    clearTimeout(measurementTimeout);
  }
  measurementTimeout = setTimeout(() => {
    requestMeasurement();
  }, 200);
}

updateUI();
