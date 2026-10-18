const screens = {
  home: document.getElementById("homeScreen"),
  readiness: document.getElementById("readinessScreen"),
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
  visionSettings: document.getElementById("visionSettingsScreen"),
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
  geometryReading: null,
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
  multiFrequenciesKhz: [8, 10, 15, 20],
  activeFrequencySlot: 1
};

const titles = {
  home: "Precious Metal Verification System",
  readiness: "System Readiness",
  scalePrepare: "Prepare Empty Scale",
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
  visionSettings: "System Assets",
  detectorSettings: "Detector Settings",
  frequencyMode: "Frequency Mode",
  frequencyEdit: "Edit Frequency"
};

// REV 2026-10-18 / ACCESS-01: the browser contains no engineering/admin PIN.
const engineeringScreens = new Set([
  "engineering", "readiness", "classifier", "liveView", "daqSettings", "loadCell",
  "calibration", "calibrationProgress", "calibrationResult", "detectorSettings",
  "frequencyMode", "frequencyEdit", "visionSettings",
  ...Object.keys(screens).filter((name) => name.startsWith("teaching"))
]);
let engineeringUnlocked = false;
let engineeringExpiryTimer = null;
let currentScreen = "home";
let historyReturnScreen = "home";
let screenNavigation = 0;
// ZERO-02: the internal operation is latched by the Weight service, not the browser.
let scalePreparationBusy = false;
let scalePreparationTimer = null;
let scalePreparationContext = "measurement";
let scalePreparationResult = null;
let scalePreparationPreviousId = null;
let scalePreparationJobId = null;
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
  geometryReading: null,
  activeDimensionField: "width",
  latestRecord: null,
  mode: "teach"
};
// FINISH-01: unavailable history must never display invented gold results.
const fallbackHistoryRecords = [];
let historyRecords = [...fallbackHistoryRecords];
const bottomMessages = [
  "Verify your sample now",
  "Proudly made in Malaysia",
  "Designed in Malaysia",
  "For Malaysia, made in Malaysia",
  "Semak ketulenan dengan yakin",
  "Buatan Malaysia"
];

