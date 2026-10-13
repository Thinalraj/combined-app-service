const screens = {
  home: document.getElementById("homeScreen"),
  scalePrepare: document.getElementById("scalePrepareScreen"),
  place: document.getElementById("placeScreen"),
  weight: document.getElementById("weightScreen"),
  dimension: document.getElementById("dimensionScreen"),
  shape: document.getElementById("shapeScreen"),
  otherShape: document.getElementById("otherShapeScreen"),
  measure: document.getElementById("measureScreen"),
  result: document.getElementById("resultScreen"),
  password: document.getElementById("passwordScreen"),
  engineering: document.getElementById("engineeringScreen"),
  classifier: document.getElementById("classifierScreen"),
  liveView: document.getElementById("liveViewScreen"),
  daqSettings: document.getElementById("daqSettingsScreen"),
  loadCell: document.getElementById("loadCellScreen"),
  signalService: document.getElementById("signalServiceScreen"),
  calibration: document.getElementById("calibrationScreen"),
  calibrationProgress: document.getElementById("calibrationProgressScreen"),
  calibrationResult: document.getElementById("calibrationResultScreen"),
  teaching: document.getElementById("teachingScreen"),
  teachingPlace: document.getElementById("teachingPlaceScreen"),
  teachingMaterial: document.getElementById("teachingMaterialScreen"),
  teachingOtherMaterial: document.getElementById("teachingOtherMaterialScreen"),
  teachingPurity: document.getElementById("teachingPurityScreen"),
  teachingShape: document.getElementById("teachingShapeScreen"),
  teachingOtherShape: document.getElementById("teachingOtherShapeScreen"),
  teachingWeight: document.getElementById("teachingWeightScreen"),
  teachingDimension: document.getElementById("teachingDimensionScreen"),
  teachingRecord: document.getElementById("teachingRecordScreen"),
  teachingRemove: document.getElementById("teachingRemoveScreen"),
  teachingSaved: document.getElementById("teachingSavedScreen"),
  teachingRecords: document.getElementById("teachingRecordsScreen"),
  teachingDetail: document.getElementById("teachingDetailScreen"),
  history: document.getElementById("historyScreen"),
  historyDetail: document.getElementById("historyDetailScreen"),
  deletePassword: document.getElementById("deletePasswordScreen"),
  detectorSettings: document.getElementById("detectorSettingsScreen"),
  frequencyMode: document.getElementById("frequencyModeScreen"),
  frequencyEdit: document.getElementById("frequencyEditScreen")
};

const title = document.getElementById("screenTitle");
const weightDisplay = document.getElementById("weightDisplay");
const progressText = document.getElementById("progressText");
const progressBar = document.getElementById("progressBar");
const ringMeter = document.getElementById("ringMeter");
const measureStage = document.getElementById("measureStage");
const measureInstruction = document.getElementById("measureInstruction");

const state = {
  weight: "",
  widthMm: "",
  lengthMm: "",
  thicknessMm: "",
  activeDimensionField: "width",
  password: "",
  shape: "Ring",
  otherShape: "Pendant",
  visionMeasurement: null,
  carouselIndex: 0,
  progressTimer: null,
  measurementWeightSampling: false,
  measurementWeightReady: false,
  teachingWeightSampling: false,
  teachingWeightReady: false,
  weightProgressTimer: null,
  engineeringTimer: null,
  signalLiveTimer: null,
  signalLiveBusy: false,
  signalLiveRunning: false,
  signalLiveVpp: 2,
  signalLiveUnit: "V",
  signalLiveMode: "raw",
  signalLiveLatest: null,
  signalLiveDeltaBaseline: null,
  loadCellTimer: null,
  loadCellHeld: false,
  acquisitionMode: "daq",
  calibrationRecord: {},
  confidenceThresholdPct: 40,
  detectorConfidenceInput: "40",
  frequencyMode: "single",
  multiFrequenciesKhz: [10, 20, 30],
  activeFrequencySlot: 1,
  signalPreset: "f1"
};

const titles = {
  home: "Precious Metal Verification System",
  place: "Place Object",
  weight: "Enter Weight",
  dimension: "Sample Dimensions",
  shape: "Select Sample Type",
  otherShape: "Other Shape",
  measure: "Measuring",
  result: "Result",
  password: "Engineering Login",
  engineering: "Engineering",
  classifier: "Classifier",
  liveView: "Live View",
  daqSettings: "DAQ Settings",
  loadCell: "Load Cell Settings",
  signalService: "Signal Service",
  calibration: "Calibration",
  calibrationProgress: "Calibrating",
  calibrationResult: "Calibration Result",
  teaching: "Teaching",
  teachingPlace: "Place Known Sample",
  teachingMaterial: "Known Material",
  teachingOtherMaterial: "Other Material",
  teachingPurity: "Purity / Grade",
  teachingShape: "Sample Shape",
  teachingOtherShape: "Other Shape",
  teachingWeight: "Teaching Weight",
  teachingDimension: "Sample Dimensions",
  teachingRecord: "Recording Reference",
  teachingRemove: "Remove Material",
  teachingSaved: "Teaching Saved",
  teachingRecords: "Teaching Records",
  teachingDetail: "Teaching Detail",
  history: "Measurement History",
  historyDetail: "Record Detail",
  deletePassword: "Delete Record",
  detectorSettings: "Detector Settings",
  frequencyMode: "Frequency Mode",
  frequencyEdit: "Edit Frequency"
};

const ENGINEERING_PIN = "242218";
const ADMIN_PIN = "242218";
let selectedHistoryId = null;
let selectedTeachingId = null;
let deletePassword = "";
let teachingRecords = [];
const teachingState = {
  material: "Gold",
  otherMaterial: "Brass",
  purity: "",
  shape: "Bar",
  otherShape: "Pendant",
  weight: "",
  weightStd: "",
  widthMm: "",
  lengthMm: "",
  thicknessMm: "",
  visionMeasurement: null,
  imageReference: null,
  activeDimensionField: "width",
  latestRecord: null,
  mode: "teach"
};
const fallbackHistoryRecords = [
  {
    id: "M-1004",
    date: "09 May 2026",
    time: "15:42",
    result: "Gold 916",
    weight: "12.45 g",
    shape: "Bar",
    confidence: "87%",
    status: "Saved locally"
  },
  {
    id: "M-1003",
    date: "09 May 2026",
    time: "15:18",
    result: "Gold 999",
    weight: "25.10 g",
    shape: "Bar",
    confidence: "91%",
    status: "Saved locally"
  },
  {
    id: "M-1002",
    date: "09 May 2026",
    time: "14:50",
    result: "Non Gold",
    weight: "8.20 g",
    shape: "Other",
    confidence: "76%",
    status: "Saved locally"
  },
  {
    id: "M-1001",
    date: "09 May 2026",
    time: "14:22",
    result: "Gold 750",
    weight: "6.85 g",
    shape: "Bar",
    confidence: "84%",
    status: "Saved locally"
  }
];
let historyRecords = [...fallbackHistoryRecords];
const bottomMessages = [
  "Verify your sample now",
  "Proudly made in Malaysia",
  "Designed in Malaysia",
  "For Malaysia, made in Malaysia",
  "Semak ketulenan dengan yakin",
  "Buatan Malaysia"
];

// REV 2026-10-02 / SCALE-01: all new-item paths share an explicit empty-pan gate.
// A net reading of zero cannot prove the platform is empty after a previous tare.
// The operator confirms removal; stable readings then verify the zero operation.
const SCALE_ZERO_TOLERANCE_G = 0.01; // Workflow band, not accuracy; verify against your scale's resolution.
const SCALE_SETUP_TIMEOUT_MS = 15000;
const scalePreparation = { target: "place", cancel: "home", busy: false };

function showScreen(name) {
  // Do not navigate away while a physical zero is in flight. Setup has a deadline.
  if (scalePreparation.busy && name !== "scalePrepare") return;
  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  screens[name].classList.add("active");
  document.getElementById("menuPanel").classList.remove("open");

  if (name !== "measure") {
    clearInterval(state.progressTimer);
  }

  if (name === "engineering") {
    loadAcquisitionMode();
    loadCalibration();
    clearInterval(state.engineeringTimer);
  } else if (name === "liveView") {
    startLiveViewMonitor();
  } else if (name === "loadCell") {
    startLoadCellMonitor();
  } else if (name === "signalService") {
    loadSignalEngineeringStatus();
    loadSignalAirCalibration();
  } else {
    clearInterval(state.engineeringTimer);
  }

  if (name !== "loadCell") {
    clearInterval(state.loadCellTimer);
  }

  if (name !== "liveView") {
    stopSignalLivePolling();
  }

  if (name !== "weight" && name !== "teachingWeight") {
    stopWeightProgressTimer();
  }

  if (name === "teachingDimension") {
    loadTeachingDetectedImage();
  }
}

function selectTeachingDimensionPanel(panel) {
  const dimensionsActive = panel !== "image";
  document.getElementById("teachingDimensionsPanel").classList.toggle("active", dimensionsActive);
  document.getElementById("teachingImagePanel").classList.toggle("active", !dimensionsActive);
  document.getElementById("teachingDimensionsTabButton").classList.toggle("active", dimensionsActive);
  document.getElementById("teachingImageTabButton").classList.toggle("active", !dimensionsActive);
  document.getElementById("teachingDimensionsTabButton").setAttribute("aria-selected", String(dimensionsActive));
  document.getElementById("teachingImageTabButton").setAttribute("aria-selected", String(!dimensionsActive));
  if (!dimensionsActive) loadTeachingDetectedImage();
}

// VISUAL-01: keep the IMG fallback; use a sibling HTML viewer when present.
// Request tokens prevent a slow old record response replacing a newer image.
function resetImageOverlay(image) {
  image.dataset.overlayRequest = String(Number(image.dataset.overlayRequest || 0) + 1);
  document.getElementById(`${image.id}Overlay`)?.remove();
}

async function tryImageOverlay(image, url, status = null) {
  resetImageOverlay(image);
  const token = image.dataset.overlayRequest;
  const controller = new AbortController();
  const deadline = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(url, {cache: "no-store", signal: controller.signal});
    if (!response.ok || !response.headers.get("content-type")?.includes("text/html")) return;
    // The viewer URL has a relative raw-image reference, so use src rather
    // than srcdoc. Sandboxing blocks scripts in any imported old HTML file.
    if (image.dataset.overlayRequest !== token) return;
    const frame = document.createElement("iframe");
    frame.id = `${image.id}Overlay`;
    frame.className = "annotation-viewer";
    frame.title = "Raw sample image with separate annotation";
    frame.setAttribute("sandbox", "");
    frame.src = url;
    image.insertAdjacentElement("afterend", frame);
    image.hidden = true;
    if (status) status.textContent = "Raw image with separate overlay";
  } catch (_) {
    // Missing sidecar or an older backend retains the existing image display.
  } finally {
    clearTimeout(deadline);
  }
}

function loadSavedImageOverlay(image, info) {
  resetImageOverlay(image);
  if (!info?.url) return;
  const url = info.overlay_url || info.url.replace(/\.(jpg|jpeg|png|webp)(?=\?|$)/i, ".html");
  if (url !== info.url) tryImageOverlay(image, `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`);
}

function loadTeachingDetectedImage() {
  const image = document.getElementById("teachingDetectedImage");
  const status = document.getElementById("teachingDetectedImageStatus");
  resetImageOverlay(image);
  image.hidden = false;
  status.textContent = "Loading detected image...";
  image.onload = () => { if (!image.hidden) status.textContent = "Latest detected item image"; };
  image.onerror = () => { if (!image.hidden) status.textContent = "No detected image available yet. Capture or detect an image first."; };
  image.src = `/api/vision/image/detected?t=${Date.now()}`;
  tryImageOverlay(image, `/api/vision/image/view?t=${Date.now()}`, status);
}

async function captureTeachingImageSnapshot() {
  const status = document.getElementById("teachingDetectedImageStatus");
  status.textContent = "Saving detected image with teaching record...";
  try {
    const response = await fetch("/api/teaching/image/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shape: getTeachingShapeLabel() })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false || !payload.image) {
      throw new Error(payload.message || payload.error || "Unable to save detected image");
    }
    teachingState.imageReference = payload.image;
    status.textContent = `Image saved · ${payload.image.filename || "teaching image"}`;
    return payload.image;
  } catch (error) {
    teachingState.imageReference = null;
    status.textContent = `Image save failed: ${error.message || "Vision service unavailable"}`;
    throw error;
  }
}

function setWeight(value) {
  state.weight = value.slice(0, 7);
  weightDisplay.textContent = state.weight || "0";
  document.querySelector("#weightScreen .value-panel").classList.remove("error");
}

function calculateGeometry(widthValue, lengthValue, thicknessValue, mode = "standard") {
  const width = Number.parseFloat(widthValue || "0");
  const length = Number.parseFloat(lengthValue || "0");
  const thickness = Number.parseFloat(thicknessValue || "0");
  const safeWidth = Number.isFinite(width) ? width : 0;
  const safeLength = Number.isFinite(length) ? length : 0;
  const safeThickness = Number.isFinite(thickness) ? thickness : 0;
  // REV 2026-10-02 / RING-01: both workflows use the same shape formula.
  // For rings/bangles width=INNER diameter and length=OUTER diameter.
  let sampleArea = safeWidth * safeLength;
  if (mode === "coin") sampleArea = Math.PI * (safeWidth / 2) ** 2;
  if (mode === "ring" || mode === "bangle") {
    sampleArea = safeWidth > 0 && safeLength > safeWidth
      ? Math.PI * (safeLength ** 2 - safeWidth ** 2) / 4 : 0;
  }
  const coilArea = Math.PI * 35 * 35;
  const contactRatio = coilArea > 0 ? (sampleArea / coilArea) * 100 : 0;
  return { safeWidth, safeLength, safeThickness, sampleArea, contactRatio };
}

function getMeasurementShapeLabel() {
  return state.shape === "Other" ? state.otherShape : state.shape;
}

function getMeasurementDimensionConfig() {
  const shape = getMeasurementShapeLabel().toLowerCase();
  if (shape === "coin") {
    return {
      mode: "coin",
      labels: { width: "Diameter", length: "Diameter", thickness: "Thickness" },
      required: ["width", "thickness"],
      hideLength: true
    };
  }
  if (shape === "ring" || shape === "bangle") {
    return {
      mode: shape,
      labels: { width: "Inner Diameter", length: "Outer Diameter", thickness: "Thickness" },
      required: ["width", "length", "thickness"],
      hideLength: false
    };
  }
  if (shape === "bar") {
    return {
      mode: "bar",
      labels: { width: "Width", length: "Length", thickness: "Thickness" },
      required: ["width", "length", "thickness"],
      hideLength: false
    };
  }
  if (shape === "chain") {
    return {
      mode: "chain",
      labels: { width: "Length", length: "Thickness", thickness: "Link Dia." },
      required: ["width", "length"],
      hideLength: false
    };
  }
  return {
    mode: "standard",
    labels: { width: "Length", length: "Width", thickness: "Thickness" },
    required: ["width", "length", "thickness"],
    hideLength: false
  };
}

function calculateGeometryForMeasurement() {
  const config = getMeasurementDimensionConfig();
  const width = Number.parseFloat(state.widthMm || "0") || 0;
  const length = Number.parseFloat(state.lengthMm || "0") || 0;
  const thickness = Number.parseFloat(state.thicknessMm || "0") || 0;
  return calculateGeometry(width, config.mode === "coin" ? width : length, thickness, config.mode);
}

function buildMeasurementDimensionPayload() {
  const config = getMeasurementDimensionConfig();
  const width = state.widthMm || "0";
  const length = config.mode === "coin" ? width : (state.lengthMm || "0");
  return {
    width_mm: width,
    length_mm: length,
    thickness_mm: state.thicknessMm || "0",
    dimension_mode: config.mode,
    dimension_labels: config.labels
  };
}

function applyVisionToMeasurement(payload) {
  state.visionMeasurement = payload || null;
  const config = getMeasurementDimensionConfig();
  const diameter = Number.parseFloat(payload?.diameter_mm);
  const width = Number.parseFloat(payload?.width_mm);
  const length = Number.parseFloat(payload?.length_mm);
  if (config.mode === "ring" || config.mode === "bangle") {
    applyRingDiameters(state, payload);
  } else if (config.mode === "coin" && Number.isFinite(diameter) && diameter > 0) {
    state.widthMm = diameter.toFixed(2);
    state.lengthMm = diameter.toFixed(2);
  } else {
    if (Number.isFinite(width) && width > 0) state.widthMm = width.toFixed(2);
    if (Number.isFinite(length) && length > 0) state.lengthMm = length.toFixed(2);
  }
  updateDimensionDisplay();
}

function applyVisionToTeaching(payload) {
  teachingState.visionMeasurement = payload || null;
  const config = getTeachingDimensionConfig();
  const diameter = Number.parseFloat(payload?.diameter_mm);
  const width = Number.parseFloat(payload?.width_mm);
  const length = Number.parseFloat(payload?.length_mm);
  if (config.mode === "ring" || config.mode === "bangle") {
    applyRingDiameters(teachingState, payload);
  } else if (config.mode === "coin" && Number.isFinite(diameter) && diameter > 0) {
    teachingState.widthMm = diameter.toFixed(2);
    teachingState.lengthMm = diameter.toFixed(2);
  } else {
    if (Number.isFinite(width) && width > 0) teachingState.widthMm = width.toFixed(2);
    if (Number.isFinite(length) && length > 0) teachingState.lengthMm = length.toFixed(2);
  }
  updateTeachingVisionSummary();
  updateTeachingDimensionDisplay();
}

function applyRingDiameters(target, payload) {
  // Explicit fields only: legacy bounding-box width/height are not diameters.
  const inner = Number(payload?.inner_diameter_mm);
  const outer = Number(payload?.outer_diameter_mm);
  target.widthMm = "";
  target.lengthMm = "";
  if (payload?.geometry_ok === true && Number.isFinite(inner) && Number.isFinite(outer)
      && inner > 0 && outer > inner) {
    target.widthMm = inner.toFixed(2);
    target.lengthMm = outer.toFixed(2);
  }
}

