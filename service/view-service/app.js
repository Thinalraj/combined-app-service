const screens = {
  home: document.getElementById("homeScreen"),
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
  loadCellTimer: null,
  loadCellHeld: false,
  acquisitionMode: "simulator",
  calibrationRecord: {},
  confidenceThresholdPct: 40,
  detectorConfidenceInput: "40",
  liveViewTab: "raw",
  frequencyMode: "single",
  multiFrequenciesKhz: [10, 20, 30],
  activeFrequencySlot: 1
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
  material: "Gold 916",
  otherMaterial: "Brass",
  purity: "Unknown",
  shape: "Bar",
  otherShape: "Pendant",
  weight: "",
  weightStd: "",
  widthMm: "",
  lengthMm: "",
  thicknessMm: "",
  visionMeasurement: null,
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

function showScreen(name) {
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
    renderLiveViewTab();
    startLiveViewMonitor();
  } else if (name === "loadCell") {
    startLoadCellMonitor();
  } else {
    clearInterval(state.engineeringTimer);
  }

  if (name !== "loadCell") {
    clearInterval(state.loadCellTimer);
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

function loadTeachingDetectedImage() {
  const image = document.getElementById("teachingDetectedImage");
  const status = document.getElementById("teachingDetectedImageStatus");
  status.textContent = "Loading detected image...";
  image.onload = () => { status.textContent = "Latest detected item image"; };
  image.onerror = () => { status.textContent = "No detected image available yet. Capture or detect an image first."; };
  image.src = `/api/vision/image/detected?t=${Date.now()}`;
}

function renderLiveViewTab() {
  const rawActive = state.liveViewTab !== "delta";
  const rawButton = document.getElementById("liveRawTabButton");
  const deltaButton = document.getElementById("liveDeltaTabButton");
  const rawPanel = document.getElementById("liveRawPanel");
  const deltaPanel = document.getElementById("liveDeltaPanel");

  rawButton.classList.toggle("active", rawActive);
  rawButton.setAttribute("aria-selected", rawActive ? "true" : "false");
  deltaButton.classList.toggle("active", !rawActive);
  deltaButton.setAttribute("aria-selected", rawActive ? "false" : "true");
  rawPanel.classList.toggle("active", rawActive);
  deltaPanel.classList.toggle("active", !rawActive);
}

function setWeight(value) {
  state.weight = value.slice(0, 7);
  weightDisplay.textContent = state.weight || "0";
  document.querySelector("#weightScreen .value-panel").classList.remove("error");
}

function calculateGeometry(widthValue, lengthValue, thicknessValue) {
  const width = Number.parseFloat(widthValue || "0");
  const length = Number.parseFloat(lengthValue || "0");
  const thickness = Number.parseFloat(thicknessValue || "0");
  const safeWidth = Number.isFinite(width) ? width : 0;
  const safeLength = Number.isFinite(length) ? length : 0;
  const safeThickness = Number.isFinite(thickness) ? thickness : 0;
  const sampleArea = safeWidth * safeLength;
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
      labels: { width: "Inner Dia.", length: "Outer Dia.", thickness: "Thickness" },
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
  if (config.mode === "coin") return calculateGeometry(width, width, thickness);
  if (config.mode === "ring" || config.mode === "bangle") {
    const innerRadius = width / 2;
    const outerRadius = length / 2;
    const sampleArea = Math.max(0, Math.PI * ((outerRadius * outerRadius) - (innerRadius * innerRadius)));
    const coilArea = Math.PI * 35 * 35;
    const contactRatio = coilArea > 0 ? (sampleArea / coilArea) * 100 : 0;
    return { safeWidth: width, safeLength: length, safeThickness: thickness, sampleArea, contactRatio };
  }
  return calculateGeometry(width, length, thickness);
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
  if (config.mode === "coin" && Number.isFinite(diameter) && diameter > 0) {
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
  if (config.mode === "coin" && Number.isFinite(diameter) && diameter > 0) {
    teachingState.widthMm = diameter.toFixed(2);
    teachingState.lengthMm = diameter.toFixed(2);
  } else {
    if (Number.isFinite(width) && width > 0) teachingState.widthMm = width.toFixed(2);
    if (Number.isFinite(length) && length > 0) teachingState.lengthMm = length.toFixed(2);
  }
  updateTeachingDimensionDisplay();
}

async function fetchVisionSize(shape, kind = "measurement") {
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
  return config.required.every((field) => Number.parseFloat(values[field] || "0") > 0);
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
  return config.required.every((field) => Number.parseFloat(values[field] || "0") > 0);
}

function resetTeachingWeight() {
  setTeachingWeight("");
  state.teachingWeightSampling = false;
  state.teachingWeightReady = false;
  setWeightControls("teaching", { sampling: false, ready: false, sampleAvailable: false });
  setWeightProgress(weightScreenConfig("teaching"), 0, 10, "Waiting to sample");
}

function resetTeachingInputs() {
  teachingState.material = "Gold 916";
  teachingState.otherMaterial = "Brass";
  teachingState.purity = "Unknown";
  teachingState.shape = "Bar";
  teachingState.otherShape = "Pendant";
  teachingState.weightStd = "";
  teachingState.widthMm = "";
  teachingState.lengthMm = "";
  teachingState.thicknessMm = "";
  teachingState.visionMeasurement = null;
  teachingState.activeDimensionField = "width";
  teachingState.latestRecord = null;
  resetTeachingWeight();
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
      <span>Shape</span>
      <span>Weight</span>
      <span>Details</span>
    </div>
  `;

  teachingRecords.forEach((record) => {
    const row = document.createElement("div");
    row.className = "teaching-row";
    row.innerHTML = `
      <span>${record.date.replace(" 2026", "")}</span>
      <strong>${record.material}</strong>
      <span>${record.shape}</span>
      <span>${record.weight}</span>
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

function showTeachingDetail(id) {
  const record = teachingRecords.find((item) => item.id === id);
  if (!record) return;
  selectedTeachingId = id;

  document.getElementById("teachingDetailMaterial").textContent = record.material;
  document.getElementById("teachingDetailDate").textContent = record.date;
  document.getElementById("teachingDetailTime").textContent = record.time;
  document.getElementById("teachingDetailShape").textContent = record.shape;
  document.getElementById("teachingDetailWeight").textContent = record.weight;
  document.getElementById("teachingDetailCh1").textContent = record.ch1_rms;
  document.getElementById("teachingDetailCh2").textContent = record.ch2_rms;
  document.getElementById("teachingDetailCh1Std").textContent = record.ch1_std || "--";
  document.getElementById("teachingDetailCh2Std").textContent = record.ch2_std || "--";
  document.getElementById("teachingDetailRatio").textContent = record.ratio;
  document.getElementById("teachingDetailCh1Delta").textContent = formatDelta(record.ch1_delta, record.ch1_delta_pct);
  document.getElementById("teachingDetailCh2Delta").textContent = formatDelta(record.ch2_delta, record.ch2_delta_pct);
  document.getElementById("teachingDetailCalibration").textContent = record.calibration_used || "--";
  document.getElementById("teachingDetailPurity").textContent = record.purity || "Known";
  document.getElementById("teachingDetailStatus").textContent = record.status;
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

function formatRecordFrequencyStep(sequence, command) {
  const step = (sequence || []).find((item) => String(item.frequency_command || "").toLowerCase() === command);
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
  document.getElementById(`${prefix}F1`).textContent = formatRecordFrequencyStep(sequence, "f1");
  document.getElementById(`${prefix}F2`).textContent = formatRecordFrequencyStep(sequence, "f2");
  document.getElementById(`${prefix}F3`).textContent = formatRecordFrequencyStep(sequence, "f3");
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

function renderCalibration(record) {
  const ch1 = record.ch1 || {};
  const ch2 = record.ch2 || {};
  const air = record.frequency_air || {};
  state.calibrationRecord = record || {};
  document.getElementById("calibratedAt").textContent = record.calibrated_at || "--";
  document.getElementById("calibrationCondition").textContent = record.condition || "No material / air reading";
  document.getElementById("calibrationSampleCount").textContent =
    record.samples_per_frequency ? `30 per frequency / ${record.sample_count || 0} total` : `${record.sample_count || "--"}`;
  document.getElementById("calCh1Mean").textContent = `${ch1.mean ?? "--"} ${ch1.unit || "A RMS"}`;
  document.getElementById("calCh1Std").textContent = `${ch1.std ?? "--"} ${ch1.unit || "A RMS"}`;
  document.getElementById("calCh1Tolerance").textContent = `± ${ch1.tolerance ?? "--"} ${ch1.unit || "A RMS"}`;
  document.getElementById("calCh2Mean").textContent = `${ch2.mean ?? "--"} ${ch2.unit || "V RMS"}`;
  document.getElementById("calCh2Std").textContent = `${ch2.std ?? "--"} ${ch2.unit || "V RMS"}`;
  document.getElementById("calCh2Tolerance").textContent = `± ${ch2.tolerance ?? "--"} ${ch2.unit || "V RMS"}`;
  document.getElementById("calF1Air").textContent = formatCalibrationFrequencyAir(air.f1);
  document.getElementById("calF2Air").textContent = formatCalibrationFrequencyAir(air.f2);
  document.getElementById("calF3Air").textContent = formatCalibrationFrequencyAir(air.f3);
  document.getElementById("calValidationStatus").textContent = record.validation_status || "Not validated";
  document.getElementById("calValidationDrift").textContent =
    record.max_drift_pct === undefined || record.max_drift_pct === null ? "--" : `${Number(record.max_drift_pct).toFixed(3)}%`;
}

async function loadCalibration() {
  try {
    const response = await fetch("/api/calibration", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to load calibration");
    renderCalibration(await response.json());
  } catch (error) {
    try {
      const response = await fetch("calibration.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load calibration.json");
      renderCalibration(await response.json());
    } catch (fallbackError) {
      renderCalibration({});
    }
  }
}

function startCalibration() {
  runCalibrationProgress("calibration");
}

function startCalibrationValidation() {
  runCalibrationProgress("validate");
}

function runCalibrationProgress(mode) {
  showScreen("calibrationProgress");
  let elapsed = 0;
  const sampleTarget = 30;
  const settleSeconds = 5;
  const sampleSeconds = 11;
  const perFrequencySeconds = settleSeconds + sampleSeconds;
  const total = mode === "validate" ? 15 : perFrequencySeconds * 3;
  const progressBar = document.getElementById("calibrationProgressBar");
  const progressText = document.getElementById("calibrationProgressText");
  const ring = document.getElementById("calibrationRingMeter");
  const stage = document.getElementById("calibrationStage");
  const durationLabel = document.getElementById("calibrationDurationLabel");
  const frequencyLabel = document.getElementById("calibrationFrequencyLabel");
  const sampleLabel = document.getElementById("calibrationSampleLabel");
  let finished = false;
  const request = mode === "validate" ? validateCalibration({ deferResultScreen: true }) : saveCalibration({ deferResultScreen: true });

  stage.textContent = mode === "validate" ? "Validating Air Baseline" : "Switching to F1";
  durationLabel.textContent = mode === "validate" ? "Validation" : "3 frequencies";
  frequencyLabel.textContent = mode === "validate" ? "Air check" : "F1";
  sampleLabel.textContent = mode === "validate" ? "Sampling air" : `CH1/CH2 0 / ${sampleTarget}`;

  progressBar.style.width = "0%";
  progressText.textContent = "0%";
  ring.style.strokeDashoffset = "314";

  const timer = setInterval(() => {
    elapsed += 1;
    const progress = finished ? 100 : Math.min(99, Math.round((elapsed / total) * 100));
    if (mode !== "validate") {
      const zeroBased = Math.min(2, Math.floor(Math.max(0, elapsed - 1) / perFrequencySeconds));
      const slot = zeroBased + 1;
      const slotElapsed = Math.max(0, elapsed - zeroBased * perFrequencySeconds);
      const sample = slotElapsed <= settleSeconds ? 0 : Math.min(sampleTarget, Math.round(((slotElapsed - settleSeconds) / sampleSeconds) * sampleTarget));
      frequencyLabel.textContent = `F${slot}`;
      sampleLabel.textContent = `CH1/CH2 ${sample} / ${sampleTarget}`;
      stage.textContent = sample === 0 ? `Switching to F${slot}` : `Sampling F${slot} air`;
    }
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    ring.style.strokeDashoffset = `${314 - (314 * progress) / 100}`;
  }, 1000);

  request.finally(() => {
    finished = true;
    clearInterval(timer);
    progressBar.style.width = "100%";
    progressText.textContent = "100%";
    ring.style.strokeDashoffset = "0";
  });
}

async function saveCalibration(options = {}) {
  try {
    const response = await fetch("/api/calibration/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        frequency_hz: getCurrentFrequencyValue(),
        frequency_slot: state.activeFrequencySlot
      })
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || "Unable to save calibration");
    }
    renderCalibration(await response.json());
  } catch (error) {
    renderCalibration({
      calibrated_at: "--",
      condition: "Calibration failed. Check USB serial and try again.",
      frequency_air: {},
      ch1: { mean: "--", std: "--", tolerance: "--", unit: "A RMS" },
      ch2: { mean: "--", std: "--", tolerance: "--", unit: "V RMS" }
    });
  }

  if (!options.deferResultScreen) return;
  showScreen("calibrationResult");
}

async function validateCalibration(options = {}) {
  try {
    const response = await fetch("/api/calibration/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        frequency_hz: getCurrentFrequencyValue(),
        frequency_slot: state.activeFrequencySlot
      })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.message || "Unable to validate calibration");
    }
    const current = state.calibrationRecord || {};
    renderCalibration({
      ...current,
      validation_status: payload.validation_status,
      max_drift_pct: payload.max_drift_pct
    });
    document.getElementById("calibrationCondition").textContent = payload.recommendation || "Validation completed";
  } catch (error) {
    const current = state.calibrationRecord || {};
    renderCalibration({
      ...current,
      validation_status: "Validation failed",
      max_drift_pct: null
    });
    document.getElementById("calibrationCondition").textContent = error.message || "Validation failed";
  }

  if (!options.deferResultScreen) return;
  showScreen("calibrationResult");
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
      labels: { width: "Inner Dia.", length: "Outer Dia.", thickness: "Thickness" },
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
  if (config.mode === "coin") return calculateGeometry(width, width, thickness);
  return calculateGeometry(width, length, thickness);
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

function startTeachingRecord() {
  const currentFrequency = getCurrentFrequencyValue();
  const geometry = calculateGeometryForTeaching();
  const dimensionPayload = buildTeachingDimensionPayload();
  document.getElementById("teachingMaterialSummary").textContent = getTeachingMaterialLabel();
  document.getElementById("teachingShapeSummary").textContent = getTeachingShapeLabel();
  document.getElementById("teachingWeightSummary").textContent =
    `${teachingState.weight || "0"} g`;
  document.getElementById("teachingDimensionSummary").textContent =
    `${dimensionPayload.width_mm} x ${dimensionPayload.length_mm} x ${dimensionPayload.thickness_mm} mm (${geometry.contactRatio.toFixed(1)}%)`;
  showScreen("teachingRecord");

  let elapsed = 0;
  let finished = false;
  const sampleTarget = 30;
  const settleSeconds = 5;
  const sampleSeconds = 11;
  const perFrequencySeconds = settleSeconds + sampleSeconds;
  const total = perFrequencySeconds * 3;
  const progressBar = document.getElementById("teachingProgressBar");
  const progressText = document.getElementById("teachingProgressText");
  const ring = document.getElementById("teachingRingMeter");

  progressBar.style.width = "0%";
  progressText.textContent = "0%";
  ring.style.strokeDashoffset = "314";
  const teachingInstruction = document.querySelector("#teachingRecordScreen .measure-copy p");
  const request = teachingState.mode === "validate"
    ? runTeachingValidation({ deferResultScreen: true })
    : saveTeachingRecord({ deferResultScreen: true });

  const timer = setInterval(() => {
    elapsed += 1;
    const progress = finished ? 100 : Math.min(99, Math.round((elapsed / total) * 100));
    const zeroBased = Math.min(2, Math.floor(Math.max(0, elapsed - 1) / perFrequencySeconds));
    const slot = zeroBased + 1;
    const slotElapsed = Math.max(0, elapsed - zeroBased * perFrequencySeconds);
    const sample = slotElapsed <= settleSeconds ? 0 : Math.min(sampleTarget, Math.round(((slotElapsed - settleSeconds) / sampleSeconds) * sampleTarget));
    if (sample === 0) {
      document.getElementById("teachingStage").textContent = `Switching to F${slot}`;
      teachingInstruction.textContent = "Waiting for frequency to settle.";
    } else {
      document.getElementById("teachingStage").textContent = `Sampling F${slot}`;
      teachingInstruction.textContent = `CH1 and CH2 sample ${sample} / ${sampleTarget}. Keep the known sample still.`;
    }
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    ring.style.strokeDashoffset = `${314 - (314 * progress) / 100}`;
  }, 1000);

  request.finally(() => {
    finished = true;
    clearInterval(timer);
    progressBar.style.width = "100%";
    progressText.textContent = "100%";
    ring.style.strokeDashoffset = "0";
  });
}

async function runTeachingValidation(options = {}) {
  const currentFrequency = getCurrentFrequencyValue();
  const dimensionPayload = buildTeachingDimensionPayload();
  const requestBody = {
    material: getTeachingMaterialLabel(),
    purity: teachingState.material === "Other" ? teachingState.purity : "Known",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
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
  const currentFrequency = getCurrentFrequencyValue();
  const dimensionPayload = buildTeachingDimensionPayload();
  const record = {
    material: getTeachingMaterialLabel(),
    purity: teachingState.material === "Other" ? teachingState.purity : "Known",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
    frequency_hz: currentFrequency,
    frequency_slot: state.activeFrequencySlot
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
    await loadTeachingRecords();
  } catch (error) {
    teachingState.latestRecord = {
      ...record,
      ch1_rms: "--",
      ch2_rms: "--",
      ch1_std: "--",
      ch2_std: "--",
      ratio: "--",
      ch1_delta: null,
      ch2_delta: null,
      status: "Teaching failed. Check USB serial and try again."
    };
  }

  renderTeachingSaved(teachingState.latestRecord);
  if (!options.deferResultScreen) return;
  showScreen("teachingRemove");
}

function renderTeachingSaved(record) {
  const validateMode = teachingState.mode === "validate";
  document.getElementById("teachingSavedEyebrow").textContent = validateMode ? "Validation Result" : "Teaching Record Saved";
  document.getElementById("teachingSavedAgainButton").textContent = validateMode ? "Validate Again" : "Teach Again";
  document.getElementById("teachingSavedMaterial").textContent = record.material;
  document.getElementById("teachingSavedShape").textContent = record.shape;
  document.getElementById("teachingSavedWeight").textContent = record.weight;
  document.getElementById("teachingSavedCh1").textContent = record.ch1_rms;
  document.getElementById("teachingSavedCh2").textContent = record.ch2_rms;
  document.getElementById("teachingSavedRatio").textContent = record.ratio;
  document.getElementById("teachingSavedCh1Delta").textContent = formatDelta(record.ch1_delta, record.ch1_delta_pct);
  document.getElementById("teachingSavedCh2Delta").textContent = formatDelta(record.ch2_delta, record.ch2_delta_pct);
  document.getElementById("teachingSavedPurity").textContent = record.purity || "Known";
  document.getElementById("teachingSavedValidation").textContent = record.validation_result || (validateMode ? "FAIL" : "N/A");
  document.getElementById("teachingSavedConfidence").textContent = record.confidence || (validateMode ? "0%" : "--");
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
  const modeValue = document.getElementById("modeValue");
  const modeToggle = document.getElementById("modeToggleButton");
  const isDaq = state.acquisitionMode === "daq";

  modeValue.textContent = isDaq ? "DAQ" : "Simulator";
  modeToggle.textContent = isDaq ? "Switch to Simulator" : "Switch to DAQ";
  modeToggle.classList.toggle("active", isDaq);
}

function updateDetectorConfidenceDisplay() {
  document.getElementById("detectorConfidenceDisplay").textContent = state.detectorConfidenceInput || "40";
}

async function loadAcquisitionMode() {
  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    if (!response.ok) throw new Error("Unable to read settings");
    const settings = await response.json();
    state.acquisitionMode = settings.acquisition_mode === "daq" ? "daq" : "simulator";
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
    state.acquisitionMode = "simulator";
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

async function refreshLiveViewReadings() {
  const liveFrequency = document.getElementById("liveFrequency");
  const primary = document.getElementById("primaryRms");
  const primaryStd = document.getElementById("primaryStd");
  const primaryQuality = document.getElementById("primaryQuality");
  const secondary = document.getElementById("secondaryRms");
  const secondaryStd = document.getElementById("secondaryStd");
  const secondaryQuality = document.getElementById("secondaryQuality");
  const deltaCh1Display = document.getElementById("liveDeltaCh1");
  const deltaCh2Display = document.getElementById("liveDeltaCh2");
  const deltaRatioDisplay = document.getElementById("liveDeltaRatio");
  const calCh1 = Number(state.calibrationRecord?.ch1?.mean);
  const calCh2 = Number(state.calibrationRecord?.ch2?.mean);

  if (state.acquisitionMode === "simulator") {
    if (liveFrequency) liveFrequency.textContent = `F${state.activeFrequencySlot} ${getCurrentFrequencyValue().toFixed(2)} kHz`;
    const ch1Val = 0.83 + Math.random() * 0.04;
    const ch2Val = 0.93 + Math.random() * 0.05;
    primary.textContent = `${ch1Val.toFixed(3)} V`;
    primaryStd.textContent = `${(0.0018 + Math.random() * 0.0025).toFixed(6)}`;
    primaryQuality.textContent = `${Math.round(96 + Math.random() * 3)}%`;
    secondary.textContent = `${ch2Val.toFixed(3)} V`;
    secondaryStd.textContent = `${(0.0020 + Math.random() * 0.0030).toFixed(6)}`;
    secondaryQuality.textContent = `${Math.round(95 + Math.random() * 4)}%`;
    if (Number.isFinite(calCh1) && Number.isFinite(calCh2)) {
      const deltaCh1 = ch1Val - calCh1;
      const deltaCh2 = ch2Val - calCh2;
      deltaCh1Display.textContent = `${deltaCh1 >= 0 ? "+" : ""}${deltaCh1.toFixed(6)} V`;
      deltaCh2Display.textContent = `${deltaCh2 >= 0 ? "+" : ""}${deltaCh2.toFixed(6)} V`;
      deltaRatioDisplay.textContent = deltaCh2 !== 0 ? `${(deltaCh1 / deltaCh2).toFixed(6)}` : "--";
    } else {
      deltaCh1Display.textContent = "--";
      deltaCh2Display.textContent = "--";
      deltaRatioDisplay.textContent = "No calibration";
    }
    return;
  }

  const sensors = await loadLatestSensors();
  if (liveFrequency) {
    const slot = Number.parseInt(sensors.frequency_slot || state.activeFrequencySlot, 10);
    const hz = Number(sensors.frequency_hz || getCurrentFrequencyValue());
    liveFrequency.textContent = `F${Number.isFinite(slot) ? slot : state.activeFrequencySlot} ${Number.isFinite(hz) ? hz.toFixed(2) : getCurrentFrequencyValue().toFixed(2)} kHz`;
  }
  if (!sensorsAreValid(sensors)) {
    primary.textContent = "Error";
    primaryStd.textContent = "-";
    primaryQuality.textContent = "Check USB";
    secondary.textContent = "Error";
    secondaryStd.textContent = "-";
    secondaryQuality.textContent = "Check USB";
    deltaCh1Display.textContent = "--";
    deltaCh2Display.textContent = "--";
    deltaRatioDisplay.textContent = "Check USB";
    return;
  }

  const ch1Val = Number(sensors.ch1.rms);
  primary.textContent = `${ch1Val.toFixed(3)} ${sensors.ch1.unit}`;
  primaryStd.textContent = `${Number(sensors.ch1.std).toFixed(6)}`;
  primaryQuality.textContent = `${Math.round(sensors.ch1.quality * 100)}%`;
  if (sensors.ch2?.valid === true) {
    const ch2Val = Number(sensors.ch2.rms);
    secondary.textContent = `${ch2Val.toFixed(3)} ${sensors.ch2.unit}`;
    secondaryStd.textContent = `${Number(sensors.ch2.std).toFixed(6)}`;
    secondaryQuality.textContent = `${Math.round(sensors.ch2.quality * 100)}%`;
  } else {
    secondary.textContent = "Pending";
    secondaryStd.textContent = "-";
    secondaryQuality.textContent = "STM32 CH2";
  }
  if (Number.isFinite(calCh1)) {
    const deltaCh1 = ch1Val - calCh1;
    deltaCh1Display.textContent = `${deltaCh1 >= 0 ? "+" : ""}${deltaCh1.toFixed(6)} ${sensors.ch1.unit}`;
    if (sensors.ch2?.valid === true && Number.isFinite(calCh2)) {
      const ch2Val = Number(sensors.ch2.rms);
      const deltaCh2 = ch2Val - calCh2;
      deltaCh2Display.textContent = `${deltaCh2 >= 0 ? "+" : ""}${deltaCh2.toFixed(6)} ${sensors.ch2.unit}`;
      deltaRatioDisplay.textContent = deltaCh2 !== 0 ? `${(deltaCh1 / deltaCh2).toFixed(6)}` : "--";
    } else {
      deltaCh2Display.textContent = "--";
      deltaRatioDisplay.textContent = "CH2 pending";
    }
  } else {
    deltaCh1Display.textContent = "--";
    deltaCh2Display.textContent = "--";
    deltaRatioDisplay.textContent = "No calibration";
  }
}

async function startLiveViewMonitor() {
  await loadAcquisitionMode();
  await refreshLiveViewReadings();

  clearInterval(state.engineeringTimer);
  state.engineeringTimer = setInterval(refreshLiveViewReadings, state.acquisitionMode === "daq" ? 1800 : 600);
}

function renderLoadCellReading(payload) {
  const weight = document.getElementById("loadCellWeight");
  const status = document.getElementById("loadCellStatus");
  const statusCard = status.closest(".metric-card");
  const port = document.getElementById("loadCellPort");
  const raw = document.getElementById("loadCellRaw");
  const updated = document.getElementById("loadCellUpdated");

  if (!payload?.ok) {
    weight.textContent = "-- g";
    status.textContent = "Error";
    statusCard.classList.remove("green");
    statusCard.classList.add("orange");
    port.textContent = payload?.port || "/dev/ttyUSB0";
    raw.textContent = `Error: ${payload?.error || "Unable to read load cell"}`;
    updated.textContent = state.loadCellHeld ? "Held" : `Updated: ${payload?.timestamp || "--"}`;
    return;
  }

  const weightValue = Number(payload.weight_g);
  weight.textContent = Number.isFinite(weightValue) ? `${weightValue.toFixed(3)} ${payload.unit || "g"}` : "-- g";
  if (payload.status === "zeroing") {
    status.textContent = "Zeroing";
    statusCard.classList.remove("green");
    statusCard.classList.add("orange");
  } else {
    status.textContent = payload.stable ? "Stable" : "Dynamic";
    statusCard.classList.toggle("green", Boolean(payload.stable));
    statusCard.classList.toggle("orange", !payload.stable);
  }
  port.textContent = payload.port || "/dev/ttyUSB0";
  raw.textContent = `Raw: ${payload.raw_response || "--"}`;
  updated.textContent = state.loadCellHeld ? "Held" : `Updated: ${payload.timestamp || "--"}`;
}

async function refreshLoadCellReading() {
  if (state.loadCellHeld) return;
  try {
    const response = await fetch("/api/load-cell/latest", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    renderLoadCellReading(payload);
  } catch (error) {
    renderLoadCellReading({ ok: false, error: "Cannot contact Flask load cell API" });
  }
}

async function readSingleLoadCell() {
  const status = document.getElementById("loadCellStatus");
  status.textContent = "Reading...";
  try {
    const response = await fetch("/api/load-cell/latest", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Unable to read load cell");
    renderLoadCellReading(payload);
    document.getElementById("loadCellRaw").textContent = `Single reading: ${payload.raw_response || "--"}`;
  } catch (error) {
    renderLoadCellReading({ ok: false, error: error.message || "Unable to read load cell" });
  }
}

async function readAverageLoadCell() {
  const status = document.getElementById("loadCellStatus");
  status.textContent = "Averaging...";
  try {
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Unable to average load cell");
    renderLoadCellReading({ ...payload, raw_response: `Average of ${payload.sample_count || 10} samples` });
    document.getElementById("loadCellRaw").textContent = `Average: ${payload.weight_g ?? "--"} g | Std: ${payload.std_g ?? "--"} g`;
  } catch (error) {
    renderLoadCellReading({ ok: false, error: error.message || "Unable to average load cell" });
  }
}

async function zeroLoadCell() {
  const status = document.getElementById("loadCellStatus");
  status.textContent = "Zeroing";
  const wasHeld = state.loadCellHeld;
  state.loadCellHeld = false;
  updateLoadCellHoldButton();
  try {
    const response = await fetch("/api/load-cell/zero", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) {
      throw new Error(payload.zero_error || payload.error || "Unable to zero load cell");
    }
    renderLoadCellReading({
      ok: true,
      weight_g: null,
      unit: "g",
      stable: false,
      status: "zeroing",
      raw_response: payload.zero_response || "TI",
      port: payload.port || "/dev/ttyUSB0",
      timestamp: payload.timestamp || "--"
    });
    setTimeout(() => {
      if (!state.loadCellHeld) {
        refreshLoadCellReading();
      }
    }, 800);
  } catch (error) {
    renderLoadCellReading({ ok: false, error: "Unable to zero load cell" });
  } finally {
    state.loadCellHeld = wasHeld;
    updateLoadCellHoldButton();
  }
}

async function prepareTeachingScale() {
  showScreen("teachingWeight");
  await sampleTeachingWeight();
}

async function prepareTeachingDimensionsFromVision() {
  const status = document.getElementById("teachingWeightStatus");
  const raw = document.getElementById("teachingWeightRaw");
  status.textContent = "Capturing image dimensions...";
  raw.textContent = "Calling vision service on port 8003";
  try {
    const vision = await fetchVisionSize(getTeachingShapeLabel(), "teaching");
    raw.textContent = vision.message || "Vision dimensions captured";
  } catch (error) {
    raw.textContent = `${error.message || "Vision unavailable"}; enter dimensions manually`;
  }
  teachingState.activeDimensionField = "width";
  updateTeachingDimensionDisplay();
  showScreen("teachingDimension");
}

async function zeroMeasurementScaleBeforePlacement() {
  const button = document.getElementById("startButton");
  const originalText = button.textContent;
  button.textContent = "Zeroing Scale...";
  button.disabled = true;
  resetMeasurementInputs();
  try {
    await fetch("/api/load-cell/zero", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
  } catch (error) {
    // Continue to placement; the weight page reports scale read errors.
  } finally {
    button.textContent = originalText;
    button.disabled = false;
  }
  showScreen("place");
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

async function zeroTeachingScaleBeforePlacement(mode) {
  teachingState.mode = mode;
  const button = mode === "validate"
    ? document.getElementById("teachingValidateButton")
    : document.getElementById("teachingStartButton");
  const originalText = button.textContent;
  button.textContent = "Zeroing...";
  button.disabled = true;
  resetTeachingInputs();
  try {
    await fetch("/api/load-cell/zero", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
  } catch (error) {
    // Continue anyway; the weight screen can still report scale read errors.
  } finally {
    button.textContent = originalText;
    button.disabled = false;
  }
  document.getElementById("teachingStage").textContent = "F1 Measuring";
  document.querySelector("#teachingRecordScreen .measure-copy p").textContent = "Switching to F1 and preparing live signal acquisition.";
  document.getElementById("teachingRecordButton").textContent = "Next";
  showScreen("teachingPlace");
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
  await readSingleLoadCell();
}

document.getElementById("startButton").addEventListener("click", () => {
  zeroMeasurementScaleBeforePlacement();
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
document.getElementById("modeToggleButton").addEventListener("click", toggleAcquisitionMode);
document.getElementById("engineeringLiveViewButton").addEventListener("click", () => showScreen("liveView"));
document.getElementById("engineeringFrequencyButton").addEventListener("click", async () => {
  await loadAcquisitionMode();
  updateFrequencyModeSelection();
  showScreen("frequencyMode");
});
document.getElementById("engineeringCalibrationButton").addEventListener("click", () => showScreen("calibration"));
document.getElementById("engineeringTeachingButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("engineeringDaqSettingsButton").addEventListener("click", () => showScreen("daqSettings"));
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
document.getElementById("liveViewBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("liveViewHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("liveRawTabButton").addEventListener("click", () => {
  state.liveViewTab = "raw";
  renderLiveViewTab();
});
document.getElementById("liveDeltaTabButton").addEventListener("click", () => {
  state.liveViewTab = "delta";
  renderLiveViewTab();
});
document.getElementById("daqSettingsBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("daqSettingsDoneButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("loadCellBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("loadCellSingleButton").addEventListener("click", readSingleLoadCell);
document.getElementById("loadCellAverageButton").addEventListener("click", readAverageLoadCell);
document.getElementById("loadCellTareButton").addEventListener("click", zeroLoadCell);
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
  showScreen(teachingState.material === "Other" ? "teachingOtherMaterial" : "teachingShape");
});
document.getElementById("teachingOtherMaterialBackButton").addEventListener("click", () => showScreen("teachingMaterial"));
document.getElementById("teachingOtherMaterialNextButton").addEventListener("click", () => showScreen("teachingPurity"));
document.getElementById("teachingPurityBackButton").addEventListener("click", () => showScreen("teachingOtherMaterial"));
document.getElementById("teachingPurityNextButton").addEventListener("click", () => showScreen("teachingShape"));
document.getElementById("teachingShapeBackButton").addEventListener("click", () => {
  showScreen(teachingState.material === "Other" ? "teachingPurity" : "teachingMaterial");
});
document.getElementById("teachingShapeNextButton").addEventListener("click", () => {
  if (teachingState.shape === "Other") {
    showScreen("teachingOtherShape");
    return;
  }
  prepareTeachingScale();
});
document.getElementById("teachingOtherShapeBackButton").addEventListener("click", () => showScreen("teachingShape"));
document.getElementById("teachingOtherShapeNextButton").addEventListener("click", () => {
  prepareTeachingScale();
});
document.getElementById("teachingDimensionBackButton").addEventListener("click", () => {
  showScreen("teachingWeight");
});
document.getElementById("teachingDimensionNextButton").addEventListener("click", () => {
  if (!teachingDimensionsAreValid()) return;
  startTeachingRecord();
});
document.getElementById("teachingDimensionsTabButton").addEventListener("click", () => selectTeachingDimensionPanel("dimensions"));
document.getElementById("teachingImageTabButton").addEventListener("click", () => selectTeachingDimensionPanel("image"));
document.getElementById("teachingRefreshImageButton").addEventListener("click", loadTeachingDetectedImage);
document.getElementById("teachingRemoveBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRemoveNextButton").addEventListener("click", () => showScreen("teachingSaved"));
document.getElementById("teachingSavedAgainButton").addEventListener("click", () => {
  resetTeachingInputs();
  showScreen("teachingPlace");
});
document.getElementById("teachingSavedDoneButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRecordsBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRecordsHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("teachingDetailBackButton").addEventListener("click", () => showScreen("teachingRecords"));
document.getElementById("teachingDetailHomeButton").addEventListener("click", () => showScreen("home"));
document.getElementById("teachingDetailDeleteButton").addEventListener("click", showDeletePasswordScreen);

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

function updateActiveRate(card) {
  const rateCard = document.getElementById("activeRateCard");
  const rateMove = document.getElementById("activeRateMove");

  document.getElementById("activeRateLabel").textContent = card.dataset.rateLabel;
  document.getElementById("activeRatePrice").textContent = card.dataset.ratePrice;
  document.getElementById("activeRateSource").textContent = `Source: ${card.dataset.rateSource}`;
  rateMove.textContent = card.dataset.rateMove;

  rateCard.classList.remove("gold-rate", "silver-rate", "palladium-rate");
  rateMove.classList.remove("up", "down", "flat");

  if (card.classList.contains("silver")) {
    rateCard.classList.add("silver-rate");
  } else if (card.classList.contains("palladium")) {
    rateCard.classList.add("palladium-rate");
  } else {
    rateCard.classList.add("gold-rate");
  }

  rateMove.classList.add(card.dataset.rateTrend || "flat");
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