async function showScreen(name) {
  // Keep the pan-empty instruction visible while the balance is operating.
  if (scalePreparationBusy && name !== "scalePrepare" && name !== "password") return;
  if (name !== "scalePrepare") clearTimeout(scalePreparationTimer);
  // Every entrance is checked, including Back buttons and direct JS navigation.
  const navigation = ++screenNavigation;
  if (engineeringScreens.has(name)) {
    let permitted = false;
    try {
      const response = await fetch("/api/engineering/session", { cache: "no-store" });
      permitted = response.ok && (await response.json()).authenticated;
    } catch (error) { /* Access stays locked if the service is unavailable. */ }
    if (navigation !== screenNavigation) return;
    if (!engineeringUnlocked || !permitted) {
      engineeringUnlocked = false;
      showPasswordScreen();
      return;
    }
  }
  if (name === "home" && engineeringUnlocked) {
    engineeringUnlocked = false;
    clearTimeout(engineeringExpiryTimer);
    try {
      await fetch("/api/engineering/logout", { method: "POST" });
    } catch (error) { /* The server also expires sessions after 30 minutes. */ }
    if (navigation !== screenNavigation) return;
  }
  if (name === "history" && !["historyDetail", "deletePassword"].includes(currentScreen)) {
    historyReturnScreen = engineeringScreens.has(currentScreen) ? "engineering" : "home";
  }
  const previousScreen = currentScreen;
  currentScreen = name;
  if (previousScreen !== name && removalScreen()) {removalNode("Confirm").checked = false;removalNode("Manual").checked=false;}
  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  screens[name].classList.add("active");
  document.getElementById("menuPanel").classList.remove("open");

  if (name !== "measure") {
    clearInterval(state.progressTimer);
  }

  if (name === "engineering") {
    loadAcquisitionMode();
    loadCalibration();
    loadTeachingRecords();
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

  // CAMERA-01: one shared preview follows the active user/engineering screen.
  updateCameraPreviewForScreen();
  if (name === "readiness") loadReadiness();
  if (name === "home") refreshReferenceRates();
  else stopReferenceRatesPolling();
}

function selectTeachingDimensionPanel(panel) {
  const dimensionsActive = panel !== "image";
  document.getElementById("teachingDimensionsPanel").classList.toggle("active", dimensionsActive);
  document.getElementById("teachingImagePanel").classList.toggle("active", !dimensionsActive);
  document.getElementById("teachingDimensionsTabButton").classList.toggle("active", dimensionsActive);
  document.getElementById("teachingImageTabButton").classList.toggle("active", !dimensionsActive);
  document.getElementById("teachingDimensionsTabButton").setAttribute("aria-selected", String(dimensionsActive));
  document.getElementById("teachingImageTabButton").setAttribute("aria-selected", String(!dimensionsActive));
  if (!dimensionsActive) updateCameraPreviewForScreen();
  else stopTeachingCameraPreview();
}

// REV 2026-10-18 / CAMERA-01: fresh camera preview, separate from frozen results.
let teachingCameraGeneration = 0;
let teachingCameraTimer = null;
let teachingCameraRequest = null;
let teachingCameraUrl = null;
let teachingCameraMode = "live";
let cameraAnnotationsEnabled = false;
let cameraSavedPhoto = null;
// NUC-03: one placement photograph per cycle; no end-user Snap control.
let placementCaptureId = null, placementBusy = false, placementCycle = 0, manualShapeMode = false;
let lastResultRecord = null;
let noticeResolve = null;
const cameraFailureScreens = new Set();
function showNotice(message, title = "Please check", question = false) {
  const dialog = document.getElementById("noticeDialog");
  if (noticeResolve) noticeResolve(false);
  document.getElementById("noticePhotoLinks").hidden = true;
  document.getElementById("noticeTitle").textContent = title;
  document.getElementById("noticeMessage").textContent = String(message || "Operation unavailable");
  document.getElementById("noticeCancel").hidden = !question;
  document.getElementById("noticeAccept").textContent = question ? "Continue with visual check" : "OK";
  if (!dialog.open) dialog.showModal();
  return new Promise(resolve => { noticeResolve = resolve; });
}
function closeNotice(answer = false) {
  document.getElementById("noticeDialog").close();
  const resolve = noticeResolve; noticeResolve = null;
  if (resolve) resolve(answer);
}
document.getElementById("noticeAccept").addEventListener("click", () => closeNotice(true));
document.getElementById("noticeCancel").addEventListener("click", () => closeNotice(false));
document.getElementById("noticeDialog").addEventListener("cancel", event => {event.preventDefault();closeNotice(false);});
function showResultDetails() {
  const r = lastResultRecord || {};
  showNotice([r.status, document.getElementById("resultReferenceSummary").textContent,
    document.getElementById("resultGeometrySummary").textContent,
    document.getElementById("resultScalePreparation").textContent,
    r.image_capture_error ? "Photo: " + r.image_capture_error : ""].filter(Boolean).join("\n\n"), "Result details");
  const photo=localPhoto(r);
  if (photo) {
    document.getElementById("noticeRawPhoto").href=photo.image_url;
    document.getElementById("noticeOverlayPhoto").href=photo.overlay_url;
    document.getElementById("noticePhotoLinks").hidden=false;
  }
}
document.getElementById("resultDetailsButton").addEventListener("click", showResultDetails);

let cameraDebugEnabled = false;
// REV 2026-10-18 / YOLO-01: three fresh, consistent frames before user placement continues.
let visionYoloConfig = null;
let visionLastDetection = null;
let visionStableFrames = 0;
let visionDetectionReceived = 0;
let visionGateTimer = null;

function yoloBoxOverlap(a, b) {
  if (!a || !b) return 0;
  const corners = v => [v[0]-v[2]/2, v[1]-v[3]/2, v[0]+v[2]/2, v[1]+v[3]/2];
  const x = corners(a), y = corners(b);
  const area = Math.max(0, Math.min(x[2],y[2])-Math.max(x[0],y[0])) * Math.max(0,Math.min(x[3],y[3])-Math.max(x[1],y[1]));
  return area / Math.max(1e-9, a[2]*a[3]+b[2]*b[3]-area);
}
function yoloCanContinue() {
  if (visionYoloConfig?.enabled === false) return true;
  const d = visionLastDetection;
  return visionYoloConfig?.enabled === true && d?.eligible === true && d.count === 1
    && d.revision === visionYoloConfig.revision && visionStableFrames >= 3
    && performance.now() - visionDetectionReceived + Number(d.capture_age_ms || 0) < 5000;
}
function updateYoloGate(message = "") {
  const autoReady = yoloCanContinue() && visionYoloConfig?.enabled === true;
  document.getElementById("placeContinueButton").disabled = !autoReady || placementBusy;
  document.getElementById("placeContinueButton").textContent = placementBusy ? "Saving photograph…" : autoReady ? "Use detected " + visionLastDetection.label + " →" : "Detecting automatically…";
  document.getElementById("autoDetectSummary").textContent = autoReady ? visionLastDetection.message : "Keep one item flat and still in the frame";
  const node = document.getElementById("cameraDetectionStatus");
  node.hidden = visionYoloConfig?.enabled === false || teachingCameraMode !== "live" || currentScreen === "scalePrepare";
  const d = visionLastDetection;
  node.textContent = message || (d ? `${d.message}${d.confidence != null ? " · " + (d.confidence*100).toFixed(0) + "%" : ""}${d.eligible ? " · steady " + visionStableFrames + "/3" : ""}` : "Waiting for live object detection");
  if (d?.eligible && !yoloCanContinue() && visionStableFrames >= 3) node.textContent = "Detection expired; waiting for a fresh frame";
  node.classList.toggle("vision-ready", Boolean(yoloCanContinue() && visionYoloConfig?.enabled));
}
function resetYoloDetection(message = "") {
  clearTimeout(visionGateTimer);
  visionLastDetection = null;
  visionStableFrames = 0;
  updateYoloGate(message);
}
function observeYoloDetection(detection) {
  const previous = visionLastDetection;
  const fresh = Number.isFinite(detection?.capture_age_ms) && detection.capture_age_ms < 5000;
  const acceptable = fresh && detection?.eligible === true && detection.count === 1 && detection.revision === visionYoloConfig?.revision;
  const consistent = acceptable && previous?.eligible && previous.revision === detection.revision
    && performance.now() - visionDetectionReceived + Number(previous.capture_age_ms || 0) < 5000
    && previous.label === detection.label
    && yoloBoxOverlap(previous.bbox_xywhn, detection.bbox_xywhn) > .5;
  visionStableFrames = acceptable ? (consistent ? Math.min(3, visionStableFrames + 1) : 1) : 0;
  visionLastDetection = detection;
  visionDetectionReceived = performance.now();
  clearTimeout(visionGateTimer);
  updateYoloGate();
  if (acceptable) visionGateTimer = setTimeout(() => updateYoloGate(), Math.max(0, 5010 - detection.capture_age_ms));
}
async function refreshYoloStatus() {
  visionYoloConfig = null;
  resetYoloDetection("Checking vision settings...");
  try {
    const response = await fetch("/api/vision/yolo/status", {cache:"no-store"});
    const payload = await response.json();
    if (!response.ok || typeof payload.enabled !== "boolean") throw new Error(payload.message || "Vision settings unavailable");
    visionYoloConfig = payload;
    updateYoloGate();
  } catch (error) {
    visionYoloConfig = {enabled:null};
    resetYoloDetection(error.message);
  }
}

// ASSETS-01: discovery lists names only; explicit adapters validate selected files.
function fillAssetSelect(id, files, role, selected) {
  const select = document.getElementById(id);
  select.replaceChildren();
  const paths = files.filter(file=>file.candidate_roles.includes(role)).map(file=>file.path);
  if (selected && !paths.includes(selected)) paths.unshift(selected);
  for (const path of paths) {
    const option = document.createElement("option");
    option.value = path;
    option.textContent = path + (files.some(file=>file.path===path) ? "" : " (missing)");
    select.appendChild(option);
  }
  select.value = selected || paths[0] || "";
}
async function scanSystemAssets() {
  const status = document.getElementById("assetsScanStatus");
  status.textContent = "Scanning...";
  try {
    const response = await fetch("/api/calibration/assets", {cache:"no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Scan failed");
    document.getElementById("assetsRoot").textContent = data.root;
    fillAssetSelect("visionModelPath", data.files, "vision", document.getElementById("visionModelPath").value);
    fillAssetSelect("assetsGoldModel", data.files, "gold", data.selection.gold);
    fillAssetSelect("assetsPurityModel", data.files, "purity", data.selection.purity);
    document.getElementById("assetsApiConfig").value = JSON.stringify(data.api, null, 2);
    await loadReferenceSettings(data.files);
    document.getElementById("assetsInventory").textContent = data.files.map(file=>file.path+" — "+file.status).join("\n") || "No supported candidate files found.";
    status.textContent = data.files.length + " files found. Select and validate before use.";
  } catch (error) { status.textContent = error.message; }
}
async function saveAssetConfiguration(kind) {
  const models = kind === "models";
  const status = document.getElementById(models ? "assetsModelsStatus" : "assetsApiStatus");
  const button = document.getElementById(models ? "assetsModelsSaveButton" : "assetsApiSaveButton");
  button.disabled = true;
  status.textContent = models ? "Validating both models..." : "Checking JSON...";
  try {
    const payload = models ? {gold:document.getElementById("assetsGoldModel").value, purity:document.getElementById("assetsPurityModel").value} : JSON.parse(document.getElementById("assetsApiConfig").value);
    const response = await fetch("/api/calibration/assets/"+kind, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Not saved");
    status.textContent = data.message || "Validated and activated. Gold Standard mode uses this pair on the next verification.";
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}
async function showApiReference(doc="api") {
  if(typeof doc!=="string")doc="api";
  const target = document.getElementById("assetsReference");
  try {
    const response = await fetch("/api/calibration/assets/reference?doc="+encodeURIComponent(doc), {cache:"no-store"});
    if (!response.ok) throw new Error("Engineering login required");
    target.textContent = await response.text(); target.hidden = false;
    const parent=target.closest?.("details");if(parent)parent.open=true;
    target.scrollIntoView?.({block:"nearest"});
  } catch (error) { document.getElementById("assetsApiStatus").textContent = error.message; }
}


// GEOMETRY-01: physical mask estimates are separate evidence; preserve learned
// classifiers' historical formula-area inputs until a matching model is used.
let geometryBusy = false;
let cameraGeometryBundle = null;
function geometrySummaryText(value) {
  if (!value) return "";
  if (!value.ok) return value.message || "Geometry unavailable";
  const number=(n,d=2)=>Number.isFinite(n)?n.toFixed(d):"unavailable";
  const source=value.height_source==="manual_known"?"known manual thickness":value.height_source==="depth_above_support"?"depth above support":"height unavailable";
  let text=`Footprint ${number(value.area_mm2)} mm² (SD ${number(value.area_std_mm2)}) · height ${number(value.height_mm,3)} mm (${source}) · volume ${number(value.volume_mm3)} mm³ · ${value.samples} frames.`;
  if (value.area_reference==="support_plane_projection") text+=" Area projected onto support plane; enter known thickness to refine.";
  const density=value.density_check;
  if (density?.available) text+=` Density ${number(density.density_g_cm3)} g/cm³ · ${density.message} (deviation ${number(density.deviation_pct,1)}%, tolerance ±${density.tolerance_pct}%).`;
  else text+=" Density unavailable: "+(density?.message || "stable mass and volume required")+".";
  if (value.warnings?.length) text+=" "+value.warnings.join("; ");
  return text+" Estimate only; does not establish gold or purity.";
}
function renderGeometrySummary(id,value) {
  const node=document.getElementById(id);
  if (!node) return;
  node.hidden=!value;node.textContent=geometrySummaryText(value);
}
async function measureGeometry(kind,manual=false) {
  if (geometryBusy) return;
  const teaching=kind==="teaching", target=teaching?teachingState:state;
  const prefix=teaching?"teaching":"user", screen=currentScreen, navigation=screenNavigation;
  const startingDimensions=JSON.stringify([target.widthMm,target.lengthMm,target.thicknessMm]);
  const status=document.getElementById(prefix+"GeometryStatus");
  const shape=teaching?getTeachingShapeLabel():getMeasurementShapeLabel();
  if (!["Coin","Bar"].includes(shape)) {status.textContent="Coin and bar only.";return;}
  const thickness=Number(target.thicknessMm);
  if (manual && (!Number.isFinite(thickness)||thickness<=0||thickness>50)) {status.textContent="Enter a known thickness in the keypad (0–50 mm), then press Use entered thickness.";return;}
  geometryBusy=true;target.geometryReading=null;
  renderGeometrySummary(prefix+"GeometrySummary",null);
  document.querySelectorAll(".geometry-measure").forEach(button=>button.disabled=true);
  const next=document.getElementById(teaching?"teachingDimensionNextButton":"dimensionNextButton");next.disabled=true;
  stopTeachingCameraPreview();
  status.textContent="Measuring repeated camera frames, then stable mass. Keep item still...";
  try {
    const response=await fetch("/api/vision/geometry/measure",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({shape,manual_height_mm:manual?thickness:null})});
    const value=await response.json();
    if (!response.ok) throw new Error(value.message||"Geometry measurement failed");
    if (currentScreen!==screen || screenNavigation!==navigation || (teaching?getTeachingShapeLabel():getMeasurementShapeLabel())!==shape
        || JSON.stringify([target.widthMm,target.lengthMm,target.thicknessMm])!==startingDimensions) {
      if(currentScreen===screen)status.textContent="Inputs or screen changed; old geometry result discarded. Measure again.";
      return;
    }
    const {preview,...evidence}=value;
    target.geometryReading=evidence;
    if(Number.isFinite(value.width_mm))target.widthMm=value.width_mm.toFixed(3);
    if(Number.isFinite(value.length_mm))target.lengthMm=value.length_mm.toFixed(3);
    if (value.height_mm!=null) target.thicknessMm=value.height_mm.toFixed(3);
    if(preview){cameraGeometryBundle=preview;teachingCameraMode="geometry";cameraAnnotationsEnabled=true;}
    if (teaching) updateTeachingDimensionDisplay();else updateDimensionDisplay();
    renderGeometrySummary(prefix+"GeometrySummary",value);
    status.textContent=value.volume_mm3==null?"Height unavailable. Enter known thickness and retry using that button.":"Mask dimensions filled. Footprint area and density are shown separately from the model formula area.";
  } catch(error) {if(currentScreen===screen){status.textContent="Measurement unavailable · enter known dimensions or retry";showNotice(error.message,"Geometry measurement");}}
  finally {
    geometryBusy=false;next.disabled=false;
    document.querySelectorAll(".geometry-measure").forEach(button=>button.disabled=false);
    if(currentScreen===screen)updateCameraPreviewForScreen(true);
  }
}
async function geometryEngineeringAction(action="status") {
  const status=document.getElementById("geometryReferenceStatus");
  if (action==="reference" && !document.getElementById("geometryEmptyConfirmed").checked) {status.textContent="Remove all items and tick the empty-support confirmation.";return;}
  const buttons=["geometryReferenceButton","geometryStatusButton","geometrySettingsSaveButton"].map(id=>document.getElementById(id));
  buttons.forEach(button=>button.disabled=true);status.textContent=action==="reference"?"Capturing empty-support frames...":"Checking geometry configuration...";
  try {
    let url="/api/calibration/geometry",options={cache:"no-store"};
    if(action!=="status"){
      url+="/"+action;
      options={method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(action==="reference"?{empty_confirmed:true}:JSON.parse(document.getElementById("geometrySettingsJson").value))};
    }
    let response=await fetch(url,options),value=await response.json();
    if(!response.ok)throw new Error(value.message||"Geometry unavailable");
    if(action!=="status"){
      response=await fetch("/api/calibration/geometry",{cache:"no-store"});value=await response.json();
      if(!response.ok)throw new Error(value.message||"Geometry status unavailable");
    }
    document.getElementById("geometrySettingsJson").value=JSON.stringify(value.settings,null,2);
    const ref=value.reference;
    status.textContent=value.reference_for_current_session?`Reference ${ref.reference_id} · ${ref.samples} frames · plane RMS ${ref.plane.rms_mm.toFixed(3)} mm. Clear the support and recalibrate if it moved.`:"No reference for this camera session. Remove items and capture one.";
    if(action==="reference")document.getElementById("geometryEmptyConfirmed").checked=false;
  }catch(error){status.textContent=error.message;}
  finally{buttons.forEach(button=>button.disabled=false);}
}


// REFERENCE-01: the selected bundle's contract is explicit; no legacy RF alias.
let referenceDraft = null;
async function loadReferenceSettings(files) {
  const status=document.getElementById("referenceModelStatus");
  try {
    const response=await fetch("/api/calibration/assets/reference-model",{cache:"no-store"});
    const cfg=await response.json();if(!response.ok)throw new Error(cfg.message||"Reference settings unavailable");
    referenceDraft=cfg;
    fillAssetSelect("referenceModelPath",files,"reference",cfg.model_path);
    document.getElementById("referenceMinScore").value=cfg.min_score*100;
    document.getElementById("referenceProfileConfirmed").checked=cfg.profile_confirmed;
    document.getElementById("referenceProfile").textContent=`F1–F4: ${cfg.frequency_hz.join(" / ")} Hz; ${cfg.amplitude_v_peak} V peak; signed raw-RMS change from air. Formula area, not mask area.`;
    status.textContent="Select the supplied signal_plus_geometry.joblib. Test does not retrain the model.";
  }catch(error){referenceDraft=null;status.textContent=error.message;}
}
async function submitReferenceModel(testOnly=false) {
  const status=document.getElementById("referenceModelStatus");
  if(!referenceDraft){status.textContent="Scan the asset folder first.";return;}
  const buttons=["referenceTestButton","referenceSaveButton","referenceUseButton"].map(id=>document.getElementById(id));buttons.forEach(button=>button.disabled=true);
  status.textContent="Checking the stored pipeline and library version...";
  try {
    const cfg={...referenceDraft,model_path:document.getElementById("referenceModelPath").value,
      min_score:Number(document.getElementById("referenceMinScore").value)/100,
      profile_confirmed:document.getElementById("referenceProfileConfirmed").checked};
    const response=await fetch("/api/calibration/assets/reference-model"+(testOnly?"/test":""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(cfg)});
    const value=await response.json();if(!response.ok)throw new Error(value.message||"Reference model failed validation");
    if(!testOnly)referenceDraft=value.settings;
    status.textContent=value.message+` Effective minimum score ${(value.metadata.effective_threshold*100).toFixed(0)}%.`;
  }catch(error){status.textContent=error.message;}
  finally{buttons.forEach(button=>button.disabled=false);}
}
async function useReferenceMode() {
  const status=document.getElementById("referenceModelStatus"),button=document.getElementById("referenceUseButton");button.disabled=true;
  try {
    const response=await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({classifier_algorithm:"gold_reference_v1"})});
    const value=await response.json();if(!response.ok)throw new Error(value.message||"Validate/select a confirmed reference profile first");
    state.classifierAlgorithm=value.classifier_algorithm;
    document.getElementById("classifierAlgorithmSelect").value=value.classifier_algorithm;
    status.textContent="Reference mode selected. Run fresh F1–F4 air calibration. Results are reference matches, not gold verification.";
  }catch(error){status.textContent=error.message;}
  finally{button.disabled=false;}
}
function renderReferenceSummary(id,record) {
  const node=document.getElementById(id);if(!node)return;
  const result=record?.classifier_result;node.hidden=!result?.reference_only;
  node.textContent=result?.reference_only?(result.simulation?"SIMULATION ONLY. ":"")+`Known-gold reference model · uncalibrated score ${Number(result.confidence||0).toFixed(2)}%. `+result.decision_message:"";
}

function visionFormValues() {
  const node = id => document.getElementById(id);
  return {enabled:node("visionEnabled").checked, model_path:node("visionModelPath").value,
    detection_confidence:Number(node("visionDetectionConfidence").value)/100,
    acceptance_confidence:Number(node("visionAcceptanceConfidence").value)/100,
    roi:["X","Y","W","H"].map(key=>Number(node("visionRoi"+key).value)/100), imgsz:640};
}
async function openVisionSettings() {
  await showScreen("visionSettings");
  if (currentScreen !== "visionSettings") return;
  const status = document.getElementById("visionSettingsStatus");
  status.textContent = "Loading...";
  try {
    const response = await fetch("/api/calibration/vision/settings", {cache:"no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Engineering login required");
    document.getElementById("visionEnabled").checked = data.enabled;
    fillAssetSelect("visionModelPath", [], "vision", data.model_path);
    await scanSystemAssets();
    geometryEngineeringAction("status");
    document.getElementById("visionDetectionConfidence").value = data.detection_confidence*100;
    document.getElementById("visionAcceptanceConfidence").value = data.acceptance_confidence*100;
    ["X","Y","W","H"].forEach((key,i)=>document.getElementById("visionRoi"+key).value=data.roi[i]*100);
    status.textContent = "Choose a scanned .pt, test it, then save. All paths are relative to system_assets.";
  } catch (error) { status.textContent = error.message; }
}
async function submitVisionSettings(testOnly = false) {
  const status = document.getElementById("visionSettingsStatus");
  const buttons = ["visionSaveButton","visionTestButton"].map(id=>document.getElementById(id));
  buttons.forEach(button=>button.disabled=true);
  status.textContent = "Loading/checking the local model. First load can take a moment...";
  try {
    const response = await fetch(`/api/calibration/vision/${testOnly ? "validate" : "settings"}`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(visionFormValues())
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Model/settings check failed");
    status.textContent = testOnly ? "Segmentation model ready: coin and bar." : "Saved. Open Live View to check detections and ROI.";
    if (!testOnly) visionYoloConfig = null;
  } catch (error) { status.textContent = error.message; }
  finally { buttons.forEach(button=>button.disabled=false); }
}


// CAMERA-DEBUG-01: debug is Engineering-only and never drawn into saved pixels.
function cameraDebugAllowed() {
  return engineeringUnlocked && engineeringScreens.has(currentScreen) && teachingCameraMode === "live" && !removalScreen();
}
function updateCameraDebugControls() {
  const button = document.getElementById("cameraDebugButton");
  button.hidden = !engineeringUnlocked || !engineeringScreens.has(currentScreen);
  button.disabled = teachingCameraMode !== "live";
  if (!cameraDebugAllowed()) cameraDebugEnabled = false;
  button.setAttribute("aria-pressed", String(cameraDebugEnabled));
  button.textContent = cameraDebugEnabled ? "Camera debug: on" : "Camera debug: off";
}
function drawCameraDebug(report) {
  const overlay = document.getElementById("cameraDebugOverlay");
  const details = document.getElementById("cameraDebugDetails");
  const visible = cameraDebugEnabled && cameraDebugAllowed() && Boolean(report);
  overlay.hidden = details.hidden = !visible;
  overlay.textContent = "";
  document.getElementById("cameraDebugJson").textContent = "";
  if (!visible) return;
  const intr = report.aligned_depth || {};
  const distance = report.scene_distance_mm?.median;
  const number = value => Number.isFinite(value) ? value.toFixed(2) : "--";
  overlay.textContent = `${intr.width || "--"}x${intr.height || "--"} | fx ${number(intr.fx_px)} fy ${number(intr.fy_px)} px\nScene range ${number(distance)} mm (not thickness)\nValid sampled depth ${number(report.valid_depth_percent)}%`;
  document.getElementById("cameraDebugJson").textContent = JSON.stringify(report, null, 2);
}


function cameraPreviewShape() {
  if (currentScreen === "teachingDimension") return getTeachingShapeLabel();
  if (currentScreen === "liveView") return document.getElementById("cameraShapeSelect").value;
  return getMeasurementShapeLabel();
}

function drawCameraOverlay(annotation) {
  const svg = document.getElementById("cameraAnnotationOverlay");
  svg.replaceChildren();
  svg.hidden = !cameraAnnotationsEnabled || !annotation;
  if (svg.hidden) return;
  const width = Number(annotation.image?.width);
  const height = Number(annotation.image?.height);
  if (!(width > 0 && height > 0)) return;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  if (annotation.detection?.roi_xywhn) {
    const [x,y,w,h] = annotation.detection.roi_xywhn;
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    for (const [key,value] of Object.entries({x:x*width,y:y*height,width:w*width,height:h*height,fill:"none",stroke:"#fbbf24","stroke-width":2,"stroke-dasharray":"6 4"})) rect.setAttribute(key,String(value));
    svg.appendChild(rect);
  }
  for (const object of annotation.objects || []) {
    if (Number.isFinite(object.confidence) && object.bbox_xywhn) {
      const [x,y,w,h] = object.bbox_xywhn;
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x",String(Math.max(0,(x-w/2)*width)));
      text.setAttribute("y",String(Math.max(18,(y-h/2)*height-4)));
      text.setAttribute("fill",object.accepted ? "#22c55e" : "#fbbf24");
      text.setAttribute("font-size",String(Math.max(16,width/50)));
      text.textContent = `${object.label} ${(object.confidence*100).toFixed(0)}%`;
      svg.appendChild(text);
    }
    const paths=[];
    for (const polygon of object.polygons || []) {
      const points=polygon.points||[];
      if(points.length<3 || !points.every(p=>p.length===2 && p.every(v=>Number.isFinite(v)&&v>=0&&v<=1)))continue;
      paths.push(points.map(([x,y],i)=>`${i?"L":"M"}${x*width},${y*height}`).join(" ")+" Z");
    }
    if(paths.length){
      const path=document.createElementNS("http://www.w3.org/2000/svg","path");
      for(const [key,value] of Object.entries({d:paths.join(" "),fill:"rgba(34,197,94,0.25)","fill-rule":"evenodd",stroke:"#22c55e","stroke-width":2,"vector-effect":"non-scaling-stroke"}))path.setAttribute(key,String(value));
      svg.appendChild(path);
    }
  }
}

function localPhoto(record) {
  const value = record?.evidence_image || record?.image || {};
  const photo = typeof value === "string" ? {image_url:value} : value;
  let raw = photo.image_url || photo.url || record?.image_url;
  if (!raw) return null;
  if (/^\/?teaching_images\//.test(raw)) raw = "/api/teaching/image/" + raw.split("/").pop();
  if (!/^\/api\/(verification|teaching)\/image\/[A-Za-z0-9_.-]+\.(jpg|jpeg|png)$/i.test(raw)) return null;
  return {...photo, image_url:raw, overlay_url:raw.replace(/\.(jpg|jpeg|png)$/i,".html"),
    annotation_url:photo.annotation_url || raw.replace(/\.(jpg|jpeg|png)$/i,".json")};
}

function renderSavedPhoto(prefix, record) {
  const panel = document.getElementById(prefix + "PhotoPanel");
  const photo = localPhoto(record);
  panel.hidden = !photo;
  if (!photo) return;
  const rawLink = document.getElementById(prefix + "PhotoDownload");
  rawLink.href = photo.image_url;
  const overlayLink = document.getElementById(prefix + "PhotoViewer");
  overlayLink.href = photo.overlay_url;
  const frame = document.getElementById(prefix + "PhotoFrame");
  if (frame) frame.src = photo.overlay_url;
}

async function saveCameraPhoto() {
  const button = document.getElementById("cameraSavePhotoButton");
  const status = document.getElementById("cameraPhotoStatus");
  button.disabled = true;
  try {
    const teaching = engineeringScreens.has(currentScreen);
    const response = await fetch(`/api/${teaching ? "teaching" : "verification"}/image/capture`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({shape:cameraPreviewShape(), detector:visionYoloConfig?.enabled ? "yolo" : "legacy"})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "Photo could not be saved");
    cameraSavedPhoto = {...payload.image, scope:teaching ? "teaching" : "verification"};
    const link = document.getElementById("cameraPhotoDownload");
    link.href = cameraSavedPhoto.image_url;
    link.hidden = false;
    status.textContent = payload.warning ? "Raw photo saved; detection unavailable: " + payload.warning : "Photo saved. Automatic masks require review before training.";
    document.getElementById("teachingCapturedImageButton").disabled = false;
  } catch (error) {
    status.textContent = error.message;
  } finally { button.disabled = false; }
}


// REV 2026-10-18 / REMOVE-01: three fresh clear batches + human inspection.
// Preview and removal use the SAME request loop, avoiding duplicate YOLO work.
let removalEvidence = null, removalClearBatches = 0, removalReceivedAt = 0;
let removalExpiryTimer = null, removalConfirmBusy = false;
function removalScreen() { return ["result", "teachingRemove"].includes(currentScreen); }
function removalNode(suffix) { return document.getElementById((currentScreen === "result" ? "result" : "teaching") + "Removal" + suffix); }
function resetRemovalEvidence(message = "Waiting for live removal checks...") {
  clearTimeout(removalExpiryTimer); removalEvidence = null; removalClearBatches = 0;
  if (removalScreen()) renderRemovalState(message);
}
function removalReady() {
  return removalEvidence?.ready_for_confirmation === true && removalClearBatches >= 3
    && teachingCameraMode === "live" && !document.hidden
    && performance.now() - removalReceivedAt + Number(removalEvidence.evidence_age_ms || 0) < 5000;
}
function renderRemovalState(message = "") {
  if (!removalScreen()) return;
  const ready = removalReady(), confirm = removalNode("Confirm");
  confirm.disabled = false; // NUC-02: the human check must remain usable.
  removalNode("Manual").disabled = false;
  removalNode("Status").textContent = message || (ready ? "Sensors indicate empty · please confirm visually" : `Checking pan… ${removalClearBatches}/3 · visual confirmation available`);
  removalNode("Status").classList.toggle("vision-ready", ready);
}
function observeRemovalEvidence(value) {
  const previous = removalEvidence;
  const continuous = previous?.preparation_id === value?.preparation_id
    && performance.now() - removalReceivedAt + Number(previous?.evidence_age_ms || 0) < 5000;
  const fresh = Number.isFinite(value?.evidence_age_ms) && value.evidence_age_ms < 5000;
  removalClearBatches = value?.ready_for_confirmation === true && fresh ? (continuous ? removalClearBatches + 1 : 1) : 0;
  removalClearBatches = Math.min(3, removalClearBatches);
  removalEvidence = value; removalReceivedAt = performance.now();
  clearTimeout(removalExpiryTimer); renderRemovalState();
  removalExpiryTimer = setTimeout(() => resetRemovalEvidence("Removal evidence expired. Select Live and wait for fresh checks."), Math.max(1,5000-Number(value?.evidence_age_ms || 0)));
}
async function confirmItemRemoved(next) {
  if (removalConfirmBusy) return;
  if (!removalNode("Confirm").checked) {
    showNotice("Remove the item and tick the box after inspecting the entire pan.", "Pan empty?");
    return;
  }
  let manual = removalNode("Manual").checked;
  if (!removalReady() && !manual) {
    removalConfirmBusy = true;
    const screen = currentScreen, navigation = screenNavigation;
    try {
      manual = await showNotice("Sensors have not confirmed an empty pan. Inspect the physical pan. Continue using your visual confirmation? No zero or internal adjustment will run.", "Manual removal confirmation", true);
      if (screen !== currentScreen || navigation !== screenNavigation || !manual) return;
    } finally {removalConfirmBusy = false;}
  }
  if (manual) {await next();return;} // User chose visual confirmation, not sensor proof.
  const previousId = removalEvidence.preparation_id, navigation = screenNavigation, screen = currentScreen;
  removalConfirmBusy = true;
  stopTeachingCameraPreview();
  removalNode("Status").textContent = "Checking once more before continuing...";
  const controller = new AbortController(); teachingCameraRequest = controller;
  const timeout = setTimeout(() => controller.abort(),12000);
  let moved = false;
  try {
    const response = await fetch("/api/verification/removal/check", {cache:"no-store",signal:controller.signal});
    const bundle = await response.json();
    if (navigation !== screenNavigation || screen !== currentScreen || document.hidden) return;
    const check = bundle.removal;
    if (!response.ok || !check?.ready_for_confirmation || check.preparation_id !== previousId || !Number.isFinite(check.evidence_age_ms) || check.evidence_age_ms >= 5000) {
      throw new Error(check?.message || bundle.message || "Removal remains unconfirmed. Try Live again.");
    }
    moved = true;
    await next();
  } catch (error) {
    if (navigation === screenNavigation && screen === currentScreen) {removalNode("Status").textContent = "Sensor check unavailable; visual confirmation remains available.";showNotice(error.message || "Removal check timed out. Retry or use visual confirmation.","Removal check");}
  } finally {
    clearTimeout(timeout); removalConfirmBusy = false;
    if (!moved && navigation === screenNavigation && screen === currentScreen) {
      // Resume automatically; the failure message remains until a fresh batch arrives.
      teachingCameraMode = "live"; loadTeachingDetectedImage();
    }
  }
}

// FINISH-01: passive readiness report stays behind Engineering authentication.
async function loadReadiness() {
  const status = document.getElementById("readinessStatus"), button = document.getElementById("readinessRefreshButton");
  const rows = document.getElementById("readinessRows");
  button.disabled = true; status.textContent = "Checking services and configuration; no sensors are activated..."; rows.replaceChildren();
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(),15000);
  try {
    const response = await fetch("/api/calibration/readiness",{cache:"no-store",signal:controller.signal});
    const report = await response.json();
    if (!response.ok) throw new Error(report.message || "Readiness unavailable; log into Engineering again");
    if (currentScreen !== "readiness") return;
    status.textContent = `${report.ready_for_trial ? "Passive checks passed" : "Setup needs attention"}. ${report.note}`;
    for (const check of report.checks) {
      const row=document.createElement("article"), heading=document.createElement("strong"), text=document.createElement("p");
      row.className="readiness-row"; heading.textContent=`${check.state.toUpperCase()} · ${check.name}`;text.textContent=check.message;
      row.append(heading,text);
      if (check.details) {const details=document.createElement("details"), summary=document.createElement("summary"), pre=document.createElement("pre");summary.textContent="Details";pre.textContent=JSON.stringify(check.details,null,2);details.append(summary,pre);row.append(details);}
      rows.appendChild(row);
    }
  } catch(error) {if(currentScreen === "readiness")status.textContent=error.message || "Readiness request failed";}
  finally {clearTimeout(timeout);button.disabled=false;}
}

function cameraPreviewHost() {
  if (currentScreen === "teachingDimension") {
    const panel = document.getElementById("teachingImagePanel");
    return panel.classList.contains("active") ? panel : null;
  }
  const hosts = {
    place: "userPlaceCameraHost",
    teachingRemove: "teachingRemoveCameraHost", result: "userResultCameraHost", liveView: "engineeringCameraHost",
    scalePrepare: "scalePreparationCameraHost"
  };
  return hosts[currentScreen] ? document.getElementById(hosts[currentScreen]) : null;
}

function teachingCameraPanelVisible() {
  return Boolean(cameraPreviewHost()) && !document.hidden;
}

async function updateCameraPreviewForScreen(preserveMode=false) {
  stopTeachingCameraPreview();
  updateCameraDebugControls();
  const host = cameraPreviewHost();
  document.getElementById("cameraSavePhotoButton").hidden = !engineeringScreens.has(currentScreen);
  document.getElementById("cameraPreviewWidget").classList.toggle("user-camera", !engineeringScreens.has(currentScreen));
  if (!host) return;
  document.getElementById("cameraBackToFlowButton").hidden=!["place","dimension","teachingDimension","result"].includes(currentScreen);
  host.appendChild(document.getElementById("cameraPreviewWidget"));
  // PHOTO-01: live preview, saved user photo and captured measurement stay distinct.
  const teaching = engineeringScreens.has(currentScreen);
  if (!teaching && cameraSavedPhoto?.scope === "teaching") cameraSavedPhoto = null;
  const capturedButton = document.getElementById("teachingCapturedImageButton");
  capturedButton.hidden = false;
  capturedButton.disabled = !teaching && !cameraSavedPhoto;
  document.getElementById("cameraShapeSelect").hidden = currentScreen !== "liveView";
  if (!teaching && !preserveMode) {
    teachingCameraMode = "live";
  }
  const photoLink = document.getElementById("cameraPhotoDownload");
  photoLink.hidden = !cameraSavedPhoto;
  if (cameraSavedPhoto) photoLink.href = cameraSavedPhoto.image_url;
  const generation = teachingCameraGeneration;
  const screen = currentScreen;
  await refreshYoloStatus();
  if (generation !== teachingCameraGeneration || screen !== currentScreen) return;
  if(visionYoloConfig?.enabled && ["place","dimension","measure"].includes(currentScreen))cameraAnnotationsEnabled=true;
  document.getElementById("cameraShapeSelect").hidden = currentScreen !== "liveView" || visionYoloConfig?.enabled === true;
  loadTeachingDetectedImage();
}

function stopTeachingCameraPreview() {
  teachingCameraGeneration += 1;
  resetRemovalEvidence();
  clearTimeout(teachingCameraTimer);
  if (teachingCameraRequest) teachingCameraRequest.abort();
  teachingCameraRequest = null;
  if (teachingCameraUrl) URL.revokeObjectURL(teachingCameraUrl);
  teachingCameraUrl = null;
  drawCameraOverlay(null);
  drawCameraDebug(null);
  resetYoloDetection();
}

function loadTeachingDetectedImage() {
  stopTeachingCameraPreview();
  updateCameraDebugControls();
  if (!teachingCameraPanelVisible()) return;
  const generation = teachingCameraGeneration;
  const live = teachingCameraMode === "live";
  const image = document.getElementById("teachingDetectedImage");
  const status = document.getElementById("teachingDetectedImageStatus");
  image.onload = null;
  image.onerror = null;
  image.hidden = true;
  status.textContent = live ? "Connecting to live camera..." : "Loading captured result...";
  document.getElementById("cameraBackToLiveButton").hidden=live;
  document.getElementById("teachingRefreshImageButton").setAttribute("aria-pressed", String(live));
  document.getElementById("teachingCapturedImageButton").setAttribute("aria-pressed", String(!live));
  const overlayButton = document.getElementById("cameraAnnotationButton");
  overlayButton.setAttribute("aria-pressed", String(cameraAnnotationsEnabled));
  overlayButton.textContent = cameraAnnotationsEnabled ? "Annotations: on" : "Annotations: off";

  async function nextFrame() {
    if (generation !== teachingCameraGeneration || !teachingCameraPanelVisible()) return;
    const removalLive = live && removalScreen();
    const yoloLive = live && visionYoloConfig?.enabled === true && currentScreen !== "scalePrepare";
    const controller = new AbortController();
    teachingCameraRequest = controller;
    const timeout = setTimeout(() => controller.abort(), removalLive ? 45000 : yoloLive ? 45000 : 8000);
    let delay = 200; // At most five preview frames/second; no overlapping requests.
    let url = null;
    try {
      let blob, annotation = null, legacy = false, debugReport = null;
      const debugLive = live && cameraDebugEnabled && cameraDebugAllowed();
      if (removalLive) {
        delay = 1000;
        const response = await fetch("/api/verification/removal/check",{cache:"no-store",signal:controller.signal});
        const bundle = await response.json();
        if (generation !== teachingCameraGeneration) return;
        if (!response.ok) throw new Error(bundle.message || "Removal check unavailable");
        observeRemovalEvidence(bundle.removal);
        if (!bundle.raw_jpeg_base64) {
          image.hidden = true; drawCameraOverlay(null); drawCameraDebug(null);
          status.textContent = bundle.removal?.camera_error ? "Camera unavailable; inspect the physical pan directly." : "No fresh frame";
          return;
        }
        annotation = bundle.annotation;
        if (yoloLive) observeYoloDetection(bundle.detection);
        const bytes = Uint8Array.from(atob(bundle.raw_jpeg_base64),c=>c.charCodeAt(0));
        blob = new Blob([bytes],{type:"image/jpeg"});
      } else if (yoloLive) {
        delay = 1000; // One sequential inference request at a time; no raw-preview inference load.
        const endpoint = debugLive ? "/api/calibration/vision/frame?debug=1" : "/api/vision/yolo/frame";
        const response = await fetch(endpoint, {cache:"no-store",signal:controller.signal});
        const bundle = await response.json();
        if (!response.ok) throw new Error(bundle.message || "YOLO/camera unavailable");
        annotation = bundle.annotation;
        debugReport = debugLive ? bundle.camera_debug : null;
        const bytes = Uint8Array.from(atob(bundle.raw_jpeg_base64), c=>c.charCodeAt(0));
        blob = new Blob([bytes], {type:"image/jpeg"});
        if (generation !== teachingCameraGeneration) return;
        observeYoloDetection(bundle.detection);
      } else if (teachingCameraMode === "geometry" && cameraGeometryBundle) {
        annotation=cameraGeometryBundle.annotation;
        const bytes=Uint8Array.from(atob(cameraGeometryBundle.raw_jpeg_base64),c=>c.charCodeAt(0));
        blob=new Blob([bytes],{type:"image/jpeg"});
      } else if (teachingCameraMode === "saved" && cameraSavedPhoto) {
        const response = await fetch(cameraSavedPhoto.image_url, {cache:"no-store", signal:controller.signal});
        if (!response.ok) throw new Error("Saved photo unavailable");
        blob = await response.blob();
        if (cameraAnnotationsEnabled) {
          const sidecar = await fetch(cameraSavedPhoto.annotation_url, {cache:"no-store", signal:controller.signal});
          if (sidecar.ok) annotation = await sidecar.json();
        }
      } else if (cameraAnnotationsEnabled || !live || debugLive) {
        const query = live ? `shape=${encodeURIComponent(cameraPreviewShape())}&annotations=${cameraAnnotationsEnabled ? 1 : 0}` : "captured=1";
        const frameEndpoint = debugLive ? "/api/calibration/camera/frame" : "/api/vision/image/frame";
        const response = await fetch(`${frameEndpoint}?${query}&t=${Date.now()}`, {
          cache:"no-store", signal:controller.signal
        });
        if (!response.ok && !live) {
          // Older services/records can still supply the original pre-annotated JPEG.
          const fallback = await fetch(`/api/vision/image/detected?t=${Date.now()}`, {cache:"no-store",signal:controller.signal});
          if (!fallback.ok) throw new Error("No captured result");
          blob = await fallback.blob();
          legacy = true;
        } else {
          if (!response.ok) throw new Error(`Camera service returned ${response.status}`);
          const bundle = await response.json();
          annotation = bundle.annotation;
          debugReport = debugLive ? bundle.camera_debug : null;
          if (debugLive && !debugReport) throw new Error("Camera diagnostics unavailable; restart Image service with this patch");
          const bytes = Uint8Array.from(atob(bundle.raw_jpeg_base64), c=>c.charCodeAt(0));
          blob = new Blob([bytes], {type:"image/jpeg"});
        }
      } else {
        const response = await fetch(`/api/vision/image/live?t=${Date.now()}`, {cache:"no-store",signal:controller.signal});
        if (!response.ok) throw new Error(`Camera service returned ${response.status}`);
        blob = await response.blob();
      }
      if (generation !== teachingCameraGeneration) return;
      url = URL.createObjectURL(blob);
      image.src = url;
      await image.decode();
      if (generation !== teachingCameraGeneration) return;
      if (teachingCameraUrl) URL.revokeObjectURL(teachingCameraUrl);
      teachingCameraUrl = url;
      url = null;
      image.hidden = false;
      drawCameraOverlay(legacy ? null : annotation);
      drawCameraDebug(debugReport);
      status.textContent = legacy ? "Legacy captured JPEG; its existing markings are part of the image"
        : (live ? `Live camera - ${new Date().toLocaleTimeString()}` : (teachingCameraMode==="geometry"?"Measured mask frame - not live":"Captured photo - not live"));
      if (cameraAnnotationsEnabled && annotation?.warning) status.textContent += " | Outlines unavailable: " + annotation.warning;
      else if (cameraAnnotationsEnabled && annotation) status.textContent += annotation.label_source==="model_prediction"?" | Segmentation mask; unreviewed":" | Automatic outlines; unreviewed";
    } catch (error) {
      if (generation !== teachingCameraGeneration) return;
      image.hidden = true; // Never present an old frame as current after an error.
      drawCameraOverlay(null);
      drawCameraDebug(null);
      resetYoloDetection(yoloLive ? error.message : "Live detection unavailable");
      if (removalLive) resetRemovalEvidence(error.message || "Removal check failed; retry Live.");
      status.textContent = live
        ? "Live camera unavailable; retrying. Check Image service on port 8003."
        : "No captured result available. Take a measurement first.";
      if (!removalLive && !cameraFailureScreens.has(currentScreen)) {
        cameraFailureScreens.add(currentScreen);
        showNotice(error.message || "Check Image service on port 8003.", "Camera unavailable");
      }
      delay = 2000;
    } finally {
      clearTimeout(timeout);
      if (url) URL.revokeObjectURL(url);
      if (generation === teachingCameraGeneration) {
        teachingCameraRequest = null;
        if (live && teachingCameraPanelVisible()) {
          teachingCameraTimer = setTimeout(nextFrame, delay);
        }
      }
    }
  }
  nextFrame();
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopTeachingCameraPreview();
  else if (teachingCameraMode === "live" && teachingCameraPanelVisible()) updateCameraPreviewForScreen();
});
window.addEventListener("pagehide", stopTeachingCameraPreview);

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

function formatDimension(value){const n=Number(value||0);return Number.isFinite(n)?n.toFixed(2).replace(/\.?0+$/,"")||"0":"0";}
function updateDimensionDisplay() {
  document.getElementById("userGeometryPanel").hidden=!["Coin","Bar"].includes(getMeasurementShapeLabel());
  const config = getMeasurementDimensionConfig();
  document.getElementById("widthLabel").textContent = config.labels.width;
  document.getElementById("lengthLabel").textContent = config.labels.length;
  document.getElementById("thicknessFieldButton").querySelector("span").textContent = config.labels.thickness;
  document.getElementById("lengthFieldButton").classList.toggle("hidden", Boolean(config.hideLength));
  if (config.hideLength && state.activeDimensionField === "length") {
    state.activeDimensionField = "width";
  }
  document.getElementById("widthDisplay").textContent = formatDimension(state.widthMm);
  document.getElementById("lengthDisplay").textContent = formatDimension(config.hideLength?state.widthMm:state.lengthMm);
  document.getElementById("thicknessDisplay").textContent = formatDimension(state.thicknessMm);
  const geometry = calculateGeometryForMeasurement();
  const maskArea=state.geometryReading?.area_mm2;
  const useMask=visionYoloConfig?.enabled && ["Coin","Bar"].includes(getMeasurementShapeLabel());
  document.getElementById("sampleAreaDisplay").textContent=useMask?(Number.isFinite(maskArea)?`${maskArea.toFixed(2)} mm²`:"unavailable"):`${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("userFormulaAreaDisplay").textContent=`${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("contactRatioDisplay").textContent=useMask?(Number.isFinite(maskArea)?`${(maskArea/(Math.PI*35*35)*100).toFixed(2)}%`:"unavailable"):`${geometry.contactRatio.toFixed(2)}%`;
  updateDimensionFieldSelection();
}

function updateTeachingDimensionDisplay() {
  document.getElementById("teachingGeometryPanel").hidden=!["Coin","Bar"].includes(getTeachingShapeLabel());
  const config = getTeachingDimensionConfig();
  document.getElementById("teachingWidthLabel").textContent = config.labels.width;
  document.getElementById("teachingLengthLabel").textContent = config.labels.length;
  document.getElementById("teachingThicknessLabel").textContent = config.labels.thickness;
  document.getElementById("teachingLengthFieldButton").classList.toggle("hidden", Boolean(config.hideLength));
  if (config.hideLength && teachingState.activeDimensionField === "length") {
    teachingState.activeDimensionField = "width";
  }
  document.getElementById("teachingWidthDisplay").textContent = formatDimension(teachingState.widthMm);
  document.getElementById("teachingLengthDisplay").textContent = formatDimension(config.hideLength?teachingState.widthMm:teachingState.lengthMm);
  document.getElementById("teachingThicknessDisplay").textContent = formatDimension(teachingState.thicknessMm);
  const geometry = calculateGeometryForTeaching();
  const maskArea=teachingState.geometryReading?.area_mm2;
  const useMask=visionYoloConfig?.enabled && ["Coin","Bar"].includes(getTeachingShapeLabel());
  document.getElementById("teachingSampleAreaDisplay").textContent=useMask?(Number.isFinite(maskArea)?`${maskArea.toFixed(2)} mm²`:"unavailable"):`${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("teachingFormulaAreaDisplay").textContent=`${geometry.sampleArea.toFixed(2)} mm²`;
  document.getElementById("teachingContactRatioDisplay").textContent = `${geometry.contactRatio.toFixed(2)}%`;
  updateTeachingDimensionFieldSelection();
}

function setDimensionValue(field, value) {
  state.geometryReading=null;renderGeometrySummary("userGeometrySummary",null);
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
  teachingState.geometryReading=null;renderGeometrySummary("teachingGeometrySummary",null);
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
  state.scalePreparationId = null;
  placementCycle++; placementCaptureId = null; placementBusy = false; manualShapeMode = false;
  cameraFailureScreens.clear();
  cameraSavedPhoto = null;
  document.getElementById("cameraPhotoDownload").hidden = true;
  document.getElementById("cameraPhotoStatus").textContent = "";
  setWeight("");
  state.measurementWeightSampling = false;
  state.measurementWeightReady = false;
  state.widthMm = "";
  state.lengthMm = "";
  state.thicknessMm = "";
  state.visionMeasurement = null;
  state.geometryReading = null;
  renderGeometrySummary("userGeometrySummary",null);
  state.activeDimensionField = "width";
  state.shape = "Coin";
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
  teachingState.scalePreparationId = null;
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
  teachingState.geometryReading = null;
  renderGeometrySummary("teachingGeometrySummary",null);
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
  const index = Math.max(0, Math.min(3, Number(state.activeFrequencySlot || 1) - 1));
  return state.multiFrequenciesKhz[index] || 0;
}

function updateFrequencyModeSelection() {
  for (let slot = 1; slot <= 4; slot += 1) {
    const button = document.getElementById(`frequencySlot${slot}Button`);
    button.classList.toggle("selected", state.activeFrequencySlot === slot);
    button.textContent = `F${slot} · ${state.multiFrequenciesKhz[slot - 1] || "not set"} kHz`;
  }
  document.getElementById("frequencyModeStatus").textContent =
    `Selected F${state.activeFrequencySlot}: ${getCurrentFrequencyValue().toFixed(2)} kHz`;
  document.getElementById("selectedFrequencyLabel").textContent = `Frequency ${state.activeFrequencySlot}`;
  document.getElementById("selectedFrequencyDisplay").textContent = String(getCurrentFrequencyValue());
  const freqText = state.multiFrequenciesKhz.map((value, index) => `F${index + 1} ${Number(value).toFixed(2)} kHz`).join(" · ");
  const calTag = document.getElementById("calibrationFrequencyTag");
  const teachTag = document.getElementById("teachingFrequencyTag");
  const liveTag = document.getElementById("liveFrequency");
  if (calTag) calTag.textContent = freqText;
  if (teachTag) teachTag.textContent = freqText;
  if (liveTag) liveTag.textContent = `F${state.activeFrequencySlot} ${getCurrentFrequencyValue().toFixed(2)} kHz`;
}

async function selectFrequencySlot(slot) {
  if (slot > state.multiFrequenciesKhz.length) {
    state.activeFrequencySlot = slot;
    updateFrequencyModeSelection();
    showScreen("frequencyEdit");
    return;
  }
  const previousSlot = state.activeFrequencySlot;
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
    if (savedSlot >= 1 && savedSlot <= state.multiFrequenciesKhz.length) state.activeFrequencySlot = savedSlot;
  } catch (error) {
    state.activeFrequencySlot = previousSlot;
    updateFrequencyModeSelection();
    document.getElementById("frequencyModeStatus").textContent = error.message || "Frequency was not applied";
    return;
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

async function submitPassword() {
  const panel = document.querySelector(".password-panel");
  const message = document.getElementById("passwordMessage");
  const pin = state.password;
  state.password = "";
  updatePasswordDisplay();
  try {
    const response = await fetch("/api/engineering/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(response.status === 429 ? "Too many attempts. Wait 60 seconds." : "Invalid PIN");
    }
    // Cancelling the login while its request was in flight must not reopen Engineering.
    if (currentScreen !== "password") {
      await fetch("/api/engineering/logout", { method: "POST" });
      return;
    }
    engineeringUnlocked = true;
    clearTimeout(engineeringExpiryTimer);
    engineeringExpiryTimer = setTimeout(() => {
      engineeringUnlocked = false;
      fetch("/api/engineering/logout", { method: "POST" }).catch(() => {});
      if (engineeringScreens.has(currentScreen)) showPasswordScreen();
    }, result.expires_in_seconds * 1000);
    panel.classList.remove("error");
    showScreen("engineering");
  } catch (error) {
    engineeringUnlocked = false;
    panel.classList.add("error");
    message.textContent = error.message || "Login service unavailable";
  }
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
      const fallbackResponse = await fetch("measurements.json", { cache: "no-store",signal:AbortSignal.timeout(8000) });
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
  const scoreLabel=document.getElementById("detailScoreLabel");if(scoreLabel)scoreLabel.textContent=record.classifier_result?.reference_only?"Reference score":"Confidence";
  document.getElementById("detailStatus").textContent = record.status;
  renderFrequencyCards("detail", record);
  renderSavedPhoto("detail", record);
  renderScalePreparationSummary("detailScalePreparation", record);
  renderGeometrySummary("detailGeometrySummary",record.geometry_evidence);
  renderReferenceSummary("detailReferenceSummary",record);
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
  renderSavedPhoto("teachingDetail", record);
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
  const hz = Number(entry.frequency_hz);
  return `${hz > 0 ? (hz / 1000).toFixed(2) + " kHz\n" : ""}${ch1}\n${ch2}`;
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
  const hz = Number(step?.frequency_hz);
  const label = Number.isFinite(hz) && hz > 0 ? `${(hz / 1000).toFixed(2)} kHz\n` : "";
  return `${label}${ch1Text}\n${ch2Text}`;
}

function renderFrequencyCards(prefix, record) {
  const sequence = record?.frequency_sequence || [];
  for (let slot = 1; slot <= 4; slot += 1) {
    const node = document.getElementById(`${prefix}F${slot}`);
    node.textContent = formatRecordFrequencyStep(sequence, `f${slot}`);
    if (slot === 4 && node.textContent === "--") node.textContent = "Not recorded in this capture";
  }
}

function renderClassifierStatus(payload) {
  const reference=payload?.selected_algorithm==="gold_reference_v1";
  document.getElementById("classifierTrainButton").textContent=reference?"Check reference model":"Compute Model";
  const classCounts = payload?.class_counts || {};
  const classReadiness = payload?.class_readiness || [];
  const warnings = payload?.warnings || [];
  document.getElementById("classifierTotalRecords").textContent = payload?.teaching_record_count ?? 0;
  document.getElementById("classifierEligibleRecords").textContent = payload?.eligible_record_count ?? 0;
  document.getElementById("classifierClassCount").textContent = payload?.class_count ?? 0;
  document.getElementById("classifierModelStatus").textContent = reference ? (payload?.reference_ready?"Reference ready":"Needs setup") : payload?.model_exists ? "Ready" : "Not trained";
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

  if(reference)classList.textContent="External 916 / 999 reference pipeline; HMI teaching records do not retrain it.";
  const warningList = document.getElementById("classifierWarnings");
  const excluded = (payload?.excluded_preview || []).map((item) => `${item.label || item.id || "Record"}: ${item.reason}`);
  const messages = warnings.length ? warnings : excluded;
  if(reference)warningList.textContent=messages.join(" ");
  else warningList.innerHTML = messages.length
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
    warningList.textContent = error.message || "Classifier training failed";
  } finally {
    button.disabled = false;
    button.textContent = state.classifierAlgorithm==="gold_reference_v1"?"Check reference model":"Compute Model";
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
    state.classifierAlgorithm=payload.classifier_algorithm;
    await loadClassifierStatus();
    if (warningList) {
      warningList.textContent = payload.classifier_algorithm==="gold_reference_v1"?"Reference mode saved. Run fresh four-frequency air calibration; no training is performed here.":"Classifier method saved. Press Compute Model to rebuild this model.";
    }
  } catch (error) {
    if (warningList) {
      warningList.textContent = error.message || "Classifier method save failed";
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
  document.getElementById("calF4Air").textContent = air.f4 ? formatCalibrationFrequencyAir(air.f4) : "Not recorded in this calibration";
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
  const total = mode === "validate" ? 15 : perFrequencySeconds * state.multiFrequenciesKhz.length;
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
  durationLabel.textContent = mode === "validate" ? "Validation" : `${state.multiFrequenciesKhz.length} frequencies`;
  frequencyLabel.textContent = mode === "validate" ? "Air check" : "F1";
  sampleLabel.textContent = mode === "validate" ? "Sampling air" : `CH1/CH2 0 / ${sampleTarget}`;

  progressBar.style.width = "0%";
  progressText.textContent = "0%";
  ring.style.strokeDashoffset = "314";

  const timer = setInterval(() => {
    elapsed += 1;
    const progress = finished ? 100 : Math.min(99, Math.round((elapsed / total) * 100));
    if (mode !== "validate") {
      const zeroBased = Math.min(state.multiFrequenciesKhz.length - 1, Math.floor(Math.max(0, elapsed - 1) / perFrequencySeconds));
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
        frequency_hz: getCurrentFrequencyValue() * 1000,
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
        frequency_hz: getCurrentFrequencyValue() * 1000,
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
  const display = document.getElementById("teachingPurityDisplay");
  if (display) display.textContent = teachingState.purity || "--";
}

function configureTeachingPurityScreen() {
  const isGold = teachingState.material === "Gold";
  const eyebrow = document.getElementById("teachingPurityEyebrow");
  eyebrow.textContent = isGold ? "Gold purity — select carat / 9xx or enter below" : "Silver purity — select 9xx or enter below";
  document.querySelectorAll("#teachingPurityGrid button").forEach((button) => {
    const purity = button.dataset.purity || "";
    button.hidden = isGold ? purity.includes("/") : !/^\d{3}$/.test(purity);
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
  return teachingState.material;
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
  const planSlots = teachingState.mode === "validate" && state.classifierAlgorithm !== "gold_reference_v1" ? [1, 3] : state.multiFrequenciesKhz.map((_, index) => index + 1);
  const total = perFrequencySeconds * planSlots.length;
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
    const zeroBased = Math.min(planSlots.length - 1, Math.floor(Math.max(0, elapsed - 1) / perFrequencySeconds));
    const slot = planSlots[zeroBased];
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
    purity: teachingState.purity || "Not applicable",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
    geometry_reading_id: teachingState.geometryReading?.reading_id || null,
    scale_preparation_id: teachingState.scalePreparationId,
    frequency_hz: currentFrequency * 1000,
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
    purity: teachingState.purity || "Not applicable",
    shape: getTeachingShapeLabel(),
    weight: `${teachingState.weight || "0"} g`,
    ...dimensionPayload,
    vision_measurement: teachingState.visionMeasurement,
    geometry_reading_id: teachingState.geometryReading?.reading_id || null,
    scale_preparation_id: teachingState.scalePreparationId,
    frequency_hz: currentFrequency * 1000,
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
  renderReferenceSummary("teachingSavedReferenceSummary",record);
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
  const scoreLabel=document.getElementById("teachingSavedScoreLabel");if(scoreLabel)scoreLabel.textContent=record.classifier_result?.reference_only?"Reference score":"Confidence";
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

  // ACCESS-01: deletion PIN validation remains on the server.
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

    if (!response.ok) throw new Error(response.status === 403 ? "Invalid PIN" : "Delete failed; check login/service");
    if (isTeachingDelete) {
      await loadTeachingRecords();
    } else {
      await loadHistoryRecords();
    }
  } catch (error) {
    // A refused/failed deletion must never look successful in the local table.
    panel.classList.add("error");
    message.textContent = error.message;
    deletePassword = "";
    updateDeletePasswordDisplay();
    return;
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
  const commands = state.classifierAlgorithm === "binary_brass_ch1_f1" ? [1]
    : state.classifierAlgorithm === "binary_brass_ch2_f1_f3" ? [1, 3]
    : state.multiFrequenciesKhz.map((_, index) => index + 1);
  // This timer is an estimate; actual completion still comes from the server response.
  const stages = commands.map((slot, index) => ({
    limit: 10 + ((index + 1) / commands.length) * 74,
    title: `Acquiring F${slot} (estimated)`,
    note: `Planned ${state.multiFrequenciesKhz[slot - 1]} kHz. Keep the item still.`
  }));
  stages.push({ limit: 100, title: "Processing", note: "Waiting for the acquisition and classifier result." });

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
  const navigation=screenNavigation;
  let record = null;
  const currentFrequency = getCurrentFrequencyValue();
  const dimensionPayload = buildMeasurementDimensionPayload();
  try {
    const response = await fetch("/api/measurement/verify", {
      signal:AbortSignal.timeout(240000),
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weight: state.weight || "0",
        shape: getMeasurementShapeLabel(),
        ...dimensionPayload,
        vision_measurement: state.visionMeasurement,
        geometry_reading_id: state.geometryReading?.reading_id || null,
        scale_preparation_id: state.scalePreparationId,
        placement_capture_id: placementCaptureId,
        frequency_hz: currentFrequency * 1000,
        frequency_slot: state.activeFrequencySlot
      })
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.message || "Unable to verify material");
      error.record = payload.id ? payload : null;
      throw error;
    }
    record = payload;
  } catch (error) {
    record = error.record || {
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

  if (navigation!==screenNavigation || currentScreen!=="measure") return;
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

  cameraSavedPhoto = localPhoto(record);
  renderSavedPhoto("result", record);
  renderScalePreparationSummary("resultScalePreparation", record);
  renderGeometrySummary("resultGeometrySummary",record.geometry_evidence);
  renderReferenceSummary("resultReferenceSummary",record);
  lastResultRecord = record;
  statusNode.textContent = needsVerification ? "Review required · open Details" : "Recorded · open Details";
  await showScreen("result");
  // A history fetch must never delay or freeze the removal screen.
  loadHistoryRecords();
  if (needsVerification && currentScreen === "result") showResultDetails();
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
    state.classifierAlgorithm = settings.classifier_algorithm;
    const threshold = Number(settings.confidence_threshold_pct);
    state.confidenceThresholdPct = Number.isFinite(threshold) ? threshold : 40;
    state.detectorConfidenceInput = String(Math.round(state.confidenceThresholdPct));
    const loadedFrequencies = Array.isArray(settings.multi_frequencies_khz) ? settings.multi_frequencies_khz : [8, 10, 15, 20];
    state.multiFrequenciesKhz = loadedFrequencies.slice(0, 4).map((value, index) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : [8, 10, 15, 20][index];
    });
    const slot = Number.parseInt(settings.active_frequency_slot, 10);
    state.activeFrequencySlot = slot >= 1 && slot <= state.multiFrequenciesKhz.length ? slot : 1;
  } catch (error) {
    state.acquisitionMode = "simulator";
    state.confidenceThresholdPct = 40;
    state.detectorConfidenceInput = "40";
    state.multiFrequenciesKhz = [8, 10, 15, 20];
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
    if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(error.error || "Unable to save frequency settings"); }
    const settings = await response.json();
    state.multiFrequenciesKhz = (settings.multi_frequencies_khz || [8, 10, 15, 20]).slice(0, 4);
    const slot = Number.parseInt(settings.active_frequency_slot, 10);
    state.activeFrequencySlot = slot >= 1 && slot <= state.multiFrequenciesKhz.length ? slot : state.activeFrequencySlot;
  } catch (error) {
    document.getElementById("frequencyModeStatus").textContent = error.message || "Frequency settings were not saved";
    return;
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
    port.textContent = payload?.port || "Weight service configured port";
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
  port.textContent = payload.port || "Weight service configured port";
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
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store", signal:AbortSignal.timeout(45000) });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Unable to average load cell");
    renderLoadCellReading({ ...payload, raw_response: `Average of ${payload.sample_count || 10} samples` });
    document.getElementById("loadCellRaw").textContent = `Average: ${payload.weight_g ?? "--"} g | Std: ${payload.std_g ?? "--"} g`;
  } catch (error) {
    renderLoadCellReading({ ok: false, error: error.message || "Unable to average load cell" });
  }
}

// REV 2026-10-18 / ZERO-02: no placement until the server verifies actual zero.
function scaleNode(id) { return document.getElementById(id); }
function scalePreparationBack() {
  return scalePreparationContext === "engineering" ? "loadCell" : scalePreparationContext === "teaching" ? "teaching" : "home";
}
function scaleNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(5) : "--";
}
function renderScalePreparationSummary(id, record) {
  const node = scaleNode(id), result = record.scale_preparation;
  node.hidden = !result;
  node.textContent = result ? `Empty-pan zero: ${scaleNumber(result.residual?.average)} g; spread ${scaleNumber(result.residual?.range)} g; ${result.residual?.samples_valid || 0} stable samples. Internal: ${result.internal?.status || "unknown"}.` : "";
}
function renderScalePreparation(job) {
  const running = job.state === "running";
  scalePreparationBusy = running;
  scaleNode("scalePreparationSpinner").hidden = !running;
  scaleNode("scalePreparationStatus").setAttribute("aria-busy",String(running));
  scalePreparationResult = job.state === "ready" && job.result?.zero_verified === true ? job : null;
  scaleNode("scalePreparationStatus").textContent = job.message || "Remove all items before starting.";
  scaleNode("scalePreparationStart").disabled = running;
  scaleNode("scalePreparationSkip").disabled=running;
  scaleNode("scalePreparationCancel").disabled = running;
  scaleNode("scalePreparationContinue").disabled = !scalePreparationResult;
  scaleNode("scalePreparationConfirm").disabled = running;
  scaleNode("scaleRepeatInternal").disabled = running;
  scaleNode("scalePreparationSave").disabled = running;
  const result = job.result;
  const internal = result?.internal || job.startup_internal;
  const labels = { completed: "Completed this preparation", already_completed_this_startup: "Completed earlier this startup; reused", unsupported: "Not supported by this balance", skipped: "Skipped in Engineering settings" };
  scaleNode("scalePreparationInternal").textContent = internal ? `Internal: ${labels[internal.status] || internal.status}${internal.command ? " (" + internal.command + ")" : ""}${internal.deviation_raw ? "; deviation " + internal.deviation_raw + " [" + internal.deviation_unit + "]" : ""}${internal.completed_at ? "; " + internal.completed_at : ""}` : "Internal check: due once this Weight-service startup.";
  scaleNode("scalePreparationReadings").textContent = result ? `Before zero: ${scaleNumber(result.initial.average)} g. After zero: ${scaleNumber(result.residual.average)} g; standard deviation ${scaleNumber(result.residual.std_g)} g; spread ${scaleNumber(result.residual.range)} g; ${result.residual.samples_valid} stable samples.` : "";
}
async function pollScalePreparation() {
  clearTimeout(scalePreparationTimer);
  if (currentScreen !== "scalePrepare") return;
  try {
    const response = await fetch("/api/load-cell/preparation/status", { cache: "no-store" });
    const job = await response.json();
    if (!response.ok) throw new Error(job.message || "Weight service unavailable");
    if (currentScreen !== "scalePrepare") return;
    // A failed POST must never adopt the previous item's READY result.
    const currentJob = job.id && (job.id === scalePreparationJobId || (scalePreparationPreviousId && job.id !== scalePreparationPreviousId));
    if (job.state === "ready" && !currentJob) {
      renderScalePreparation({ state: "idle", startup_internal: job.startup_internal, message: "This is a previous preparation. Confirm the empty pan and press Prepare." });
      return;
    }
    renderScalePreparation(job);
    if (job.state === "running") scalePreparationTimer = setTimeout(pollScalePreparation, 500);
  } catch (error) {
    // A lost HTTP response does not prove that an internal operation has stopped.
    scaleNode("scalePreparationStatus").textContent = `${error.message}. Keep the pan empty; retrying status.`;
    scalePreparationTimer = setTimeout(pollScalePreparation, 1500);
  }
}
async function openScalePreparation(context) {
  if (scalePreparationBusy) return;
  scalePreparationContext = context;
  scalePreparationResult = null;
  scalePreparationPreviousId = null;
  scalePreparationJobId = null;
  scaleNode("scalePreparationConfirm").checked = false;
  scaleNode("scaleRepeatInternal").checked = false;
  const engineer = context !== "measurement" && engineeringUnlocked;
  scaleNode("scalePreparationEngineering").hidden = !engineer;
  scaleNode("scalePreparationSkip").hidden=context==="engineering";
  scaleNode("scalePreparationContinue").textContent = context === "engineering" ? "Back to scale" : "Place item";
  renderScalePreparation({ state: "idle" });
  await showScreen("scalePrepare");
  if (engineer) {
    try {
      const response = await fetch("/api/settings", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load scale settings");
      const settings = (await response.json()).scale_preparation || {};
      for (const [key, fallback] of Object.entries({ empty_limit_g: 0.1, zero_tolerance_g: 0.01, max_spread_g: 0.02, internal_mode: "auto" })) {
        scaleNode("scaleSetting_" + key).value = settings[key] ?? fallback;
      }
    } catch (error) { scaleNode("scalePreparationSettingsStatus").textContent = error.message; }
  }
  // Resume an operation after a page reload; do not start a second adjustment.
  // A previously READY result belongs to the prior item, so only adopt RUNNING.
  try {
    const response = await fetch("/api/load-cell/preparation/status", { cache: "no-store" });
    const job = await response.json();
    if (response.ok) scalePreparationPreviousId = job.id || "idle";
    if (response.ok && job.state === "running") {
      scalePreparationJobId = job.id;
      renderScalePreparation(job);
      scalePreparationTimer = setTimeout(pollScalePreparation, 500);
    } else if (response.ok) {
      renderScalePreparation({ state: "idle", startup_internal: job.startup_internal });
    }
  } catch (error) { scaleNode("scalePreparationStatus").textContent = "Weight service unavailable. Empty the pan, then try Prepare."; }
}
async function startScalePreparation() {
  if (scalePreparationBusy) return;
  if (!scaleNode("scalePreparationConfirm").checked) {
    scaleNode("scalePreparationStatus").textContent = "Remove every item, then tick the empty-pan confirmation.";
    return;
  }
  clearTimeout(scalePreparationTimer);
  renderScalePreparation({ state: "running", message: "Keep the pan empty. Starting preparation..." });
  const repeat = scalePreparationContext !== "measurement" && engineeringUnlocked && scaleNode("scaleRepeatInternal").checked;
  try {
    const response = await fetch(repeat ? "/api/calibration/scale/prepare" : "/api/load-cell/preparation/start", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pan_empty_confirmed: true, repeat_internal: repeat })
    });
    const job = await response.json();
    if (!response.ok) throw new Error(job.message || job.error || "Preparation could not start");
    scalePreparationJobId = job.id;
    renderScalePreparation(job.state === "ready" ? { ...job, state: "running", message: "Confirming preparation status..." } : job);
  } catch (error) {
    scaleNode("scalePreparationStatus").textContent = `${error.message}. Checking balance status; keep the pan empty.`;
  }
  // Always ask the server after POST, including a lost response or a busy reply.
  scalePreparationTimer = setTimeout(pollScalePreparation, 500);
}
async function saveScalePreparationSettings() {
  if (scalePreparationBusy) return;
  const settings = {};
  for (const key of ["empty_limit_g", "zero_tolerance_g", "max_spread_g"]) settings[key] = Number(scaleNode("scaleSetting_" + key).value);
  settings.internal_mode = scaleNode("scaleSetting_internal_mode").value;
  try {
    const response = await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scale_preparation: settings }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || result.error || "Settings not saved; log into Engineering again");
    scaleNode("scalePreparationSettingsStatus").textContent = "Saved. Applies to the next preparation; startup check stays latched unless Repeat is selected.";
  } catch (error) { scaleNode("scalePreparationSettingsStatus").textContent = error.message; }
}
scaleNode("scalePreparationStart").addEventListener("click", startScalePreparation);
scaleNode("scalePreparationSave").addEventListener("click", saveScalePreparationSettings);
scaleNode("scalePreparationCancel").addEventListener("click", () => { if (!scalePreparationBusy) showScreen(scalePreparationBack()); });
scaleNode("scalePreparationContinue").addEventListener("click", () => {
  if (!scalePreparationResult || scalePreparationBusy) return;
  if (scalePreparationContext === "measurement") state.scalePreparationId = scalePreparationResult.id;
  if (scalePreparationContext === "teaching") teachingState.scalePreparationId = scalePreparationResult.id;
  const next = scalePreparationContext === "engineering" ? "loadCell" : scalePreparationContext === "teaching" ? "teachingPlace" : "place";
  scalePreparationResult = null;
  showScreen(next);
});

async function zeroLoadCell() {
  await openScalePreparation("engineering");
}

async function prepareTeachingScale() {
  showScreen("teachingWeight");
  await sampleTeachingWeight();
}

async function prepareTeachingDimensionsFromVision() {
  await refreshYoloStatus();
  if (visionYoloConfig?.enabled && ["Coin","Bar"].includes(getTeachingShapeLabel())) {
    await showScreen("teachingDimension");
    if(currentScreen==="teachingDimension")await measureGeometry("teaching");
    return;
  }
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
  resetMeasurementInputs();
  const navigation=screenNavigation;
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response=await fetch("/api/load-cell/preparation/reuse",{cache:"no-store",signal:controller.signal});
    const result=await response.json();
    if (navigation!==screenNavigation) return;
    if(response.ok && result.state === "running") {await openScalePreparation("measurement");return;}
    if(response.ok && result.reusable) {state.scalePreparationId=result.id;await showScreen("place");return;}
  }catch(error){if(navigation!==screenNavigation)return;}
  finally {clearTimeout(timeout);}
  // No automatic TST3/C3/Z in the customer loop. Engineering prepares once.
  // Unverified zero remains explicit in the record and disables density evidence.
  if (navigation===screenNavigation) await showScreen("place");
}
document.getElementById("scalePreparationSkip").addEventListener("click", () => {
  if(scalePreparationBusy)return;
  clearTimeout(scalePreparationTimer);
  if(scalePreparationContext==="teaching")teachingState.scalePreparationId=null;
  else state.scalePreparationId=null;
  scalePreparationResult=null;
  showScreen(scalePreparationContext==="teaching"?"teachingPlace":"place");
});

async function prepareMeasurementScale() {
  showScreen("weight");
  await sampleMeasurementWeight();
}

async function prepareMeasurementDimensionsFromVision() {
  await refreshYoloStatus();
  if (visionYoloConfig?.enabled && ["Coin","Bar"].includes(getMeasurementShapeLabel())) {
    await showScreen("dimension");
    if(currentScreen==="dimension")await measureGeometry("measurement");
    return;
  }
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
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store", signal:AbortSignal.timeout(45000) });
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
    raw.textContent = "Try Sample Again";
    showNotice(error.message || "Check the balance connection.", "Scale reading failed");
    setWeightProgress(config, 0, 10, "Reading failed", "error");
    setWeightControls("measurement", { sampling: false, ready: false, sampleAvailable: true });
  } finally {
    stopWeightProgressTimer();
  }
}

async function zeroTeachingScaleBeforePlacement(mode) {
  teachingState.mode = mode;
  resetTeachingInputs();
  document.getElementById("teachingStage").textContent = "F1 Measuring";
  document.querySelector("#teachingRecordScreen .measure-copy p").textContent = "Switching to F1 and preparing live signal acquisition.";
  document.getElementById("teachingRecordButton").textContent = "Next";
  await openScalePreparation("teaching");
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
    const response = await fetch("/api/load-cell/average?samples=10", { cache: "no-store", signal:AbortSignal.timeout(45000) });
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
    raw.textContent = "Try Sample Again";
    showNotice(error.message || "Check the balance connection.", "Scale reading failed");
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
// NUC-03: automatic selection goes directly to mass. Manual is a fallback.
async function beginManualMeasurement() {
  if (placementBusy) return;
  const screen=currentScreen, cycle=placementCycle;
  placementBusy=true; manualShapeMode=true;
  try {
    if (await capturePlacementPhoto() && currentScreen===screen && placementCycle===cycle) await prepareMeasurementScale();
  } finally {placementBusy=false;}
}
async function capturePlacementPhoto() {
  if (placementCaptureId) return true;
  const cycle = placementCycle;
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch("/api/verification/image/capture", {
      method:"POST", headers:{"Content-Type":"application/json"}, signal:controller.signal,
      body:JSON.stringify({shape:getMeasurementShapeLabel(), phase:"placement_auto", manual_selection:manualShapeMode})
    });
    const payload = await response.json();
    if (cycle !== placementCycle) return false;
    if (!response.ok) throw new Error(payload.message || "Photograph could not be saved");
    placementCaptureId = payload.placement_capture_id;
    cameraSavedPhoto = {...payload.image, scope:"verification"};
    return true;
  } catch (error) {
    if (cycle === placementCycle) showNotice(error.message || "Camera timed out. Retry detection.", "Camera");
    return false;
  } finally {clearTimeout(timer);}
}
document.getElementById("placeContinueButton").addEventListener("click", async () => {
  if (placementBusy || !yoloCanContinue() || !visionYoloConfig?.enabled) return;
  manualShapeMode = false;
  state.shape = visionLastDetection.label === "coin" ? "Coin" : "Bar";
  updateShapeSelection(); placementBusy = true; updateYoloGate();
  stopTeachingCameraPreview();
  const cycle = placementCycle;
  try {
    if (await capturePlacementPhoto() && cycle === placementCycle && currentScreen === "place") await prepareMeasurementScale();
  } finally {
    placementBusy = false; updateYoloGate();
    if (currentScreen === "place") updateCameraPreviewForScreen();
  }
});
document.getElementById("manualShapeButton").addEventListener("click", () => {
  if (!placementBusy) {manualShapeMode = true;showScreen("shape");}
});
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
document.getElementById("measureButton").addEventListener("click", async () => {
  if (state.shape === "Other") {
    updateOtherShapeSelection();
    showScreen("otherShape");
    return;
  }
  await beginManualMeasurement();
});
document.getElementById("otherShapeBackButton").addEventListener("click", () => showScreen("shape"));
document.getElementById("otherShapeNextButton").addEventListener("click", async () => {
  await beginManualMeasurement();
});
document.getElementById("newMeasurementButton").addEventListener("click", () => {
  resetMeasurementInputs(); showScreen("home");
});
document.getElementById("resultAnotherButton").addEventListener("click", () => confirmItemRemoved(zeroMeasurementScaleBeforePlacement));
document.getElementById("engineeringReadinessButton").addEventListener("click", () => showScreen("readiness"));
document.getElementById("readinessRefreshButton").addEventListener("click", loadReadiness);
document.getElementById("readinessBackButton").addEventListener("click", () => showScreen("engineering"));
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
// NUC-03: request only this launcher's kiosk browser to close, never all Chrome.
const launchToken = new URLSearchParams(location.hash.slice(1)).get("kiosk");
if (launchToken) {sessionStorage.setItem("afisKioskToken",launchToken);history.replaceState(null,"",location.pathname+location.search);}
document.getElementById("menuExitButton").addEventListener("click", async () => {
  if (!window.confirm("Close the kiosk? Backend services will keep running.")) return;
  if (scalePreparationBusy) {showNotice("Wait for balance preparation to finish before closing.");return;}
  try {
    const response = await fetch("/api/kiosk/exit", {method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({token:sessionStorage.getItem("afisKioskToken") || ""}),signal:AbortSignal.timeout(5000)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Kiosk launcher is unavailable");
  } catch(error) {
    window.close();
    showNotice("This browser was not opened by the local kiosk launcher. Close it with Alt+F4, then use start_all.bat or launch_chrome.bat. " + error.message,"Exit");
  }
});
document.getElementById("modeToggleButton").addEventListener("click", toggleAcquisitionMode);
document.getElementById("engineeringVisionButton").addEventListener("click", openVisionSettings);
document.getElementById("visionBackButton").addEventListener("click", () => showScreen("engineering"));
document.querySelectorAll(".geometry-measure").forEach(button=>button.addEventListener("click",()=>measureGeometry(button.dataset.kind,button.dataset.manual==="1")));
document.getElementById("geometryReferenceButton").addEventListener("click",()=>geometryEngineeringAction("reference"));
document.getElementById("geometryGuideButton").addEventListener("click",()=>showApiReference("geometry"));
document.getElementById("geometryStatusButton").addEventListener("click",()=>geometryEngineeringAction("status"));
document.getElementById("geometrySettingsSaveButton").addEventListener("click",()=>geometryEngineeringAction("settings"));
document.getElementById("referenceModelPath").addEventListener("change",()=>{
  document.getElementById("referenceProfileConfirmed").checked=false;
  document.getElementById("referenceModelStatus").textContent="Model changed. Confirm its training acquisition profile, then validate/select it.";
});
document.getElementById("referenceTestButton").addEventListener("click",()=>submitReferenceModel(true));
document.getElementById("referenceSaveButton").addEventListener("click",()=>submitReferenceModel(false));
document.getElementById("referenceUseButton").addEventListener("click",useReferenceMode);
document.getElementById("assetsScanButton").addEventListener("click", scanSystemAssets);
document.getElementById("assetsModelsSaveButton").addEventListener("click", ()=>saveAssetConfiguration("models"));
document.getElementById("assetsApiSaveButton").addEventListener("click", ()=>saveAssetConfiguration("api"));
document.getElementById("assetsReferenceButton").addEventListener("click", showApiReference);
document.getElementById("visionSaveButton").addEventListener("click", () => submitVisionSettings(false));
document.getElementById("visionTestButton").addEventListener("click", () => submitVisionSettings(true));
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
document.getElementById("frequencySlot4Button").addEventListener("click", () => selectFrequencySlot(4));
document.getElementById("fourFrequencyPresetButton").addEventListener("click", () => {
  state.multiFrequenciesKhz = [8, 10, 15, 20];
  state.activeFrequencySlot = 1;
  updateFrequencyModeSelection();
  document.getElementById("frequencyModeStatus").textContent = "8 / 10 / 15 / 20 kHz selected. Press Save, then recalibrate.";
});
document.getElementById("frequencyModeBackButton").addEventListener("click", () => showScreen("engineering"));
document.getElementById("frequencyModeSaveButton").addEventListener("click", saveFrequencySettings);
document.getElementById("editFrequencyButton").addEventListener("click", () => showScreen("frequencyEdit"));
document.getElementById("frequencyEditBackButton").addEventListener("click", () => showScreen("frequencyMode"));
document.getElementById("frequencyEditSetButton").addEventListener("click", () => showScreen("frequencyMode"));
document.getElementById("historyBackButton").addEventListener("click", () => showScreen(historyReturnScreen));
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
  const needsPurity = teachingState.material === "Gold" || teachingState.material === "Silver";
  if (needsPurity) {
    configureTeachingPurityScreen();
    showScreen("teachingPurity");
  } else {
    prepareTeachingScale();
  }
});
document.getElementById("teachingOtherMaterialBackButton").addEventListener("click", () => showScreen("teachingMaterial"));
document.getElementById("teachingOtherMaterialNextButton").addEventListener("click", () => showScreen("teachingPurity"));
document.getElementById("teachingPurityBackButton").addEventListener("click", () => showScreen("teachingMaterial"));
document.getElementById("teachingPurityNextButton").addEventListener("click", () => {
  if (!teachingState.purity) return;
  prepareTeachingScale();
});
document.getElementById("teachingShapeBackButton").addEventListener("click", () => {
  const needsPurity = teachingState.material === "Gold" || teachingState.material === "Silver";
  showScreen(needsPurity ? "teachingPurity" : "teachingMaterial");
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
document.getElementById("cameraBackToLiveButton").addEventListener("click", () => {
  teachingCameraMode="live";loadTeachingDetectedImage();
});
document.getElementById("cameraBackToFlowButton").addEventListener("click", () => {
  teachingCameraMode="live";
  if(currentScreen==="teachingDimension")selectTeachingDimensionPanel("dimensions");
  else {
    loadTeachingDetectedImage();
    const button=document.getElementById(currentScreen==="place"?"placeContinueButton":currentScreen==="dimension"?"dimensionNextButton":"newMeasurementButton");
    button?.scrollIntoView?.({block:"nearest"});
  }
});
document.getElementById("teachingRefreshImageButton").addEventListener("click", () => {
  teachingCameraMode = "live";
  loadTeachingDetectedImage();
});
document.getElementById("teachingCapturedImageButton").addEventListener("click", () => {
  teachingCameraMode = cameraSavedPhoto ? "saved" : "captured";
  loadTeachingDetectedImage();
});
document.getElementById("cameraAnnotationButton").addEventListener("click", () => {
  cameraAnnotationsEnabled = !cameraAnnotationsEnabled;
  loadTeachingDetectedImage();
});
document.getElementById("cameraDebugButton").addEventListener("click", () => {
  if (!cameraDebugAllowed()) return;
  cameraDebugEnabled = !cameraDebugEnabled;
  loadTeachingDetectedImage();
});
document.getElementById("cameraSavePhotoButton").addEventListener("click", saveCameraPhoto);
document.getElementById("cameraShapeSelect").addEventListener("change", loadTeachingDetectedImage);
document.getElementById("teachingRemoveBackButton").addEventListener("click", () => showScreen("teaching"));
document.getElementById("teachingRemoveNextButton").addEventListener("click", () => confirmItemRemoved(() => showScreen("teachingSaved")));
document.getElementById("teachingSavedAgainButton").addEventListener("click", () => {
  zeroTeachingScaleBeforePlacement(teachingState.mode || "teach");
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
    placementCaptureId = null;
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
    placementCaptureId = null;
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
  if (key === "clear") teachingState.purity = "";
  else if (teachingState.purity.length < 4) teachingState.purity += key;
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
  const index = Math.max(0, Math.min(3, Number(state.activeFrequencySlot || 1) - 1));
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

// REV 2026-10-18 / RATES-LIST-01: stable, scrollable rows replace rotating prices.
const metalRateRows = [
  ["Gold 999", "XAU", 0.999], ["Gold 916", "XAU", 0.916],
  ["Gold 750", "XAU", 0.750], ["Silver 999", "XAG", 0.999],
  ["Silver 925", "XAG", 0.925], ["Platinum", "XPT", 1], ["Palladium", "XPD", 1]
];
let referenceRates = null;
let referenceRatesBusy = false;
let referenceRatesOffline = false;
let referenceRatesTimer = null;
let rateCardIndex = 0;
function moveRateCard(step) {
  rateCardIndex = (rateCardIndex + step + metalRateRows.length) % metalRateRows.length;
  [...document.getElementById("metalRatesList").children].forEach((row,index) => {
    const offset = (index-rateCardIndex+metalRateRows.length)%metalRateRows.length;
    row.classList.toggle("active",offset===0);
    row.classList.toggle("previous",offset===metalRateRows.length-1);
    row.classList.toggle("next",offset===1);
    row.setAttribute("aria-hidden",String(offset!==0));
  });
  document.getElementById("rateCardPosition").textContent = `${rateCardIndex+1} / ${metalRateRows.length}`;
}
document.getElementById("ratesPreviousButton").addEventListener("click",()=>moveRateCard(-1));
document.getElementById("ratesNextButton").addEventListener("click",()=>moveRateCard(1));
document.getElementById("metalRatesList").addEventListener("keydown",event=>{
  if (["ArrowLeft","ArrowRight"].includes(event.key)) {event.preventDefault();moveRateCard(event.key==="ArrowLeft"?-1:1);}
});

function rateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown quote time" : date.toLocaleString("en-MY", {
    timeZone:"Asia/Kuala_Lumpur", day:"2-digit", month:"short", year:"numeric",
    hour:"2-digit", minute:"2-digit", hour12:false
  }) + " MYT";
}

function initializeMetalRateRows() {
  const list = document.getElementById("metalRatesList");
  metalRateRows.forEach(([label], index) => {
    const row = document.createElement("article");
    row.className = "metal-rate-row";
    row.setAttribute("role", "listitem");
    const name = document.createElement("strong");
    name.textContent = label;
    // Reuse the original local bullion artwork and CSS bar-stack fallbacks.
    const graphic = document.createElement("div");
    const stacks=["gold-stack bars-3","gold-stack bars-2","gold-stack bars-1","silver-stack bars-3","silver-stack bars-2","silver-stack bars-1","palladium-stack bars-1"];
    const pictures=["gold-24k-display.png","gold-22k-display.png","gold-18k-display.png","silver-999-display.png","silver-925-display.png",null,"palladium-display.png"];
    graphic.className = "object " + stacks[index]; graphic.setAttribute("aria-hidden","true");
    for(let bar=0;bar<3;bar++)graphic.appendChild(document.createElement("span"));
    if(pictures[index]) {
      const img=document.createElement("img");img.alt="";
      img.onload=()=>graphic.classList.add("has-image");
      img.src="assets/"+pictures[index];graphic.appendChild(img);
    }
    row.appendChild(graphic);
    row.appendChild(name);
    for (const part of ["Price", "Trend", "Time"]) {
      const node = document.createElement(part === "Price" ? "strong" : "span");
      node.id = `metalRate${index}${part}`;
      node.className = `metal-rate-${part.toLowerCase()}`;
      row.appendChild(node);
    }
    list.appendChild(row);
  });
  moveRateCard(0);
  renderReferenceRates();
}

function renderReferenceRates() {
  metalRateRows.forEach(([label, symbol, purity], index) => {
    const quote = referenceRates?.metals?.[symbol];
    const price = document.getElementById(`metalRate${index}Price`);
    const trend = document.getElementById(`metalRate${index}Trend`);
    const time = document.getElementById(`metalRate${index}Time`);
    trend.className = "metal-rate-trend flat";
    if (!Number.isFinite(quote?.myr_per_g) || quote.myr_per_g <= 0) {
      price.textContent = "—";
      trend.textContent = referenceRates?.pending && !referenceRatesOffline ? "Loading" : "Unavailable";
      time.textContent = "No quote available";
      return;
    }
    price.textContent = `RM ${(quote.myr_per_g * purity).toFixed(2)}/g`;
    const stale = referenceRatesOffline || quote.stale;
    const change = quote.change_pct;
    if (stale) trend.textContent = "STALE / last known";
    else if (!Number.isFinite(change)) trend.textContent = "Trend pending";
    else {
      trend.textContent = `${change > 0 ? "▲" : change < 0 ? "▼" : "—"} ${Math.abs(change).toFixed(2)}%`;
      trend.classList.add(change > 0 ? "up" : change < 0 ? "down" : "flat");
    }
    time.textContent = `${stale ? "Last quote" : "Quote"}: ${rateTime(quote.updated_at)} · FX ${quote.fx_date}`;
    trend.title = quote.baseline_at ? `Compared with ${rateTime(quote.baseline_at)}` : "A second successful quote is needed";
  });
  const status = document.getElementById("metalRatesStatus");
  const button = document.getElementById("refreshRatesButton");
  const cooldown = Number(referenceRates?.manual_retry_after) || 0;
  button.disabled = referenceRatesBusy || (!referenceRatesOffline && (referenceRates?.pending || cooldown > 0));
  button.textContent = referenceRates?.pending && !referenceRatesOffline ? "Refreshing…"
    : cooldown > 0 && !referenceRatesOffline ? `Wait ${cooldown}s` : referenceRatesOffline ? "Retry refresh" : "Refresh";
  status.textContent = referenceRatesOffline ? "Price service unavailable. Saved quotes are marked stale."
    : referenceRates?.pending ? "Refreshing prices..."
    : Object.keys(referenceRates?.errors || {}).length ? "Some prices could not be updated; check stale/unavailable rows."
    : "Reference prices · Use previous / next for every metal";
}

function stopReferenceRatesPolling() {
  clearTimeout(referenceRatesTimer);
  referenceRatesTimer = null;
}

async function refreshReferenceRates(manual = false) {
  if (referenceRatesBusy || document.hidden || !screens.home.classList.contains("active")) return;
  stopReferenceRatesPolling();
  referenceRatesBusy = true;
  renderReferenceRates();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(manual ? "/api/metal-rates/refresh" : "/api/metal-rates", {
      method:manual ? "POST" : "GET", cache:"no-store", signal:controller.signal
    });
    if (!response.ok) throw new Error("Rates unavailable");
    const data = await response.json();
    if (data.currency !== "MYR" || data.unit !== "g" || !data.metals || Array.isArray(data.metals)) throw new Error("Invalid rates response");
    referenceRates = data;
    referenceRatesOffline = false;
  } catch (error) {
    referenceRatesOffline = true;
  } finally {
    clearTimeout(timeout);
    referenceRatesBusy = false;
    renderReferenceRates();
    if (!document.hidden && screens.home.classList.contains("active")) {
      const waiting = referenceRates?.pending || referenceRates?.manual_retry_after > 0;
      referenceRatesTimer = setTimeout(() => refreshReferenceRates(), !referenceRatesOffline && waiting ? 5000 : 60000);
    }
  }
}

document.getElementById("refreshRatesButton").addEventListener("click", () => refreshReferenceRates(true));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopReferenceRatesPolling();
  else refreshReferenceRates();
});

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
loadHistoryRecords();
// ACCESS-01: private records/calibration are loaded after login.
updateDetectorConfidenceDisplay();
loadAcquisitionMode();

initializeMetalRateRows();
refreshReferenceRates();