function updateTeachingVisionSummary() {
  const shapeNode = document.getElementById("teachingVisionShapeDisplay");
  const diameterNode = document.getElementById("teachingVisionDiameterDisplay");
  const areaNode = document.getElementById("teachingVisionAreaDisplay");
  if (!shapeNode || !diameterNode || !areaNode) return;

  const payload = teachingState.visionMeasurement || {};
  const diameter = Number.parseFloat(payload.diameter_mm);
  const inner = Number.parseFloat(payload.inner_diameter_mm);
  const outer = Number.parseFloat(payload.outer_diameter_mm);
  const area = Number.parseFloat(payload.surface_area_mm2);
  shapeNode.textContent = getTeachingShapeLabel() || "--";
  diameterNode.textContent = payload.geometry_ok && inner > 0 && outer > inner
    ? `${inner.toFixed(2)} / ${outer.toFixed(2)} mm (I/O)`
    : (Number.isFinite(diameter) && diameter > 0 ? `${diameter.toFixed(2)} mm` : "--");
  areaNode.textContent = Number.isFinite(area) && area > 0 ? `${area.toFixed(2)} mm²` : "--";
}

async function fetchVisionSize(shape, kind = "measurement") {
  // Clear previous auto-fill before a fresh ring capture, including API failure.
  // Manual entry remains available if the current hole/depth cannot be measured.
  if (["ring", "bangle"].includes(String(shape).toLowerCase())) {
    if (kind === "teaching") applyVisionToTeaching(null);
    else applyVisionToMeasurement(null);
  }
  const response = await fetch(`/api/vision/size?shape=${encodeURIComponent(shape)}`, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || "Vision service could not detect the sample");
  }
  if (kind === "teaching") {
    applyVisionToTeaching(payload);
  } else {
    applyVisionToMeasurement(payload);
  }
  return payload;
}

function updateOtherShapeSelection() {
  document.querySelectorAll("#otherShapeGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.otherShape === state.otherShape);
  });
}

function updateDimensionFieldSelection() {
  document.getElementById("widthFieldButton").classList.toggle("selected", state.activeDimensionField === "width");
  document.getElementById("lengthFieldButton").classList.toggle("selected", state.activeDimensionField === "length");
  document.getElementById("thicknessFieldButton").classList.toggle("selected", state.activeDimensionField === "thickness");
}

function updateTeachingDimensionFieldSelection() {
  document.getElementById("teachingWidthFieldButton").classList.toggle("selected", teachingState.activeDimensionField === "width");
  document.getElementById("teachingLengthFieldButton").classList.toggle("selected", teachingState.activeDimensionField === "length");
  document.getElementById("teachingThicknessFieldButton").classList.toggle("selected", teachingState.activeDimensionField === "thickness");
}

function updateDimensionDisplay() {
  const config = getMeasurementDimensionConfig();
  document.getElementById("widthLabel").textContent = config.labels.width;
  document.getElementById("lengthLabel").textContent = config.labels.length;
  document.getElementById("thicknessFieldButton").querySelector("span").textContent = config.labels.thickness;
  document.getElementById("lengthFieldButton").classList.toggle("hidden", Boolean(config.hideLength));
  if (config.hideLength && state.activeDimensionField === "length") {
    state.activeDimensionField = "width";
  }
  document.getElementById("widthDisplay").textContent = state.widthMm || "0";
  document.getElementById("lengthDisplay").textContent = config.hideLength ? (state.widthMm || "0") : (state.lengthMm || "0");
  document.getElementById("thicknessDisplay").textContent = state.thicknessMm || "0";
  const geometry = calculateGeometryForMeasurement();
  document.getElementById("sampleAreaDisplay").textContent = `${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("contactRatioDisplay").textContent = `${geometry.contactRatio.toFixed(2)}%`;
  updateDimensionFieldSelection();
}

function updateTeachingDimensionDisplay() {
  const config = getTeachingDimensionConfig();
  document.getElementById("teachingWidthLabel").textContent = config.labels.width;
  document.getElementById("teachingLengthLabel").textContent = config.labels.length;
  document.getElementById("teachingThicknessLabel").textContent = config.labels.thickness;
  document.getElementById("teachingLengthFieldButton").classList.toggle("hidden", Boolean(config.hideLength));
  if (config.hideLength && teachingState.activeDimensionField === "length") {
    teachingState.activeDimensionField = "width";
  }
  document.getElementById("teachingWidthDisplay").textContent = teachingState.widthMm || "0";
  document.getElementById("teachingLengthDisplay").textContent = config.hideLength ? (teachingState.widthMm || "0") : (teachingState.lengthMm || "0");
  document.getElementById("teachingThicknessDisplay").textContent = teachingState.thicknessMm || "0";
  const geometry = calculateGeometryForTeaching();
  document.getElementById("teachingSampleAreaDisplay").textContent = `${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("teachingContactRatioDisplay").textContent = `${geometry.contactRatio.toFixed(2)}%`;
  updateTeachingDimensionFieldSelection();
}

function setDimensionValue(field, value) {
  if (field === "length") {
    state.lengthMm = value.slice(0, 7);
  } else if (field === "thickness") {
    state.thicknessMm = value.slice(0, 7);
  } else {
    state.widthMm = value.slice(0, 7);
  }
  updateDimensionDisplay();
}

function setTeachingDimensionValue(field, value) {
  if (field === "length") {
    teachingState.lengthMm = value.slice(0, 7);
  } else if (field === "thickness") {
    teachingState.thicknessMm = value.slice(0, 7);
  } else {
    teachingState.widthMm = value.slice(0, 7);
  }
  updateTeachingDimensionDisplay();
}

function resetMeasurementInputs() {
  setWeight("");
  state.measurementWeightSampling = false;
  state.measurementWeightReady = false;
  state.widthMm = "";
  state.lengthMm = "";
  state.thicknessMm = "";
  state.visionMeasurement = null;
  state.activeDimensionField = "width";
  state.shape = "Ring";
  state.otherShape = "Pendant";
  updateShapeSelection();
  updateOtherShapeSelection();
  updateDimensionDisplay();
  progressText.textContent = "0%";
  progressBar.style.width = "0%";
  ringMeter.style.strokeDashoffset = "314";
  setWeightControls("measurement", { sampling: false, ready: false, sampleAvailable: false });
  setWeightProgress(weightScreenConfig("measurement"), 0, 10, "Waiting to sample");
}

function weightIsValid() {
  return Number.parseFloat(state.weight || "0") > 0;
}

function weightScreenConfig(kind) {
  const isTeaching = kind === "teaching";
  return {
    kind,
    display: document.getElementById(isTeaching ? "teachingWeightDisplay" : "weightDisplay"),
    status: document.getElementById(isTeaching ? "teachingWeightStatus" : "measurementWeightStatus"),
    raw: document.getElementById(isTeaching ? "teachingWeightRaw" : "measurementWeightRaw"),
    sampleButton: document.getElementById(isTeaching ? "teachingWeightSampleButton" : "measurementWeightSampleButton"),
    nextButton: document.getElementById(isTeaching ? "teachingRecordButton" : "weightNextButton"),
    progress: document.getElementById(isTeaching ? "teachingWeightProgress" : "measurementWeightProgress"),
    progressLabel: document.getElementById(isTeaching ? "teachingWeightProgressLabel" : "measurementWeightProgressLabel"),
    progressCount: document.getElementById(isTeaching ? "teachingWeightProgressCount" : "measurementWeightProgressCount"),
    progressBar: document.getElementById(isTeaching ? "teachingWeightProgressBar" : "measurementWeightProgressBar")
  };
}

function setWeightProgress(config, count, total, label, mode = "active") {
  const safeTotal = Math.max(1, total);
  const safeCount = Math.max(0, Math.min(safeTotal, count));
  const percent = (safeCount / safeTotal) * 100;
  config.progress.classList.toggle("complete", mode === "complete");
  config.progress.classList.toggle("error", mode === "error");
  config.progressLabel.textContent = label;
  config.progressCount.textContent = `${safeCount} / ${safeTotal}`;
  config.progressBar.style.width = `${percent}%`;
}

function stopWeightProgressTimer() {
  clearInterval(state.weightProgressTimer);
  state.weightProgressTimer = null;
}

function startWeightProgressTimer(config, total = 10) {
  stopWeightProgressTimer();
  let count = 0;
  setWeightProgress(config, count, total, "Sampling scale");
  state.weightProgressTimer = setInterval(() => {
    count = Math.min(total - 1, count + 1);
    setWeightProgress(config, count, total, "Averaging readings");
    if (count >= total - 1) {
      stopWeightProgressTimer();
    }
  }, 230);
}

function setWeightControls(kind, { sampling, ready, sampleAvailable = ready }) {
  const config = weightScreenConfig(kind);
  if (kind === "teaching") {
    state.teachingWeightSampling = sampling;
    state.teachingWeightReady = ready;
  } else {
    state.measurementWeightSampling = sampling;
    state.measurementWeightReady = ready;
  }
  config.nextButton.disabled = sampling || !ready;
  config.sampleButton.disabled = sampling || !sampleAvailable;
  config.nextButton.classList.toggle("disabled", config.nextButton.disabled);
  config.sampleButton.classList.toggle("disabled", config.sampleButton.disabled);
}

function showWeightError() {
  const panel = document.querySelector("#weightScreen .value-panel");
  panel.classList.add("error");
  weightDisplay.textContent = "0";
  document.getElementById("measurementWeightStatus").textContent = "Weight required";
  document.getElementById("measurementWeightRaw").textContent = "Please sample the scale again";
  setWeightControls("measurement", { sampling: false, ready: false, sampleAvailable: true });
  setWeightProgress(weightScreenConfig("measurement"), 0, 10, "Weight required", "error");
}

function setTeachingWeight(value) {
  teachingState.weight = value.slice(0, 7);
  document.getElementById("teachingWeightDisplay").textContent = teachingState.weight || "0";
}

function dimensionsAreValid() {
  const config = getMeasurementDimensionConfig();
  const values = {
    width: state.widthMm,
    length: state.lengthMm,
    thickness: state.thicknessMm
  };
  return config.required.every((field) => Number.isFinite(Number(values[field])) && Number(values[field]) > 0)
    && (!["ring", "bangle"].includes(config.mode) || Number(values.length) > Number(values.width));
}

function weightIsValidTeaching() {
  return Number.parseFloat(teachingState.weight || "0") > 0;
}

function teachingDimensionsAreValid() {
  const config = getTeachingDimensionConfig();
  const values = {
    width: teachingState.widthMm,
    length: teachingState.lengthMm,
    thickness: teachingState.thicknessMm
  };
  return config.required.every((field) => Number.isFinite(Number(values[field])) && Number(values[field]) > 0)
    && (!["ring", "bangle"].includes(config.mode) || Number(values.length) > Number(values.width));
}

function resetTeachingWeight() {
  setTeachingWeight("");
  state.teachingWeightSampling = false;
  state.teachingWeightReady = false;
  setWeightControls("teaching", { sampling: false, ready: false, sampleAvailable: false });
  setWeightProgress(weightScreenConfig("teaching"), 0, 10, "Waiting to sample");
}

function resetTeachingInputs() {
  teachingState.material = "Gold";
  teachingState.otherMaterial = "Brass";
  teachingState.purity = "";
  teachingState.shape = "Bar";
  teachingState.otherShape = "Pendant";
  teachingState.weightStd = "";
  teachingState.widthMm = "";
  teachingState.lengthMm = "";
  teachingState.thicknessMm = "";
  teachingState.visionMeasurement = null;
  teachingState.imageReference = null;
  teachingState.activeDimensionField = "width";
  teachingState.latestRecord = null;
  resetTeachingWeight();
  updateTeachingVisionSummary();
  updateTeachingDimensionDisplay();
  updateTeachingMaterialSelection();
  updateTeachingOtherMaterialSelection();
  updateTeachingPuritySelection();
  updateTeachingShapeSelection();
  updateTeachingOtherShapeSelection();
}

function getCurrentFrequencyValue() {
  const index = Math.max(0, Math.min(2, Number(state.activeFrequencySlot || 1) - 1));
  return state.multiFrequenciesKhz[index] || 10;
}

function updateFrequencyModeSelection() {
  document.getElementById("frequencySlot1Button").classList.toggle("selected", state.activeFrequencySlot === 1);
  document.getElementById("frequencySlot2Button").classList.toggle("selected", state.activeFrequencySlot === 2);
  document.getElementById("frequencySlot3Button").classList.toggle("selected", state.activeFrequencySlot === 3);
  document.getElementById("frequencyModeStatus").textContent =
    `Current: Frequency ${state.activeFrequencySlot} (${getCurrentFrequencyValue().toFixed(2)} kHz)`;
  document.getElementById("selectedFrequencyLabel").textContent = `Frequency ${state.activeFrequencySlot}`;
  document.getElementById("selectedFrequencyDisplay").textContent = String(getCurrentFrequencyValue());
  const freqText =
    `Sequence: F1 (${Number(state.multiFrequenciesKhz[0] || 0).toFixed(2)} kHz) -> ` +
    `F2 (${Number(state.multiFrequenciesKhz[1] || 0).toFixed(2)} kHz) -> ` +
    `F3 (${Number(state.multiFrequenciesKhz[2] || 0).toFixed(2)} kHz)`;
  const calTag = document.getElementById("calibrationFrequencyTag");
  const teachTag = document.getElementById("teachingFrequencyTag");
  const liveTag = document.getElementById("liveFrequency");
  if (calTag) calTag.textContent = freqText;
  if (teachTag) teachTag.textContent = freqText;
  if (liveTag) liveTag.textContent = `F${state.activeFrequencySlot} ${getCurrentFrequencyValue().toFixed(2)} kHz`;
}

async function selectFrequencySlot(slot) {
  state.activeFrequencySlot = slot;
  updateFrequencyModeSelection();

  try {
    const response = await fetch("/api/daq/frequency", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_frequency_slot: slot })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || "Unable to set frequency");
    const savedSlot = Number.parseInt(payload.active_frequency_slot, 10);
    if (savedSlot >= 1 && savedSlot <= 3) state.activeFrequencySlot = savedSlot;
  } catch (error) {
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_frequency_slot: slot })
      });
    } catch (saveError) {
      // Keep local selection visible; live view will report serial problems.
    }
  }

  updateFrequencyModeSelection();
  if (screens.liveView.classList.contains("active")) {
    await refreshLiveViewReadings();
  }
}

function updateShapeSelection() {
  document.querySelectorAll(".shape-option").forEach((button) => {
    button.classList.toggle("selected", button.dataset.shape === state.shape);
  });
}

function updateOtherShapeSelection() {
  document.querySelectorAll("#otherShapeGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.otherShape === state.otherShape);
  });
}

function initializeCarouselImages() {
  document.querySelectorAll(".object img").forEach((image) => {
    image.addEventListener("load", () => {
      image.closest(".object").classList.add("has-image");
    });
    image.addEventListener("error", () => {
      image.closest(".object").classList.remove("has-image");
    });

    if (image.complete && image.naturalWidth > 0) {
      image.closest(".object").classList.add("has-image");
    }
  });
}

function updateSystemClock() {
  const now = new Date();
  const date = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
  const time = now.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit"
  });
  document.getElementById("systemDate").textContent = date;
  document.getElementById("systemTime").textContent = time;
  document.getElementById("systemClock").dateTime = now.toISOString();
}

function showPasswordScreen() {
  state.password = "";
  updatePasswordDisplay();
  document.querySelector(".password-panel").classList.remove("error");
  document.getElementById("passwordMessage").textContent = "Enter PIN to continue";
  showScreen("password");
}

function updatePasswordDisplay() {
  const masked = "*".repeat(state.password.length).padEnd(6, "-");
  document.getElementById("passwordDisplay").textContent = masked;
}

function submitPassword() {
  const panel = document.querySelector(".password-panel");
  const message = document.getElementById("passwordMessage");

  if (state.password === ENGINEERING_PIN) {
    panel.classList.remove("error");
    showScreen("engineering");
    return;
  }

  panel.classList.add("error");
  message.textContent = "Invalid PIN";
  state.password = "";
  updatePasswordDisplay();
}

function renderHistory() {
  const table = document.getElementById("historyTable");
  table.innerHTML = `
    <div class="history-row header">
      <span>Date</span>
      <span>Time</span>
      <span>Result</span>
      <span>Weight</span>
      <span>Shape</span>
      <span>Details</span>
    </div>
  `;

  historyRecords.forEach((record) => {
    const row = document.createElement("div");
    row.className = "history-row";
    row.innerHTML = `
      <span>${record.date.replace(" 2026", "")}</span>
      <span>${record.time}</span>
      <strong>${record.result}</strong>
      <span>${record.weight}</span>
      <span>${record.shape}</span>
      <button type="button" data-history-id="${record.id}">View</button>
    `;
    row.addEventListener("click", () => showHistoryDetail(record.id));
    table.appendChild(row);
  });
}

async function loadHistoryRecords() {
  try {
    const response = await fetch("/api/history", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load measurement history");
    const records = await response.json();
    if (!Array.isArray(records)) throw new Error("Measurement history must be an array");
    historyRecords = records;
  } catch (error) {
    try {
      const fallbackResponse = await fetch("measurements.json", { cache: "no-store" });
      if (!fallbackResponse.ok) throw new Error("Unable to load measurements.json");
      const records = await fallbackResponse.json();
      historyRecords = Array.isArray(records) ? records : [...fallbackHistoryRecords];
    } catch (fallbackError) {
      historyRecords = [...fallbackHistoryRecords];
    }
  }

  renderHistory();
}

function renderTeachingRecords() {
  const table = document.getElementById("teachingTable");
  table.innerHTML = `
    <div class="teaching-row header">
      <span>Date</span>
      <span>Material</span>
      <span>Purity</span>
      <span>Shape</span>
      <span>Weight</span>
      <span>Details</span>
    </div>
  `;

  teachingRecords.forEach((record) => {
    const row = document.createElement("div");
    row.className = "teaching-row";
    row.innerHTML = `
      <span>${String(record.date || "--").replace(" 2026", "")}</span>
      <strong title="${record.id || ""}">${record.material || "--"}</strong>
      <span>${record.purity || "--"}</span>
      <span>${record.shape || "--"}</span>
      <span>${record.weight || "--"}</span>
      <button type="button" data-teaching-id="${record.id}">View</button>
    `;
    row.addEventListener("click", () => showTeachingDetail(record.id));
    table.appendChild(row);
  });
}

async function loadTeachingRecords() {
  try {
    const response = await fetch("/api/teaching", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load teaching records");
    const records = await response.json();
    teachingRecords = Array.isArray(records) ? records : [];
  } catch (error) {
    try {
      const response = await fetch("teaching_library.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load teaching_library.json");
      const records = await response.json();
      teachingRecords = Array.isArray(records) ? records : [];
    } catch (fallbackError) {
      teachingRecords = [];
    }
  }

  renderTeachingRecords();
}

function showHistoryDetail(id) {
  const record = historyRecords.find((item) => item.id === id);
  if (!record) return;
  selectedHistoryId = id;

  document.getElementById("detailResult").textContent = record.result;
  document.getElementById("detailDate").textContent = record.date;
  document.getElementById("detailTime").textContent = record.time;
  document.getElementById("detailWeight").textContent = record.weight;
  document.getElementById("detailShape").textContent = record.shape;
  document.getElementById("detailConfidence").textContent = record.confidence;
  document.getElementById("detailStatus").textContent = record.status;
  renderFrequencyCards("detail", record);
  showScreen("historyDetail");
}

function selectTeachingDetailPanel(panel) {
  const dataActive = panel !== "image";
  document.getElementById("teachingDetailDataPanel").classList.toggle("active", dataActive);
  document.getElementById("teachingDetailImagePanel").classList.toggle("active", !dataActive);
  document.getElementById("teachingDetailDataTabButton").classList.toggle("active", dataActive);
  document.getElementById("teachingDetailImageTabButton").classList.toggle("active", !dataActive);
  document.getElementById("teachingDetailDataTabButton").setAttribute("aria-selected", String(dataActive));
  document.getElementById("teachingDetailImageTabButton").setAttribute("aria-selected", String(!dataActive));
}

function showTeachingDetail(id) {
  const record = teachingRecords.find((item) => item.id === id);
  if (!record) return;
  selectedTeachingId = id;

  document.getElementById("teachingDetailMaterial").textContent = record.material;
  document.getElementById("teachingDetailId").textContent = record.id || "--";
  document.getElementById("teachingDetailDate").textContent = record.date;
  document.getElementById("teachingDetailTime").textContent = record.time;
  document.getElementById("teachingDetailShape").textContent = record.shape;
  document.getElementById("teachingDetailWeight").textContent = record.weight;
  document.getElementById("teachingDetailDimensions").textContent = `${Number(record.width_mm || 0).toFixed(2)} × ${Number(record.length_mm || 0).toFixed(2)} × ${Number(record.thickness_mm || 0).toFixed(2)} mm`;
  document.getElementById("teachingDetailArea").textContent = `${Number(record.sample_area_mm2 || 0).toFixed(2)} mm²`;
  document.getElementById("teachingDetailPurity").textContent = record.purity || "Known";
  document.getElementById("teachingDetailSignalMode").textContent = record.measurement_mode || record.acquisition_mode || "--";
  document.getElementById("teachingDetailSamples").textContent = record.samples_per_frequency ? `${record.samples_per_frequency} per frequency` : "--";
  document.getElementById("teachingDetailAmplitude").textContent = record.amplitude_v_peak !== undefined ? `${Number(record.amplitude_v_peak).toFixed(2)} Vpk / ${Number(record.peak_to_peak_v || 0).toFixed(2)} Vpp` : "--";
  document.getElementById("teachingDetailCalibration").textContent = record.calibration_used || "--";
  document.getElementById("teachingDetailCapturedAt").textContent = record.signal_capture?.captured_at || record.created_at || "--";
  document.getElementById("teachingDetailStatus").textContent = record.status || "Reference sample";
  const imageInfo = record.image || null;
  const imageNode = document.getElementById("teachingDetailImage");
  const imageMessage = document.getElementById("teachingDetailImageMessage");
  const imageStatus = document.getElementById("teachingDetailImageStatus");
  loadSavedImageOverlay(imageNode, imageInfo);
  if (imageInfo?.url) {
    imageNode.hidden = false;
    imageNode.src = `${imageInfo.url}?t=${Date.now()}`;
    imageMessage.textContent = imageInfo.captured_at ? `Captured ${imageInfo.captured_at}` : "Saved with this teaching record.";
    imageStatus.textContent = "Saved";
  } else {
    imageNode.removeAttribute("src");
    imageNode.hidden = true;
    imageMessage.textContent = "No image saved with this record.";
    imageStatus.textContent = "Not available";
  }
  selectTeachingDetailPanel("data");
  renderFrequencyCards("teachingDetail", record);
  showScreen("teachingDetail");
}

function formatDelta(delta, deltaPct) {
  if (delta === null || delta === undefined) return "--";
  const sign = Number(delta) >= 0 ? "+" : "";
  const pct = deltaPct === null || deltaPct === undefined ? "" : ` (${sign}${Number(deltaPct).toFixed(3)}%)`;
  return `${sign}${Number(delta).toFixed(6)}${pct}`;
}

function formatCalibrationFrequencyAir(entry) {
  if (!entry || (!entry.ch1 && !entry.ch2)) return "--";
  const ch1Count = Number(entry.ch1?.sample_count || 0);
  const ch2Count = Number(entry.ch2?.sample_count || 0);
  const ch1 = entry.ch1 ? `CH1 ${Number(entry.ch1.rms ?? 0).toFixed(6)} ${entry.ch1.unit || "V"} | ${Number(entry.ch1.std ?? 0).toFixed(6)} std | n=${ch1Count}` : "CH1 --";
  const ch2 = entry.ch2 ? `CH2 ${Number(entry.ch2.rms ?? 0).toFixed(6)} ${entry.ch2.unit || "V"} | ${Number(entry.ch2.std ?? 0).toFixed(6)} std | n=${ch2Count}` : "CH2 pending";
  return `${ch1}\n${ch2}`;
}

function formatSignalCaptureFrequency(record, command) {
  const item = record?.signal_capture?.frequencies?.[command];
  const stats = item?.statistics || {};
  const rms = stats?.ac_rms_v || {};
  const peak = stats?.peak_amplitude_v || {};
  const p2p = stats?.peak_to_peak_v || {};
  const measuredFrequency = stats?.frequency_hz || {};
  const dc = stats?.dc_v || {};
  if (rms.mean === undefined || rms.mean === null) return null;
  const count = Number(item?.number_of_samples || record?.samples_per_frequency || 0);
  const freqKhz = Number(item?.frequency_hz || 0) / 1000;
  return `${Number(rms.mean).toFixed(6)} V RMS ± ${Number(rms.std || 0).toFixed(6)} | ` +
    `${Number(p2p.mean || 0).toFixed(4)} Vpp | ${Number(peak.mean || 0).toFixed(4)} Vpk | ` +
    `${Number(measuredFrequency.mean || 0).toFixed(1)} Hz measured | DC ${Number(dc.mean || 0).toFixed(5)} V | ` +
    `${freqKhz.toFixed(0)} kHz set | n=${count}`;
}

function formatRecordFrequencyStep(sequence, command) {
  const step = (sequence || []).find((item) => String(item.frequency_command || "").toLowerCase() === command);
  const signal = step?.channels?.signal;
  if (signal) {
    return `${Number(signal.rms ?? 0).toFixed(6)} V RMS ± ${Number(signal.std ?? 0).toFixed(6)} | n=${Number(signal.sample_count || 0)}`;
  }
  const ch1 = step?.channels?.ch1;
  const ch2 = step?.channels?.ch2;
  if (!ch1 && !ch2) return "--";
  const ch1Text = ch1
    ? `CH1 ${Number(ch1.rms ?? 0).toFixed(6)} ${ch1.unit || "V"} | ${Number(ch1.std ?? 0).toFixed(6)} std | n=${Number(ch1.sample_count || 0)}`
    : "CH1 --";
  const ch2Text = ch2
    ? `CH2 ${Number(ch2.rms ?? 0).toFixed(6)} ${ch2.unit || "V"} | ${Number(ch2.std ?? 0).toFixed(6)} std | n=${Number(ch2.sample_count || 0)}`
    : "CH2 pending";
  return `${ch1Text}\n${ch2Text}`;
}

function renderFrequencyCards(prefix, record) {
  const sequence = record?.frequency_sequence || [];
  ["f1", "f2", "f3", "f4"].forEach((command, index) => {
    const node = document.getElementById(`${prefix}F${index + 1}`);
    if (!node) return;
    node.textContent = formatSignalCaptureFrequency(record, command) || formatRecordFrequencyStep(sequence, command);
  });
}

function renderClassifierStatus(payload) {
  const classCounts = payload?.class_counts || {};
  const classReadiness = payload?.class_readiness || [];
  const warnings = payload?.warnings || [];
  document.getElementById("classifierTotalRecords").textContent = payload?.teaching_record_count ?? 0;
  document.getElementById("classifierEligibleRecords").textContent = payload?.eligible_record_count ?? 0;
  document.getElementById("classifierClassCount").textContent = payload?.class_count ?? 0;
  document.getElementById("classifierModelStatus").textContent = payload?.model_exists ? "Ready" : "Not trained";
  document.getElementById("classifierTrainedAt").textContent = payload?.model_trained_at || "--";
  document.getElementById("classifierCalibration").textContent = payload?.calibrated_at || "--";
  document.getElementById("classifierExcludedRecords").textContent = payload?.excluded_record_count ?? 0;
  document.getElementById("classifierMethod").textContent = payload?.model_method || "Mahalanobis";
  const selectedAlgorithm = payload?.selected_algorithm || "mahalanobis";
  const selectedMeta = (payload?.classifier_algorithms || []).find((item) => item.key === selectedAlgorithm);
  document.getElementById("classifierSelectedMethod").textContent = selectedMeta?.label || selectedAlgorithm;
  const algorithmSelect = document.getElementById("classifierAlgorithmSelect");
  if (algorithmSelect && algorithmSelect.value !== selectedAlgorithm) {
    algorithmSelect.value = selectedAlgorithm;
  }

  const classList = document.getElementById("classifierClassList");
  const rows = classReadiness.length
    ? classReadiness
    : Object.entries(classCounts).map(([label, count]) => ({
      label,
      sample_count: count,
      minimum_samples: payload?.minimum_active_samples || 5,
      active: count >= (payload?.minimum_active_samples || 5),
      status: count >= (payload?.minimum_active_samples || 5) ? "Active" : "Learning"
    }));
  classList.innerHTML = rows.length
    ? rows
      .sort((a, b) => String(a.label).localeCompare(String(b.label)))
      .map((item) => {
        const minimum = Number(item.minimum_samples || payload?.minimum_active_samples || 5);
        const count = Number(item.sample_count || 0);
        const progress = Math.max(0, Math.min(100, (count / minimum) * 100));
        const threshold = item.acceptance_threshold === null || item.acceptance_threshold === undefined
          ? "--"
          : Number(item.acceptance_threshold).toFixed(3);
        const statusClass = item.active ? "active" : "learning";
        const needed = Number(item.needed_samples || Math.max(0, minimum - count));
        const statusText = item.active ? "Active" : `Learning (${needed} more)`;
        return `
          <div class="classifier-readiness-row ${statusClass}">
            <div>
              <strong>${item.label}</strong>
              <span>${statusText} | ${count} samples | threshold ${threshold}</span>
            </div>
            <em>${item.active ? "ON" : "LEARN"}</em>
            <i style="--ready-width:${progress}%"></i>
          </div>
        `;
      }).join("")
    : "<span>No eligible classes yet</span><strong>--</strong>";

  const warningList = document.getElementById("classifierWarnings");
  const excluded = (payload?.excluded_preview || []).map((item) => `${item.label || item.id || "Record"}: ${item.reason}`);
  const messages = warnings.length ? warnings : excluded;
  warningList.innerHTML = messages.length
    ? messages.slice(0, 8).map((message) => `<span>${message}</span>`).join("")
    : "<span>No warnings</span>";
}

async function loadClassifierStatus() {
  try {
    const response = await fetch("/api/classifier/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load classifier status");
    renderClassifierStatus(await response.json());
  } catch (error) {
    renderClassifierStatus({
      teaching_record_count: 0,
      eligible_record_count: 0,
      class_count: 0,
      model_exists: false,
      warnings: [error.message || "Classifier status unavailable"]
    });
  }
}

async function trainClassifierModel() {
  const button = document.getElementById("classifierTrainButton");
  button.disabled = true;
  button.textContent = "Computing...";
  try {
    const response = await fetch("/api/classifier/train", { method: "POST" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || "Unable to compute classifier");
    await loadClassifierStatus();
  } catch (error) {
    const warningList = document.getElementById("classifierWarnings");
    warningList.innerHTML = `<span>${error.message || "Classifier training failed"}</span>`;
  } finally {
    button.disabled = false;
    button.textContent = "Compute Model";
  }
}

async function saveClassifierAlgorithm() {
  const select = document.getElementById("classifierAlgorithmSelect");
  const warningList = document.getElementById("classifierWarnings");
  if (!select) return;
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ classifier_algorithm: select.value })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || payload.error || "Unable to save classifier method");
    await loadClassifierStatus();
    if (warningList) {
      warningList.innerHTML = "<span>Classifier method saved. Press Compute Model to rebuild this model.</span>";
    }
  } catch (error) {
    if (warningList) {
      warningList.innerHTML = `<span>${error.message || "Classifier method save failed"}</span>`;
    }
  }
}

function calibrationFrequencyDisplayName(key) {
  const labels = { f1: "F1 · 8 kHz", f2: "F2 · 10 kHz", f3: "F3 · 15 kHz", f4: "F4 · 20 kHz" };
  return labels[key] || key.toUpperCase();
}

function formatSignalCalibrationCard(record, key) {
  const item = record?.frequencies?.[key] || {};
  const rms = item?.statistics?.ac_rms_v || {};
  const mean = Number(rms.mean);
  if (!Number.isFinite(mean)) return "--";
  const std = Number(rms.std);
  const validation = record?.last_validation?.frequencies?.[key] || {};
  const drift = Number(validation.drift_pct);
  const driftText = Number.isFinite(drift)
    ? ` · Δ ${drift >= 0 ? "+" : ""}${drift.toFixed(2)}% ${validation.within_threshold ? "PASS" : "FAIL"}`
    : "";
  return `${mean.toFixed(6)} V RMS${Number.isFinite(std) ? ` ± ${std.toFixed(6)}` : ""}${driftText}`;
}

function renderCalibration(record) {
  const safe = record || {};
  state.calibrationRecord = safe;
  const validation = safe.last_validation || safe.validation || {};
  const hasBaseline = Boolean(safe.calibrated_at);

  document.getElementById("calibrationResultTitle").textContent = hasBaseline
    ? (validation.status === "RECALIBRATION REQUIRED" ? "Recalibration Required" : "Air Baseline Saved")
    : "No Air Baseline Saved";
  document.getElementById("calibratedAt").textContent = safe.calibrated_at
    ? new Date(safe.calibrated_at).toLocaleString()
    : "--";
  document.getElementById("calibrationCondition").textContent = safe.condition || "Air / no material";
  document.getElementById("calibrationSampleCount").textContent = safe.samples_per_frequency
    ? `${safe.samples_per_frequency} per frequency · F1–F4`
    : "--";
  document.getElementById("calAmplitude").textContent = Number.isFinite(Number(safe.amplitude_v_peak))
    ? `${Number(safe.amplitude_v_peak).toFixed(2)} V peak`
    : "--";
  document.getElementById("calPeakToPeak").textContent = Number.isFinite(Number(safe.peak_to_peak_v))
    ? `${Number(safe.peak_to_peak_v).toFixed(2)} Vpp`
    : "--";
  document.getElementById("calValidationThreshold").textContent = `${Number(safe.validation_threshold_pct ?? validation.threshold_pct ?? 5).toFixed(2)}%`;
  document.getElementById("calValidationAt").textContent = validation.validated_at
    ? new Date(validation.validated_at).toLocaleString()
    : "Not validated";
  document.getElementById("calValidationStatus").textContent = validation.status || "Not validated";
  document.getElementById("calValidationDrift").textContent = Number.isFinite(Number(validation.max_drift_pct))
    ? `${Number(validation.max_drift_pct).toFixed(2)}%`
    : "--";
  document.getElementById("calibrationValidationNote").textContent = validation.recommendation
    || "Validation compares a fresh AC RMS mean at F1–F4 against this saved baseline. Every frequency must remain within 5%.";

  ["f1", "f2", "f3", "f4"].forEach((key) => {
    const el = document.getElementById(`cal${key.toUpperCase()}Air`);
    if (el) el.textContent = formatSignalCalibrationCard(safe, key);
  });
}

async function loadCalibration() {
  try {
    const response = await fetch("/api/signal/air-calibration", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load signal air calibration");
    renderCalibration(await response.json());
  } catch (error) {
    renderCalibration({});
  }
}

function startCalibration() {
  runCalibrationProgress("calibration");
}

function startCalibrationValidation() {
  runCalibrationProgress("validate");
}

async function runCalibrationProgress(mode) {
  showScreen("calibrationProgress");
  const sampleTarget = 30;
  const frequencies = [
    { key: "F1", hz: "8 kHz" },
    { key: "F2", hz: "10 kHz" },
    { key: "F3", hz: "15 kHz" },
    { key: "F4", hz: "20 kHz" }
  ];
  const estimatedSecondsPerFrequency = 4.5;
  const totalSeconds = estimatedSecondsPerFrequency * frequencies.length;
  const startedAt = Date.now();
  const progressBar = document.getElementById("calibrationProgressBar");
  const progressText = document.getElementById("calibrationProgressText");
  const ring = document.getElementById("calibrationRingMeter");
  const stage = document.getElementById("calibrationStage");
  const durationLabel = document.getElementById("calibrationDurationLabel");
  const frequencyLabel = document.getElementById("calibrationFrequencyLabel");
  const sampleLabel = document.getElementById("calibrationSampleLabel");

  durationLabel.textContent = mode === "validate" ? "Fresh F1–F4 validation" : "F1–F4 calibration";
  stage.textContent = mode === "validate" ? "Starting Validation" : "Starting Calibration";
  frequencyLabel.textContent = "F1 · 8 kHz";
  sampleLabel.textContent = `Sample 0 / ${sampleTarget}`;
  progressBar.style.width = "0%";
  progressText.textContent = "0%";
  ring.style.strokeDashoffset = "314";

  let finished = false;
  const timer = setInterval(() => {
    const elapsedSeconds = (Date.now() - startedAt) / 1000;
    const progress = finished ? 100 : Math.min(98, Math.round((elapsedSeconds / totalSeconds) * 100));
    const slotIndex = Math.min(frequencies.length - 1, Math.floor(elapsedSeconds / estimatedSecondsPerFrequency));
    const slotElapsed = Math.max(0, elapsedSeconds - slotIndex * estimatedSecondsPerFrequency);
    const sample = Math.min(sampleTarget, Math.max(0, Math.round((slotElapsed / estimatedSecondsPerFrequency) * sampleTarget)));
    const freq = frequencies[slotIndex];
    frequencyLabel.textContent = `${freq.key} · ${freq.hz}`;
    sampleLabel.textContent = `Sample ${sample} / ${sampleTarget}`;
    stage.textContent = `${mode === "validate" ? "Validating" : "Calibrating"} ${freq.key}`;
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    ring.style.strokeDashoffset = `${314 - (314 * progress) / 100}`;
  }, 250);

  try {
    if (mode === "validate") {
      await validateCalibration();
    } else {
      await saveCalibration();
    }
  } finally {
    finished = true;
    clearInterval(timer);
    progressBar.style.width = "100%";
    progressText.textContent = "100%";
    ring.style.strokeDashoffset = "0";
    showScreen("calibrationResult");
  }
}

async function saveCalibration() {
  try {
    const response = await fetch("/api/signal/air-calibration/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || payload.error || "Unable to run air calibration");
    renderCalibration(payload);
    return true;
  } catch (error) {
    renderCalibration({
      calibrated_at: null,
      condition: error.message || "Calibration failed. Check the signal service and ADP2230.",
      frequencies: {},
      last_validation: {}
    });
    return false;
  }
}

async function validateCalibration() {
  try {
    const response = await fetch("/api/signal/air-calibration/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || payload.error || "Unable to validate air calibration");
    renderCalibration(payload);
    return true;
  } catch (error) {
    const current = state.calibrationRecord || {};
    renderCalibration({
      ...current,
      last_validation: {
        ...(current.last_validation || {}),
        status: "VALIDATION FAILED",
        recommendation: error.message || "Validation failed",
        max_drift_pct: null
      }
    });
    return false;
  }
}

function updateTeachingMaterialSelection() {
  document.querySelectorAll("#teachingMaterialGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.material === teachingState.material);
  });
}

function updateTeachingOtherMaterialSelection() {
  document.querySelectorAll("#teachingOtherMaterialGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.otherMaterial === teachingState.otherMaterial);
  });
}

function updateTeachingPuritySelection() {
  document.querySelectorAll("#teachingPurityGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.purity === teachingState.purity);
  });
  const display = document.getElementById("teachingPurityDisplay");
  if (display) display.textContent = teachingState.purity || "--";
}

function configureTeachingPurityScreen() {
  const material = getTeachingMaterialLabel();
  const isGold = material === "Gold";
  const isSilver = material === "Silver";
  const eyebrow = document.getElementById("teachingPurityEyebrow");

  if (isGold) {
    eyebrow.textContent = "Step 3 of 9 · Gold purity — select carat / fineness or enter the known value";
  } else if (isSilver) {
    eyebrow.textContent = "Step 3 of 9 · Silver purity — select fineness or enter the known value";
  } else {
    eyebrow.textContent = `Step 3 of 9 · ${material} purity / grade — select a known value or enter it below`;
  }

  document.querySelectorAll("#teachingPurityGrid button").forEach((button) => {
    const purity = button.dataset.purity || "";
    if (purity === "N/A") {
      button.hidden = false;
    } else if (isGold) {
      button.hidden = !purity.includes("/");
    } else {
      button.hidden = !/^\d{3}$/.test(purity);
    }
  });
  updateTeachingPuritySelection();
}

function updateTeachingShapeSelection() {
  document.querySelectorAll("#teachingShapeGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.teachingShape === teachingState.shape);
  });
}

function updateTeachingOtherShapeSelection() {
  document.querySelectorAll("#teachingOtherShapeGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.otherShape === teachingState.otherShape);
  });
}

function getTeachingDimensionConfig() {
  const shape = getTeachingShapeLabel().toLowerCase();
  if (shape === "coin") {
    return {
      mode: "coin",
      labels: { width: "Diameter", length: "Diameter", thickness: "Thickness" },
      required: ["width", "thickness"],
      hideLength: true
    };
  }
  if (shape === "ring" || shape === "bangle") {
    return {
      mode: shape,
      labels: { width: "Inner Diameter", length: "Outer Diameter", thickness: "Thickness" },
      required: ["width", "length", "thickness"]
    };
  }
  if (shape === "bar") {
    return {
      mode: "bar",
      labels: { width: "Width", length: "Length", thickness: "Thickness" },
      required: ["width", "length", "thickness"]
    };
  }
  if (shape === "chain") {
    return {
      mode: "chain",
      labels: { width: "Length", length: "Thickness", thickness: "Link Dia." },
      required: ["width", "length"]
    };
  }
  return {
    mode: "standard",
    labels: { width: "Length", length: "Width", thickness: "Thickness" },
    required: ["width", "length", "thickness"]
  };
}

function calculateGeometryForTeaching() {
  const config = getTeachingDimensionConfig();
  const width = Number.parseFloat(teachingState.widthMm || "0") || 0;
  const length = Number.parseFloat(teachingState.lengthMm || "0") || 0;
  const thickness = Number.parseFloat(teachingState.thicknessMm || "0") || 0;
  return calculateGeometry(width, config.mode === "coin" ? width : length, thickness, config.mode);
}

function buildTeachingDimensionPayload() {
  const config = getTeachingDimensionConfig();
  const width = teachingState.widthMm || "0";
  return {
    width_mm: width,
    length_mm: config.mode === "coin" ? width : (teachingState.lengthMm || "0"),
    thickness_mm: teachingState.thicknessMm || "0",
    dimension_mode: config.mode,
    dimension_labels: config.labels
  };
}

function getTeachingMaterialLabel() {
  return teachingState.material === "Other" ? teachingState.otherMaterial : teachingState.material;
}

function getTeachingShapeLabel() {
  return teachingState.shape === "Other" ? teachingState.otherShape : teachingState.shape;
}

function setTeachingSignalProgress(percent, stageText, instructionText) {
  const safe = Math.max(0, Math.min(100, Number(percent) || 0));
  const progressBar = document.getElementById("teachingProgressBar");
  const progressText = document.getElementById("teachingProgressText");
  const ring = document.getElementById("teachingRingMeter");
  const stage = document.getElementById("teachingStage");
  const instruction = document.querySelector("#teachingRecordScreen .measure-copy p");
  progressBar.style.width = `${safe}%`;
  progressText.textContent = `${Math.round(safe)}%`;
  ring.style.strokeDashoffset = `${314 - (314 * safe) / 100}`;
  if (stageText) stage.textContent = stageText;
  if (instructionText) instruction.textContent = instructionText;
}

function delayMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function animateTeachingSampleProgress(fromPct, toPct, expectedMs, promise) {
  let done = false;
  const startedAt = Date.now();
  const cap = Math.max(fromPct, toPct - 1.2);
  const timer = setInterval(() => {
    if (done) return;
    const elapsed = Date.now() - startedAt;
    const fraction = Math.min(0.96, elapsed / Math.max(500, expectedMs));
    const value = fromPct + ((cap - fromPct) * fraction);
    setTeachingSignalProgress(value);
  }, 150);
  try {
    const result = await promise;
    done = true;
    clearInterval(timer);
    setTeachingSignalProgress(toPct);
    return result;
  } catch (error) {
    done = true;
    clearInterval(timer);
    throw error;
  }
}

async function signalJsonRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || payload.message || `Signal request failed: ${url}`);
  }
  return payload;
}

async function captureTeachingSignalSequence() {
  const sampleTarget = 30;
  const sampleInterval = 0.1;
  const frequencies = [
    { key: "f1", label: "F1", hz: 8000 },
    { key: "f2", label: "F2", hz: 10000 },
    { key: "f3", label: "F3", hz: 15000 },
    { key: "f4", label: "F4", hz: 20000 }
  ];
  const capture = {
    captured_at: new Date().toISOString(),
    condition: "Material present",
    waveform: "sine",
    amplitude_v_peak: 1.0,
    peak_to_peak_v: 2.0,
    samples_per_frequency: sampleTarget,
    sample_interval_s: sampleInterval,
    settle_seconds: 0.5,
    frequency_order: frequencies.map((item) => item.key),
    frequencies: {}
  };

  // The signal capture occupies 0–96%. Saving the completed teaching record occupies 96–100%.
  const segment = 96 / frequencies.length;
  try {
    await fetch("/api/signal/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => null);
    for (let index = 0; index < frequencies.length; index += 1) {
      const freq = frequencies[index];
      const base = index * segment;
      const startDone = base + 2.5;
      const settleDone = base + 5;
      const sampleDone = base + segment - 2;
      const stopDone = base + segment;

      setTeachingSignalProgress(base, `${freq.label} · ${(freq.hz / 1000).toFixed(0)} kHz`, `Starting ${freq.label} at 1.00 V peak...`);
      const startResult = await signalJsonRequest("/api/signal/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset: freq.key })
      });
      setTeachingSignalProgress(startDone, `${freq.label} · ${(freq.hz / 1000).toFixed(0)} kHz`, `${freq.label} running. Waiting 0.5 s for the signal to settle...`);
      await animateTeachingSampleProgress(startDone, settleDone, 500, delayMs(500));

      setTeachingSignalProgress(settleDone, `${freq.label} · ${(freq.hz / 1000).toFixed(0)} kHz`, `Sampling ${freq.label}: 30 measurements in progress...`);
      const sampleResult = await animateTeachingSampleProgress(
        settleDone,
        sampleDone,
        Math.max(3200, sampleTarget * sampleInterval * 1000 + 500),
        signalJsonRequest("/api/signal/sample", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ number_of_samples: sampleTarget, interval: sampleInterval })
        })
      );

      capture.frequencies[freq.key] = {
        frequency_hz: freq.hz,
        start: startResult,
        number_of_samples: sampleResult.number_of_samples ?? sampleTarget,
        interval_s: sampleResult.interval_s ?? sampleInterval,
        statistics: sampleResult.statistics || {},
        measurements: Array.isArray(sampleResult.measurements) ? sampleResult.measurements : []
      };

      setTeachingSignalProgress(sampleDone, `${freq.label} complete`, `${freq.label} samples received. Stopping waveform...`);
      await signalJsonRequest("/api/signal/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}"
      });
      setTeachingSignalProgress(stopDone, `${freq.label} complete`, `${freq.label}: ${capture.frequencies[freq.key].number_of_samples} samples captured successfully.`);
    }
  } catch (error) {
    await fetch("/api/signal/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => null);
    throw error;
  }
  return capture;
}

async function startTeachingRecord() {
  const geometry = calculateGeometryForTeaching();
  const dimensionPayload = buildTeachingDimensionPayload();
  document.getElementById("teachingMaterialSummary").textContent = getTeachingMaterialLabel();
  document.getElementById("teachingShapeSummary").textContent = getTeachingShapeLabel();
  document.getElementById("teachingWeightSummary").textContent = `${teachingState.weight || "0"} g`;
  document.getElementById("teachingDimensionSummary").textContent =
    `${dimensionPayload.width_mm} x ${dimensionPayload.length_mm} x ${dimensionPayload.thickness_mm} mm (${geometry.contactRatio.toFixed(1)}%)`;
  showScreen("teachingRecord");
  setTeachingSignalProgress(0, "Starting F1 · 8 kHz", "Keep the known sample still. Progress advances when each real signal API operation completes.");

  if (teachingState.mode === "validate") {
    // Validation remains a single backend transaction; hold the bar below completion until the backend returns.
    try {
      setTeachingSignalProgress(10, "Validation Capture", "Capturing a fresh validation sample...");
      await runTeachingValidation({ deferResultScreen: true });
      setTeachingSignalProgress(100, "Validation Complete", "Fresh validation capture completed.");
    } catch (error) {
      setTeachingSignalProgress(0, "Validation Failed", error.message || "Validation failed");
    }
    return;
  }

  try {
    const signalCapture = await captureTeachingSignalSequence();
    setTeachingSignalProgress(96, "Saving Teaching Record", "F1–F4 complete. Saving measurements and captured image...");
    const saved = await saveTeachingRecord({ deferResultScreen: true, signalCapture });
    if (!saved) {
      setTeachingSignalProgress(96, "Save Failed", teachingState.latestRecord?.status || "Teaching record could not be saved.");
      showScreen("teachingSaved");
      return;
    }
    setTeachingSignalProgress(100, "Capture Complete", "F1–F4 signal data and teaching record saved.");
    await delayMs(350);
    showScreen("teachingRemove");
  } catch (error) {
    teachingState.latestRecord = {
      material: getTeachingMaterialLabel(),
      purity: teachingState.purity || "Not applicable",
      shape: getTeachingShapeLabel(),
      weight: `${teachingState.weight || "0"} g`,
      id: "Not saved",
      status: error.message || "Teaching signal capture failed.",
      signal_capture: { frequencies: {} }
    };
    renderTeachingSaved(teachingState.latestRecord);
    setTeachingSignalProgress(0, "Signal Capture Failed", teachingState.latestRecord.status);
    const status = document.getElementById("teachingDetectedImageStatus");
    if (status) status.textContent = `${teachingState.latestRecord.status} Press Next to retry.`;
    showScreen("teachingDimension");
    selectTeachingDimensionPanel("dimensions");
  }
}

async function runTeachingValidation(options = {}) {
  const currentFrequency = getCurrentFrequencyValue();
  const dimensionPayload = buildTeachingDimensionPayload();
  const requestBody = {
    material: getTeachingMaterialLabel(),
    purity: teachingState.purity || "Not applicable",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
    image: teachingState.imageReference,
    frequency_hz: currentFrequency,
    frequency_slot: state.activeFrequencySlot
  };

  try {
    const response = await fetch("/api/teaching/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody)
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || "Unable to validate sample");
    }
    teachingState.latestRecord = await response.json();
  } catch (error) {
    teachingState.latestRecord = {
      ...requestBody,
      ch1_rms: "--",
      ch2_rms: "--",
      ratio: "--",
      ch1_delta: null,
      ch2_delta: null,
      validation_result: "FAIL",
      confidence: "0%",
      status: error.message || "Validation failed. Check USB serial and try again."
    };
  }

  renderTeachingSaved(teachingState.latestRecord);
  if (!options.deferResultScreen) return;
  showScreen("teachingRemove");
}

async function saveTeachingRecord(options = {}) {
  const dimensionPayload = buildTeachingDimensionPayload();
  let saved = false;
  const record = {
    material: getTeachingMaterialLabel(),
    purity: teachingState.purity || "Not applicable",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    weight_std_g: teachingState.weightStd || null,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
    image: teachingState.imageReference,
    signal_capture: options.signalCapture || null,
    samples_per_frequency: 30,
    sample_interval_s: 0.1
  };

  try {
    const response = await fetch("/api/teaching", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record)
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || "Unable to save teaching record");
    }
    teachingState.latestRecord = await response.json();
    saved = true;
    await loadTeachingRecords();
  } catch (error) {
    teachingState.latestRecord = {
      ...record,
      id: "Not saved",
      status: error.message || "Teaching failed. Check the signal service and ADP2230, then try again.",
      signal_capture: options.signalCapture || { frequencies: {} }
    };
  }

  renderTeachingSaved(teachingState.latestRecord);
  return saved;
}


function selectTeachingSavedPanel(panel) {
  const dataActive = panel !== "image";
  document.getElementById("teachingSavedDataPanel").classList.toggle("active", dataActive);
  document.getElementById("teachingSavedImagePanel").classList.toggle("active", !dataActive);
  document.getElementById("teachingSavedDataTabButton").classList.toggle("active", dataActive);
  document.getElementById("teachingSavedImageTabButton").classList.toggle("active", !dataActive);
  document.getElementById("teachingSavedDataTabButton").setAttribute("aria-selected", String(dataActive));
  document.getElementById("teachingSavedImageTabButton").setAttribute("aria-selected", String(!dataActive));
}

function renderTeachingSaved(record) {
  const validateMode = teachingState.mode === "validate";
  document.getElementById("teachingSavedEyebrow").textContent = validateMode ? "Step 9 of 9 · Validation Result" : "Step 9 of 9 · Teaching Result";
  document.getElementById("teachingSavedAgainButton").textContent = validateMode ? "Scan New Validation" : "Scan New Material";
  document.getElementById("teachingSavedMaterial").textContent = record.material || "--";
  document.getElementById("teachingSavedRecordId").textContent = record.id || "--";
  document.getElementById("teachingSavedShape").textContent = record.shape || "--";
  document.getElementById("teachingSavedWeight").textContent = record.weight || "--";
  document.getElementById("teachingSavedPurity").textContent = record.purity || "Known";
  document.getElementById("teachingSavedSignalMode").textContent = record.measurement_mode || record.acquisition_mode || "--";
  document.getElementById("teachingSavedSamples").textContent = record.samples_per_frequency ? `${record.samples_per_frequency} per frequency` : "--";
  document.getElementById("teachingSavedCalibration").textContent = record.calibration_used || "--";
  document.getElementById("teachingSavedStatus").textContent = record.status || "Reference sample";
  const savedImageInfo = record.image || null;
  const savedImageNode = document.getElementById("teachingSavedImage");
  const savedImageMessage = document.getElementById("teachingSavedImageMessage");
  loadSavedImageOverlay(savedImageNode, savedImageInfo);
  document.getElementById("teachingSavedImageStatus").textContent = savedImageInfo?.url ? "Saved" : "Not available";
  if (savedImageInfo?.url) {
    savedImageNode.hidden = false;
    savedImageNode.src = `${savedImageInfo.url}?t=${Date.now()}`;
    savedImageMessage.textContent = savedImageInfo.captured_at ? `Captured ${savedImageInfo.captured_at}` : "Saved with this teaching record.";
  } else {
    savedImageNode.removeAttribute("src");
    savedImageNode.hidden = true;
    savedImageMessage.textContent = "No image saved with this record.";
  }
  selectTeachingSavedPanel("data");
  renderFrequencyCards("teachingSaved", record);
}


function showDeletePasswordScreen() {
  deletePassword = "";
  updateDeletePasswordDisplay();
  document.querySelector("#deletePasswordScreen .password-panel").classList.remove("error", "warning");
  document.getElementById("deletePasswordMessage").textContent = "Enter PIN to delete record";
  showScreen("deletePassword");
}

function updateDeletePasswordDisplay() {
  const masked = "*".repeat(deletePassword.length).padEnd(6, "-");
  document.getElementById("deletePasswordDisplay").textContent = masked;
}

async function confirmDelete() {
  const panel = document.querySelector("#deletePasswordScreen .password-panel");
  const message = document.getElementById("deletePasswordMessage");

  if (deletePassword !== ADMIN_PIN) {
    panel.classList.add("error");
    message.textContent = "Invalid PIN";
    deletePassword = "";
    updateDeletePasswordDisplay();
    return;
  }

  const isTeachingDelete = Boolean(selectedTeachingId);
  const deleteUrl = isTeachingDelete
    ? `/api/teaching/${selectedTeachingId}/delete`
    : `/api/history/${selectedHistoryId}/delete`;

  try {
    const response = await fetch(deleteUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: deletePassword })
    });

    if (!response.ok) throw new Error("Delete failed");
    if (isTeachingDelete) {
      await loadTeachingRecords();
    } else {
      await loadHistoryRecords();
    }
  } catch (error) {
    if (isTeachingDelete) {
      teachingRecords = teachingRecords.filter((record) => record.id !== selectedTeachingId);
      renderTeachingRecords();
    } else {
      historyRecords = historyRecords.filter((record) => record.id !== selectedHistoryId);
      renderHistory();
    }
  }

  selectedHistoryId = null;
  selectedTeachingId = null;
  showScreen(isTeachingDelete ? "teachingRecords" : "history");
}

function startMeasurement() {
  const currentFrequency = getCurrentFrequencyValue();
  const geometry = calculateGeometryForMeasurement();
  const dimensionPayload = buildMeasurementDimensionPayload();
  document.getElementById("weightSummary").textContent = `${state.weight || "0"} g`;
  document.getElementById("shapeSummary").textContent = `${getMeasurementShapeLabel()} @ ${Number(currentFrequency).toFixed(2)} kHz`;
  document.getElementById("dimensionSummary").textContent =
    `${dimensionPayload.width_mm} x ${dimensionPayload.length_mm} x ${dimensionPayload.thickness_mm} mm (${geometry.contactRatio.toFixed(1)}%)`;
  showScreen("measure");

  let progress = 0;
  let matchingTicks = 0;
  let resultStarted = false;
  const stages = [
    { limit: 12, title: "F1 Measuring", note: "Switching to F1 and waiting for signal to settle." },
    { limit: 22, title: "F1 Complete", note: "F1 reading captured successfully." },
    { limit: 40, title: "F2 Measuring", note: "Switching to F2 and taking the next reading." },
    { limit: 52, title: "F2 Complete", note: "F2 reading captured successfully." },
    { limit: 72, title: "F3 Measuring", note: "Switching to F3 and collecting the final reading." },
    { limit: 84, title: "F3 Complete", note: "F3 reading captured successfully." },
    { limit: 92, title: "Analyzing", note: "Computing calibrated signal features." },
    { limit: 100, title: "Classifying", note: "Applying the selected detector model." }
  ];

  state.progressTimer = setInterval(() => {
    if (progress < 92) {
      progress += 2;
    } else {
      matchingTicks += 1;
      progress = 92 + (matchingTicks % 8);
    }
    const stage = stages.find((item) => progress <= item.limit) || stages[stages.length - 1];
    measureStage.textContent = progress >= 92 ? "Classifying" : stage.title;
    measureInstruction.textContent = progress >= 92
      ? "Processing classifier result. Please wait..."
      : stage.note;
    progressText.textContent = `${progress}%`;
    progressBar.style.width = `${progress}%`;
    ringMeter.style.strokeDashoffset = `${314 - (314 * progress) / 100}`;

    if (progress >= 92 && !resultStarted) {
      resultStarted = true;
      showResult().finally(() => {
        clearInterval(state.progressTimer);
        progressText.textContent = "100%";
        progressBar.style.width = "100%";
        ringMeter.style.strokeDashoffset = "0";
      });
    }
  }, 300);
}

async function showResult() {
  let record = null;
  const currentFrequency = getCurrentFrequencyValue();
  const dimensionPayload = buildMeasurementDimensionPayload();
  try {
    const response = await fetch("/api/measurement/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weight: state.weight || "0",
        shape: getMeasurementShapeLabel(),
        ...dimensionPayload,
        vision_measurement: state.visionMeasurement,
        frequency_hz: currentFrequency,
        frequency_slot: state.activeFrequencySlot
      })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "Unable to verify material");
    record = payload;
  } catch (error) {
    record = {
      result: "Unable to Detect Material",
      confidence: "0%",
      weight: `${state.weight || "0"} g`,
      shape: getMeasurementShapeLabel(),
      ...dimensionPayload,
      status: error.message || "No matching reference record found",
      needs_verification: true,
      frequency_hz: currentFrequency
    };
  }

  document.getElementById("resultMaterial").textContent = record.result || "Unable to Detect Material";
  document.getElementById("resultConfidence").textContent = "";
  document.getElementById("resultWeight").textContent = record.weight || `${state.weight || "0"} g`;
  document.getElementById("resultShape").textContent = record.shape || getMeasurementShapeLabel();
  document.getElementById("resultStatus").textContent = record.status || "Saved locally";
  const statusNode = document.getElementById("resultStatus");
  const needsVerification = Boolean(record.needs_verification);
  statusNode.classList.toggle("signal-ok", !needsVerification);
  statusNode.classList.toggle("signal-warn", needsVerification);
  statusNode.classList.toggle("down", false);

  await loadHistoryRecords();
  showScreen("result");
}

async function loadLatestSensors() {
  try {
    const response = await fetch("/api/sensors/latest", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to read sensors");
    return await response.json();
  } catch (error) {
    return {
      status: "error",
      ch1: { valid: false, error: "Cannot contact Flask sensor API" },
      ch2: { valid: false, error: "Cannot contact Flask sensor API" }
    };
  }
}

function sensorsAreValid(sensors) {
  return (sensors?.status === "online" || sensors?.status === "partial") && sensors?.ch1?.valid === true;
}

function updateAcquisitionModeDisplay() {
  // Simulator switching has been retired from the kiosk UI. Keep this helper
  // null-safe because older cached pages may still contain the legacy fields.
  const modeValue = document.getElementById("modeValue");
  const modeToggle = document.getElementById("modeToggleButton");
  if (!modeValue || !modeToggle) return;
  modeValue.textContent = "DAQ";
  modeToggle.textContent = "DAQ Active";
  modeToggle.classList.add("active");
}

function updateDetectorConfidenceDisplay() {
  document.getElementById("detectorConfidenceDisplay").textContent = state.detectorConfidenceInput || "40";
}

async function loadAcquisitionMode() {
  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to read settings");
    const settings = await response.json();
    state.acquisitionMode = "daq";
    const threshold = Number(settings.confidence_threshold_pct);
    state.confidenceThresholdPct = Number.isFinite(threshold) ? threshold : 40;
    state.detectorConfidenceInput = String(Math.round(state.confidenceThresholdPct));
    const loadedFrequencies = Array.isArray(settings.multi_frequencies_khz) ? settings.multi_frequencies_khz : [10, 20, 30];
    state.multiFrequenciesKhz = loadedFrequencies.slice(0, 3).map((value, index) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : [10, 20, 30][index];
    });
    const slot = Number.parseInt(settings.active_frequency_slot, 10);
    state.activeFrequencySlot = slot >= 1 && slot <= 3 ? slot : 1;
  } catch (error) {
    state.acquisitionMode = "daq";
    state.confidenceThresholdPct = 40;
    state.detectorConfidenceInput = "40";
    state.multiFrequenciesKhz = [10, 20, 30];
    state.activeFrequencySlot = 1;
  }

  updateAcquisitionModeDisplay();
  updateDetectorConfidenceDisplay();
  updateFrequencyModeSelection();
}

async function toggleAcquisitionMode() {
  const nextMode = state.acquisitionMode === "daq" ? "simulator" : "daq";
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acquisition_mode: nextMode })
    });
    if (!response.ok) throw new Error("Unable to save settings");
    const settings = await response.json();
    state.acquisitionMode = settings.acquisition_mode === "daq" ? "daq" : "simulator";
    const threshold = Number(settings.confidence_threshold_pct);
    state.confidenceThresholdPct = Number.isFinite(threshold) ? threshold : state.confidenceThresholdPct;
  } catch (error) {
    state.acquisitionMode = nextMode;
  }

  updateAcquisitionModeDisplay();
  if (screens.liveView.classList.contains("active")) {
    await startLiveViewMonitor();
  }
}

async function saveDetectorSettings() {
  const threshold = Number.parseInt(state.detectorConfidenceInput || "40", 10);
  const safeThreshold = Number.isFinite(threshold) ? Math.max(0, Math.min(100, threshold)) : 40;
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confidence_threshold_pct: safeThreshold })
    });
    if (!response.ok) throw new Error("Unable to save detector settings");
    const settings = await response.json();
    state.confidenceThresholdPct = Number(settings.confidence_threshold_pct) || safeThreshold;
    state.detectorConfidenceInput = String(Math.round(state.confidenceThresholdPct));
  } catch (error) {
    state.detectorConfidenceInput = String(safeThreshold);
  }
  updateDetectorConfidenceDisplay();
  showScreen("engineering");
}

async function saveFrequencySettings() {
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        multi_frequencies_khz: state.multiFrequenciesKhz,
        active_frequency_slot: state.activeFrequencySlot
      })
    });
    if (!response.ok) throw new Error("Unable to save frequency settings");
    const settings = await response.json();
    state.multiFrequenciesKhz = (settings.multi_frequencies_khz || [10, 20, 30]).slice(0, 3);
    const slot = Number.parseInt(settings.active_frequency_slot, 10);
    state.activeFrequencySlot = slot >= 1 && slot <= 3 ? slot : state.activeFrequencySlot;
  } catch (error) {
    // Keep local values for demo continuity.
  }
  updateFrequencyModeSelection();
  showScreen("engineering");
}

function getSensorErrorMessage(sensors) {
  const ch1Error = sensors?.ch1?.error;
  const ch2Error = sensors?.ch2?.error;
  if (ch1Error && ch2Error) return "CH1 and CH2 unavailable";
  if (ch1Error) return `CH1 unavailable`;
  if (ch2Error) return `CH2 unavailable`;
  return "Sensor data not valid";
}

async function saveMeasurementRecord(record) {
  try {
    const response = await fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record)
    });
    if (!response.ok) throw new Error("Save failed");
    await loadHistoryRecords();
  } catch (error) {
    const now = new Date();
    historyRecords.unshift({
      id: `M-${now.getHours()}${now.getMinutes()}${now.getSeconds()}`,
      date: now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
      time: now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
      ...record
    });
    renderHistory();
  }
}

const SIGNAL_LIVE_INTERVAL_MS = 500;

function signalLiveMetric(value, digits = 6, unit = "V") {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(digits)} ${unit}` : `-- ${unit}`;
}

function signalLiveVoltageMetric(value, digitsV = 6) {
  const number = Number(value);
  const useMv = state.signalLiveUnit === "mV";
  const unit = useMv ? "mV" : "V";
  if (!Number.isFinite(number)) return `-- ${unit}`;
  const scaled = useMv ? number * 1000 : number;
  const digits = useMv ? Math.max(2, digitsV - 3) : digitsV;
  return `${scaled.toFixed(digits)} ${unit}`;
}

function updateSignalLivePresetUi() {
  const preset = SIGNAL_PRESETS[state.signalPreset] || SIGNAL_PRESETS.f1;
  document.querySelectorAll("#liveSignalPresetGrid button[data-signal-preset]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.signalPreset === state.signalPreset);
  });
  const label = document.getElementById("liveSelectedFrequency");
  if (label) label.textContent = `${preset.label} · ${(preset.frequencyHz / 1000).toFixed(2)} kHz`;
}

function updateSignalLiveOptionsUi() {
  document.querySelectorAll("#liveAmplitudeToggle button[data-live-vpp]").forEach((button) => {
    button.classList.toggle("selected", Number(button.dataset.liveVpp) === Number(state.signalLiveVpp));
  });
  document.querySelectorAll("#liveUnitToggle button[data-live-unit]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.liveUnit === state.signalLiveUnit);
  });
  document.querySelectorAll("#liveModeToggle button[data-live-mode]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.liveMode === state.signalLiveMode);
  });

  const selectedAmplitude = document.getElementById("liveSelectedAmplitude");
  if (selectedAmplitude) selectedAmplitude.textContent = `${Number(state.signalLiveVpp).toFixed(2)} Vpp`;

  const rawPanel = document.getElementById("liveRawPanel");
  const deltaPanel = document.getElementById("liveDeltaPanel");
  const isDelta = state.signalLiveMode === "delta";
  if (rawPanel) rawPanel.hidden = isDelta;
  if (deltaPanel) deltaPanel.hidden = !isDelta;
}

function setSignalLiveRunning(running) {
  state.signalLiveRunning = Boolean(running);
  const status = document.getElementById("liveSignalStatus");
  const polling = document.getElementById("livePollingStatus");
  const startButton = document.getElementById("liveSignalStartButton");
  const stopButton = document.getElementById("liveSignalStopButton");
  if (status) status.textContent = state.signalLiveRunning ? "Running" : "Stopped";
  if (polling) polling.textContent = state.signalLiveRunning ? "Polling every 0.5 s" : "Polling stopped";
  if (startButton) startButton.disabled = state.signalLiveRunning;
  if (stopButton) stopButton.disabled = !state.signalLiveRunning;
}

function resetSignalLiveDeltaBaseline(useCurrent = false) {
  const current = Number(state.signalLiveLatest?.ac_rms_v);
  state.signalLiveDeltaBaseline = useCurrent && Number.isFinite(current) && current !== 0 ? current : null;
  renderSignalLiveDelta(useCurrent ? (state.signalLiveLatest || {}) : {});
}

function renderSignalLiveDelta(payload) {
  const dropNode = document.getElementById("liveDeltaDrop");
  const referenceNode = document.getElementById("liveDeltaReference");
  if (!dropNode || !referenceNode) return;

  const current = Number(payload?.ac_rms_v);
  if (state.signalLiveMode !== "delta") return;

  if (state.signalLiveDeltaBaseline === null && Number.isFinite(current) && current !== 0) {
    state.signalLiveDeltaBaseline = current;
  }

  const baseline = Number(state.signalLiveDeltaBaseline);
  if (!Number.isFinite(current) || !Number.isFinite(baseline) || baseline === 0) {
    dropNode.textContent = "--%";
    referenceNode.textContent = "Waiting for a valid AC RMS reading to establish the 100% reference.";
    return;
  }

  const dropPct = ((baseline - current) / baseline) * 100;
  dropNode.textContent = `${dropPct.toFixed(2)}%`;
  const baseText = signalLiveVoltageMetric(baseline, 6);
  referenceNode.textContent = `100% reference: ${baseText} AC RMS · current signal is ${Math.max(0, 100 - dropPct).toFixed(2)}% of reference`;
}

function renderSignalLiveMeasurement(payload) {
  const hasMeasurement = payload.ac_rms_v !== undefined || payload.peak_amplitude_v !== undefined || payload.dc_v !== undefined;
  if (hasMeasurement) {
    state.signalLiveLatest = { ...(state.signalLiveLatest || {}), ...payload };
    document.getElementById("liveAcRms").textContent = signalLiveVoltageMetric(payload.ac_rms_v, 6);
    document.getElementById("livePeakAmplitude").textContent = signalLiveVoltageMetric(payload.peak_amplitude_v, 6);
    document.getElementById("livePeakToPeak").textContent = signalLiveVoltageMetric(payload.peak_to_peak_v, 6);
    document.getElementById("liveMeasuredFrequency").textContent = signalLiveMetric(payload.frequency_hz, 2, "Hz");
    document.getElementById("liveDcVoltage").textContent = signalLiveVoltageMetric(payload.dc_v, 6);
    document.getElementById("liveAdcSampleRate").textContent = signalLiveMetric(payload.adc_sample_rate_hz, 0, "Hz");
    document.getElementById("liveAdcPoints").textContent = Number.isFinite(Number(payload.adc_points)) ? String(payload.adc_points) : "--";
    document.getElementById("liveSignalUpdated").textContent = new Date().toLocaleTimeString();
    document.getElementById("liveSignalMessage").textContent = state.signalLiveMode === "delta"
      ? "Delta is referenced to the AC RMS value captured as 100%."
      : "Live measurement received from the ADP2230 signal service.";
    renderSignalLiveDelta(payload);
  }

  const commandedFrequency = payload.frequency_set_hz ?? payload.frequency_hz;
  const commandedAmplitude = payload.amplitude_set_v ?? payload.amplitude_v_peak;
  if (Number.isFinite(Number(commandedFrequency))) {
    document.getElementById("liveCommandedFrequency").textContent = signalLiveMetric(commandedFrequency, 0, "Hz");
  }
  if (Number.isFinite(Number(commandedAmplitude))) {
    document.getElementById("liveCommandedAmplitude").textContent = signalLiveVoltageMetric(commandedAmplitude, 3).replace(/ (m?V)$/, " $1pk");
    const actualVpp = Number(commandedAmplitude) * 2;
    if (Math.abs(actualVpp - 1) < 0.05 || Math.abs(actualVpp - 2) < 0.05) {
      state.signalLiveVpp = Math.abs(actualVpp - 1) < Math.abs(actualVpp - 2) ? 1 : 2;
      updateSignalLiveOptionsUi();
    }
  }

  const frequencySet = Number(commandedFrequency);
  if (Number.isFinite(frequencySet)) {
    const matched = Object.entries(SIGNAL_PRESETS).find(([, item]) => item.frequencyHz === Math.round(frequencySet));
    if (matched) {
      state.signalPreset = matched[0];
      updateSignalLivePresetUi();
      updateSignalPresetSelection();
    }
  }
}

function clearSignalLiveValues(message = "Signal stopped. Select a frequency and press Start.") {
  document.getElementById("liveSignalMessage").textContent = message;
}

async function pollSignalLiveMeasurement() {
  if (!state.signalLiveRunning || state.signalLiveBusy || !screens.liveView.classList.contains("active")) return;
  state.signalLiveBusy = true;
  try {
    const response = await fetch("/api/signal/measurement", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Unable to read live signal");
    }
    renderSignalLiveMeasurement(payload);
  } catch (error) {
    document.getElementById("liveSignalMessage").textContent = `Live read error: ${error.message || "Signal service unavailable"}`;
    if (/not running/i.test(String(error.message || ""))) {
      setSignalLiveRunning(false);
      stopSignalLivePolling();
    }
  } finally {
    state.signalLiveBusy = false;
  }
}

function startSignalLivePolling() {
  clearInterval(state.signalLiveTimer);
  if (!state.signalLiveRunning) return;
  pollSignalLiveMeasurement();
  state.signalLiveTimer = setInterval(pollSignalLiveMeasurement, SIGNAL_LIVE_INTERVAL_MS);
}

function stopSignalLivePolling() {
  clearInterval(state.signalLiveTimer);
  state.signalLiveTimer = null;
  state.signalLiveBusy = false;
}

async function loadSignalLiveStatus() {
  updateSignalLivePresetUi();
  updateSignalLiveOptionsUi();
  try {
    const response = await fetch("/api/signal/status", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Signal service unavailable");
    }

    const running = payload.signal_running ?? (String(payload.status || "").toLowerCase() === "running");
    const frequency = Number(payload.frequency_set_hz ?? payload.frequency_hz);
    const amplitude = Number(payload.amplitude_v_peak ?? payload.amplitude_set_v);
    if (Number.isFinite(frequency)) {
      const matched = Object.entries(SIGNAL_PRESETS).find(([, item]) => item.frequencyHz === Math.round(frequency));
      if (matched) state.signalPreset = matched[0];
    }
    if (Number.isFinite(amplitude)) {
      const vpp = amplitude * 2;
      if (Math.abs(vpp - 1) < 0.05 || Math.abs(vpp - 2) < 0.05) {
        state.signalLiveVpp = Math.abs(vpp - 1) < Math.abs(vpp - 2) ? 1 : 2;
      }
    }
    updateSignalLivePresetUi();
    updateSignalLiveOptionsUi();
    updateSignalPresetSelection();
    setSignalLiveRunning(running);
    document.getElementById("liveSignalMessage").textContent = running
      ? "Signal is already running. Live polling has started."
      : "Select F1–F4, output level and display mode, then press Start.";
    if (running) startSignalLivePolling();
  } catch (error) {
    setSignalLiveRunning(false);
    document.getElementById("liveSignalStatus").textContent = "Offline";
    document.getElementById("liveSignalMessage").textContent = `Signal service error: ${error.message || "Unable to get status"}`;
  }
}

async function startSignalLive() {
  stopSignalLivePolling();
  if (state.signalLiveMode === "delta") resetSignalLiveDeltaBaseline(false);
  document.getElementById("liveSignalStatus").textContent = "Starting...";
  document.getElementById("liveSignalMessage").textContent = `Starting ${String(state.signalPreset || "f1").toUpperCase()} at ${Number(state.signalLiveVpp).toFixed(0)} Vpp...`;
  try {
    const response = await fetch("/api/signal/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: state.signalPreset, peak_to_peak_v: state.signalLiveVpp })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Unable to start signal");
    }
    setSignalLiveRunning(true);
    renderSignalLiveMeasurement(payload);
    document.getElementById("liveSignalMessage").textContent = state.signalLiveMode === "delta"
      ? "Signal started. The first valid AC RMS reading becomes the 100% reference."
      : "Signal started. Reading live values every 0.5 s.";
    startSignalLivePolling();
  } catch (error) {
    setSignalLiveRunning(false);
    document.getElementById("liveSignalStatus").textContent = "Error";
    document.getElementById("liveSignalMessage").textContent = `Start error: ${error.message || "Unable to start signal"}`;
  }
}

async function stopSignalLive() {
  stopSignalLivePolling();
  document.getElementById("liveSignalStatus").textContent = "Stopping...";
  try {
    const response = await fetch("/api/signal/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Unable to stop signal");
    }
    setSignalLiveRunning(false);
    clearSignalLiveValues("Signal stopped. Last measured values are retained on screen.");
    document.getElementById("liveSignalUpdated").textContent = new Date().toLocaleTimeString();
  } catch (error) {
    setSignalLiveRunning(false);
    document.getElementById("liveSignalStatus").textContent = "Error";
    document.getElementById("liveSignalMessage").textContent = `Stop error: ${error.message || "Unable to stop signal"}`;
  }
}

async function selectSignalLivePreset(preset) {
  if (!SIGNAL_PRESETS[preset] || preset === state.signalPreset) return;
  const wasRunning = state.signalLiveRunning;
  if (wasRunning) await stopSignalLive();
  state.signalPreset = preset;
  resetSignalLiveDeltaBaseline(false);
  updateSignalLivePresetUi();
  updateSignalPresetSelection();
  const selected = SIGNAL_PRESETS[preset];
  document.getElementById("liveSignalMessage").textContent = wasRunning
    ? `Changing to ${selected.label} ${(selected.frequencyHz / 1000).toFixed(0)} kHz...`
    : `${selected.label} selected. Press Start to output ${(selected.frequencyHz / 1000).toFixed(0)} kHz.`;
  if (wasRunning) await startSignalLive();
}

async function selectSignalLiveAmplitude(vpp) {
  const next = Number(vpp);
  if (![1, 2].includes(next) || next === Number(state.signalLiveVpp)) return;
  const wasRunning = state.signalLiveRunning;
  if (wasRunning) await stopSignalLive();
  state.signalLiveVpp = next;
  resetSignalLiveDeltaBaseline(false);
  updateSignalLiveOptionsUi();
  document.getElementById("liveSignalMessage").textContent = wasRunning
    ? `Changing output to ${next.toFixed(0)} Vpp...`
    : `${next.toFixed(0)} Vpp selected (${(next / 2).toFixed(1)} V peak).`;
  if (wasRunning) await startSignalLive();
}

function selectSignalLiveUnit(unit) {
  if (!["V", "mV"].includes(unit) || unit === state.signalLiveUnit) return;
  state.signalLiveUnit = unit;
  updateSignalLiveOptionsUi();
  if (state.signalLiveLatest) renderSignalLiveMeasurement(state.signalLiveLatest);
  else renderSignalLiveDelta({});
}

function selectSignalLiveMode(mode) {
  if (!["raw", "delta"].includes(mode)) return;
  if (mode === "delta") {
    state.signalLiveMode = "delta";
    resetSignalLiveDeltaBaseline(true);
  } else {
    state.signalLiveMode = "raw";
    state.signalLiveDeltaBaseline = null;
  }
  updateSignalLiveOptionsUi();
  if (state.signalLiveLatest) renderSignalLiveMeasurement(state.signalLiveLatest);
}

async function startLiveViewMonitor() {
  stopSignalLivePolling();
  await loadSignalLiveStatus();
}

async function exitSignalLiveView(targetScreen) {
  if (state.signalLiveRunning) {
    await stopSignalLive();
  } else {
    stopSignalLivePolling();
  }
  showScreen(targetScreen);
}

function loadCellDisplayPayload(payload) {
  return payload?.service_payload && typeof payload.service_payload === "object"
    ? payload.service_payload
    : payload;
}

function setLoadCellBusy(action) {
  document.getElementById("loadCellAction").textContent = action;
  document.getElementById("loadCellStatus").textContent = "Working...";
  document.getElementById("loadCellRaw").textContent = `Calling weight service: ${action}`;
}

function renderLoadCellReading(payload, action = "Result") {
  const weight = document.getElementById("loadCellWeight");
  const status = document.getElementById("loadCellStatus");
  const statusCard = status.closest(".metric-card");
  const port = document.getElementById("loadCellPort");
  const raw = document.getElementById("loadCellRaw");
  const updated = document.getElementById("loadCellUpdated");
  const resultJson = document.getElementById("loadCellResultJson");
  const actionNode = document.getElementById("loadCellAction");
  const samplesNode = document.getElementById("loadCellSamples");
  const rangeNode = document.getElementById("loadCellRange");
  const stabilityNode = document.getElementById("loadCellStability");

  actionNode.textContent = action;
  resultJson.textContent = JSON.stringify(loadCellDisplayPayload(payload || {}), null, 2);

  if (!payload?.ok) {
    weight.textContent = "-- g";
    status.textContent = "Error";
    statusCard.classList.remove("green");
    statusCard.classList.add("orange");
    port.textContent = payload?.port || "127.0.0.1:8002";
    samplesNode.textContent = "--";
    rangeNode.textContent = "--";
    stabilityNode.textContent = "--";
    raw.textContent = `Error: ${payload?.error || payload?.message || "Unable to contact weight service"}`;
    updated.textContent = `Updated: ${payload?.timestamp || new Date().toLocaleTimeString()}`;
    return;
  }

  const weightValue = Number(payload.weight_g);
  weight.textContent = Number.isFinite(weightValue)
    ? `${weightValue.toFixed(3)} ${payload.unit || "g"}`
    : "-- g";

  const normalizedStatus = String(payload.status || "OK").toLowerCase();
  if (normalizedStatus === "dynamic" || normalizedStatus === "d") {
    status.textContent = "Dynamic";
    statusCard.classList.remove("green");
    statusCard.classList.add("orange");
  } else if (normalizedStatus === "stable" || normalizedStatus === "s") {
    status.textContent = "Stable";
    statusCard.classList.add("green");
    statusCard.classList.remove("orange");
  } else if (payload.connected === false) {
    status.textContent = "Offline";
    statusCard.classList.remove("green");
    statusCard.classList.add("orange");
  } else {
    status.textContent = payload.message || payload.status || "OK";
    statusCard.classList.add("green");
    statusCard.classList.remove("orange");
  }

  const portText = payload.port || payload.service || "127.0.0.1:8002";
  port.textContent = payload.baud ? `${portText} @ ${payload.baud}` : portText;

  const count = Number(payload.sample_count || payload.requested_sample_count || 0);
  samplesNode.textContent = count > 0 ? String(count) : "--";
  if (Number.isFinite(Number(payload.min_g)) && Number.isFinite(Number(payload.max_g))) {
    rangeNode.textContent = `${Number(payload.min_g).toFixed(3)}–${Number(payload.max_g).toFixed(3)} g`;
  } else {
    rangeNode.textContent = "--";
  }

  const stableCount = Number(payload.stable_sample_count || 0);
  const dynamicCount = Number(payload.dynamic_sample_count || 0);
  stabilityNode.textContent = count > 1 ? `${stableCount} / ${dynamicCount}` : (payload.stable ? "Stable" : (weightValue ? "Dynamic" : "--"));
  raw.textContent = `Response: ${payload.raw_response || payload.message || "OK"}`;
  updated.textContent = `Updated: ${payload.timestamp || new Date().toLocaleTimeString()}`;
}

async function callLoadCellApi(action, endpoint, options = {}) {
  setLoadCellBusy(action);
  try {
    const response = await fetch(endpoint, { cache: "no-store", ...options });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) {
      throw Object.assign(new Error(payload.error || payload.message || `${action} failed`), { payload });
    }
    renderLoadCellReading(payload, action);
    return payload;
  } catch (error) {
    renderLoadCellReading({
      ok: false,
      ...(error.payload || {}),
      error: error.message || `${action} failed`,
      timestamp: new Date().toLocaleTimeString()
    }, action);
    return null;
  }
}

async function readSingleLoadCell() {
  return callLoadCellApi("Single Measurement", "/api/load-cell/latest");
}

async function readAverageLoadCell() {
  return callLoadCellApi("Sampling (30 readings)", "/api/load-cell/average?samples=30");
}

async function zeroLoadCell() {
  return callLoadCellApi("Zero (ZI)", "/api/load-cell/zero", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
}

async function tareLoadCell() {
  return callLoadCellApi("Tare (TI)", "/api/load-cell/tare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
}

async function getLoadCellStatus() {
  return callLoadCellApi("Get Status", "/api/load-cell/status");
}

const SIGNAL_PRESETS = {
  f1: { label: "F1", frequencyHz: 8000 },
  f2: { label: "F2", frequencyHz: 10000 },
  f3: { label: "F3", frequencyHz: 15000 },
  f4: { label: "F4", frequencyHz: 20000 }
};

function updateSignalPresetSelection() {
  const preset = SIGNAL_PRESETS[state.signalPreset] || SIGNAL_PRESETS.f1;
  document.querySelectorAll("#signalPresetGrid button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.signalPreset === state.signalPreset);
  });
  document.querySelectorAll("#liveSignalPresetGrid button[data-signal-preset]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.signalPreset === state.signalPreset);
  });
  const serviceLabel = document.getElementById("signalSelectedFrequency");
  const liveLabel = document.getElementById("liveSelectedFrequency");
  if (serviceLabel) serviceLabel.textContent = `${preset.label} · ${(preset.frequencyHz / 1000).toFixed(2)} kHz`;
  if (liveLabel) liveLabel.textContent = `${preset.label} · ${(preset.frequencyHz / 1000).toFixed(2)} kHz`;
  const amplitude = document.getElementById("signalAmplitude");
  if (amplitude) amplitude.textContent = "1.00 Vpk · 2.00 Vpp";
}

function selectSignalPreset(preset) {
  if (!SIGNAL_PRESETS[preset]) return;
  state.signalPreset = preset;
  updateSignalPresetSelection();
}

function signalMetricValue(value, digits = 6, unit = "V") {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(digits)} ${unit}` : `-- ${unit}`;
}

function renderSignalPayload(payload, action = "Result") {
  const statusNode = document.getElementById("signalServiceStatus");
  const resultJson = document.getElementById("signalResultJson");
  const responseText = document.getElementById("signalResponseText");
  const updated = document.getElementById("signalUpdated");
  const lastAction = document.getElementById("signalLastAction");
  const stats = payload?.statistics || {};
  const rmsStats = stats.ac_rms_v || {};
  const freqStats = stats.frequency_hz || {};

  lastAction.textContent = action;
  resultJson.textContent = JSON.stringify(payload || {}, null, 2);
  updated.textContent = `Updated: ${payload?.timestamp || new Date().toLocaleTimeString()}`;

  if (!payload?.ok) {
    statusNode.textContent = "Error";
    responseText.textContent = `Error: ${payload?.error || payload?.message || "Signal service call failed"}`;
    return;
  }

  const running = payload.signal_running ?? (String(payload.status || "").toLowerCase() === "running");
  if (payload.status || payload.signal_running !== undefined) {
    statusNode.textContent = running ? "Running" : (payload.status || "Stopped");
  }

  const frequencySet = Number(payload.frequency_set_hz ?? payload.frequency_hz);
  if (Number.isFinite(frequencySet) && frequencySet > 0) {
    const matched = Object.entries(SIGNAL_PRESETS).find(([, item]) => item.frequencyHz === Math.round(frequencySet));
    if (matched) {
      state.signalPreset = matched[0];
      updateSignalPresetSelection();
    }
  }

  document.getElementById("signalAcRms").textContent = signalMetricValue(payload.ac_rms_v, 6, "V");
  document.getElementById("signalPeak").textContent = signalMetricValue(payload.peak_amplitude_v, 6, "V");
  document.getElementById("signalP2P").textContent = signalMetricValue(payload.peak_to_peak_v, 6, "V");
  document.getElementById("signalMeasuredFrequency").textContent = signalMetricValue(payload.frequency_hz, 2, "Hz");
  document.getElementById("signalDc").textContent = signalMetricValue(payload.dc_v, 6, "V");

  const count = Number(payload.number_of_samples || payload.measurements?.length || 0);
  document.getElementById("signalSampleCount").textContent = count > 0 ? String(count) : "--";
  if (Number.isFinite(Number(rmsStats.mean))) {
    document.getElementById("signalSampleRms").textContent = `${Number(rmsStats.mean).toFixed(6)} ± ${Number(rmsStats.std || 0).toFixed(6)} V`;
  } else {
    document.getElementById("signalSampleRms").textContent = "--";
  }
  document.getElementById("signalSampleFrequency").textContent = Number.isFinite(Number(freqStats.mean))
    ? `${Number(freqStats.mean).toFixed(2)} Hz`
    : "--";
  responseText.textContent = `Response: ${action} completed`;
}

async function callSignalEngineeringApi(action, endpoint, options = {}) {
  document.getElementById("signalLastAction").textContent = action;
  document.getElementById("signalServiceStatus").textContent = "Working...";
  document.getElementById("signalResponseText").textContent = `${action}...`;
  try {
    const response = await fetch(endpoint, { cache: "no-store", ...options });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw Object.assign(new Error(payload.error || payload.message || `${action} failed`), { payload });
    }
    renderSignalPayload({ ok: true, ...payload }, action);
    return payload;
  } catch (error) {
    renderSignalPayload({
      ok: false,
      ...(error.payload || {}),
      error: error.message || `${action} failed`,
      timestamp: new Date().toLocaleTimeString()
    }, action);
    return null;
  }
}

async function startSignalEngineering() {
  return callSignalEngineeringApi("Signal Start", "/api/signal/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset: state.signalPreset })
  });
}

async function stopSignalEngineering() {
  return callSignalEngineeringApi("Signal Stop", "/api/signal/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
}

async function getSignalMeasurement() {
  return callSignalEngineeringApi("Get Measurement", "/api/signal/measurement");
}

async function sampleSignalEngineering() {
  return callSignalEngineeringApi("Sample ×30", "/api/signal/sample", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number_of_samples: 30, interval: 0.1 })
  });
}

async function loadSignalEngineeringStatus() {
  updateSignalPresetSelection();
  return callSignalEngineeringApi("Get Status", "/api/signal/status");
}

function formatAirCalibrationFrequency(key, item) {
  const rms = item?.statistics?.ac_rms_v || {};
  const freq = item?.statistics?.frequency_hz || {};
  if (!Number.isFinite(Number(rms.mean))) return `${key.toUpperCase()} --`;
  return `${key.toUpperCase()} ${Number(rms.mean).toFixed(6)} V RMS · ${Number(freq.mean || 0).toFixed(1)} Hz`;
}

function renderSignalAirCalibration(record) {
  const status = document.getElementById("signalCalibrationStatus");
  const detail = document.getElementById("signalCalibrationDetail");
  if (!record?.calibrated_at) {
    status.textContent = "No air calibration saved";
    detail.textContent = "F1–F4 · 30 samples each · 1.0 V peak";
    return;
  }
  status.textContent = `Saved ${new Date(record.calibrated_at).toLocaleString()}`;
  const frequencies = record.frequencies || {};
  detail.textContent = ["f1", "f2", "f3", "f4"]
    .map((key) => formatAirCalibrationFrequency(key, frequencies[key]))
    .join(" | ");
}

async function loadSignalAirCalibration() {
  try {
    const response = await fetch("/api/signal/air-calibration", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load signal air calibration");
    renderSignalAirCalibration(await response.json());
  } catch (error) {
    renderSignalAirCalibration({});
  }
}

async function runSignalAirCalibration() {
  const button = document.getElementById("signalAirCalibrationButton");
  const status = document.getElementById("signalCalibrationStatus");
  button.disabled = true;
  status.textContent = "Running F1 → F4 air calibration...";
  document.getElementById("signalResponseText").textContent = "Keep the sensing area empty and do not touch the sensor.";
  try {
    const response = await fetch("/api/signal/air-calibration/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || payload.message || "Air calibration failed");
    }
    renderSignalAirCalibration(payload);
    document.getElementById("signalResultJson").textContent = JSON.stringify(payload, null, 2);
    document.getElementById("signalResponseText").textContent = "Response: air calibration saved in private server storage.";
    document.getElementById("signalUpdated").textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    await loadSignalEngineeringStatus();
  } catch (error) {
    status.textContent = "Air calibration failed";
    document.getElementById("signalResponseText").textContent = `Error: ${error.message || "Air calibration failed"}`;
  } finally {
    button.disabled = false;
  }
}

async function prepareTeachingScale() {
  showScreen("teachingWeight");
  await sampleTeachingWeight();
}

async function prepareTeachingDimensionsFromVision() {
  const status = document.getElementById("teachingWeightStatus");
  const raw = document.getElementById("teachingWeightRaw");
  const selectedShape = getTeachingShapeLabel();
  status.textContent = `Capturing ${selectedShape} dimensions...`;
  raw.textContent = `Calling vision service on port 8003 with shape=${selectedShape}`;
  try {
    const vision = await fetchVisionSize(selectedShape, "teaching");
    raw.textContent = vision.message || "Vision dimensions captured";
  } catch (error) {
    raw.textContent = `${error.message || "Vision unavailable"}; enter dimensions manually`;
  }
  teachingState.activeDimensionField = "width";
  updateTeachingDimensionDisplay();
  showScreen("teachingDimension");
}

function zeroMeasurementScaleBeforePlacement() {
  if (scalePreparation.busy) return;
  resetMeasurementInputs();
  beginScalePreparation("place", "home");
}

function beginScalePreparation(target, cancel) {
  scalePreparation.target = target;
  scalePreparation.cancel = cancel;
  document.getElementById("scalePrepareStatus").textContent =
    "Remove the previous item. Leave the platform empty, then press Platform Empty — Zero.";
  showScreen("scalePrepare"); // No hardware command is sent by Start / Scan New Material.
}

async function scaleSetupRequest(url, signal, method = "GET") {
  const response = await fetch(url, {
    method, signal, cache: "no-store",
    ...(method === "POST" ? {
      headers: { "Content-Type": "application/json" }, body: "{}"
    } : {})
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok !== true) {
    throw new Error(payload.message || payload.error || "Scale service did not confirm success.");
  }
  return payload;
}

async function waitForStableScale(signal, requireZero) {
  let consecutive = 0;
  while (!signal.aborted) {
    const reading = await scaleSetupRequest("/api/load-cell/latest", signal);
    // Reject unsupported units instead of treating kilograms as grams.
    if (String(reading.unit || "").trim().toLowerCase() !== "g") {
      throw new Error("Set the scale unit to grams, then retry.");
    }
    if (typeof reading.weight_g !== "number" || !Number.isFinite(reading.weight_g)) {
      throw new Error("Scale returned an invalid weight.");
    }
    // Use the device's explicit S/D status; the legacy adapter guesses stable
    // when a service omits its status, which is not adequate for this check.
    const status = String(reading.service_payload?.status ?? reading.status ?? "").toUpperCase();
    const stable = status === "S" || status === "STABLE";
    const inBand = !requireZero || Math.abs(reading.weight_g) <= SCALE_ZERO_TOLERANCE_G;
    consecutive = stable && inBand ? consecutive + 1 : 0;
    document.getElementById("scalePrepareStatus").textContent =
      `${requireZero ? "Checking zero" : "Waiting for the empty platform to settle"}: ` +
      `${reading.weight_g.toFixed(3)} g · ${stable ? "stable" : "moving"} · ${consecutive}/3`;
    if (consecutive >= 3) return;
    await delayMs(250);
  }
  throw new Error("Scale setup timed out. Keep the platform empty and retry.");
}

async function confirmEmptyPlatformAndZero() {
  if (scalePreparation.busy || !screens.scalePrepare.classList.contains("active")) return;
  scalePreparation.busy = true;
  const button = document.getElementById("scalePrepareZeroButton");
  const cancel = document.getElementById("scalePrepareCancelButton");
  const menu = document.getElementById("menuButton");
  button.disabled = cancel.disabled = menu.disabled = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), SCALE_SETUP_TIMEOUT_MS);
  let ready = false;
  try {
    await waitForStableScale(controller.signal, false);
    document.getElementById("scalePrepareStatus").textContent = "Zeroing the empty platform...";
    const result = await scaleSetupRequest("/api/load-cell/zero", controller.signal, "POST");
    // MT-SICS ZI replies S/D mean stable/dynamic zero. HTTP 200 alone is not
    // proof: the current scale API also returns success for rejected commands.
    const reply = String(result.raw_response || "").trim();
    if (!/^ZI\s+S$/i.test(reply)) {
      throw new Error(/^ZI\s+D$/i.test(reply)
        ? "Zero occurred while the platform was moving. Leave it empty, let it settle and retry."
        : `Zero not confirmed (${reply || "no device reply"}). Keep the platform empty and retry.`);
    }
    await waitForStableScale(controller.signal, true);
    ready = true;
  } catch (error) {
    document.getElementById("scalePrepareStatus").textContent = controller.signal.aborted
      ? "Scale setup timed out. Keep the platform empty and retry."
      : (error.message || "Unable to prepare scale. Keep the platform empty and retry.");
  } finally {
    clearTimeout(timeout);
    scalePreparation.busy = false;
    button.disabled = cancel.disabled = menu.disabled = false;
  }
  // Only a confirmed, stable zero opens the place-next-item screen.
  if (ready) showScreen(scalePreparation.target);
}

async function prepareMeasurementScale() {
  showScreen("weight");
  await sampleMeasurementWeight();
}

async function prepareMeasurementDimensionsFromVision() {
  const status = document.getElementById("measurementWeightStatus");
  const raw = document.getElementById("measurementWeightRaw");
  status.textContent = "Capturing image dimensions...";
  raw.textContent = "Calling vision service on port 8003";
  try {
    const vision = await fetchVisionSize(getMeasurementShapeLabel(), "measurement");
    raw.textContent = vision.message || "Vision dimensions captured";
  } catch (error) {
    raw.textContent = `${error.message || "Vision unavailable"}; enter dimensions manually`;
  }
  state.activeDimensionField = "width";
  updateDimensionDisplay();
  showScreen("dimension");
}

async function sampleMeasurementWeight() {
  const config = weightScreenConfig("measurement");
  const status = config.status;
  const raw = config.raw;
  const panel = document.querySelector("#weightScreen .value-panel");
  panel.classList.remove("error");
  status.textContent = "Sampling live scale...";
  raw.textContent = "0 / 10";
  setWeightControls("measurement", { sampling: true, ready: false, sampleAvailable: false });
  startWeightProgressTimer(config, 10);
  setWeight("");
  try {
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Unable to read scale");
    setWeight(String(payload.weight_g ?? ""));
    status.textContent = payload.dynamic_sample_count
      ? `${payload.sample_count || 0} samples averaged (dynamic accepted)`
      : `${payload.sample_count || 0} samples averaged`;
    raw.textContent = payload.dynamic_sample_count
      ? `Std ${payload.std_g ?? "--"} g | Stable ${payload.stable_sample_count || 0} | Dynamic ${payload.dynamic_sample_count || 0}`
      : `Std ${payload.std_g ?? "--"} g | ${payload.min_g ?? "--"} to ${payload.max_g ?? "--"} g`;
    setWeightProgress(config, Number(payload.sample_count || 10), 10, "Weight captured", "complete");
    setWeightControls("measurement", { sampling: false, ready: weightIsValid(), sampleAvailable: true });
  } catch (error) {
    status.textContent = "Scale reading failed";
    raw.textContent = error.message || "Try Sample Again";
    setWeightProgress(config, 0, 10, "Reading failed", "error");
    setWeightControls("measurement", { sampling: false, ready: false, sampleAvailable: true });
  } finally {
    stopWeightProgressTimer();
  }
}

function zeroTeachingScaleBeforePlacement(mode) {
  if (scalePreparation.busy) return;
  teachingState.mode = mode;
  resetTeachingInputs();
  document.getElementById("teachingStage").textContent = "F1 · 8 kHz";
  document.querySelector("#teachingRecordScreen .measure-copy p").textContent = "F1–F4 will be sampled sequentially after dimensions are confirmed.";
  document.getElementById("teachingRecordButton").textContent = "Next";
  beginScalePreparation("teachingPlace", "teaching");
}

async function sampleTeachingWeight() {
  const config = weightScreenConfig("teaching");
  const status = config.status;
  const raw = config.raw;
  status.textContent = "Sampling live scale...";
  raw.textContent = "0 / 10";
  setWeightControls("teaching", { sampling: true, ready: false, sampleAvailable: false });
  startWeightProgressTimer(config, 10);
  setTeachingWeight("");
  try {
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Unable to read scale");
    setTeachingWeight(String(payload.weight_g ?? ""));
    teachingState.weightStd = String(payload.std_g ?? "");
    status.textContent = payload.dynamic_sample_count
      ? `${payload.sample_count || 0} samples averaged (dynamic accepted)`
      : `${payload.sample_count || 0} samples averaged`;
    raw.textContent = payload.dynamic_sample_count
      ? `Std ${payload.std_g ?? "--"} g | Stable ${payload.stable_sample_count || 0} | Dynamic ${payload.dynamic_sample_count || 0}`
      : `Std ${payload.std_g ?? "--"} g | ${payload.min_g ?? "--"} to ${payload.max_g ?? "--"} g`;
    setWeightProgress(config, Number(payload.sample_count || 10), 10, "Weight captured", "complete");
    setWeightControls("teaching", { sampling: false, ready: weightIsValidTeaching(), sampleAvailable: true });
  } catch (error) {
    status.textContent = "Scale reading failed";
    raw.textContent = error.message || "Try Sample Again";
    setWeightProgress(config, 0, 10, "Reading failed", "error");
    setWeightControls("teaching", { sampling: false, ready: false, sampleAvailable: true });
  } finally {
    stopWeightProgressTimer();
  }
}

function updateLoadCellHoldButton() {
  const button = document.getElementById("loadCellHoldButton");
  if (!button) return;
  button.textContent = state.loadCellHeld ? "Resume" : "Hold";
  button.classList.toggle("primary", state.loadCellHeld);
  button.classList.toggle("secondary", !state.loadCellHeld);
}

function toggleLoadCellHold() {
  state.loadCellHeld = !state.loadCellHeld;
  updateLoadCellHoldButton();
  const updated = document.getElementById("loadCellUpdated");
  if (state.loadCellHeld) {
    updated.textContent = "Held";
  } else {
    refreshLoadCellReading();
  }
}

async function startLoadCellMonitor() {
  state.loadCellHeld = false;
  clearInterval(state.loadCellTimer);
  await getLoadCellStatus();
}

document.getElementById("startButton").addEventListener("click", () => {
  zeroMeasurementScaleBeforePlacement();
});
document.getElementById("scalePrepareZeroButton").addEventListener("click", confirmEmptyPlatformAndZero);
document.getElementById("scalePrepareCancelButton").addEventListener("click", () => {
  if (!scalePreparation.busy) showScreen(scalePreparation.cancel);
});
document.getElementById("placeContinueButton").addEventListener("click", () => showScreen("shape"));
document.getElementById("weightBackButton").addEventListener("click", () => showScreen("shape"));
document.getElementById("measurementWeightSampleButton").addEventListener("click", sampleMeasurementWeight);
document.getElementById("weightNextButton").addEventListener("click", async () => {
  if (state.measurementWeightSampling || !state.measurementWeightReady) return;
  if (!weightIsValid()) {
    showWeightError();
    return;
  }
  await prepareMeasurementDimensionsFromVision();
});
document.getElementById("dimensionBackButton").addEventListener("click", () => showScreen("weight"));
document.getElementById("dimensionNextButton").addEventListener("click", () => {
  if (!dimensionsAreValid()) return;
  startMeasurement();
});
document.getElementById("shapeBackButton").addEventListener("click", () => showScreen("place"));
document.getElementById("measureButton").addEventListener("click", () => {
  if (state.shape === "Other") {
    updateOtherShapeSelection();
    showScreen("otherShape");
    return;
  }
  prepareMeasurementScale();
});
document.getElementById("otherShapeBackButton").addEventListener("click", () => showScreen("shape"));
document.getElementById("otherShapeNextButton").addEventListener("click", () => {
  prepareMeasurementScale();
});
document.getElementById("newMeasurementButton").addEventListener("click", () => {
  resetMeasurementInputs();
  showScreen("home");
});
document.getElementById("detailsButton").addEventListener("click", async () => {
  await loadHistoryRecords();
  showScreen("history");
});
document.getElementById("engineeringExitButton").addEventListener("click", () => {
  showScreen("home");
});
document.getElementById("passwordCancelButton").addEventListener("click", () => {
  showScreen("home");
});
document.getElementById("passwordEnterButton").addEventListener("click", submitPassword);
document.getElementById("menuButton").addEventListener("click", () => {
  document.getElementById("menuPanel").classList.toggle("open");
});
document.getElementById("menuEngineeringButton").addEventListener("click", showPasswordScreen);
document.getElementById("menuHistoryButton").addEventListener("click", () => showScreen("history"));
document.getElementById("menuExitButton").addEventListener("click", () => {
  if (!window.confirm("Are you sure you want to exit the application?")) return;
  window.open("", "_self");
  window.close();
});
const legacyModeToggleButton = document.getElementById("modeToggleButton");
if (legacyModeToggleButton) legacyModeToggleButton.addEventListener("click", toggleAcquisitionMode);
document.getElementById("engineeringLiveViewButton").addEventListener("click", () => showScreen("liveView"));
document.getElementById("engineeringCalibrationButton").addEventListener("click", () => showScreen("calibration"));
document.getElementById("engineeringTeachingButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("engineeringLoadCellButton").addEventListener("click", () => showScreen("loadCell"));
document.getElementById("engineeringDetectorSettingsButton").addEventListener("click", async () => {
  await loadAcquisitionMode();
  showScreen("detectorSettings");
});
document.getElementById("engineeringClassifierButton").addEventListener("click", async () => {
  await loadClassifierStatus();
  showScreen("classifier");
});
document.getElementById("viewCalibrationButton").addEventListener("click", async () => {
  await loadCalibration();
  showScreen("calibrationResult");
});
document.getElementById("engineeringHistoryButton").addEventListener("click", () => showScreen("history"));
document.getElementById("classifierBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("classifierTrainButton").addEventListener("click", trainClassifierModel);
document.getElementById("classifierAlgorithmSelect").addEventListener("change", saveClassifierAlgorithm);
document.getElementById("liveViewBackButton").addEventListener("click", () => exitSignalLiveView("engineering"));
document.getElementById("liveViewHomeButton").addEventListener("click", () => exitSignalLiveView("home"));
document.getElementById("liveSignalStartButton").addEventListener("click", startSignalLive);
document.getElementById("liveSignalStopButton").addEventListener("click", stopSignalLive);
document.getElementById("liveSignalPresetGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-signal-preset]");
  if (!button) return;
  selectSignalLivePreset(button.dataset.signalPreset);
});
document.getElementById("liveAmplitudeToggle").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-live-vpp]");
  if (!button) return;
  selectSignalLiveAmplitude(button.dataset.liveVpp);
});
document.getElementById("liveUnitToggle").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-live-unit]");
  if (!button) return;
  selectSignalLiveUnit(button.dataset.liveUnit);
});
document.getElementById("liveModeToggle").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-live-mode]");
  if (!button) return;
  selectSignalLiveMode(button.dataset.liveMode);
});
document.getElementById("daqSettingsBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("daqSettingsDoneButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("loadCellBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("loadCellZeroButton").addEventListener("click", zeroLoadCell);
document.getElementById("loadCellTareButton").addEventListener("click", tareLoadCell);
document.getElementById("loadCellSingleButton").addEventListener("click", readSingleLoadCell);
document.getElementById("loadCellAverageButton").addEventListener("click", readAverageLoadCell);
document.getElementById("loadCellStatusButton").addEventListener("click", getLoadCellStatus);
document.getElementById("signalBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("signalStartButton").addEventListener("click", startSignalEngineering);
document.getElementById("signalStopButton").addEventListener("click", stopSignalEngineering);
document.getElementById("signalMeasurementButton").addEventListener("click", getSignalMeasurement);
document.getElementById("signalSampleButton").addEventListener("click", sampleSignalEngineering);
document.getElementById("signalStatusButton").addEventListener("click", loadSignalEngineeringStatus);
document.getElementById("signalAirCalibrationButton").addEventListener("click", runSignalAirCalibration);
document.getElementById("signalPresetGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-signal-preset]");
  if (!button) return;
  selectSignalPreset(button.dataset.signalPreset);
});
document.getElementById("detectorSettingsCancelButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("detectorSettingsSaveButton").addEventListener("click", saveDetectorSettings);
document.getElementById("frequencySlot1Button").addEventListener("click", () => selectFrequencySlot(1));
document.getElementById("frequencySlot2Button").addEventListener("click", () => selectFrequencySlot(2));
document.getElementById("frequencySlot3Button").addEventListener("click", () => selectFrequencySlot(3));
document.getElementById("frequencyModeBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("frequencyModeSaveButton").addEventListener("click", saveFrequencySettings);
document.getElementById("editFrequencyButton").addEventListener("click", () => showScreen("frequencyEdit"));
document.getElementById("frequencyEditBackButton").addEventListener("click", () => showScreen("frequencyMode"));
document.getElementById("frequencyEditSetButton").addEventListener("click", () => showScreen("frequencyMode"));
document.getElementById("historyBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("historyHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("detailBackButton").addEventListener("click", () => showScreen("history"));
document.getElementById("detailHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("detailDeleteButton").addEventListener("click", showDeletePasswordScreen);
document.getElementById("deleteCancelButton").addEventListener("click", () => {
  showScreen(selectedTeachingId ? "teachingDetail" : "historyDetail");
});
document.getElementById("deleteConfirmButton").addEventListener("click", confirmDelete);
document.getElementById("calibrationCancelButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("calibrationStartButton").addEventListener("click", startCalibration);
document.getElementById("validateCalibrationButton").addEventListener("click", startCalibrationValidation);
document.getElementById("calibrationAgainButton").addEventListener("click", () => showScreen("calibration"));
document.getElementById("calibrationValidateAgainButton").addEventListener("click", startCalibrationValidation);
document.getElementById("calibrationDoneButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("teachingCancelButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("teachingViewButton").addEventListener("click", async () => {
  await loadTeachingRecords();
  showScreen("teachingRecords");
});
document.getElementById("teachingStartButton").addEventListener("click", () => zeroTeachingScaleBeforePlacement("teach"));
document.getElementById("teachingValidateButton").addEventListener("click", () => zeroTeachingScaleBeforePlacement("validate"));
document.getElementById("teachingPlaceBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingPlaceNextButton").addEventListener("click", () => showScreen("teachingMaterial"));
document.getElementById("teachingWeightBackButton").addEventListener("click", () => showScreen(teachingState.shape === "Other" ? "teachingOtherShape" : "teachingShape"));
document.getElementById("teachingWeightSampleButton").addEventListener("click", sampleTeachingWeight);
document.getElementById("teachingRecordButton").addEventListener("click", async () => {
  if (state.teachingWeightSampling || !state.teachingWeightReady) return;
  if (!weightIsValidTeaching()) return;
  await prepareTeachingDimensionsFromVision();
});
document.getElementById("teachingMaterialBackButton").addEventListener("click", () => showScreen("teachingPlace"));
document.getElementById("teachingMaterialNextButton").addEventListener("click", () => {
  if (!teachingState.material) return;
  if (teachingState.material === "Other") {
    showScreen("teachingOtherMaterial");
    return;
  }
  configureTeachingPurityScreen();
  showScreen("teachingPurity");
});
document.getElementById("teachingOtherMaterialBackButton").addEventListener("click", () => showScreen("teachingMaterial"));
document.getElementById("teachingOtherMaterialNextButton").addEventListener("click", () => {
  if (!teachingState.otherMaterial) return;
  configureTeachingPurityScreen();
  showScreen("teachingPurity");
});
document.getElementById("teachingPurityBackButton").addEventListener("click", () => {
  showScreen(teachingState.material === "Other" ? "teachingOtherMaterial" : "teachingMaterial");
});
document.getElementById("teachingPurityNextButton").addEventListener("click", () => {
  if (!teachingState.purity) return;
  showScreen("teachingShape");
});
document.getElementById("teachingShapeBackButton").addEventListener("click", () => showScreen("teachingPurity"));
document.getElementById("teachingShapeNextButton").addEventListener("click", () => {
  if (!teachingState.shape) return;
  if (teachingState.shape === "Other") {
    showScreen("teachingOtherShape");
    return;
  }
  prepareTeachingScale();
});
document.getElementById("teachingOtherShapeBackButton").addEventListener("click", () => showScreen("teachingShape"));
document.getElementById("teachingOtherShapeNextButton").addEventListener("click", () => {
  if (!teachingState.otherShape) return;
  prepareTeachingScale();
});
document.getElementById("teachingDimensionBackButton").addEventListener("click", () => {
  showScreen("teachingWeight");
});
document.getElementById("teachingDimensionNextButton").addEventListener("click", async () => {
  if (!teachingDimensionsAreValid()) return;
  const button = document.getElementById("teachingDimensionNextButton");
  button.disabled = true;
  try {
    await captureTeachingImageSnapshot();
    await startTeachingRecord();
  } catch (error) {
    selectTeachingDimensionPanel("image");
  } finally {
    button.disabled = false;
  }
});
document.getElementById("teachingDimensionsTabButton").addEventListener("click", () => selectTeachingDimensionPanel("dimensions"));
document.getElementById("teachingImageTabButton").addEventListener("click", () => selectTeachingDimensionPanel("image"));
document.getElementById("teachingRefreshImageButton").addEventListener("click", loadTeachingDetectedImage);
document.getElementById("teachingRemoveBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRemoveNextButton").addEventListener("click", () => showScreen("teachingSaved"));
document.getElementById("teachingSavedAgainButton").addEventListener("click", () => {
  zeroTeachingScaleBeforePlacement(teachingState.mode);
});
document.getElementById("teachingSavedDoneButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("teachingSavedDataTabButton").addEventListener("click", () => selectTeachingSavedPanel("data"));
document.getElementById("teachingSavedImageTabButton").addEventListener("click", () => selectTeachingSavedPanel("image"));
document.getElementById("teachingRecordsBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRecordsHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("teachingDetailBackButton").addEventListener("click", () => showScreen("teachingRecords"));
document.getElementById("teachingDetailHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("teachingDetailDeleteButton").addEventListener("click", showDeletePasswordScreen);
document.getElementById("teachingDetailDataTabButton").addEventListener("click", () => selectTeachingDetailPanel("data"));
document.getElementById("teachingDetailImageTabButton").addEventListener("click", () => selectTeachingDetailPanel("image"));

document.querySelectorAll("[data-back-home]").forEach((button) => {
  button.addEventListener("click", () => showScreen("home"));
});

const manualWeightKeypad = document.getElementById("keypad");
if (manualWeightKeypad) {
  manualWeightKeypad.addEventListener("click", (event) => {
    const key = event.target.dataset.key;
    if (!key) return;

    if (key === "clear") {
      setWeight("");
      return;
    }

    if (key === "." && state.weight.includes(".")) return;
    if (state.weight === "" && key === ".") {
      setWeight("0.");
      return;
    }

    setWeight(state.weight + key);
  });
}

document.getElementById("widthFieldButton").addEventListener("click", () => {
  state.activeDimensionField = "width";
  updateDimensionFieldSelection();
});
document.getElementById("lengthFieldButton").addEventListener("click", () => {
  state.activeDimensionField = "length";
  updateDimensionFieldSelection();
});
document.getElementById("thicknessFieldButton").addEventListener("click", () => {
  state.activeDimensionField = "thickness";
  updateDimensionFieldSelection();
});
document.getElementById("dimensionKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.dimensionKey;
  if (!key) return;
  const current = state.activeDimensionField === "length"
    ? state.lengthMm
    : state.activeDimensionField === "thickness"
      ? state.thicknessMm
      : state.widthMm;
  if (key === "clear") {
    setDimensionValue(state.activeDimensionField, "");
    return;
  }
  if (key === "." && current.includes(".")) return;
  if (current === "" && key === ".") {
    setDimensionValue(state.activeDimensionField, "0.");
    return;
  }
  setDimensionValue(state.activeDimensionField, `${current}${key}`);
});

document.getElementById("passwordKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.pin;
  if (!key) return;

  document.querySelector(".password-panel").classList.remove("error");
  document.getElementById("passwordMessage").textContent = "Enter PIN to continue";

  if (key === "clear") {
    state.password = "";
  } else if (key === "back") {
    state.password = state.password.slice(0, -1);
  } else if (state.password.length < 6) {
    state.password += key;
  }

  updatePasswordDisplay();

  if (state.password.length === 6) {
    submitPassword();
  }
});

document.getElementById("deletePasswordKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.deletePin;
  if (!key) return;

  const panel = document.querySelector("#deletePasswordScreen .password-panel");
  panel.classList.remove("error", "warning");
  document.getElementById("deletePasswordMessage").textContent = "Enter PIN to delete record";

  if (key === "clear") {
    deletePassword = "";
  } else if (key === "back") {
    deletePassword = deletePassword.slice(0, -1);
  } else if (deletePassword.length < 6) {
    deletePassword += key;
  }

  updateDeletePasswordDisplay();

  if (deletePassword.length === 6) {
    panel.classList.add("warning");
    document.getElementById("deletePasswordMessage").textContent = "Press Confirm Delete";
  }
});

document.getElementById("shapeGrid").addEventListener("click", (event) => {
  const button = event.target.closest(".shape-option");
  if (!button) return;
  state.shape = button.dataset.shape;
  updateShapeSelection();
  if (state.shape !== "Other") {
    state.otherShape = "Pendant";
  }
  updateDimensionDisplay();
});

document.getElementById("otherShapeGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  state.otherShape = button.dataset.otherShape;
  updateOtherShapeSelection();
  updateDimensionDisplay();
});

document.getElementById("teachingMaterialGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  teachingState.material = button.dataset.material;
  teachingState.purity = "";
  updateTeachingMaterialSelection();
});

document.getElementById("teachingOtherMaterialGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  teachingState.otherMaterial = button.dataset.otherMaterial;
  updateTeachingOtherMaterialSelection();
});

document.getElementById("teachingPurityGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  teachingState.purity = button.dataset.purity;
  updateTeachingPuritySelection();
});

document.getElementById("teachingPurityKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.teachingPurityKey;
  if (!key) return;
  if (key === "clear") {
    teachingState.purity = "";
  } else {
    if (teachingState.purity === "N/A") teachingState.purity = "";
    if (teachingState.purity.length < 4) teachingState.purity += key;
  }
  updateTeachingPuritySelection();
});

document.getElementById("teachingShapeGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  teachingState.shape = button.dataset.teachingShape;
  updateTeachingShapeSelection();
});

document.getElementById("teachingOtherShapeGrid").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  teachingState.otherShape = button.dataset.otherShape;
  updateTeachingOtherShapeSelection();
});

document.getElementById("teachingKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.teachingKey;
  if (!key) return;

  if (key === "clear") {
    setTeachingWeight("");
    return;
  }

  if (key === "." && teachingState.weight.includes(".")) return;
  if (teachingState.weight === "" && key === ".") {
    setTeachingWeight("0.");
    return;
  }

  setTeachingWeight(teachingState.weight + key);
});

document.getElementById("teachingWidthFieldButton").addEventListener("click", () => {
  teachingState.activeDimensionField = "width";
  updateTeachingDimensionFieldSelection();
});
document.getElementById("teachingLengthFieldButton").addEventListener("click", () => {
  teachingState.activeDimensionField = "length";
  updateTeachingDimensionFieldSelection();
});
document.getElementById("teachingThicknessFieldButton").addEventListener("click", () => {
  teachingState.activeDimensionField = "thickness";
  updateTeachingDimensionFieldSelection();
});
document.getElementById("teachingDimensionKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.teachingDimensionKey;
  if (!key) return;
  const current = teachingState.activeDimensionField === "length"
    ? teachingState.lengthMm
    : teachingState.activeDimensionField === "thickness"
      ? teachingState.thicknessMm
      : teachingState.widthMm;
  if (key === "clear") {
    setTeachingDimensionValue(teachingState.activeDimensionField, "");
    return;
  }
  if (key === "." && current.includes(".")) return;
  if (current === "" && key === ".") {
    setTeachingDimensionValue(teachingState.activeDimensionField, "0.");
    return;
  }
  setTeachingDimensionValue(teachingState.activeDimensionField, `${current}${key}`);
});

document.getElementById("frequencySettingsKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.frequencySettingsKey;
  if (!key) return;
  const index = Math.max(0, Math.min(2, Number(state.activeFrequencySlot || 1) - 1));
  let current = String(state.multiFrequenciesKhz[index] ?? 0);
  if (key === "clear") {
    current = "";
  } else if (key === "." && current.includes(".")) {
    return;
  } else if (current === "" && key === ".") {
    current = "0.";
  } else {
    current = `${current}${key}`.slice(0, 7);
  }
  const parsed = Number.parseFloat(current || "0");
  state.multiFrequenciesKhz[index] = Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  updateFrequencyModeSelection();
});

document.getElementById("detectorSettingsKeypad").addEventListener("click", (event) => {
  const key = event.target.dataset.detectorKey;
  if (!key) return;

  if (key === "clear") {
    state.detectorConfidenceInput = "";
    updateDetectorConfidenceDisplay();
    return;
  }
  if (key === "back") {
    state.detectorConfidenceInput = state.detectorConfidenceInput.slice(0, -1);
    updateDetectorConfidenceDisplay();
    return;
  }
  if (state.detectorConfidenceInput.length >= 3) return;
  state.detectorConfidenceInput += key;
  const value = Number.parseInt(state.detectorConfidenceInput, 10);
  if (Number.isFinite(value) && value > 100) {
    state.detectorConfidenceInput = "100";
  }
  updateDetectorConfidenceDisplay();
});

function updateCarousel() {
  const cards = Array.from(document.querySelectorAll(".sample-card"));
  const prevIndex = (state.carouselIndex - 1 + cards.length) % cards.length;
  const nextIndex = (state.carouselIndex + 1) % cards.length;

  cards.forEach((card, index) => {
    card.classList.toggle("prev", index === prevIndex);
    card.classList.toggle("active", index === state.carouselIndex);
    card.classList.toggle("next", index === nextIndex);
  });

  updateActiveRate(cards[state.carouselIndex]);
}

// REV 2026-10-02 / RATES-01: prices are spot metal estimates, not retail
// jewellery prices. Purity scales the metal content; workmanship is excluded.
let referenceRates = null;
let referenceRatesBusy = false;
let referenceRatesOffline = false;

function updateActiveRate(card) {
  const rateCard = document.getElementById("activeRateCard");
  const rateMove = document.getElementById("activeRateMove");
  const priceDisplay = document.getElementById("activeRatePrice");
  const updatedDisplay = document.getElementById("activeRateUpdated");
  const quote = referenceRates?.metals?.[card.dataset.metal];
  document.getElementById("activeRateLabel").textContent = card.dataset.rateLabel;
  document.getElementById("activeRateSource").textContent = "Gold API + Frankfurter";
  rateCard.classList.remove("gold-rate", "silver-rate", "palladium-rate");
  rateCard.classList.add(card.classList.contains("silver") ? "silver-rate" : card.classList.contains("palladium") ? "palladium-rate" : "gold-rate");
  rateMove.classList.remove("up", "down", "flat");
  const price = quote?.myr_per_g;
  if (!Number.isFinite(price) || price <= 0) {
    priceDisplay.textContent = "—";
    rateMove.textContent = referenceRatesOffline ? "Unavailable" : referenceRates?.pending ? "Loading" : "Unavailable";
    rateMove.classList.add("flat");
    updatedDisplay.textContent = "No quote available";
    return;
  }
  priceDisplay.textContent = `RM ${(price * Number(card.dataset.purity)).toFixed(2)}/g`;
  const stale = referenceRatesOffline || quote.stale;
  const change = quote.change_pct;
  if (stale || !Number.isFinite(change)) {
    rateMove.textContent = stale ? "STALE" : "Trend pending";
    rateMove.classList.add("flat");
  } else {
    rateMove.textContent = `${change > 0 ? "▲" : change < 0 ? "▼" : "—"} ${Math.abs(change).toFixed(2)}% since previous update`;
    rateMove.classList.add(change > 0 ? "up" : change < 0 ? "down" : "flat");
  }
  const timestamp = new Date(quote.updated_at);
  const label = Number.isNaN(timestamp.getTime()) ? "Unknown quote time" : timestamp.toLocaleString("en-MY", {timeZone: "Asia/Kuala_Lumpur", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false}) + " MYT";
  updatedDisplay.textContent = `${stale ? "Last quote" : "Quote"}: ${label} · FX ${quote.fx_date}`;
  rateMove.title = quote.baseline_at ? `Compared with quote at ${quote.baseline_at}` : "A second successful quote is needed";
}

// RATES-02: GET only reads the daily cache; POST explicitly requests an update.
async function refreshReferenceRates(manual = false) {
  if (referenceRatesBusy) return;
  referenceRatesBusy = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(manual ? "/api/metal-rates/refresh" : "/api/metal-rates", {
      method: manual ? "POST" : "GET", cache: "no-store", signal: controller.signal});
    if (!response.ok) throw new Error("Rates unavailable");
    const data = await response.json();
    if (data.currency !== "MYR" || data.unit !== "g" || !data.metals) throw new Error("Invalid rates response");
    referenceRates = data;
    referenceRatesOffline = false;
    const button = document.getElementById("refreshRatesButton");
    const seconds = data.manual_retry_after || 0;
    button.disabled = data.pending || seconds > 0;
    button.textContent = data.pending ? "Refreshing…" : seconds > 0 ? `Wait ${seconds}s` : "Refresh";
  } catch (_) {
    // Keep a last-known quote, but never present it as fresh after an error.
    referenceRatesOffline = true;
    const button = document.getElementById("refreshRatesButton");
    button.disabled = false;
    button.textContent = "Retry refresh";
  } finally {
    clearTimeout(timeout);
    referenceRatesBusy = false;
    updateCarousel();
    if (referenceRates?.pending && !referenceRatesOffline) setTimeout(() => refreshReferenceRates(), 5000);
  }
}

setInterval(() => {
  const cards = Array.from(document.querySelectorAll(".sample-card"));
  state.carouselIndex = (state.carouselIndex + 1) % cards.length;
  updateCarousel();
}, 10000);

let bottomMessageIndex = 0;
setInterval(() => {
  const message = document.getElementById("bottomMessage");
  bottomMessageIndex = (bottomMessageIndex + 1) % bottomMessages.length;
  message.style.opacity = "0";
  setTimeout(() => {
    message.textContent = bottomMessages[bottomMessageIndex];
    message.style.opacity = "1";
  }, 220);
}, 3500);

updateSystemClock();
setInterval(updateSystemClock, 1000);
updateCarousel();
updateShapeSelection();
updateDimensionDisplay();
updateTeachingMaterialSelection();
updateTeachingOtherMaterialSelection();
updateTeachingPuritySelection();
updateTeachingShapeSelection();
updateTeachingOtherShapeSelection();
updateTeachingDimensionDisplay();
setWeightControls("measurement", { sampling: false, ready: false, sampleAvailable: false });
setWeightProgress(weightScreenConfig("measurement"), 0, 10, "Waiting to sample");
setWeightControls("teaching", { sampling: false, ready: false, sampleAvailable: false });
setWeightProgress(weightScreenConfig("teaching"), 0, 10, "Waiting to sample");
initializeCarouselImages();
loadHistoryRecords();
loadCalibration();
loadTeachingRecords();
updateDetectorConfidenceDisplay();
loadAcquisitionMode();

// REV 2026-10-02 / DISPLAY-01: use the actual viewport, including browser
// zoom and window resizing, instead of assuming a particular kiosk monitor.
function fitTouchDisplay() {
  const viewport = window.visualViewport;
  const width = viewport ? viewport.width : window.innerWidth;
  const height = viewport ? viewport.height : window.innerHeight;
  const scale = Math.min(width / 800, height / 480);
  document.documentElement.style.setProperty("--ui-scale", String(scale));
}
fitTouchDisplay();
window.addEventListener("resize", fitTouchDisplay);
window.visualViewport?.addEventListener("resize", fitTouchDisplay);

refreshReferenceRates();
// Poll our local cache for completion/cooldown; this does not call the providers.
setInterval(() => refreshReferenceRates(), 60000);
document.getElementById("refreshRatesButton").addEventListener("click", () => refreshReferenceRates(true));
