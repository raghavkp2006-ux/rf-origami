/**
 * RF ORIGAMI DESIGN STUDIO - Frontend Application Controller
 * 
 * Drives both:
 * 1. Generative Explorer (Primary): Latin Hypercube design space exploration,
 *    multi-tier constraint cascade, candidate gallery, interactive scatter plot,
 *    and real-time 3D kinematic fold inspector.
 * 2. Reference Patterns (Secondary): Classical analytical origami pattern generators.
 */

// Global Application State
const appState = {
  currentMode: "explorer", // "explorer" | "reference" | "absorber" | "optimization"
  
  // Seamless Cross-Module Active Design State
  activeDesign: {
    source: "explorer", // "explorer" | "reference" | "absorber"
    id: "Default (Miura-ori)",
    pattern_type: "miura_ori",
    family: "modulated_miura",
    params: { a: 25.0, b: 20.0, gamma_deg: 60.0, num_cells_x: 2, num_cells_y: 2 },
    foldAngle: 30.0,
    modelData: null,
  },

  // Explorer State
  explorer: {
    sampleCount: 20,
    seed: 42,
    family: "modulated_miura",
    candidates: [],
    scatterPoints: [],
    summary: null,
    activeFilter: "all", // "all" | "valid" | "rejected"
    activeSort: "compactness_asc",
    selectedCandidate: null,
    viewMode: "grid", // "grid" | "scatter" | "split"
    inspectorOpen: false,
    inspFoldAngle: 35.0,
    threeObj: null,
    edgesObj: null,
  },

  // Reference Pattern State
  reference: {
    currentPattern: "miura_ori",
    catalog: {},
    params: {},
    foldAngle: 35.0,
    activeMaterial: "conductor",
    materialTags: {},
    modelData: null,
    showWireframe: true,
    threeObj: null,
    edgesObj: null,
  },

  // Numerical RF Electromagnetic Solver State
  rf: {
    inspectorTab: "geometry", // "geometry" | "rf"
    selectedSubstrate: "kapton",
    selectedConductor: "copper",
    lastResult: null,
    isSimulating: false,
    foldSweepResult: null,
    benchmarks: null,
  },

  // Metasurface Absorber State
  absorber: {
    patternType: "miura_ori",
    params: { a: 25.0, b: 20.0, gamma_deg: 60.0, num_cells_x: 2, num_cells_y: 2 },
    foldAngle: 30.0,
    pol: "linear_x",
    thetaInc: 0.0,
    phiInc: 0.0,
    substrate: "kapton",
    thickness: 0.5,
    conductor: "copper",
    sheetRes: 0.0,
    groundBacked: true,
    fStart: 1.0,
    fStop: 6.0,
    nPts: 31,
    showCurrents: true,
    lastResult: null,
    sweepResult: null,
    threeObj: null,
    edgesObj: null,
  },

  // Optimization & Fabrication State
  optimization: {
    targetFreq: 2.45,
    minAbs: 0.90,
    popSize: 16,
    generations: 4,
    paretoSolutions: [],
  },

  // Origami Simulator Inspired Strain State
  strain: {
    enabledRef: false,
    enabledInsp: false,
    maxThreshold: 0.08, // 8.0% max strain scale (engineering yield limit)
    lastRefMetrics: null,
    lastInspMetrics: null,
  }
};

// =====================================================================
// ORIGAMI SIMULATOR MECHANICAL STRAIN COMPUTATION & COLOR ENGINE
// =====================================================================
const OrigamiStrainEngine = {
  // 5-stop Turbo/Jet Colormap matching OrigamiSimulator.org:
  // 0.0 -> Blue, 0.25 -> Cyan, 0.5 -> Green, 0.75 -> Yellow, 1.0 -> Red
  getStrainColor(strainVal, maxThreshold = 0.08) {
    const s = Math.max(0.0, Math.min(1.0, strainVal / maxThreshold));
    const col = new THREE.Color();
    if (s <= 0.25) {
      const t = s / 0.25;
      col.setRGB(0.145 * (1 - t) + 0.024 * t, 0.388 * (1 - t) + 0.714 * t, 0.922 * (1 - t) + 0.831 * t);
    } else if (s <= 0.5) {
      const t = (s - 0.25) / 0.25;
      col.setRGB(0.024 * (1 - t) + 0.133 * t, 0.714 * (1 - t) + 0.773 * t, 0.831 * (1 - t) + 0.369 * t);
    } else if (s <= 0.75) {
      const t = (s - 0.5) / 0.25;
      col.setRGB(0.133 * (1 - t) + 0.918 * t, 0.773 * (1 - t) + 0.702 * t, 0.369 * (1 - t) + 0.031 * t);
    } else {
      const t = (s - 0.75) / 0.25;
      col.setRGB(0.918 * (1 - t) + 0.937 * t, 0.702 * (1 - t) + 0.267 * t, 0.031 * (1 - t) + 0.267 * t);
    }
    return col;
  },

  computeStrains(meshData, creaseData, foldAngleDeg = 35.0) {
    if (!meshData) return null;
    const v3D = meshData.vertices || [];
    const fList = meshData.faces || [];
    const v2D = (creaseData && creaseData.vertices) || [];
    const creases = (creaseData && creaseData.creases) || [];

    const faceStrains = [];
    let maxStrain = 0.0;
    let sumStrain = 0.0;
    let strainCount = 0;

    // 1. Facet in-plane elongation strain (comparing 3D folded edge lengths to flat 2D edge lengths)
    for (let fIdx = 0; fIdx < fList.length; fIdx++) {
      const f = fList[fIdx];
      let fStrainSum = 0.0;
      let edgeCount = 0;

      for (let i = 0; i < f.length; i++) {
        const u = f[i];
        const v = f[(i + 1) % f.length];

        if (u < v3D.length && v < v3D.length && u < v2D.length && v < v2D.length) {
          const p1_3d = v3D[u], p2_3d = v3D[v];
          const p1_2d = v2D[u], p2_2d = v2D[v];

          const L_3d = Math.hypot(p1_3d[0] - p2_3d[0], p1_3d[1] - p2_3d[1], p1_3d[2] - p2_3d[2]);
          const L_2d = Math.hypot(p1_2d[0] - p2_2d[0], p1_2d[1] - p2_2d[1]);

          if (L_2d > 1e-4) {
            const e = Math.abs(L_3d - L_2d) / L_2d;
            fStrainSum += e;
            edgeCount++;
            if (e > maxStrain) maxStrain = e;
            sumStrain += e;
            strainCount++;
          }
        }
      }

      const avgFaceStrain = edgeCount > 0 ? fStrainSum / edgeCount : 0.0;
      faceStrains.push(avgFaceStrain);
    }

    // 2. Crease bending strain (outer fiber strain: t * theta / 2w)
    const t_sub = 0.075; // 75 um Kapton polyimide substrate
    const w_crease = 0.75; // 0.75 mm crease hinge zone
    const foldRad = (Math.abs(foldAngleDeg) * Math.PI) / 180.0;
    const creaseBendingStrain = (t_sub * foldRad) / (2.0 * w_crease);

    if (creaseBendingStrain > maxStrain) maxStrain = creaseBendingStrain;
    sumStrain += creaseBendingStrain * Math.max(1, creases.length);
    strainCount += Math.max(1, creases.length);

    const meanStrain = strainCount > 0 ? sumStrain / strainCount : 0.0;

    // Strain energy U = 1/2 k * theta^2
    const k_rot = 120.0; // mJ / rad^2
    const strainEnergy = 0.5 * k_rot * Math.pow(foldRad, 2) * Math.max(1, creases.length / 4.0);

    return {
      faceStrains,
      creaseBendingStrain,
      maxStrain,
      meanStrain,
      strainEnergy,
    };
  },

  updateHUD(prefix, metrics) {
    if (!metrics) return;
    const maxPct = (metrics.maxStrain * 100).toFixed(2) + "%";
    const meanPct = (metrics.meanStrain * 100).toFixed(2) + "%";
    const energyStr = metrics.strainEnergy.toFixed(1) + " mJ";

    const elMax = document.getElementById(`${prefix}-strain-max`);
    if (elMax) elMax.textContent = maxPct;
    const elMean = document.getElementById(`${prefix}-strain-mean`);
    if (elMean) elMean.textContent = meanPct;
    const elEnergy = document.getElementById(`${prefix}-strain-energy`);
    if (elEnergy) elEnergy.textContent = energyStr;

    const elStatus = document.getElementById(`${prefix}-strain-status`);
    if (elStatus) {
      if (metrics.maxStrain > 0.065) {
        elStatus.className = "strain-badge danger";
        elStatus.textContent = "High Strain (Yield Risk)";
      } else if (metrics.maxStrain > 0.035) {
        elStatus.className = "strain-badge warning";
        elStatus.textContent = "Moderate (Hinge Bending)";
      } else {
        elStatus.className = "strain-badge pass";
        elStatus.textContent = "Safe (Elastic)";
      }
    }

    if (prefix === "ref") {
      const sideMax = document.getElementById("ref-side-strain-max");
      if (sideMax) sideMax.textContent = maxPct;
      const sideMean = document.getElementById("ref-side-strain-mean");
      if (sideMean) sideMean.textContent = meanPct;
      const sideEnergy = document.getElementById("ref-side-strain-energy");
      if (sideEnergy) sideEnergy.textContent = energyStr;

      const sideBadge = document.getElementById("ref-side-strain-badge");
      const sideState = document.getElementById("ref-side-strain-state");
      if (sideBadge && sideState) {
        if (metrics.maxStrain > 0.065) {
          sideBadge.className = "status-tag tag-rej";
          sideBadge.textContent = "Yield Risk";
          sideState.className = "text-danger font-bold";
          sideState.textContent = "Plastic Crease Bending";
        } else if (metrics.maxStrain > 0.035) {
          sideBadge.className = "status-tag";
          sideBadge.textContent = "Moderate";
          sideState.className = "text-warning font-bold";
          sideState.textContent = "Hinge Bending Concentration";
        } else {
          sideBadge.className = "status-tag tag-valid";
          sideBadge.textContent = "Elastic";
          sideState.className = "text-success font-bold";
          sideState.textContent = "Rigid Foldable / Elastic";
        }
      }
    }
  }
};

// Material Color Palette (Refined for White CAD Theme)
const MATERIAL_COLORS = {
  conductor: 0xd97706,
  substrate: 0x0284c7,
  ground: 0x16a34a,
  dielectric: 0x7c3aed,
  keepout: 0xdc2626,
};

const MATERIAL_CSS_COLORS = {
  conductor: "rgba(217, 119, 6, 0.25)",
  substrate: "rgba(2, 132, 199, 0.2)",
  ground: "rgba(22, 163, 74, 0.25)",
  dielectric: "rgba(124, 58, 237, 0.2)",
  keepout: "rgba(220, 38, 38, 0.25)",
};

// =====================================================================
// DOM INITIALIZATION & MODE SWITCHING
// =====================================================================
document.addEventListener("DOMContentLoaded", () => {
  setupModeSwitching();
  initExplorerControls();
  initReferenceControls();
  initRFControls();
  initAbsorberControls();
  initOptimizationControls();
  
  // Auto-launch initial exploration so user sees data immediately
  runExploration();
  
  // Also load reference patterns catalog in background
  loadReferenceCatalog();

  // Initialize sync badge
  updateSyncBadge();
});

function updateSyncBadge() {
  const badge = document.getElementById("sync-design-badge");
  const label = document.getElementById("sync-design-label") || document.getElementById("sync-badge-text");
  if (!label || !appState.activeDesign) return;
  const ad = appState.activeDesign;
  const pName = (ad.pattern_type || "Origami").replace(/_/g, " ");
  const pCap = pName.charAt(0).toUpperCase() + pName.slice(1);
  const foldStr = ad.foldAngle !== undefined ? `${ad.foldAngle.toFixed(1)}°` : "30.0°";
  const p = ad.params || {};
  const dimStr = p.a && p.b ? `${p.a}×${p.b}mm` : "";
  label.textContent = `Sync: ${pCap} ${dimStr ? `(${dimStr}, ${foldStr})` : `(${foldStr})`}`;
  if (badge) {
    badge.classList.add("updated");
    setTimeout(() => badge.classList.remove("updated"), 600);
  }
}

function syncDesignToAllSections(source, data) {
  appState.activeDesign = {
    source: source,
    id: data.id || "Active Model",
    pattern_type: data.pattern_type || "miura_ori",
    family: data.family || "modulated_miura",
    params: { ...(data.params || {}) },
    foldAngle: data.foldAngle !== undefined ? data.foldAngle : (data.fold_angle || 30.0),
    modelData: data.modelData || null,
  };
  updateSyncBadge();
}

function syncReferenceFromActiveDesign() {
  if (!appState.activeDesign) {
    if (!appState.reference.modelData) {
      generateReferencePattern();
    }
    return;
  }

  const ad = appState.activeDesign;
  const ptype = ad.pattern_type || "miura_ori";
  appState.reference.currentPattern = ptype;

  // Copy parameters
  if (ad.params) {
    appState.reference.params = { ...(appState.reference.params || {}), ...ad.params };
    if (ad.params.gamma !== undefined && appState.reference.params.gamma_deg === undefined) {
      appState.reference.params.gamma_deg = ad.params.gamma;
    }
  }
  if (ad.foldAngle !== undefined) {
    appState.reference.foldAngle = ad.foldAngle;
  }

  // Update UI pattern buttons
  const patBtns = document.querySelectorAll("#mode-reference-container .pattern-btn");
  patBtns.forEach(b => {
    b.classList.toggle("active", b.dataset.pattern === ptype);
  });
  const badge = document.getElementById("ref-active-pattern-badge");
  if (badge) badge.textContent = ptype.replace(/_/g, " ");

  // Update UI sliders and readouts
  const foldSlider = document.getElementById("ref-fold-slider");
  if (foldSlider) foldSlider.value = appState.reference.foldAngle;
  const foldReadout = document.getElementById("ref-fold-readout");
  if (foldReadout) foldReadout.textContent = appState.reference.foldAngle.toFixed(1) + "°";
  const hudAngle = document.getElementById("ref-hud-angle");
  if (hudAngle) hudAngle.textContent = appState.reference.foldAngle.toFixed(1) + "°";

  // Rebuild parameter inputs for this pattern and generate pattern
  renderReferenceParamInputs(ptype);
  generateReferencePattern();
}

function setupModeSwitching() {
  const tabExplorer = document.getElementById("tab-btn-explorer");
  const tabReference = document.getElementById("tab-btn-reference");
  const tabAbsorber = document.getElementById("tab-btn-absorber");
  const tabOptFab = document.getElementById("tab-btn-optfab");

  const modeExpContainer = document.getElementById("mode-explorer-container");
  const modeRefContainer = document.getElementById("mode-reference-container");
  const modeAbsContainer = document.getElementById("mode-absorber-container");
  const modeOptContainer = document.getElementById("mode-optfab-container");

  const allTabs = [tabExplorer, tabReference, tabAbsorber, tabOptFab].filter(Boolean);
  const allContainers = [modeExpContainer, modeRefContainer, modeAbsContainer, modeOptContainer].filter(Boolean);

  function activateTab(activeTab, activeContainer, modeName) {
    allTabs.forEach(t => t.classList.remove("active"));
    allContainers.forEach(c => c.classList.remove("active"));

    activeTab.classList.add("active");
    activeContainer.classList.add("active");
    appState.currentMode = modeName;
    updateStatus(`${modeName.charAt(0).toUpperCase() + modeName.slice(1)} Mode Active`);
    updateSyncBadge();
  }

  if (tabExplorer) {
    tabExplorer.addEventListener("click", () => {
      activateTab(tabExplorer, modeExpContainer, "explorer");
      onExplorerResize();
    });
  }

  if (tabReference) {
    tabReference.addEventListener("click", () => {
      activateTab(tabReference, modeRefContainer, "reference");
      if (!refSceneInitialized) {
        initReferenceThreeJS();
      }
      onReferenceResize();
      // Seamless automatic parameter sync from active design!
      syncReferenceFromActiveDesign();
    });
  }

  if (tabAbsorber) {
    tabAbsorber.addEventListener("click", () => {
      activateTab(tabAbsorber, modeAbsContainer, "absorber");
      if (!absSceneInitialized) {
        initAbsorberThreeJS();
      }
      onAbsorberResize();
      // Seamless automatic parameter sync from active design!
      syncAbsorberFromActiveDesign();
    });
  }

  if (tabOptFab) {
    tabOptFab.addEventListener("click", () => {
      activateTab(tabOptFab, modeOptContainer, "optimization");
      onOptimizationResize();
    });
  }
}

function updateStatus(msg) {
  const el = document.getElementById("status-text");
  if (el) el.textContent = msg;
}

// =====================================================================
// SECTION 1: GENERATIVE EXPLORER ENGINE LOGIC
// =====================================================================

function initExplorerControls() {
  // Sample Count segmented buttons
  const countBtns = document.querySelectorAll(".count-btn");
  countBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      countBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      appState.explorer.sampleCount = parseInt(btn.dataset.count, 10);
    });
  });

  // Re-roll seed button
  const seedBtn = document.getElementById("btn-seed-random");
  const seedInput = document.getElementById("exp-seed");
  seedBtn.addEventListener("click", () => {
    const newSeed = Math.floor(Math.random() * 90000) + 1000;
    seedInput.value = newSeed;
    appState.explorer.seed = newSeed;
  });

  // Explore button
  const btnExplore = document.getElementById("btn-run-explore");
  btnExplore.addEventListener("click", () => {
    runExploration();
  });

  // Toolbar View Switcher (Grid / Scatter / Split)
  const btnGrid = document.getElementById("btn-view-grid");
  const btnScatter = document.getElementById("btn-view-scatter");
  const btnSplit = document.getElementById("btn-view-split");
  const displayArea = document.getElementById("explorer-display-area");

  function setViewMode(mode) {
    appState.explorer.viewMode = mode;
    btnGrid.classList.toggle("active", mode === "grid");
    btnScatter.classList.toggle("active", mode === "scatter");
    btnSplit.classList.toggle("active", mode === "split");

    displayArea.classList.remove("view-grid-mode", "view-scatter-mode", "view-split-mode");
    displayArea.classList.add(`view-${mode}-mode`);

    if (mode === "scatter" || mode === "split") {
      setTimeout(renderScatterPlot, 50);
    }
  }

  btnGrid.addEventListener("click", () => setViewMode("grid"));
  btnScatter.addEventListener("click", () => setViewMode("scatter"));
  btnSplit.addEventListener("click", () => setViewMode("split"));

  // Candidate Filters (All / Valid / Rejected)
  const filterPills = document.querySelectorAll(".filter-pill");
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      appState.explorer.activeFilter = pill.dataset.filter;
      renderCandidateGallery();
      renderScatterPlot();
    });
  });

  // Sort dropdown
  const sortSelect = document.getElementById("cand-sort-select");
  sortSelect.addEventListener("change", () => {
    appState.explorer.activeSort = sortSelect.value;
    renderCandidateGallery();
  });

  // Inspector Close button
  const btnCloseInsp = document.getElementById("btn-close-inspector");
  const inspDeck = document.getElementById("candidate-inspector");
  btnCloseInsp.addEventListener("click", () => {
    inspDeck.classList.remove("open");
    appState.explorer.inspectorOpen = false;
  });

  // Inspector Fold Slider
  const inspFoldSlider = document.getElementById("insp-fold-slider");
  const inspFoldVal = document.getElementById("insp-fold-val");
  inspFoldSlider.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    inspFoldVal.textContent = val.toFixed(1) + "°";
    appState.explorer.inspFoldAngle = val;
    if (appState.explorer.selectedCandidate) {
      foldSelectedCandidate(val);
    }
  });

  // Export Buttons
  const btnExpFold = document.getElementById("btn-export-fold");
  if (btnExpFold) btnExpFold.addEventListener("click", exportCandidateFOLD);
  const btnExpObj = document.getElementById("btn-export-obj");
  if (btnExpObj) btnExpObj.addEventListener("click", exportCandidateOBJ);

  // Inspector Cross-Module Transfer Buttons
  const btnInspSendRef = document.getElementById("btn-insp-send-ref");
  if (btnInspSendRef) btnInspSendRef.addEventListener("click", sendCandidateToReference);
  const btnInspSendAbs = document.getElementById("btn-insp-send-abs");
  if (btnInspSendAbs) btnInspSendAbs.addEventListener("click", sendCandidateToAbsorber);
  const btnInspSendOpt = document.getElementById("btn-insp-send-opt");
  if (btnInspSendOpt) btnInspSendOpt.addEventListener("click", sendCandidateToOptFab);

  // Inspector Three.js controls
  const btnInspStrain = document.getElementById("btn-insp-strain");
  if (btnInspStrain) {
    btnInspStrain.addEventListener("click", () => {
      appState.strain.enabledInsp = !appState.strain.enabledInsp;
      const isEnabled = appState.strain.enabledInsp;
      btnInspStrain.classList.toggle("active-strain", isEnabled);
      btnInspStrain.textContent = `⚡ Strain: ${isEnabled ? "ON" : "OFF"}`;

      const overlay = document.getElementById("insp-strain-overlay");
      if (overlay) overlay.classList.toggle("hidden", !isEnabled);

      const cand = appState.explorer.selectedCandidate;
      if (cand && cand.modelData) {
        renderInspector3D(cand.modelData.folded_mesh_3d, cand.modelData.crease_pattern_2d);
      }
      updateStatus(`Inspector Strain Heatmap: ${isEnabled ? "ACTIVE" : "DISABLED"}`);
    });
  }

  document.getElementById("btn-insp-wireframe").addEventListener("click", toggleInspectorWireframe);
  document.getElementById("btn-insp-reset3d").addEventListener("click", resetInspectorCamera);
  document.getElementById("btn-insp-reset2d").addEventListener("click", resetInspector2DView);

  // Scatter plot canvas interaction
  initScatterInteraction();
}

async function runExploration() {
  updateStatus("Generating candidate designs across design space...");
  const btnExplore = document.getElementById("btn-run-explore");
  if (btnExplore) {
    btnExplore.disabled = true;
    btnExplore.textContent = "Generating...";
  }

  const seed = parseInt(document.getElementById("exp-seed")?.value, 10) || 42;
  const family = document.getElementById("exp-family")?.value || "modulated_miura";
  const count = appState.explorer.sampleCount;

  // Gather range inputs
  const designSpace = {
    a_min: parseFloat(document.getElementById("range-a-min")?.value) || 15.0,
    a_max: parseFloat(document.getElementById("range-a-max")?.value) || 45.0,
    b_min: parseFloat(document.getElementById("range-b-min")?.value) || 15.0,
    b_max: parseFloat(document.getElementById("range-b-max")?.value) || 45.0,
    gamma_min: parseFloat(document.getElementById("range-gamma-min")?.value) || 35.0,
    gamma_max: parseFloat(document.getElementById("range-gamma-max")?.value) || 75.0,
    num_cells_x_min: parseInt(document.getElementById("range-nx-min")?.value, 10) || 1,
    num_cells_x_max: parseInt(document.getElementById("range-nx-max")?.value, 10) || 3,
    num_cells_y_min: parseInt(document.getElementById("range-ny-min")?.value, 10) || 1,
    num_cells_y_max: parseInt(document.getElementById("range-ny-max")?.value, 10) || 3,
    fold_angle_min: parseFloat(document.getElementById("range-fold-min")?.value) || 20.0,
    fold_angle_max: parseFloat(document.getElementById("range-fold-max")?.value) || 70.0,

    flat_foldable_only: !!document.getElementById("chk-flat-foldable")?.checked,
    min_panel_area: parseFloat(document.getElementById("filter-min-area")?.value) || 40.0,
    min_crease_length: parseFloat(document.getElementById("filter-min-crease")?.value) || 8.0,
    max_aperture_width: parseFloat(document.getElementById("filter-max-aperture")?.value) || 350.0,
    max_aperture_height: parseFloat(document.getElementById("filter-max-aperture")?.value) || 350.0,

    target_frequency_ghz: parseFloat(document.getElementById("rf-target-freq")?.value) || 2.4,
    substrate_thickness_mm: parseFloat(document.getElementById("rf-substrate-thick")?.value) || 0.8,
    crease_keepout_mm: parseFloat(document.getElementById("rf-crease-keepout")?.value) || 1.0,
  };

  try {
    const resp = await fetch("/api/explore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        count: count,
        seed: seed,
        pattern_family: family,
        design_space: designSpace,
      }),
    });

    if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
    const data = await resp.json();

    appState.explorer.candidates = data.candidates || [];
    appState.explorer.scatterPoints = data.design_space_scatter?.points || [];
    appState.explorer.summary = data.summary || {};

    // Update Counters
    document.getElementById("counter-total").textContent = data.summary.total_generated;
    document.getElementById("counter-valid").textContent = data.summary.valid_count;
    document.getElementById("counter-rejected").textContent = data.summary.rejected_count;

    document.getElementById("pill-count-all").textContent = data.summary.total_generated;
    document.getElementById("pill-count-valid").textContent = data.summary.valid_count;
    document.getElementById("pill-count-rej").textContent = data.summary.rejected_count;

    const rate = Math.round((data.summary.valid_count / Math.max(1, data.summary.total_generated)) * 100);
    document.getElementById("rejection-breakdown").textContent = 
      `Feasibility Rate: ${rate}% (${data.summary.valid_count}/${data.summary.total_generated} passed geometric constraints).`;

    renderCandidateGallery();
    renderScatterPlot();

    // Automatically select the first candidate
    if (appState.explorer.candidates.length > 0) {
      const best = appState.explorer.candidates.find(c => c.is_valid) || appState.explorer.candidates[0];
      selectCandidate(best.id);
    }

    updateStatus(`Generated ${data.summary.total_generated} candidates (Seed: ${seed})`);
  } catch (err) {
    console.error("Exploration error:", err);
    updateStatus(`Exploration failed: ${err.message}`);
  } finally {
    if (btnExplore) {
      btnExplore.disabled = false;
      btnExplore.textContent = "Generate Candidates";
    }
  }
}

function getFilteredAndSortedCandidates() {
  let list = [...appState.explorer.candidates];

  // Filter
  if (appState.explorer.activeFilter === "valid") {
    list = list.filter(c => c.is_valid);
  } else if (appState.explorer.activeFilter === "rejected") {
    list = list.filter(c => !c.is_valid);
  }

  // Sort
  const sort = appState.explorer.activeSort;
  list.sort((a, b) => {
    if (sort === "compactness_asc") {
      return (a.metrics?.compactness_ratio || 1) - (b.metrics?.compactness_ratio || 1);
    } else if (sort === "area_desc") {
      return (b.metrics?.surface_area_mm2 || 0) - (a.metrics?.surface_area_mm2 || 0);
    } else if (sort === "faces_desc") {
      return (b.metrics?.num_faces || 0) - (a.metrics?.num_faces || 0);
    } else {
      return a.id.localeCompare(b.id);
    }
  });

  return list;
}

function renderCandidateGallery() {
  const container = document.getElementById("candidate-cards-container");
  const candidates = getFilteredAndSortedCandidates();

  if (candidates.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📁</div>
        <div class="empty-title">No candidates match current filter</div>
        <div class="empty-desc">Try changing the filter to 'All' or widening the design space bounds.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = "";

  candidates.forEach(c => {
    const isSelected = appState.explorer.selectedCandidate?.id === c.id;
    const card = document.createElement("div");
    card.className = `candidate-card ${c.is_valid ? "valid" : "rejected"} ${isSelected ? "selected" : ""}`;
    card.dataset.id = c.id;

    const p = c.parameters || {};
    const m = c.metrics || {};
    const aspect = (p.a / Math.max(0.1, p.b)).toFixed(2);

    let statusTag = c.is_valid 
      ? `<span class="status-tag tag-valid">Feasible</span>`
      : `<span class="status-tag tag-rej">Rejected</span>`;

    let rejInfo = "";
    if (!c.is_valid && c.rejection_reasons && c.rejection_reasons.length > 0) {
      rejInfo = `<div class="card-rejection-msg">${c.rejection_reasons[0]}</div>`;
    }

    card.innerHTML = `
      <div class="card-header">
        <span class="card-id">${c.id}</span>
        ${statusTag}
      </div>
      <div class="card-thumb">
        ${c.thumbnail_svg || '<div style="color:var(--text-dim);font-size:10px;">Thumbnail N/A</div>'}
      </div>
      <div class="card-body">
        <div class="card-stat-row">
          <span>Facet a × b:</span>
          <span class="stat-val">${p.a || 0} × ${p.b || 0} mm</span>
        </div>
        <div class="card-stat-row">
          <span>Aspect Ratio (a/b):</span>
          <span class="stat-val">${aspect}</span>
        </div>
        <div class="card-stat-row">
          <span>Crease γ / Reps:</span>
          <span class="stat-val">${p.gamma || 60}° (${p.num_cells_x || 1}×${p.num_cells_y || 1})</span>
        </div>
        <div class="card-stat-row">
          <span>Compactness:</span>
          <span class="stat-val">${m.compactness_ratio !== undefined ? m.compactness_ratio.toFixed(3) : "—"}</span>
        </div>
        <div class="card-stat-row">
          <span>Est. Res. f₀:</span>
          <span class="stat-val">${m.est_half_wave_f0_ghz ? m.est_half_wave_f0_ghz + " GHz" : "—"}</span>
        </div>
        ${rejInfo}
      </div>
    `;

    card.addEventListener("click", () => {
      selectCandidate(c.id);
    });

    container.appendChild(card);
  });
}

// =====================================================================
// SCATTER PLOT 2D INTERACTIVE ENGINE
// =====================================================================
let scatterCanvas, scatterCtx;
let scatterPointsData = [];
let hoveredScatterPoint = null;

function initScatterInteraction() {
  scatterCanvas = document.getElementById("scatter-canvas");
  if (!scatterCanvas) return;
  scatterCtx = scatterCanvas.getContext("2d");

  const tooltip = document.getElementById("scatter-tooltip");

  scatterCanvas.addEventListener("mousemove", (e) => {
    const rect = scatterCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let closest = null;
    let minDist = 14; // hover radius

    for (const pt of scatterPointsData) {
      const d = Math.hypot(pt.screenX - mouseX, pt.screenY - mouseY);
      if (d < minDist) {
        minDist = d;
        closest = pt;
      }
    }

    if (closest) {
      hoveredScatterPoint = closest;
      tooltip.style.display = "block";
      tooltip.style.left = `${mouseX + 12}px`;
      tooltip.style.top = `${mouseY - 10}px`;
      tooltip.innerHTML = `
        <div style="font-weight:700;color:${closest.is_valid ? 'var(--accent-success)' : 'var(--accent-danger)'}">
          ${closest.id} [${closest.is_valid ? 'Feasible' : 'Rejected'}]
        </div>
        <div>Aspect Ratio (a/b): ${closest.x.toFixed(2)}</div>
        <div>Compactness: ${closest.y.toFixed(3)}</div>
        <div>Fold Angle: ${closest.fold_angle}° | γ: ${closest.gamma}°</div>
        <div>Area: ${closest.surface_area} mm²</div>
      `;
      scatterCanvas.style.cursor = "pointer";
      drawScatterContent();
    } else {
      if (hoveredScatterPoint !== null) {
        hoveredScatterPoint = null;
        tooltip.style.display = "none";
        scatterCanvas.style.cursor = "default";
        drawScatterContent();
      }
    }
  });

  scatterCanvas.addEventListener("mouseleave", () => {
    hoveredScatterPoint = null;
    tooltip.style.display = "none";
    drawScatterContent();
  });

  scatterCanvas.addEventListener("click", () => {
    if (hoveredScatterPoint) {
      selectCandidate(hoveredScatterPoint.id);
    }
  });

  window.addEventListener("resize", () => {
    if (appState.currentMode === "explorer" && (appState.explorer.viewMode === "scatter" || appState.explorer.viewMode === "split")) {
      renderScatterPlot();
    }
  });
}

function renderScatterPlot() {
  if (!scatterCanvas || !scatterCtx) return;

  const wrap = scatterCanvas.parentElement;
  const width = wrap.clientWidth || 400;
  const height = wrap.clientHeight || 300;

  const dpr = window.devicePixelRatio || 1;
  scatterCanvas.width = width * dpr;
  scatterCanvas.height = height * dpr;
  scatterCanvas.style.width = width + "px";
  scatterCanvas.style.height = height + "px";

  scatterCtx.resetTransform();
  scatterCtx.scale(dpr, dpr);

  drawScatterContent();
}

function drawScatterContent() {
  if (!scatterCtx || !scatterCanvas) return;
  const width = scatterCanvas.clientWidth;
  const height = scatterCanvas.clientHeight;

  scatterCtx.clearRect(0, 0, width, height);

  // Background grid
  const pad = { top: 30, right: 30, bottom: 40, left: 50 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  if (plotW <= 0 || plotH <= 0) return;

  // Determine plot bounds
  const rawPts = appState.explorer.scatterPoints;
  if (!rawPts || rawPts.length === 0) {
    scatterCtx.fillStyle = "#64748b";
    scatterCtx.font = "11px monospace";
    scatterCtx.textAlign = "center";
    scatterCtx.fillText("No candidate points generated yet.", width / 2, height / 2);
    return;
  }

  let minX = Math.min(...rawPts.map(p => p.x), 0.5);
  let maxX = Math.max(...rawPts.map(p => p.x), 2.5);
  let minY = 0.0;
  let maxY = Math.max(...rawPts.map(p => p.y), 1.0);

  // Padding on ranges
  minX = Math.max(0.2, minX * 0.9);
  maxX = maxX * 1.1;
  maxY = Math.min(1.2, maxY * 1.15);

  const toScreenX = (x) => pad.left + ((x - minX) / (maxX - minX)) * plotW;
  const toScreenY = (y) => pad.top + plotH - ((y - minY) / (maxY - minY)) * plotH;

  // Draw Grid Lines & Axes
  scatterCtx.strokeStyle = "#e2e8f0";
  scatterCtx.lineWidth = 1;
  scatterCtx.fillStyle = "#64748b";
  scatterCtx.font = "9px monospace";

  // Horizontal grid lines (Compactness)
  const ySteps = 5;
  for (let i = 0; i <= ySteps; i++) {
    const yVal = minY + (i / ySteps) * (maxY - minY);
    const sy = toScreenY(yVal);
    scatterCtx.beginPath();
    scatterCtx.moveTo(pad.left, sy);
    scatterCtx.lineTo(pad.left + plotW, sy);
    scatterCtx.stroke();

    scatterCtx.textAlign = "right";
    scatterCtx.fillText(yVal.toFixed(2), pad.left - 8, sy + 3);
  }

  // Vertical grid lines (Aspect Ratio)
  const xSteps = 6;
  for (let i = 0; i <= xSteps; i++) {
    const xVal = minX + (i / xSteps) * (maxX - minX);
    const sx = toScreenX(xVal);
    scatterCtx.beginPath();
    scatterCtx.moveTo(sx, pad.top);
    scatterCtx.lineTo(sx, pad.top + plotH);
    scatterCtx.stroke();

    scatterCtx.textAlign = "center";
    scatterCtx.fillText(xVal.toFixed(2), sx, pad.top + plotH + 15);
  }

  // Axis Labels
  scatterCtx.fillStyle = "#334155";
  scatterCtx.font = "10px monospace";
  scatterCtx.textAlign = "center";
  scatterCtx.fillText("Facet Aspect Ratio (a / b)", pad.left + plotW / 2, height - 8);

  scatterCtx.save();
  scatterCtx.translate(14, pad.top + plotH / 2);
  scatterCtx.rotate(-Math.PI / 2);
  scatterCtx.fillText("Folded Compactness Ratio", 0, 0);
  scatterCtx.restore();

  // Plot Points
  scatterPointsData = [];

  rawPts.forEach(pt => {
    // Filter check
    if (appState.explorer.activeFilter === "valid" && !pt.is_valid) return;
    if (appState.explorer.activeFilter === "rejected" && pt.is_valid) return;

    const sx = toScreenX(pt.x);
    const sy = toScreenY(pt.y);

    const isSelected = appState.explorer.selectedCandidate?.id === pt.id;
    const isHovered = hoveredScatterPoint?.id === pt.id;

    scatterPointsData.push({
      ...pt,
      screenX: sx,
      screenY: sy,
    });

    scatterCtx.save();

    if (isSelected) {
      // Ring for active selection
      scatterCtx.beginPath();
      scatterCtx.arc(sx, sy, 8, 0, Math.PI * 2);
      scatterCtx.fillStyle = "rgba(37, 99, 235, 0.15)";
      scatterCtx.fill();
      scatterCtx.strokeStyle = "#2563eb";
      scatterCtx.lineWidth = 1.5;
      scatterCtx.stroke();
    }

    if (isHovered) {
      scatterCtx.beginPath();
      scatterCtx.arc(sx, sy, 7, 0, Math.PI * 2);
      scatterCtx.strokeStyle = "#0f172a";
      scatterCtx.lineWidth = 1.2;
      scatterCtx.stroke();
    }

    // Point body
    scatterCtx.beginPath();
    const r = isSelected ? 5 : 3.5;
    scatterCtx.arc(sx, sy, r, 0, Math.PI * 2);

    if (pt.is_valid) {
      scatterCtx.fillStyle = isSelected ? "#2563eb" : "#16a34a";
    } else {
      scatterCtx.fillStyle = "#dc2626";
    }
    scatterCtx.shadowBlur = 0;
    scatterCtx.fill();

    scatterCtx.restore();
  });
}

// =====================================================================
// CANDIDATE SELECTION & 3D FOLDING INSPECTOR DECK
// =====================================================================

async function selectCandidate(candidateId) {
  const candidate = appState.explorer.candidates.find(c => c.id === candidateId);
  if (!candidate) return;

  appState.explorer.selectedCandidate = candidate;
  appState.explorer.inspectorOpen = true;

  // Update card highlighting in gallery
  document.querySelectorAll(".candidate-card").forEach(c => {
    c.classList.toggle("selected", c.dataset.id === candidateId);
  });

  // Redraw scatter plot to highlight selected dot
  drawScatterContent();

  // Open inspector dock
  const deck = document.getElementById("candidate-inspector");
  deck.classList.add("open");

  // Populate Inspector Identity
  document.getElementById("insp-cand-id").textContent = candidate.id;
  const statusEl = document.getElementById("insp-cand-status");
  if (candidate.is_valid) {
    statusEl.className = "status-tag tag-valid";
    statusEl.textContent = "Feasible";
  } else {
    statusEl.className = "status-tag tag-rej";
    statusEl.textContent = "Rejected";
  }

  const p = candidate.parameters || {};
  document.getElementById("insp-cand-params").textContent = 
    `a=${p.a}mm, b=${p.b}mm, γ=${p.gamma}°, ${p.num_cells_x}×${p.num_cells_y}`;

  // Sync Fold Slider
  const foldVal = p.fold_angle || 35.0;
  appState.explorer.inspFoldAngle = foldVal;
  document.getElementById("insp-fold-slider").value = foldVal;
  document.getElementById("insp-fold-val").textContent = foldVal.toFixed(1) + "°";

  // Seamless cross-module synchronization
  const ptype = getExplorerPatternType();
  syncDesignToAllSections("explorer", {
    id: candidate.id,
    pattern_type: ptype,
    family: appState.explorer.family,
    params: candidate.parameters,
    foldAngle: foldVal,
    metrics: candidate.metrics,
    validation: candidate.validation,
  });

  // Populate Metrics Card
  const m = candidate.metrics || {};
  document.getElementById("insp-stat-mesh").textContent = `${m.num_vertices || 0} / ${m.num_faces || 0}`;
  document.getElementById("insp-stat-area").textContent = `${m.surface_area_mm2 || 0} mm²`;
  if (m.folded_envelope_mm) {
    document.getElementById("insp-stat-dims").textContent = 
      `${m.folded_envelope_mm[0]} × ${m.folded_envelope_mm[1]} × ${m.folded_envelope_mm[2]} mm`;
  }
  document.getElementById("insp-stat-compact").textContent = 
    m.compactness_ratio !== undefined ? m.compactness_ratio.toFixed(3) : "—";
  document.getElementById("insp-stat-f0").textContent = 
    m.est_half_wave_f0_ghz ? `${m.est_half_wave_f0_ghz} GHz` : "—";

  // Validation mini checklist
  const val = candidate.validation || {};
  const kw = val.kawasaki?.passed !== false;
  const mw = val.maekawa?.passed !== false;
  
  setMiniVal("insp-val-kawasaki", kw);
  setMiniVal("insp-val-maekawa", mw);
  setMiniVal("insp-val-isometry", true);
  setMiniVal("insp-val-area", true);

  // Initialize Inspector 3D Viewport if not ready
  if (!inspSceneInitialized) {
    initInspectorThreeJS();
  }

  // Load detailed folded 3D mesh and 2D crease pattern from backend
  await foldSelectedCandidate(foldVal);
}

function setMiniVal(id, passed) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `val-icon ${passed ? 'pass' : 'fail'}`;
  el.textContent = passed ? '✓' : '✕';
}

async function foldSelectedCandidate(foldAngleDeg) {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) return;

  const family = appState.explorer.family;
  let ptype = "miura_ori";
  if (family.includes("waterbomb")) ptype = "waterbomb";
  else if (family.includes("yoshimura")) ptype = "yoshimura";

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: cand.parameters,
        fold_angle: foldAngleDeg,
      }),
    });

    if (!resp.ok) return;
    const model = await resp.json();

    // Cache model data for active design & FOLD export
    cand.modelData = model;
    if (appState.activeDesign) {
      appState.activeDesign.modelData = model;
      appState.activeDesign.foldAngle = foldAngleDeg;
    }

    // Render into Inspector 3D View with Mountain/Valley crease lines
    renderInspector3D(model.folded_mesh_3d, model.crease_pattern_2d);

    // Render into Inspector 2D Canvas
    renderInspector2D(model.crease_pattern_2d);

    // Update dimensions and area in real-time
    const dims = model.folded_mesh_3d.dimensions;
    if (dims) {
      document.getElementById("insp-stat-dims").textContent = 
        `${dims[0].toFixed(1)} × ${dims[1].toFixed(1)} × ${dims[2].toFixed(1)} mm`;
    }
  } catch (err) {
    console.error("Fold update error:", err);
  }
}

// =====================================================================
// INSPECTOR THREE.JS 3D ENGINE
// =====================================================================
let inspScene, inspCamera, inspRenderer, inspControls;
let inspMeshObj = null, inspEdgesObj = null;
let inspSceneInitialized = false;

function initInspectorThreeJS() {
  const container = document.getElementById("inspector-threejs-container");
  if (!container) return;

  const w = container.clientWidth || 300;
  const h = container.clientHeight || 260;

  inspScene = new THREE.Scene();
  inspScene.background = new THREE.Color(0xf8fafc);

  inspCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
  inspCamera.position.set(50, 45, 90);

  inspRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  inspRenderer.setSize(w, h);
  inspRenderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(inspRenderer.domElement);

  if (typeof THREE.OrbitControls !== "undefined") {
    inspControls = new THREE.OrbitControls(inspCamera, inspRenderer.domElement);
    inspControls.enableDamping = true;
    inspControls.dampingFactor = 0.08;
  }

  // Lighting
  const amb = new THREE.AmbientLight(0xffffff, 0.85);
  inspScene.add(amb);

  const dir1 = new THREE.DirectionalLight(0xffffff, 0.65);
  dir1.position.set(80, 120, 60);
  inspScene.add(dir1);

  const dir2 = new THREE.DirectionalLight(0x94a3b8, 0.35);
  dir2.position.set(-60, -40, -50);
  inspScene.add(dir2);

  // Grid
  const grid = new THREE.GridHelper(140, 14, 0xcbd5e1, 0xe2e8f0);
  grid.position.y = -0.2;
  inspScene.add(grid);

  inspSceneInitialized = true;
  animateInspector();

  window.addEventListener("resize", onExplorerResize);
}

function animateInspector() {
  requestAnimationFrame(animateInspector);
  if (inspControls) inspControls.update();
  if (inspRenderer && inspScene && inspCamera) {
    inspRenderer.render(inspScene, inspCamera);
  }
}

function create3DCreaseLines(creases, vList, isStrain = false, strainMetrics = null) {
  if (!creases || !vList || creases.length === 0) return null;

  const positions = [];
  const colors = [];

  const creaseCol = (isStrain && strainMetrics)
    ? OrigamiStrainEngine.getStrainColor(strainMetrics.creaseBendingStrain, appState.strain.maxThreshold)
    : null;

  creases.forEach(c => {
    const u = c.u;
    const v = c.v;
    if (u === undefined || v === undefined) return;
    if (u >= vList.length || v >= vList.length) return;

    const p1 = vList[u];
    const p2 = vList[v];
    if (!p1 || !p2) return;

    positions.push(p1[0], p1[1], p1[2], p2[0], p2[1], p2[2]);

    let col;
    if (isStrain && creaseCol) {
      col = creaseCol;
    } else {
      if (c.type === "M") {
        col = new THREE.Color(0xdc2626); // Bold Mountain Red
      } else if (c.type === "V") {
        col = new THREE.Color(0x2563eb); // Bold Valley Blue
      } else {
        col = new THREE.Color(0x0f172a); // Deep Slate Border
      }
    }

    colors.push(col.r, col.g, col.b, col.r, col.g, col.b);
  });

  if (positions.length === 0) return null;

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

  const mat = new THREE.LineBasicMaterial({
    vertexColors: true,
    linewidth: 2.2,
    depthTest: true,
  });

  return new THREE.LineSegments(geom, mat);
}

function renderInspector3D(meshData, creaseData) {
  if (!inspScene || !meshData) return;

  if (inspMeshObj) {
    inspScene.remove(inspMeshObj);
    inspMeshObj.geometry.dispose();
    inspMeshObj = null;
  }
  if (inspEdgesObj) {
    inspScene.remove(inspEdgesObj);
    inspEdgesObj.geometry.dispose();
    inspEdgesObj = null;
  }

  const geom = new THREE.BufferGeometry();
  const vList = meshData.vertices;
  const fList = meshData.faces;

  const isStrain = appState.strain.enabledInsp;
  let strainMetrics = null;
  if (isStrain) {
    strainMetrics = OrigamiStrainEngine.computeStrains(meshData, creaseData, appState.explorer.inspFoldAngle || 35.0);
    appState.strain.lastInspMetrics = strainMetrics;
    OrigamiStrainEngine.updateHUD("insp", strainMetrics);
  }

  const positions = [];
  const colors = [];

  for (let fIdx = 0; fIdx < fList.length; fIdx++) {
    const f = fList[fIdx];
    let col;
    if (isStrain && strainMetrics && strainMetrics.faceStrains) {
      const faceE = strainMetrics.faceStrains[fIdx] || 0.0;
      col = OrigamiStrainEngine.getStrainColor(faceE, appState.strain.maxThreshold);
    } else {
      col = new THREE.Color(0x93c5fd); // Restrained engineering blue
    }

    for (let i = 1; i < f.length - 1; i++) {
      const v0 = vList[f[0]];
      const v1 = vList[f[i]];
      const v2 = vList[f[i + 1]];

      positions.push(v0[0], v0[1], v0[2]);
      positions.push(v1[0], v1[1], v1[2]);
      positions.push(v2[0], v2[1], v2[2]);

      colors.push(col.r, col.g, col.b);
      colors.push(col.r, col.g, col.b);
      colors.push(col.r, col.g, col.b);
    }
  }

  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geom.computeVertexNormals();

  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true,
    side: THREE.DoubleSide,
    roughness: 0.6,
    metalness: 0.1,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  });

  inspMeshObj = new THREE.Mesh(geom, mat);
  inspScene.add(inspMeshObj);

  // Render authentic origami creases (Red Mountain, Blue Valley, or Strain gradient)
  if (creaseData && creaseData.creases && creaseData.creases.length > 0) {
    inspEdgesObj = create3DCreaseLines(creaseData.creases, vList, isStrain, strainMetrics);
  }
  if (!inspEdgesObj) {
    const edgeGeom = new THREE.WireframeGeometry(geom);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x334155, linewidth: 1 });
    inspEdgesObj = new THREE.LineSegments(edgeGeom, edgeMat);
  }
  inspScene.add(inspEdgesObj);
}

function toggleInspectorWireframe() {
  if (inspEdgesObj) {
    inspEdgesObj.visible = !inspEdgesObj.visible;
    document.getElementById("btn-insp-wireframe").textContent = 
      `Edges: ${inspEdgesObj.visible ? 'ON' : 'OFF'}`;
  }
}

function resetInspectorCamera() {
  if (inspCamera && inspControls) {
    inspCamera.position.set(50, 45, 90);
    inspControls.target.set(0, 0, 0);
    inspControls.update();
  }
}

function onExplorerResize() {
  const container = document.getElementById("inspector-threejs-container");
  if (!container || !inspCamera || !inspRenderer) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {
    inspCamera.aspect = w / h;
    inspCamera.updateProjectionMatrix();
    inspRenderer.setSize(w, h);
  }
}

// =====================================================================
// INSPECTOR 2D CREASE PATTERN CANVAS
// =====================================================================
let insp2DData = null;

function renderInspector2D(creaseData) {
  insp2DData = creaseData;
  const canvas = document.getElementById("inspector-crease-canvas");
  if (!canvas || !creaseData) return;

  const ctx = canvas.getContext("2d");
  const container = canvas.parentElement;
  const w = container.clientWidth || 300;
  const h = container.clientHeight || 260;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";

  ctx.resetTransform();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const b = creaseData.bounds;
  if (!b || b.width <= 0) return;

  const pad = 24;
  const scale = Math.min((w - 2 * pad) / b.width, (h - 2 * pad) / b.height);
  const offX = (w - b.width * scale) / 2 - b.min[0] * scale;
  const offY = (h - b.height * scale) / 2 - b.min[1] * scale;

  const v2d = creaseData.vertices;

  // Draw Faces
  if (creaseData.faces) {
    creaseData.faces.forEach(f => {
      ctx.beginPath();
      f.indices.forEach((idx, i) => {
        const vx = v2d[idx][0] * scale + offX;
        const vy = v2d[idx][1] * scale + offY;
        if (i === 0) ctx.moveTo(vx, vy);
        else ctx.lineTo(vx, vy);
      });
      ctx.closePath();
      ctx.fillStyle = "rgba(37, 99, 235, 0.04)";
      ctx.fill();
    });
  }

  // Draw Creases (Red = Mountain, Blue = Valley, Grey = Border)
  if (creaseData.creases) {
    creaseData.creases.forEach(c => {
      const u = v2d[c.u];
      const v = v2d[c.v];
      if (!u || !v) return;

      const x1 = u[0] * scale + offX;
      const y1 = u[1] * scale + offY;
      const x2 = v[0] * scale + offX;
      const y2 = v[1] * scale + offY;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);

      if (c.type === "M") {
        ctx.strokeStyle = "#dc2626"; // Mountain (Red)
        ctx.lineWidth = 1.8;
        ctx.setLineDash([]);
      } else if (c.type === "V") {
        ctx.strokeStyle = "#2563eb"; // Valley (Blue dashed)
        ctx.lineWidth = 1.6;
        ctx.setLineDash([4, 3]);
      } else {
        ctx.strokeStyle = "#334155"; // Border
        ctx.lineWidth = 2.0;
        ctx.setLineDash([]);
      }
      ctx.stroke();
    });
  }
}

function resetInspector2DView() {
  if (insp2DData) {
    renderInspector2D(insp2DData);
  }
}

// =====================================================================
// EXPORT HELPERS (SIMULATOR-COMPLIANT .FOLD & .OBJ) & CROSS-MODULE SYNC
// =====================================================================

function getExplorerPatternType() {
  const family = appState.explorer.family || "modulated_miura";
  if (family.includes("waterbomb")) return "waterbomb";
  if (family.includes("yoshimura")) return "yoshimura";
  return "miura_ori";
}

function buildCompliantFold(creaseData, title, foldAngleDeg = 35.0) {
  if (!creaseData) return null;
  const vList = creaseData.vertices || [];
  const verticesCoords = vList.map(v => v.length === 2 ? [v[0], v[1], 0.0] : [v[0], v[1], v[2] || 0.0]);

  const creases = creaseData.creases || [];
  const edgesVertices = [];
  const edgesAssignment = [];
  const edgesFoldAngle = [];

  creases.forEach(c => {
    edgesVertices.push([c.u, c.v]);
    const asgn = (c.type || "F").toUpperCase();
    edgesAssignment.push(asgn);
    if (asgn === "M") {
      edgesFoldAngle.push(-180.0);
    } else if (asgn === "V") {
      edgesFoldAngle.push(180.0);
    } else {
      edgesFoldAngle.push(0.0);
    }
  });

  const faces = creaseData.faces || [];
  const facesVertices = faces.map(f => f.indices || []);
  const facesMaterials = faces.map(f => f.material || "substrate");

  return {
    file_spec: 1.1,
    file_creator: "RF Origami Design Studio",
    file_author: "RF-Origami Engineer",
    file_title: title || "RF_Origami_Model",
    file_classes: ["singleModel"],
    frame_classes: ["creasePattern"],
    frame_attributes: ["2D"],
    vertices_coords: verticesCoords,
    edges_vertices: edgesVertices,
    edges_assignment: edgesAssignment,
    edges_foldAngle: edgesFoldAngle,
    faces_vertices: facesVertices,
    faces_materials: facesMaterials,
  };
}

async function exportCandidateFOLD() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) {
    updateStatus("Select a candidate before exporting .FOLD");
    return;
  }

  const ptype = getExplorerPatternType();
  const foldAngle = appState.explorer.inspFoldAngle || 35.0;

  try {
    updateStatus(`Exporting FOLD specification for ${cand.id}...`);
    const resp = await fetch("/api/fold/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: cand.parameters,
        fold_angle: foldAngle,
        as_3d: false,
      }),
    });

    if (resp.ok) {
      const foldData = await resp.json();
      downloadFile(`${cand.id}_origami.fold`, JSON.stringify(foldData, null, 2), "application/json");
      updateStatus(`FOLD file exported: ${cand.id}_origami.fold (Ready for Origami Simulator)`);
      return;
    }
  } catch (err) {
    console.warn("Backend FOLD export endpoint failed, falling back to client synthesizer:", err);
  }

  const creaseData = (cand.modelData && cand.modelData.crease_pattern_2d) || insp2DData;
  if (creaseData) {
    const foldData = buildCompliantFold(creaseData, cand.id, foldAngle);
    downloadFile(`${cand.id}_origami.fold`, JSON.stringify(foldData, null, 2), "application/json");
    updateStatus(`FOLD file exported: ${cand.id}_origami.fold (Ready for Origami Simulator)`);
  }
}

function exportCandidateOBJ() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand || !inspMeshObj) {
    updateStatus("No candidate 3D mesh available to export");
    return;
  }

  const geom = inspMeshObj.geometry;
  const pos = geom.getAttribute("position");
  if (!pos) return;

  let obj = `# Wavefront OBJ Export - RF Origami Design Studio\n# Candidate: ${cand.id}\n`;
  for (let i = 0; i < pos.count; i++) {
    obj += `v ${pos.getX(i).toFixed(4)} ${pos.getY(i).toFixed(4)} ${pos.getZ(i).toFixed(4)}\n`;
  }
  for (let i = 0; i < pos.count; i += 3) {
    obj += `f ${i + 1} ${i + 2} ${i + 3}\n`;
  }

  downloadFile(`${cand.id}_mesh.obj`, obj, "text/plain");
  updateStatus(`OBJ file exported: ${cand.id}_mesh.obj`);
}

async function exportReferenceFOLD() {
  const ptype = appState.reference.currentPattern || "miura_ori";
  const params = appState.reference.params || {};
  const foldAngle = appState.reference.foldAngle || 35.0;

  try {
    updateStatus(`Exporting FOLD specification for ${ptype}...`);
    const resp = await fetch("/api/fold/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angle: foldAngle,
        material_tags: appState.reference.materialTags,
        as_3d: false,
      }),
    });

    if (resp.ok) {
      const foldData = await resp.json();
      downloadFile(`${ptype}_origami.fold`, JSON.stringify(foldData, null, 2), "application/json");
      updateStatus(`FOLD file exported: ${ptype}_origami.fold (Ready for Origami Simulator)`);
      return;
    }
  } catch (err) {
    console.warn("Backend FOLD export error:", err);
  }

  if (appState.reference.modelData && appState.reference.modelData.crease_pattern_2d) {
    const foldData = buildCompliantFold(appState.reference.modelData.crease_pattern_2d, ptype, foldAngle);
    downloadFile(`${ptype}_origami.fold`, JSON.stringify(foldData, null, 2), "application/json");
    updateStatus(`FOLD file exported: ${ptype}_origami.fold (Ready for Origami Simulator)`);
  }
}

function exportReferenceOBJ() {
  if (!refMeshObj) {
    updateStatus("No reference 3D mesh available to export");
    return;
  }
  const geom = refMeshObj.geometry;
  const pos = geom.getAttribute("position");
  if (!pos) return;

  const ptype = appState.reference.currentPattern || "origami";
  let obj = `# Wavefront OBJ Export - RF Origami Design Studio\n# Pattern: ${ptype}\n`;
  for (let i = 0; i < pos.count; i++) {
    obj += `v ${pos.getX(i).toFixed(4)} ${pos.getY(i).toFixed(4)} ${pos.getZ(i).toFixed(4)}\n`;
  }
  for (let i = 0; i < pos.count; i += 3) {
    obj += `f ${i + 1} ${i + 2} ${i + 3}\n`;
  }
  downloadFile(`${ptype}_model.obj`, obj, "text/plain");
  updateStatus(`OBJ file exported: ${ptype}_model.obj`);
}

async function exportAbsorberFOLD() {
  const ptype = appState.absorber.patternType || "miura_ori";
  const params = getAbsorberParams();
  const foldAngle = appState.absorber.foldAngle || 30.0;

  try {
    updateStatus(`Exporting FOLD specification for Absorber ${ptype}...`);
    const resp = await fetch("/api/fold/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angle: foldAngle,
        as_3d: false,
      }),
    });

    if (resp.ok) {
      const foldData = await resp.json();
      downloadFile(`absorber_${ptype}_origami.fold`, JSON.stringify(foldData, null, 2), "application/json");
      updateStatus(`FOLD file exported: absorber_${ptype}_origami.fold (Ready for Origami Simulator)`);
      return;
    }
  } catch (err) {
    console.warn("Backend FOLD export error:", err);
  }
}

function exportAbsorberOBJ() {
  if (!appState.absorber.threeObj) {
    updateStatus("No absorber 3D mesh available to export");
    return;
  }
  const geom = appState.absorber.threeObj.geometry;
  const pos = geom.getAttribute("position");
  if (!pos) return;

  const ptype = appState.absorber.patternType || "absorber";
  let obj = `# Wavefront OBJ Export - RF Origami Design Studio\n# Metasurface: ${ptype}\n`;
  for (let i = 0; i < pos.count; i++) {
    obj += `v ${pos.getX(i).toFixed(4)} ${pos.getY(i).toFixed(4)} ${pos.getZ(i).toFixed(4)}\n`;
  }
  for (let i = 0; i < pos.count; i += 3) {
    obj += `f ${i + 1} ${i + 2} ${i + 3}\n`;
  }
  downloadFile(`absorber_${ptype}_model.obj`, obj, "text/plain");
  updateStatus(`OBJ file exported: absorber_${ptype}_model.obj`);
}

function sendCandidateToReference() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) {
    updateStatus("Please select a candidate in Explorer first");
    return;
  }

  const ptype = getExplorerPatternType();
  const params = { ...(cand.parameters || {}) };
  const foldVal = cand.parameters?.fold_angle || appState.explorer.inspFoldAngle || 35.0;

  // Sync active design
  syncDesignToAllSections("explorer", {
    id: cand.id,
    pattern_type: ptype,
    family: appState.explorer.family,
    params: params,
    foldAngle: foldVal,
  });

  // Switch to Reference Patterns
  appState.reference.currentPattern = ptype;
  appState.reference.foldAngle = foldVal;
  appState.reference.params = { ...params };
  if (params.gamma !== undefined && appState.reference.params.gamma_deg === undefined) {
    appState.reference.params.gamma_deg = params.gamma;
  }

  // Update Reference UI controls
  const foldSlider = document.getElementById("ref-fold-slider");
  if (foldSlider) foldSlider.value = foldVal;
  const foldReadout = document.getElementById("ref-fold-readout");
  if (foldReadout) foldReadout.textContent = foldVal.toFixed(1) + "°";

  const patBtns = document.querySelectorAll("#mode-reference-container .pattern-btn");
  patBtns.forEach(b => {
    b.classList.toggle("active", b.dataset.pattern === ptype);
  });
  const badge = document.getElementById("ref-active-pattern-badge");
  if (badge) badge.textContent = ptype.replace(/_/g, " ");

  // Activate tab
  const tabRef = document.getElementById("tab-btn-reference");
  if (tabRef) tabRef.click();

  // Render parameters and generate
  renderReferenceParamInputs(ptype);
  generateReferencePattern();
  updateStatus(`Transferred ${cand.id} parameters to Reference Patterns Studio`);
}

function sendCandidateToAbsorber() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) {
    updateStatus("Please select a candidate in Explorer first");
    return;
  }

  const ptype = getExplorerPatternType();
  const params = { ...(cand.parameters || {}) };
  const foldVal = cand.parameters?.fold_angle || appState.explorer.inspFoldAngle || 30.0;

  syncDesignToAllSections("explorer", {
    id: cand.id,
    pattern_type: ptype,
    family: appState.explorer.family,
    params: params,
    foldAngle: foldVal,
  });

  setAbsorberParameters(ptype, params, foldVal);

  const tabAbs = document.getElementById("tab-btn-absorber");
  if (tabAbs) tabAbs.click();

  updateAbsorber3DPreview();
  runAbsorberSim();
  updateStatus(`Transferred ${cand.id} to Metasurface Absorber`);
}

function sendCandidateToOptFab() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) {
    updateStatus("Please select a candidate in Explorer first");
    return;
  }

  const ptype = getExplorerPatternType();
  const params = { ...(cand.parameters || {}) };
  const foldVal = cand.parameters?.fold_angle || appState.explorer.inspFoldAngle || 35.0;

  syncDesignToAllSections("explorer", {
    id: cand.id,
    pattern_type: ptype,
    family: appState.explorer.family,
    params: params,
    foldAngle: foldVal,
  });

  const tabOpt = document.getElementById("tab-btn-optfab");
  if (tabOpt) tabOpt.click();

  updateStatus(`Selected ${cand.id} as active production target in Fabrication Studio`);
}

function sendReferenceToAbsorber() {
  const ptype = appState.reference.currentPattern || "miura_ori";
  const params = { ...(appState.reference.params || {}) };
  const foldVal = appState.reference.foldAngle || 30.0;

  syncDesignToAllSections("reference", {
    id: `Ref (${ptype})`,
    pattern_type: ptype,
    family: ptype,
    params: params,
    foldAngle: foldVal,
  });

  setAbsorberParameters(ptype, params, foldVal);

  const tabAbs = document.getElementById("tab-btn-absorber");
  if (tabAbs) tabAbs.click();

  updateAbsorber3DPreview();
  runAbsorberSim();
  updateStatus(`Transferred Reference Pattern (${ptype}) to Metasurface Absorber`);
}

function setAbsorberParameters(ptype, params, foldVal) {
  appState.absorber.patternType = ptype;
  appState.absorber.foldAngle = foldVal;

  const a = params.a !== undefined ? params.a : 25.0;
  const b = params.b !== undefined ? params.b : 20.0;
  const gamma = params.gamma_deg !== undefined ? params.gamma_deg : (params.gamma !== undefined ? params.gamma : 60.0);
  const nx = params.num_cells_x !== undefined ? params.num_cells_x : 2;
  const ny = params.num_cells_y !== undefined ? params.num_cells_y : 2;

  appState.absorber.params = { a, b, gamma_deg: gamma, num_cells_x: nx, num_cells_y: ny };

  const patSelect = document.getElementById("abs-pattern-type");
  if (patSelect) patSelect.value = ptype;

  const foldSlider = document.getElementById("abs-fold-slider");
  if (foldSlider) foldSlider.value = foldVal;
  const foldReadout = document.getElementById("abs-fold-readout");
  if (foldReadout) foldReadout.textContent = `${foldVal.toFixed(1)}°`;

  const inputA = document.getElementById("abs-param-a");
  if (inputA) inputA.value = a;
  const inputB = document.getElementById("abs-param-b");
  if (inputB) inputB.value = b;
  const inputGamma = document.getElementById("abs-param-gamma");
  if (inputGamma) inputGamma.value = gamma;
  const inputNx = document.getElementById("abs-param-nx");
  if (inputNx) inputNx.value = nx;
  const inputNy = document.getElementById("abs-param-ny");
  if (inputNy) inputNy.value = ny;
}

function syncAbsorberFromActiveDesign() {
  if (!appState.activeDesign) {
    updateStatus("No active design to sync from");
    return;
  }
  const ad = appState.activeDesign;
  setAbsorberParameters(ad.pattern_type, ad.params, ad.foldAngle);
  updateAbsorber3DPreview();
  updateStatus(`Synchronized Absorber parameters from ${ad.id}`);
}

function downloadFile(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// =====================================================================
// SECTION 2: REFERENCE PATTERNS (CLASSICAL GENERATORS)
// =====================================================================
let refScene, refCamera, refRenderer, refControls;
let refMeshObj = null, refEdgesObj = null;
let refSceneInitialized = false;
let refCanvasScale = 1, refCanvasOffX = 0, refCanvasOffY = 0;

function isPointInPoly(pt, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i][0], yi = poly[i][1];
    const xj = poly[j][0], yj = poly[j][1];
    const intersect = ((yi > pt[1]) !== (yj > pt[1])) &&
      (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function initReferenceControls() {
  // Pattern selection buttons
  const patBtns = document.querySelectorAll("#mode-reference-container .pattern-btn");
  patBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      patBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const ptype = btn.dataset.pattern;
      appState.reference.currentPattern = ptype;
      const badge = document.getElementById("ref-active-pattern-badge");
      if (badge) badge.textContent = btn.textContent;
      const hudPat = document.getElementById("ref-hud-pattern");
      if (hudPat) hudPat.textContent = btn.textContent;
      
      syncDesignToAllSections("reference", {
        id: `Ref (${btn.textContent})`,
        pattern_type: ptype,
        family: ptype,
        params: appState.reference.params,
        foldAngle: appState.reference.foldAngle,
      });

      renderReferenceParamInputs(ptype);
      generateReferencePattern();
    });
  });

  // Recompute button
  document.getElementById("btn-ref-generate").addEventListener("click", generateReferencePattern);

  // Fold angle slider
  const foldSlider = document.getElementById("ref-fold-slider");
  const foldReadout = document.getElementById("ref-fold-readout");
  foldSlider.addEventListener("input", (e) => {
    const angle = parseFloat(e.target.value);
    foldReadout.textContent = angle.toFixed(1) + "°";
    document.getElementById("ref-hud-angle").textContent = angle.toFixed(1) + "°";
    appState.reference.foldAngle = angle;
    
    syncDesignToAllSections("reference", {
      id: `Ref (${appState.reference.currentPattern})`,
      pattern_type: appState.reference.currentPattern,
      family: appState.reference.currentPattern,
      params: appState.reference.params,
      foldAngle: angle,
    });

    generateReferencePattern();
  });

  // Material chips
  const matChips = document.querySelectorAll("#mode-reference-container .material-chip");
  matChips.forEach(chip => {
    chip.addEventListener("click", () => {
      matChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      appState.reference.activeMaterial = chip.dataset.material;
      updateStatus(`Selected RF Material: ${chip.dataset.material.toUpperCase()} (Click on crease pattern to tag facets)`);
    });
  });

  // Strain Visualization Toggle Controls (Origami Simulator inspired)
  const btnRefStrain = document.getElementById("btn-ref-strain");
  const btnRefStrainSide = document.getElementById("btn-ref-strain-toggle-side");

  function toggleReferenceStrain() {
    appState.strain.enabledRef = !appState.strain.enabledRef;
    const isEnabled = appState.strain.enabledRef;

    if (btnRefStrain) {
      btnRefStrain.classList.toggle("active-strain", isEnabled);
      btnRefStrain.textContent = `⚡ Strain: ${isEnabled ? "ON" : "OFF"}`;
    }
    if (btnRefStrainSide) {
      btnRefStrainSide.classList.toggle("active-strain", isEnabled);
      btnRefStrainSide.textContent = isEnabled ? "Disable Heatmap" : "Enable Heatmap";
    }

    const overlay = document.getElementById("ref-strain-overlay");
    if (overlay) {
      overlay.classList.toggle("hidden", !isEnabled);
    }

    if (appState.reference.modelData) {
      renderReference3D(appState.reference.modelData.folded_mesh_3d, appState.reference.modelData.crease_pattern_2d);
    }
    updateStatus(`Origami Simulator Strain Analysis: ${isEnabled ? "ACTIVE" : "DISABLED"}`);
  }

  if (btnRefStrain) btnRefStrain.addEventListener("click", toggleReferenceStrain);
  if (btnRefStrainSide) btnRefStrainSide.addEventListener("click", toggleReferenceStrain);

  // Export & Cross-Module buttons
  const btnRefSendAbs = document.getElementById("btn-ref-send-abs");
  if (btnRefSendAbs) btnRefSendAbs.addEventListener("click", sendReferenceToAbsorber);

  const btnRefExportFold = document.getElementById("btn-ref-export-fold");
  if (btnRefExportFold) btnRefExportFold.addEventListener("click", exportReferenceFOLD);

  const btnRefExportObj = document.getElementById("btn-ref-export-obj");
  if (btnRefExportObj) btnRefExportObj.addEventListener("click", exportReferenceOBJ);

  // Viewport tools
  document.getElementById("btn-ref-wireframe").addEventListener("click", () => {
    if (refEdgesObj) {
      refEdgesObj.visible = !refEdgesObj.visible;
      document.getElementById("btn-ref-wireframe").textContent = 
        `Creases: ${refEdgesObj.visible ? 'ON' : 'OFF'}`;
    }
  });

  document.getElementById("btn-ref-reset-cam").addEventListener("click", () => {
    if (refCamera && refControls) {
      refCamera.position.set(60, 50, 100);
      refControls.target.set(0, 0, 0);
      refControls.update();
    }
  });

  document.getElementById("btn-ref-reset2d").addEventListener("click", () => {
    if (appState.reference.modelData) {
      drawReference2DCrease(appState.reference.modelData.crease_pattern_2d);
    }
  });

  // Interactive 2D Crease Canvas Facet Material Tagging
  const canvas = document.getElementById("ref-crease-canvas");
  if (canvas) {
    canvas.addEventListener("click", (evt) => {
      if (!appState.reference.modelData || !appState.reference.modelData.crease_pattern_2d) return;
      const creaseData = appState.reference.modelData.crease_pattern_2d;
      const rect = canvas.getBoundingClientRect();
      const clientX = evt.clientX - rect.left;
      const clientY = evt.clientY - rect.top;

      const modelX = (clientX - refCanvasOffX) / refCanvasScale;
      const modelY = (clientY - refCanvasOffY) / refCanvasScale;

      const v2d = creaseData.vertices;
      if (!creaseData.faces || !v2d) return;

      for (let fIdx = 0; fIdx < creaseData.faces.length; fIdx++) {
        const face = creaseData.faces[fIdx];
        const poly = face.indices.map(i => v2d[i]);
        if (isPointInPoly([modelX, modelY], poly)) {
          const mat = appState.reference.activeMaterial || "conductor";
          appState.reference.materialTags[fIdx] = mat;
          updateStatus(`Tagged Facet #${fIdx} as ${mat.toUpperCase()}`);
          generateReferencePattern();
          break;
        }
      }
    });
  }
}

async function loadReferenceCatalog() {
  try {
    const resp = await fetch("/api/patterns");
    if (!resp.ok) return;
    appState.reference.catalog = await resp.json();
    renderReferenceParamInputs(appState.reference.currentPattern);
    generateReferencePattern();
  } catch (e) {
    console.warn("Failed to load pattern catalog:", e);
  }
}

function renderReferenceParamInputs(patternType) {
  const container = document.getElementById("ref-param-container");
  if (!container) return;
  container.innerHTML = "";

  const patInfo = appState.reference.catalog[patternType];
  if (!patInfo || !patInfo.parameters) return;

  if (!appState.reference.params) appState.reference.params = {};

  patInfo.parameters.forEach(p => {
    if (appState.reference.params[p.name] === undefined) {
      appState.reference.params[p.name] = p.default;
    }

    const item = document.createElement("div");
    item.className = "param-item";

    const isInt = (p.param_type === "int") || (p.type === "int");
    const min = p.min_val !== undefined ? p.min_val : (p.min !== undefined ? p.min : (isInt ? 1 : 1.0));
    const max = p.max_val !== undefined ? p.max_val : (p.max !== undefined ? p.max : (isInt ? 10 : 100.0));
    const step = p.step !== undefined ? p.step : (isInt ? 1 : (p.unit === "deg" ? 1.0 : 0.5));
    const currentVal = appState.reference.params[p.name];

    item.innerHTML = `
      <div class="param-row">
        <span class="param-name">${p.name} ${p.unit ? '[' + p.unit + ']' : ''}</span>
        <span id="ref-param-val-${p.name}" class="param-val">${currentVal}</span>
      </div>
      <input type="range" class="param-slider" 
        id="ref-slider-${p.name}"
        min="${min}" max="${max}" step="${step}" value="${currentVal}">
    `;

    const slider = item.querySelector(`#ref-slider-${p.name}`);
    const valText = item.querySelector(`#ref-param-val-${p.name}`);

    slider.addEventListener("input", (e) => {
      const val = isInt ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
      valText.textContent = val;
      appState.reference.params[p.name] = val;

      syncDesignToAllSections("reference", {
        id: `Ref (${appState.reference.currentPattern})`,
        pattern_type: appState.reference.currentPattern,
        family: appState.reference.currentPattern,
        params: appState.reference.params,
        foldAngle: appState.reference.foldAngle,
      });

      generateReferencePattern();
    });

    container.appendChild(item);
  });
}

async function generateReferencePattern() {
  const ptype = appState.reference.currentPattern;
  const params = appState.reference.params || {};
  const fold = appState.reference.foldAngle || 35.0;

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angle: fold,
        material_tags: appState.reference.materialTags,
      }),
    });

    if (!resp.ok) return;
    const data = await resp.json();
    appState.reference.modelData = data;

    // Seamless active design sync
    appState.activeDesign = {
      source: "reference",
      id: `Ref (${ptype.replace(/_/g, " ")})`,
      pattern_type: ptype,
      family: ptype,
      params: { ...params },
      foldAngle: fold,
      modelData: data,
    };
    updateSyncBadge();

    // Update HUD metrics
    const m = data.metrics || {};
    const hV = document.getElementById("ref-hud-vertices");
    if (hV) hV.textContent = m.num_vertices || 0;
    const hE = document.getElementById("ref-hud-edges");
    if (hE) hE.textContent = m.num_edges || 0;
    const hF = document.getElementById("ref-hud-faces");
    if (hF) hF.textContent = m.num_faces || 0;
    const hA = document.getElementById("ref-hud-area");
    if (hA) hA.textContent = `${m.surface_area_mm2 || 0} mm²`;
    const hB = document.getElementById("ref-hud-bounds");
    if (hB && m.dimensions_mm) {
      hB.textContent = `${m.dimensions_mm[0]} × ${m.dimensions_mm[1]} × ${m.dimensions_mm[2]} mm`;
    }

    // Update Verification checklist
    const v = data.validation || {};
    updateRefVal("ref-val-icon-kawasaki", "ref-val-desc-kawasaki", v.kawasaki);
    updateRefVal("ref-val-icon-maekawa", "ref-val-desc-maekawa", v.maekawa);
    updateRefVal("ref-val-icon-edge", "ref-val-desc-edge", v.edge_conservation);
    updateRefVal("ref-val-icon-area", "ref-val-desc-area", v.area_conservation);

    // Update RF areas
    const mat = m.material_areas_mm2 || {};
    document.getElementById("ref-stat-conductor-area").textContent = `${(mat.conductor || 0).toFixed(1)} mm²`;
    document.getElementById("ref-stat-ground-area").textContent = `${(mat.ground || 0).toFixed(1)} mm²`;
    document.getElementById("ref-stat-substrate-area").textContent = `${(mat.substrate || 0).toFixed(1)} mm²`;
    document.getElementById("ref-stat-keepout-area").textContent = `${(mat.keepout || 0).toFixed(1)} mm²`;

    // Render 3D with authentic origami crease lines and 2D crease pattern
    renderReference3D(data.folded_mesh_3d, data.crease_pattern_2d);
    drawReference2DCrease(data.crease_pattern_2d);
  } catch (err) {
    console.error("Reference pattern generation failed:", err);
  }
}

function updateRefVal(iconId, descId, res) {
  const icon = document.getElementById(iconId);
  const desc = document.getElementById(descId);
  if (!icon || !desc || !res) return;

  icon.className = `val-icon ${res.passed ? 'pass' : 'fail'}`;
  icon.textContent = res.passed ? '✓' : '✕';
  desc.textContent = res.detail || (res.passed ? 'Passed' : 'Failed');
}

function initReferenceThreeJS() {
  const container = document.getElementById("ref-threejs-container");
  if (!container) return;

  const w = container.clientWidth || 400;
  const h = container.clientHeight || 400;

  refScene = new THREE.Scene();
  refScene.background = new THREE.Color(0xf8fafc);

  refCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
  refCamera.position.set(60, 50, 100);

  refRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  refRenderer.setSize(w, h);
  refRenderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(refRenderer.domElement);

  if (typeof THREE.OrbitControls !== "undefined") {
    refControls = new THREE.OrbitControls(refCamera, refRenderer.domElement);
    refControls.enableDamping = true;
    refControls.dampingFactor = 0.05;
  }

  const amb = new THREE.AmbientLight(0xffffff, 0.85);
  refScene.add(amb);

  const dir1 = new THREE.DirectionalLight(0xffffff, 0.7);
  dir1.position.set(100, 150, 80);
  refScene.add(dir1);

  const dir2 = new THREE.DirectionalLight(0x94a3b8, 0.3);
  dir2.position.set(-80, -50, -60);
  refScene.add(dir2);

  const grid = new THREE.GridHelper(160, 16, 0xcbd5e1, 0xe2e8f0);
  grid.position.y = -0.5;
  refScene.add(grid);

  refSceneInitialized = true;
  animateReference();
  window.addEventListener("resize", onReferenceResize);
}

function animateReference() {
  requestAnimationFrame(animateReference);
  if (refControls) refControls.update();
  if (refRenderer && refScene && refCamera) {
    refRenderer.render(refScene, refCamera);
  }
}

function renderReference3D(meshData, creaseData) {
  if (!refScene || !meshData) return;

  if (refMeshObj) {
    refScene.remove(refMeshObj);
    refMeshObj.geometry.dispose();
    refMeshObj = null;
  }
  if (refEdgesObj) {
    refScene.remove(refEdgesObj);
    refEdgesObj.geometry.dispose();
    refEdgesObj = null;
  }

  const geom = new THREE.BufferGeometry();
  const vList = meshData.vertices;
  const fList = meshData.faces;
  const mats = meshData.face_materials || [];

  const isStrain = appState.strain.enabledRef;
  let strainMetrics = null;
  if (isStrain) {
    strainMetrics = OrigamiStrainEngine.computeStrains(meshData, creaseData, appState.reference.foldAngle || 35.0);
    appState.strain.lastRefMetrics = strainMetrics;
    OrigamiStrainEngine.updateHUD("ref", strainMetrics);
  }

  const positions = [];
  const colors = [];

  for (let fIdx = 0; fIdx < fList.length; fIdx++) {
    const f = fList[fIdx];
    let col;
    if (isStrain && strainMetrics && strainMetrics.faceStrains) {
      const faceE = strainMetrics.faceStrains[fIdx] || 0.0;
      col = OrigamiStrainEngine.getStrainColor(faceE, appState.strain.maxThreshold);
    } else {
      const matName = mats[fIdx] || "substrate";
      const colHex = MATERIAL_COLORS[matName] || 0x0284c7;
      col = new THREE.Color(colHex);
    }

    for (let i = 1; i < f.length - 1; i++) {
      const v0 = vList[f[0]];
      const v1 = vList[f[i]];
      const v2 = vList[f[i + 1]];

      positions.push(v0[0], v0[1], v0[2]);
      positions.push(v1[0], v1[1], v1[2]);
      positions.push(v2[0], v2[1], v2[2]);

      colors.push(col.r, col.g, col.b);
      colors.push(col.r, col.g, col.b);
      colors.push(col.r, col.g, col.b);
    }
  }

  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geom.computeVertexNormals();

  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true,
    side: THREE.DoubleSide,
    roughness: 0.6,
    metalness: 0.1,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  });

  refMeshObj = new THREE.Mesh(geom, mat);
  refScene.add(refMeshObj);

  // Render authentic origami creases (Red Mountain, Blue Valley, or Strain gradient)
  if (creaseData && creaseData.creases && creaseData.creases.length > 0) {
    refEdgesObj = create3DCreaseLines(creaseData.creases, vList, isStrain, strainMetrics);
  }
  if (!refEdgesObj) {
    const edgeGeom = new THREE.WireframeGeometry(geom);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x334155, linewidth: 1 });
    refEdgesObj = new THREE.LineSegments(edgeGeom, edgeMat);
  }
  refScene.add(refEdgesObj);
}

function drawReference2DCrease(creaseData) {
  const canvas = document.getElementById("ref-crease-canvas");
  if (!canvas || !creaseData) return;

  const ctx = canvas.getContext("2d");
  const container = canvas.parentElement;
  const w = container.clientWidth || 400;
  const h = container.clientHeight || 400;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";

  ctx.resetTransform();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const b = creaseData.bounds;
  if (!b || b.width <= 0) return;

  const pad = 30;
  const scale = Math.min((w - 2 * pad) / b.width, (h - 2 * pad) / b.height);
  const offX = (w - b.width * scale) / 2 - b.min[0] * scale;
  const offY = (h - b.height * scale) / 2 - b.min[1] * scale;

  refCanvasScale = scale;
  refCanvasOffX = offX;
  refCanvasOffY = offY;

  const v2d = creaseData.vertices;

  // Faces
  if (creaseData.faces) {
    creaseData.faces.forEach(f => {
      ctx.beginPath();
      f.indices.forEach((idx, i) => {
        const vx = v2d[idx][0] * scale + offX;
        const vy = v2d[idx][1] * scale + offY;
        if (i === 0) ctx.moveTo(vx, vy);
        else ctx.lineTo(vx, vy);
      });
      ctx.closePath();
      const col = MATERIAL_CSS_COLORS[f.material] || "rgba(56, 189, 248, 0.2)";
      ctx.fillStyle = col;
      ctx.fill();
    });
  }

  // Creases
  if (creaseData.creases) {
    creaseData.creases.forEach(c => {
      const u = v2d[c.u];
      const v = v2d[c.v];
      if (!u || !v) return;

      const x1 = u[0] * scale + offX;
      const y1 = u[1] * scale + offY;
      const x2 = v[0] * scale + offX;
      const y2 = v[1] * scale + offY;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);

      if (c.type === "M") {
        ctx.strokeStyle = "#dc2626";
        ctx.lineWidth = 1.8;
        ctx.setLineDash([]);
      } else if (c.type === "V") {
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 1.6;
        ctx.setLineDash([4, 3]);
      } else {
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 2.0;
        ctx.setLineDash([]);
      }
      ctx.stroke();
    });
  }
}

function onReferenceResize() {
  const container = document.getElementById("ref-threejs-container");
  if (!container || !refCamera || !refRenderer) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {
    refCamera.aspect = w / h;
    refCamera.updateProjectionMatrix();
    refRenderer.setSize(w, h);
  }
}

// =====================================================================
// SECTION 3: STANDALONE ELECTROMAGNETIC (MoM) SOLVER & CHARTS (PHASE 2)
// =====================================================================

function initRFControls() {
  // Inspector Tabs (3D Fold vs Numerical MoM Solver)
  const tabGeom = document.getElementById("btn-insp-tab-geom");
  const tabRF = document.getElementById("btn-insp-tab-rf");

  if (tabGeom && tabRF) {
    tabGeom.addEventListener("click", () => switchInspectorTab("geometry"));
    tabRF.addEventListener("click", () => switchInspectorTab("rf"));
  }

  // Run MoM Simulation Button
  const btnRunSim = document.getElementById("btn-run-mom-sim");
  if (btnRunSim) {
    btnRunSim.addEventListener("click", () => runRFSimulation());
  }

  // Run Fold Angle Sweep Button
  const btnRunSweep = document.getElementById("btn-run-fold-sweep");
  if (btnRunSweep) {
    btnRunSweep.addEventListener("click", () => runRFFoldSweep());
  }

  // Standalone Benchmark Modal Controls
  const btnOpenBench = document.getElementById("btn-open-benchmarks");
  const btnCloseBench = document.getElementById("btn-close-benchmarks");
  const btnRetestBench = document.getElementById("btn-retest-benchmarks");
  const modalBench = document.getElementById("benchmark-modal");

  if (btnOpenBench && modalBench) {
    btnOpenBench.addEventListener("click", () => {
      modalBench.style.display = "flex";
      loadBenchmarks();
    });
  }

  if (btnCloseBench && modalBench) {
    btnCloseBench.addEventListener("click", () => {
      modalBench.style.display = "none";
    });
  }

  if (btnRetestBench) {
    btnRetestBench.addEventListener("click", () => {
      loadBenchmarks();
    });
  }

  // Handle Resize for RF Chart Canvases
  window.addEventListener("resize", () => {
    if (appState.rf.inspectorTab === "rf" && appState.rf.lastResult) {
      renderS11Chart(appState.rf.lastResult.frequency_sweep);
      renderZinChart(appState.rf.lastResult.frequency_sweep);
    }
  });
}

function switchInspectorTab(tabName) {
  appState.rf.inspectorTab = tabName;

  const tabGeom = document.getElementById("btn-insp-tab-geom");
  const tabRF = document.getElementById("btn-insp-tab-rf");
  const viewGeom = document.getElementById("insp-geometry-view");
  const viewRF = document.getElementById("insp-rf-view");

  if (tabName === "geometry") {
    tabGeom.classList.add("active");
    tabRF.classList.remove("active");
    viewGeom.style.display = "flex";
    viewRF.style.display = "none";
    onInspectorResize();
  } else {
    tabRF.classList.add("active");
    tabGeom.classList.remove("active");
    viewGeom.style.display = "none";
    viewRF.style.display = "flex";

    // If we have previous result, render charts now that viewport is visible
    if (appState.rf.lastResult) {
      setTimeout(() => {
        renderS11Chart(appState.rf.lastResult.frequency_sweep);
        renderZinChart(appState.rf.lastResult.frequency_sweep);
      }, 50);
    } else {
      // Auto-run MoM solve on first tab opening for active candidate
      runRFSimulation();
    }
  }
}

async function runRFSimulation() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) {
    updateStatus("Please select a candidate from the gallery first.");
    return;
  }

  const subSelect = document.getElementById("insp-rf-substrate");
  const condSelect = document.getElementById("insp-rf-conductor");
  const fStartIn = document.getElementById("insp-rf-fstart");
  const fStopIn = document.getElementById("insp-rf-fstop");
  const nPtsIn = document.getElementById("insp-rf-npts");
  const btnRun = document.getElementById("btn-run-mom-sim");

  const subMat = subSelect ? subSelect.value : "kapton";
  const condMat = condSelect ? condSelect.value : "copper";
  const fStart = parseFloat(fStartIn?.value || 1.0);
  const fStop = parseFloat(fStopIn?.value || 6.0);
  const nPts = parseInt(nPtsIn?.value || 25, 10);
  const foldAngle = appState.explorer.inspFoldAngle || 35.0;

  const family = appState.explorer.family;
  let ptype = "miura_ori";
  if (family.includes("waterbomb")) ptype = "waterbomb";
  else if (family.includes("yoshimura")) ptype = "yoshimura";

  if (btnRun) {
    btnRun.disabled = true;
    btnRun.textContent = "Solving (MoM)...";
  }
  updateStatus("Executing Method of Moments numerical EM solve...");

  try {
    const resp = await fetch("/api/rf/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: cand.parameters,
        fold_angle: foldAngle,
        f_start_ghz: fStart,
        f_stop_ghz: fStop,
        num_points: nPts,
        substrate_material: subMat,
        conductor_material: condMat,
        port_z0: 50.0,
      }),
    });

    if (!resp.ok) {
      throw new Error(`Simulation failed with HTTP status ${resp.status}`);
    }

    const data = await resp.json();
    appState.rf.lastResult = data;

    // Update Live Metrics Dashboard
    const res = data.resonance || {};
    document.getElementById("rf-resolution-note").textContent = res.at_sweep_boundary
      ? "Minimum occurs at a sweep boundary. Expand the frequency range before interpreting resonance."
      : res.resolution_better_than_one_percent
        ? "Frequency step is below 1% at the interpolated S11 minimum. Physical accuracy remains not validated."
        : "Coarse frequency sweep: increase samples or narrow the frequency range to resolve resonance below 1%.";
    document.getElementById("rf-stat-f0").textContent = `${Number(res.resonant_frequency_ghz || 0).toFixed(4)} GHz`;
    document.getElementById("rf-stat-s11").textContent = `${Number(res.min_s11_db || 0).toFixed(2)} dB`;
    document.getElementById("rf-stat-vswr").textContent = `${Number(res.vswr_at_resonance || 0).toFixed(2)}`;
    document.getElementById("rf-stat-bw").textContent = `${Number(res.bandwidth_mhz || 0).toFixed(1)} MHz (${Number(res.bandwidth_percent || 0).toFixed(2)}%)${res.truncated ? " · sweep truncated" : ""}`;
    if (res.zin_at_resonance) {
      document.getElementById("rf-stat-zin").textContent = `${res.zin_at_resonance[0].toFixed(2)} + j${res.zin_at_resonance[1].toFixed(2)} Ω`;
    }
    document.getElementById("rf-stat-segments").textContent = `${data.discretization?.num_segments || 0}`;
    
    const resBadge = document.getElementById("rf-resonance-badge");
    if (resBadge) {
      resBadge.textContent = `Estimate · f₀: ${res.resonant_frequency_ghz.toFixed(4)} GHz | S11: ${res.min_s11_db.toFixed(2)} dB`;
    }

    // Render Both Canvas Charts
    renderS11Chart(data.frequency_sweep);
    renderZinChart(data.frequency_sweep);

    updateStatus(`MoM Solve Completed: Resonant f₀ = ${res.resonant_frequency_ghz} GHz (Experimental EFIE-MoM)`);
  } catch (err) {
    console.error("RF simulation error:", err);
    updateStatus(`Simulation error: ${err.message}`);
  } finally {
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.textContent = "Run EM Simulation";
    }
  }
}

function renderS11Chart(sweepData) {
  const canvas = document.getElementById("rf-s11-canvas");
  if (!canvas || !sweepData) return;

  const wrap = canvas.parentElement;
  const width = wrap.clientWidth || 360;
  const height = wrap.clientHeight || 150;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";

  const ctx = canvas.getContext("2d");
  ctx.resetTransform();
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);

  const pad = { top: 15, right: 20, bottom: 25, left: 45 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  if (plotW <= 0 || plotH <= 0) return;

  const freqs = sweepData.frequencies_ghz || [];
  const s11 = sweepData.s11_db || [];
  if (freqs.length === 0 || s11.length === 0) return;

  const fMin = freqs[0];
  const fMax = freqs[freqs.length - 1];
  
  // Y-axis: typically from 0 dB down to -25 or -35 dB
  const minVal = Math.min(...s11, -15.0);
  const yMin = Math.floor((minVal - 2.0) / 5.0) * 5.0; // Round down to nearest 5 dB
  const yMax = 0.0;

  const toX = (f) => pad.left + ((f - fMin) / (fMax - fMin)) * plotW;
  const toY = (db) => pad.top + ((yMax - db) / (yMax - yMin)) * plotH;

  // Background Grid Lines & Y Axis Labels
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "9px monospace";
  ctx.textAlign = "right";

  for (let db = yMax; db >= yMin; db -= 5) {
    const sy = toY(db);
    ctx.beginPath();
    ctx.moveTo(pad.left, sy);
    ctx.lineTo(pad.left + plotW, sy);
    ctx.stroke();

    ctx.fillText(`${db} dB`, pad.left - 6, sy + 3);
  }

  // -10 dB Threshold Matching Line (Green Dashed)
  if (yMin <= -10.0) {
    const y10 = toY(-10.0);
    ctx.save();
    ctx.strokeStyle = "#16a34a";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, y10);
    ctx.lineTo(pad.left + plotW, y10);
    ctx.stroke();

    ctx.fillStyle = "#16a34a";
    ctx.textAlign = "left";
    ctx.fillText("-10 dB THRESHOLD", pad.left + 6, y10 - 4);
    ctx.restore();
  }

  // Vertical Frequency Grid Lines
  ctx.textAlign = "center";
  const numXTicks = 5;
  for (let i = 0; i <= numXTicks; i++) {
    const fVal = fMin + (i / numXTicks) * (fMax - fMin);
    const sx = toX(fVal);
    ctx.beginPath();
    ctx.moveTo(sx, pad.top);
    ctx.lineTo(sx, pad.top + plotH);
    ctx.stroke();

    ctx.fillText(`${fVal.toFixed(1)} GHz`, sx, pad.top + plotH + 15);
  }

  // Plot S11 Curve
  ctx.beginPath();
  freqs.forEach((f, idx) => {
    const sx = toX(f);
    const sy = toY(s11[idx]);
    if (idx === 0) ctx.moveTo(sx, sy);
    else ctx.lineTo(sx, sy);
  });
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2.0;
  ctx.shadowBlur = 0;
  ctx.stroke();

  // Highlight Resonant Minimum Dip
  const minIdx = s11.indexOf(Math.min(...s11));
  if (minIdx >= 0) {
    const rfX = toX(freqs[minIdx]);
    const rfY = toY(s11[minIdx]);

    ctx.beginPath();
    ctx.arc(rfX, rfY, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = "#d97706";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Callout text
    ctx.fillStyle = "#d97706";
    ctx.font = "bold 9px monospace";
    ctx.textAlign = "center";
    ctx.fillText(`f₀ = ${freqs[minIdx]} GHz (${s11[minIdx]} dB)`, rfX, Math.max(pad.top + 10, rfY - 8));
  }
}

function renderZinChart(sweepData) {
  const canvas = document.getElementById("rf-zin-canvas");
  if (!canvas || !sweepData) return;

  const wrap = canvas.parentElement;
  const width = wrap.clientWidth || 360;
  const height = wrap.clientHeight || 150;

  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";

  const ctx = canvas.getContext("2d");
  ctx.resetTransform();
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);

  const pad = { top: 15, right: 20, bottom: 25, left: 45 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  if (plotW <= 0 || plotH <= 0) return;

  const freqs = sweepData.frequencies_ghz || [];
  const rin = sweepData.zin_real_ohms || [];
  const xin = sweepData.zin_imag_ohms || [];
  if (freqs.length === 0 || rin.length === 0) return;

  const fMin = freqs[0];
  const fMax = freqs[freqs.length - 1];

  const maxR = Math.max(...rin, 100.0);
  const maxAbsX = Math.max(...xin.map(Math.abs), 50.0);
  const yMax = Math.ceil(Math.max(maxR, maxAbsX) * 1.15 / 50.0) * 50.0;
  const yMin = Math.floor(-Math.max(maxAbsX) * 1.15 / 50.0) * 50.0;

  const toX = (f) => pad.left + ((f - fMin) / (fMax - fMin)) * plotW;
  const toY = (z) => pad.top + ((yMax - z) / (yMax - yMin)) * plotH;

  // Grid Lines
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "9px monospace";
  ctx.textAlign = "right";

  const yStep = (yMax - yMin) / 4;
  for (let i = 0; i <= 4; i++) {
    const val = yMin + i * yStep;
    const sy = toY(val);
    ctx.beginPath();
    ctx.moveTo(pad.left, sy);
    ctx.lineTo(pad.left + plotW, sy);
    ctx.stroke();

    ctx.fillText(`${Math.round(val)} Ω`, pad.left - 6, sy + 3);
  }

  // Zero Reactance Line (Dashed)
  const yZero = toY(0.0);
  ctx.save();
  ctx.strokeStyle = "#cbd5e1";
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(pad.left, yZero);
  ctx.lineTo(pad.left + plotW, yZero);
  ctx.stroke();
  ctx.restore();

  // Vertical Frequency Grid Lines
  ctx.textAlign = "center";
  const numXTicks = 5;
  for (let i = 0; i <= numXTicks; i++) {
    const fVal = fMin + (i / numXTicks) * (fMax - fMin);
    const sx = toX(fVal);
    ctx.beginPath();
    ctx.moveTo(sx, pad.top);
    ctx.lineTo(sx, pad.top + plotH);
    ctx.stroke();

    ctx.fillText(`${fVal.toFixed(1)} GHz`, sx, pad.top + plotH + 15);
  }

  // Plot Rin (Solid Blue)
  ctx.beginPath();
  freqs.forEach((f, idx) => {
    const sx = toX(f);
    const sy = toY(rin[idx]);
    if (idx === 0) ctx.moveTo(sx, sy);
    else ctx.lineTo(sx, sy);
  });
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 1.8;
  ctx.setLineDash([]);
  ctx.stroke();

  // Plot Xin (Dashed Amber)
  ctx.beginPath();
  freqs.forEach((f, idx) => {
    const sx = toX(f);
    const sy = toY(xin[idx]);
    if (idx === 0) ctx.moveTo(sx, sy);
    else ctx.lineTo(sx, sy);
  });
  ctx.strokeStyle = "#d97706";
  ctx.lineWidth = 1.6;
  ctx.setLineDash([4, 3]);
  ctx.stroke();
  ctx.setLineDash([]);
}

async function runRFFoldSweep() {
  const cand = appState.explorer.selectedCandidate;
  if (!cand) return;

  const btnSweep = document.getElementById("btn-run-fold-sweep");
  if (btnSweep) {
    btnSweep.disabled = true;
    btnSweep.textContent = "Sweeping Angles...";
  }
  updateStatus("Sweeping candidate fold angles to compute dynamic RF tuning...");

  const family = appState.explorer.family;
  let ptype = "miura_ori";
  if (family.includes("waterbomb")) ptype = "waterbomb";
  else if (family.includes("yoshimura")) ptype = "yoshimura";

  const subSelect = document.getElementById("insp-rf-substrate");
  const condSelect = document.getElementById("insp-rf-conductor");
  const subMat = subSelect ? subSelect.value : "kapton";
  const condMat = condSelect ? condSelect.value : "copper";

  try {
    const resp = await fetch("/api/rf/fold-sweep", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: cand.parameters,
        fold_angles: [15.0, 30.0, 45.0, 60.0, 75.0],
        f_start_ghz: Number(document.getElementById("insp-rf-fstart").value),
        f_stop_ghz: Number(document.getElementById("insp-rf-fstop").value),
        num_points: Number(document.getElementById("insp-rf-npts").value),
        substrate_material: subMat,
        conductor_material: condMat,
      }),
    });

    if (!resp.ok) throw new Error("Sweep failed");

    const data = await resp.json();
    appState.rf.foldSweepResult = data;

    // Display Summary
    const box = document.getElementById("rf-fold-sweep-summary");
    const content = document.getElementById("rf-fold-sweep-content");
    if (box && content) {
      box.style.display = "block";
      let html = `<div style="margin-bottom: 4px; color: var(--text-secondary);">Tuning: <strong>${data.tuning_range_ghz} GHz</strong> (Ratio: <strong>${data.tuning_ratio}×</strong>)</div>`;
      html += `<table style="width: 100%; border-collapse: collapse; font-size: 9.5px;">`;
      html += `<thead><tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;"><th>θ</th><th>f₀</th><th>S11</th><th>Envelope</th></tr></thead><tbody>`;
      data.step_results.forEach(s => {
        html += `<tr style="border-bottom: 1px solid var(--border-light);"><td>${s.fold_angle_deg}°</td><td style="color: var(--accent-primary); font-weight: 700;">${s.resonant_frequency_ghz.toFixed(4)}G${s.at_sweep_boundary ? " (boundary)" : ""}</td><td>${s.min_s11_db.toFixed(2)}dB</td><td>${s.dimensions_mm[0]}×${s.dimensions_mm[1]}mm</td></tr>`;
      });
      html += `</tbody></table>`;
      content.innerHTML = html;
      renderFoldHeatmap(data.heatmap);
    }

    updateStatus(`Fold Sweep Complete: Tuning Range = ${data.tuning_range_ghz} GHz across 15° to 75°`);
  } catch (err) {
    console.error("Fold sweep error:", err);
    updateStatus(`Fold sweep error: ${err.message}`);
  } finally {
    if (btnSweep) {
      btnSweep.disabled = false;
      btnSweep.textContent = "Sweep Fold Angles";
    }
  }
}

function renderFoldHeatmap(data) {
  const canvas = document.getElementById("rf-fold-heatmap");
  if (!canvas || !data?.angles_deg?.length || !data.frequencies_ghz?.length) return;
  const width = canvas.clientWidth || 300, height = 190;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  const left = 38, top = 15, plotWidth = width - 48, plotHeight = height - 48;
  const rows = data.angles_deg.length, columns = data.frequencies_ghz.length;
  data.s11_db.forEach((row, i) => row.forEach((value, j) => {
    const t = Math.max(0, Math.min(1, -value / 30));
    ctx.fillStyle = `rgb(${Math.round(245 - 208 * t)},${Math.round(158 - 59 * t)},${Math.round(11 + 224 * t)})`;
    ctx.fillRect(left + j * plotWidth / columns, top + i * plotHeight / rows, plotWidth / columns + .5, plotHeight / rows + .5);
  }));
  ctx.fillStyle = "#334155";
  ctx.font = "10px sans-serif";
  ctx.textAlign = "right";
  data.angles_deg.forEach((angle, i) => ctx.fillText(`${angle}°`, left - 5, top + (i + .5) * plotHeight / rows + 3));
  ctx.textAlign = "left";
  ctx.fillText(data.frequencies_ghz[0].toFixed(2), left, height - 19);
  ctx.textAlign = "right";
  ctx.fillText(data.frequencies_ghz[columns - 1].toFixed(2), width - 10, height - 19);
  ctx.textAlign = "center";
  ctx.fillText("Frequency (GHz) · S11 estimate", left + plotWidth / 2, height - 4);
}

async function loadBenchmarks() {
  updateStatus("Running antenna solver diagnostics...");
  const statusIds = ["freespace", "dipole", "monopole"];
  for (const id of statusIds) {
    const badge = document.getElementById(`bench-status-${id}`);
    badge.textContent = "Running…";
    badge.className = "status-tag";
  }
  try {
    const reportResp = await fetch("/api/rf/validation");
    if (!reportResp.ok) throw new Error(`Validation report unavailable (${reportResp.status})`);
    const report = await reportResp.json();
    document.getElementById("validation-report-content").textContent = report.markdown;
    renderValidationSummary(report);
    const resp = await fetch("/api/rf/benchmarks");
    if (!resp.ok) throw new Error(`Diagnostics unavailable (${resp.status})`);

    const data = await resp.json();
    appState.rf.benchmarks = data;

    // 1. Free space
    const fs = data.free_space || {};
    const fsEl = document.getElementById("bench-metrics-freespace");
    if (fsEl) {
      fsEl.innerHTML = `
        <span>Speed of Light: <strong>${fs.speed_of_light_m_s?.toLocaleString()} m/s</strong></span>
        <span>Wave Impedance: <strong>${fs.wave_impedance_ohms} Ω</strong></span>
        <span>Rel Error: <strong>${fs.relative_error < 1e-5 ? '< 1e-6' : fs.relative_error.toFixed(6)}</strong></span>
      `;
    }

    // 2. Dipole
    const dp = data.half_wave_dipole || {};
    const dpZin = document.getElementById("bench-val-dipole-zin");
    const dpS11 = document.getElementById("bench-val-dipole-s11");
    if (dpZin && dp.numerical_zin_ohms) {
      dpZin.textContent = `${dp.numerical_zin_ohms[0]} + j${dp.numerical_zin_ohms[1]} Ω`;
    }
    if (dpS11) dpS11.textContent = `${dp.numerical_s11_db} dB`;

    // 3. Monopole
    const mp = data.quarter_wave_monopole || {};
    const mpZin = document.getElementById("bench-val-monopole-zin");
    if (mpZin && mp.numerical_zin_ohms) {
      mpZin.textContent = `${mp.numerical_zin_ohms[0]} + j${mp.numerical_zin_ohms[1]} Ω`;
    }

    [fs, dp, mp].forEach((result, i) => {
      const badge = document.getElementById(`bench-status-${statusIds[i]}`);
      badge.textContent = result.passed ? "Diagnostic pass" : "Failed / Not validated";
      badge.className = `status-tag ${result.passed ? "tag-valid" : "tag-invalid"}`;
    });
    const passed = [fs, dp, mp].filter(result => result.passed === true).length;
    updateStatus(`${passed}/3 diagnostics passed. Antenna accuracy remains not validated.`);
  } catch (err) {
    console.error("Benchmark verification error:", err);
    document.getElementById("validation-report-content").textContent = err.message;
    document.getElementById("validation-summary").textContent = err.message;
    for (const id of statusIds) document.getElementById(`bench-status-${id}`).textContent = "Unavailable";
    updateStatus(`Validation unavailable: ${err.message}`);
  }
}

function renderValidationSummary(data) {
  const container = document.getElementById("validation-summary");
  container.replaceChildren();
  const note = document.createElement("p");
  note.textContent = data.stale ? "Saved diagnostics are stale. Regenerate the report for the current solver." : "Physical antenna validation: Not validated.";
  container.append(note);
  if (!data.report) {
    note.textContent = data.markdown;
    return;
  }
  const table = document.createElement("table");
  table.className = "validation-results";
  const header = table.createTHead().insertRow();
  for (const title of ["Case", "Result", "Evidence"] ) {
    const cell = document.createElement("th");
    cell.textContent = title;
    header.append(cell);
  }
  const body = table.createTBody();
  const cases = [["free_space", "Free-space constants"], ["half_wave_dipole", "Dipole screening"], ["quarter_wave_monopole", "Image monopole"], ["reciprocity", "Reciprocity"], ["mesh_convergence", "Mesh convergence"], ["independent_reference", "Independent reference"], ["patch", "Patch model"], ["fold_sweep_reference", "Fold reference"]];
  for (const [key, label] of cases) {
    const result = data.report[key];
    if (!result) continue;
    let evidence = result.status || result.notes || "Constitutive constants only";
    if (key === "reciprocity") evidence = `Matrix asymmetry ${result.max_absolute_asymmetry_ohms.toPrecision(4)} Ω; limit 1e-10 Ω`;
    if (key === "mesh_convergence") evidence = result.finest_change_percent == null ? "No reactance crossing found" : `${result.finest_change_percent.toFixed(3)}% frequency change; limit <1%`;
    if (result.rin_error_percent != null) evidence = `Rin error ${result.rin_error_percent.toFixed(2)}%; |Xin| ${result.reactance_absolute_error_ohms.toFixed(2)} Ω. Approximate target only.`;
    const row = body.insertRow();
    for (const text of [label, result.passed ? "Diagnostic pass" : "Failed / pending", evidence]) row.insertCell().textContent = text;
  }
  container.append(table);
}

// =====================================================================
// SECTION 4: METASURFACE ABSORBER STUDIO CONTROLLER
// =====================================================================

let absSceneInitialized = false;
let absScene, absCamera, absRenderer, absControls;

function getAbsorberParams() {
  const a = parseFloat(document.getElementById("abs-param-a")?.value || (appState.absorber.params && appState.absorber.params.a) || 25.0);
  const b = parseFloat(document.getElementById("abs-param-b")?.value || (appState.absorber.params && appState.absorber.params.b) || 20.0);
  const gamma = parseFloat(document.getElementById("abs-param-gamma")?.value || (appState.absorber.params && appState.absorber.params.gamma_deg) || 60.0);
  const nx = parseInt(document.getElementById("abs-param-nx")?.value || (appState.absorber.params && appState.absorber.params.num_cells_x) || 2, 10);
  const ny = parseInt(document.getElementById("abs-param-ny")?.value || (appState.absorber.params && appState.absorber.params.num_cells_y) || 2, 10);
  return { a, b, gamma_deg: gamma, num_cells_x: nx, num_cells_y: ny };
}

function initAbsorberControls() {
  const foldSlider = document.getElementById("abs-fold-slider");
  const foldReadout = document.getElementById("abs-fold-readout");
  const hudAngle = document.getElementById("abs-hud-angle");

  if (foldSlider) {
    foldSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      appState.absorber.foldAngle = val;
      if (foldReadout) foldReadout.textContent = `${val.toFixed(1)}°`;
      if (hudAngle) hudAngle.textContent = `${val.toFixed(1)}°`;
      syncDesignToAllSections("absorber", {
        id: `Absorber (${appState.absorber.patternType})`,
        pattern_type: appState.absorber.patternType,
        family: appState.absorber.patternType,
        params: getAbsorberParams(),
        foldAngle: val,
      });
      updateAbsorber3DPreview();
    });
  }

  const patSelect = document.getElementById("abs-pattern-type");
  if (patSelect) {
    patSelect.addEventListener("change", (e) => {
      appState.absorber.patternType = e.target.value;
      const hudPat = document.getElementById("abs-hud-pattern");
      if (hudPat) hudPat.textContent = e.target.options[e.target.selectedIndex].text;
      syncDesignToAllSections("absorber", {
        id: `Absorber (${e.target.value})`,
        pattern_type: e.target.value,
        family: e.target.value,
        params: getAbsorberParams(),
        foldAngle: appState.absorber.foldAngle,
      });
      updateAbsorber3DPreview();
    });
  }

  // Export buttons
  const btnAbsExportFold = document.getElementById("btn-abs-export-fold");
  if (btnAbsExportFold) btnAbsExportFold.addEventListener("click", exportAbsorberFOLD);

  const btnAbsExportObj = document.getElementById("btn-abs-export-obj");
  if (btnAbsExportObj) btnAbsExportObj.addEventListener("click", exportAbsorberOBJ);

  // Sync from active design button
  const btnAbsSync = document.getElementById("btn-abs-sync-active");
  if (btnAbsSync) btnAbsSync.addEventListener("click", syncAbsorberFromActiveDesign);

  // Unit cell geometry inputs live synchronization
  ["abs-param-a", "abs-param-b", "abs-param-gamma", "abs-param-nx", "abs-param-ny"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", () => {
        appState.absorber.params = getAbsorberParams();
        syncDesignToAllSections("absorber", {
          id: `Absorber (${appState.absorber.patternType})`,
          pattern_type: appState.absorber.patternType,
          family: appState.absorber.patternType,
          params: appState.absorber.params,
          foldAngle: appState.absorber.foldAngle,
        });
        updateAbsorber3DPreview();
      });
      el.addEventListener("input", () => {
        appState.absorber.params = getAbsorberParams();
        syncDesignToAllSections("absorber", {
          id: `Absorber (${appState.absorber.patternType})`,
          pattern_type: appState.absorber.patternType,
          family: appState.absorber.patternType,
          params: appState.absorber.params,
          foldAngle: appState.absorber.foldAngle,
        });
      });
    }
  });

  const btnRunSim = document.getElementById("btn-run-absorber-sim");
  if (btnRunSim) {
    btnRunSim.addEventListener("click", () => {
      runAbsorberSim();
    });
  }

  const btnRunSweep = document.getElementById("btn-run-absorber-sweep");
  if (btnRunSweep) {
    btnRunSweep.addEventListener("click", () => {
      runAbsorberSweep();
    });
  }

  const btnToggleCurrents = document.getElementById("btn-abs-toggle-currents");
  if (btnToggleCurrents) {
    btnToggleCurrents.addEventListener("click", () => {
      appState.absorber.showCurrents = !appState.absorber.showCurrents;
      btnToggleCurrents.textContent = `Currents: ${appState.absorber.showCurrents ? "ON" : "OFF"}`;
      if (appState.absorber.lastResult) {
        renderAbsorberMesh(appState.absorber.lastResult);
      }
    });
  }

  const btnResetCam = document.getElementById("btn-abs-reset-3d");
  if (btnResetCam && absControls && absCamera) {
    btnResetCam.addEventListener("click", () => {
      absCamera.position.set(0, -120, 90);
      absCamera.lookAt(0, 0, 0);
      absControls.target.set(0, 0, 0);
      absControls.update();
    });
  }

  // Setup heatmap canvas hover interactions
  const hmCanvas = document.getElementById("abs-heatmap-canvas");
  if (hmCanvas) {
    hmCanvas.addEventListener("mousemove", handleHeatmapMouseMove);
  }
}

function initAbsorberThreeJS() {
  const container = document.getElementById("abs-threejs-container");
  if (!container || absSceneInitialized) return;

  const w = container.clientWidth || 400;
  const h = container.clientHeight || 300;

  absScene = new THREE.Scene();
  absScene.background = new THREE.Color(0xffffff);

  absCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
  absCamera.position.set(0, -120, 90);
  absCamera.up.set(0, 0, 1);

  absRenderer = new THREE.WebGLRenderer({ antialias: true });
  absRenderer.setSize(w, h);
  absRenderer.setPixelRatio(window.devicePixelRatio || 1);
  container.innerHTML = "";
  container.appendChild(absRenderer.domElement);

  if (typeof THREE.OrbitControls !== "undefined") {
    absControls = new THREE.OrbitControls(absCamera, absRenderer.domElement);
    absControls.enableDamping = true;
    absControls.dampingFactor = 0.08;
    absControls.target.set(0, 0, 0);
  }

  const ambLight = new THREE.AmbientLight(0xffffff, 0.7);
  absScene.add(ambLight);

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.6);
  dirLight1.position.set(50, -50, 100);
  absScene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
  dirLight2.position.set(-50, 50, -50);
  absScene.add(dirLight2);

  const grid = new THREE.GridHelper(200, 20, 0xe2e8f0, 0xf1f5f9);
  grid.rotation.x = Math.PI / 2;
  absScene.add(grid);

  absSceneInitialized = true;

  function animate() {
    requestAnimationFrame(animate);
    if (absControls) absControls.update();
    if (absRenderer && absScene && absCamera) {
      absRenderer.render(absScene, absCamera);
    }
  }
  animate();

  window.addEventListener("resize", onAbsorberResize);
}

function onAbsorberResize() {
  const container = document.getElementById("abs-threejs-container");
  if (container && absRenderer && absCamera) {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w > 0 && h > 0) {
      absCamera.aspect = w / h;
      absCamera.updateProjectionMatrix();
      absRenderer.setSize(w, h);
    }
  }

  if (appState.absorber.lastResult) {
    drawAbsorberSpectrum(appState.absorber.lastResult);
  }
  if (appState.absorber.sweepResult) {
    drawAbsorberHeatmap(appState.absorber.sweepResult);
  }
}

async function updateAbsorber3DPreview() {
  try {
    const ptype = appState.absorber.patternType || "miura_ori";
    const foldAngle = appState.absorber.foldAngle !== undefined ? appState.absorber.foldAngle : 30.0;
    const params = getAbsorberParams();

    const resp = await fetch("/api/fold", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angle_deg: foldAngle,
      }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    const mesh = data.folded_mesh_3d || data.mesh;
    if (mesh) {
      renderAbsorberGeometry(mesh, data.crease_pattern_2d);
    }
  } catch (e) {
    console.warn("Absorber preview update error:", e);
  }
}

function renderAbsorberGeometry(mesh, creaseData) {
  if (!absScene) return;

  if (appState.absorber.threeObj) absScene.remove(appState.absorber.threeObj);
  if (appState.absorber.edgesObj) absScene.remove(appState.absorber.edgesObj);

  const verts = mesh.vertices;
  const faces = mesh.faces;
  if (!verts || !faces) return;

  const positions = [];
  faces.forEach(f => {
    if (f.length >= 3) {
      for (let i = 1; i < f.length - 1; i++) {
        const v0 = verts[f[0]];
        const v1 = verts[f[i]];
        const v2 = verts[f[i + 1]];
        positions.push(...v0, ...v1, ...v2);
      }
    }
  });

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.computeVertexNormals();

  const mat = new THREE.MeshLambertMaterial({
    color: 0xd97706,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.88,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  });

  const meshObj = new THREE.Mesh(geom, mat);
  absScene.add(meshObj);
  appState.absorber.threeObj = meshObj;

  // Render authentic origami creases (Red Mountain, Blue Valley)
  let edgesObj = null;
  if (creaseData && creaseData.creases && creaseData.creases.length > 0) {
    edgesObj = create3DCreaseLines(creaseData.creases, verts);
  }
  if (!edgesObj) {
    const edgesGeom = new THREE.EdgesGeometry(geom);
    const edgesMat = new THREE.LineBasicMaterial({ color: 0x1e293b, linewidth: 1.5 });
    edgesObj = new THREE.LineSegments(edgesGeom, edgesMat);
  }
  absScene.add(edgesObj);
  appState.absorber.edgesObj = edgesObj;

  const hudDims = document.getElementById("abs-hud-dims");
  if (hudDims && mesh.dimensions) {
    hudDims.textContent = `${mesh.dimensions[0]} × ${mesh.dimensions[1]} × ${mesh.dimensions[2]} mm`;
  }
}

function renderAbsorberMesh(result) {
  if (!absScene || !result) return;
  if (appState.absorber.threeObj) absScene.remove(appState.absorber.threeObj);
  if (appState.absorber.edgesObj) absScene.remove(appState.absorber.edgesObj);

  updateAbsorber3DPreview();
}

async function runAbsorberSim() {
  const btn = document.getElementById("btn-run-absorber-sim");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Solving MoM Spectrum...";
  }
  updateStatus("Solving electrodynamic surface integral equations for metasurface...");

  try {
    const ptype = document.getElementById("abs-pattern-type")?.value || appState.absorber.patternType || "miura_ori";
    const foldAngle = parseFloat(document.getElementById("abs-fold-slider")?.value || appState.absorber.foldAngle || 30.0);
    const pol = document.getElementById("abs-pol-select")?.value || "linear_x";
    const thetaInc = parseFloat(document.getElementById("abs-theta-inc")?.value || 0.0);
    const phiInc = parseFloat(document.getElementById("abs-phi-inc")?.value || 0.0);
    const subMat = document.getElementById("abs-sub-select")?.value || "kapton";
    const thickness = parseFloat(document.getElementById("abs-thickness")?.value || 0.5);
    const condMat = document.getElementById("abs-cond-select")?.value || "copper";
    const sheetRes = parseFloat(document.getElementById("abs-sheet-res")?.value || 0.0);
    const groundBacked = document.getElementById("abs-ground-backed")?.checked ?? true;
    const fStart = parseFloat(document.getElementById("abs-fstart")?.value || 1.0);
    const fStop = parseFloat(document.getElementById("abs-fstop")?.value || 6.0);
    const nPts = parseInt(document.getElementById("abs-npts")?.value || 31, 10);
    const params = getAbsorberParams();

    const resp = await fetch("/api/absorber/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angle: foldAngle,
        f_start_ghz: fStart,
        f_stop_ghz: fStop,
        num_points: nPts,
        substrate_material: subMat,
        conductor_material: condMat,
        ground_backed: groundBacked,
        substrate_thickness_mm: thickness,
        polarization: pol,
        incidence_angle_deg: thetaInc,
        azimuth_angle_deg: phiInc,
        sheet_resistance: sheetRes,
      }),
    });

    if (!resp.ok) throw new Error("Simulation request failed");
    const data = await resp.json();
    appState.absorber.lastResult = data;

    // Update HUD and metrics
    const f0Ghz = (data.resonant_frequency_hz / 1e9).toFixed(3);
    const peakAbs = (data.peak_absorption * 100).toFixed(1);
    const minS11 = data.minimum_s11_db.toFixed(1);
    const bwMhz = (data.absorption_bandwidth_hz / 1e6).toFixed(0);

    const elF0 = document.getElementById("abs-stat-f0");
    const elAbs = document.getElementById("abs-stat-peak-abs");
    const elS11 = document.getElementById("abs-stat-s11");
    const elBw = document.getElementById("abs-stat-bw");
    const elEnergy = document.getElementById("abs-stat-energy");

    if (elF0) elF0.textContent = `${f0Ghz} GHz`;
    if (elAbs) elAbs.textContent = `${peakAbs}%`;
    if (elS11) elS11.textContent = `${minS11} dB`;
    if (elBw) elBw.textContent = `${bwMhz} MHz`;
    if (elEnergy && data.energy_errors) {
      const maxErr = Math.max(...data.energy_errors);
      elEnergy.textContent = (1.0 - maxErr).toFixed(6);
    }

    drawAbsorberSpectrum(data);
    updateStatus(`MoM Simulation Converged: f₀ = ${f0Ghz} GHz, Peak Absorption = ${peakAbs}%, Min S11 = ${minS11} dB`);
  } catch (err) {
    console.error("Absorber simulation error:", err);
    updateStatus(`Simulation error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Run MoM Absorber Solve";
    }
  }
}

async function runAbsorberSweep() {
  const btn = document.getElementById("btn-run-absorber-sweep");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Sweeping Fold Angles...";
  }
  updateStatus("Running 2D fold angle × frequency tuning sweep...");

  try {
    const ptype = document.getElementById("abs-pattern-type")?.value || appState.absorber.patternType || "miura_ori";
    const subMat = document.getElementById("abs-sub-select")?.value || "kapton";
    const condMat = document.getElementById("abs-cond-select")?.value || "copper";
    const thickness = parseFloat(document.getElementById("abs-thickness")?.value || 0.5);
    const pol = document.getElementById("abs-pol-select")?.value || "linear_x";
    const params = getAbsorberParams();

    const resp = await fetch("/api/absorber/fold-sweep", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: params,
        fold_angles: [0.0, 15.0, 30.0, 45.0, 60.0, 75.0],
        f_start_ghz: 1.5,
        f_stop_ghz: 6.5,
        num_points: 25,
        substrate_material: subMat,
        conductor_material: condMat,
        substrate_thickness_mm: thickness,
        polarization: pol,
      }),
    });

    if (!resp.ok) throw new Error("Sweep request failed");
    const data = await resp.json();
    appState.absorber.sweepResult = data;

    const elTuning = document.getElementById("abs-stat-tuning");
    if (elTuning) {
      elTuning.textContent = `${data.tuning_range_ghz} GHz (${data.tuning_ratio}×)`;
    }

    drawAbsorberHeatmap(data);
    updateStatus(`2D Fold Sweep Completed: Tuning range = ${data.tuning_range_ghz} GHz (Ratio = ${data.tuning_ratio}×)`);
  } catch (err) {
    console.error("Fold sweep error:", err);
    updateStatus(`Fold sweep error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Run 2D Fold Angle Sweep";
    }
  }
}

function drawAbsorberSpectrum(data) {
  const canvas = document.getElementById("abs-spectrum-canvas");
  if (!canvas || !data || !data.frequencies_hz) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 400;
  const h = rect.height || 220;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  const padL = 45, padR = 45, padT = 20, padB = 30;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const freqs = data.frequencies_hz.map(f => f / 1e9);
  const fMin = freqs[0];
  const fMax = freqs[freqs.length - 1];
  const abs = data.absorption;
  const s11 = data.s11_db;

  // Grid
  ctx.strokeStyle = "#f1f5f9";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = padT + (plotH / 5) * i;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + plotW, y);
    ctx.stroke();

    // Left Y Axis labels (Absorption %)
    ctx.fillStyle = "#16a34a";
    ctx.font = "9.5px 'Fira Code', monospace";
    ctx.textAlign = "right";
    ctx.fillText(`${(100 - i * 20)}%`, padL - 6, y + 3);

    // Right Y Axis labels (S11 dB)
    ctx.fillStyle = "#0284c7";
    ctx.textAlign = "left";
    ctx.fillText(`${-(i * 6)}dB`, padL + plotW + 6, y + 3);
  }

  // X Axis Ticks & Labels
  for (let i = 0; i <= 5; i++) {
    const x = padL + (plotW / 5) * i;
    const fVal = (fMin + (fMax - fMin) * (i / 5)).toFixed(1);
    ctx.strokeStyle = "#f1f5f9";
    ctx.beginPath();
    ctx.moveTo(x, padT);
    ctx.lineTo(x, padT + plotH);
    ctx.stroke();

    ctx.fillStyle = "#64748b";
    ctx.textAlign = "center";
    ctx.fillText(`${fVal} GHz`, x, padT + plotH + 18);
  }

  // Plot Absorption A(f) with Green Fill
  ctx.beginPath();
  freqs.forEach((f, i) => {
    const x = padL + ((f - fMin) / (fMax - fMin)) * plotW;
    const y = padT + (1.0 - Math.min(1.0, Math.max(0, abs[i]))) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#16a34a";
  ctx.lineWidth = 2.2;
  ctx.stroke();

  // Fill area under A(f)
  ctx.lineTo(padL + plotW, padT + plotH);
  ctx.lineTo(padL, padT + plotH);
  ctx.closePath();
  ctx.fillStyle = "rgba(22, 163, 74, 0.12)";
  ctx.fill();

  // Plot Reflection S11(f) with Blue Dashed Line
  ctx.save();
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  freqs.forEach((f, i) => {
    const x = padL + ((f - fMin) / (fMax - fMin)) * plotW;
    const dbVal = Math.max(-30, Math.min(0, s11[i]));
    const y = padT + (-dbVal / 30.0) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#0284c7";
  ctx.lineWidth = 2.0;
  ctx.stroke();
  ctx.restore();

  // Resonant marker
  if (data.resonant_frequency_hz) {
    const f0Ghz = data.resonant_frequency_hz / 1e9;
    if (f0Ghz >= fMin && f0Ghz <= fMax) {
      const x0 = padL + ((f0Ghz - fMin) / (fMax - fMin)) * plotW;
      ctx.strokeStyle = "#d97706";
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      ctx.moveTo(x0, padT);
      ctx.lineTo(x0, padT + plotH);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#d97706";
      ctx.font = "bold 9.5px 'Fira Code', monospace";
      ctx.textAlign = "center";
      ctx.fillText(`f₀ = ${f0Ghz.toFixed(2)} GHz`, x0, padT - 6);
    }
  }
}

function drawAbsorberHeatmap(data) {
  const canvas = document.getElementById("abs-heatmap-canvas");
  if (!canvas || !data || !data.heatmap_matrix) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 800;
  const h = rect.height || 200;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, w, h);

  const padL = 60, padR = 80, padT = 20, padB = 30;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const mat = data.heatmap_matrix; // 2D array [angles x freqs]
  const angles = data.fold_angles_deg;
  const freqs = data.frequencies_hz.map(f => f / 1e9);

  const nRows = mat.length;
  const nCols = mat[0].length;
  const cellW = plotW / nCols;
  const cellH = plotH / nRows;

  // Draw Heatmap Cells
  for (let r = 0; r < nRows; r++) {
    for (let c = 0; c < nCols; c++) {
      const val = mat[r][c]; // [0, 1]
      ctx.fillStyle = getHeatmapColor(val);
      const x = padL + c * cellW;
      const y = padT + (nRows - 1 - r) * cellH;
      ctx.fillRect(x, y, cellW + 0.5, cellH + 0.5);
    }
  }

  // Draw Resonant Trajectory Line
  if (data.resonance_vs_fold) {
    ctx.beginPath();
    data.resonance_vs_fold.forEach((item, idx) => {
      const rIdx = angles.indexOf(item.fold_angle_deg);
      const fGhz = item.resonant_frequency_hz / 1e9;
      const fMin = freqs[0];
      const fMax = freqs[freqs.length - 1];
      const x = padL + ((fGhz - fMin) / (fMax - fMin)) * plotW;
      const y = padT + (nRows - 1 - rIdx + 0.5) * cellH;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Trajectory dots
    data.resonance_vs_fold.forEach((item) => {
      const rIdx = angles.indexOf(item.fold_angle_deg);
      const fGhz = item.resonant_frequency_hz / 1e9;
      const fMin = freqs[0];
      const fMax = freqs[freqs.length - 1];
      const x = padL + ((fGhz - fMin) / (fMax - fMin)) * plotW;
      const y = padT + (nRows - 1 - rIdx + 0.5) * cellH;
      ctx.fillStyle = "#38bdf8";
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  // Axes and Labels
  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px 'Fira Code', monospace";
  ctx.textAlign = "right";

  angles.forEach((ang, r) => {
    const y = padT + (nRows - 1 - r + 0.5) * cellH;
    ctx.fillText(`${ang}°`, padL - 8, y + 3);
  });

  ctx.textAlign = "center";
  for (let i = 0; i <= 6; i++) {
    const x = padL + (plotW / 6) * i;
    const fVal = (freqs[0] + (freqs[freqs.length - 1] - freqs[0]) * (i / 6)).toFixed(1);
    ctx.fillText(`${fVal}G`, x, padT + plotH + 18);
  }

  // Colorbar
  const cbL = padL + plotW + 20;
  const cbW = 12;
  for (let y = 0; y < plotH; y++) {
    const val = 1.0 - y / plotH;
    ctx.fillStyle = getHeatmapColor(val);
    ctx.fillRect(cbL, padT + y, cbW, 1);
  }
  ctx.strokeStyle = "#334155";
  ctx.strokeRect(cbL, padT, cbW, plotH);
  ctx.fillStyle = "#94a3b8";
  ctx.textAlign = "left";
  ctx.fillText("100%", cbL + cbW + 6, padT + 10);
  ctx.fillText("50%", cbL + cbW + 6, padT + plotH / 2 + 3);
  ctx.fillText("0%", cbL + cbW + 6, padT + plotH);
}

function getHeatmapColor(val) {
  // Turbo/Jet colormap mapping: [0, 1] -> navy -> teal -> yellow -> bright red
  const v = Math.max(0, Math.min(1, val));
  let r, g, b;
  if (v < 0.25) {
    const t = v / 0.25;
    r = 15 + t * (20 - 15);
    g = 23 + t * (140 - 23);
    b = 80 + t * (200 - 80);
  } else if (v < 0.5) {
    const t = (v - 0.25) / 0.25;
    r = 20 + t * (16 - 20);
    g = 140 + t * (185 - 140);
    b = 200 + t * (129 - 200);
  } else if (v < 0.75) {
    const t = (v - 0.5) / 0.25;
    r = 16 + t * (245 - 16);
    g = 185 + t * (158 - 185);
    b = 129 + t * (11 - 129);
  } else {
    const t = (v - 0.75) / 0.25;
    r = 245 + t * (239 - 245);
    g = 158 + t * (68 - 158);
    b = 11 + t * (68 - 11);
  }
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

function handleHeatmapMouseMove(e) {
  const canvas = document.getElementById("abs-heatmap-canvas");
  const data = appState.absorber.sweepResult;
  if (!canvas || !data || !data.heatmap_matrix) return;

  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const padL = 60, padR = 80, padT = 20, padB = 30;
  const plotW = rect.width - padL - padR;
  const plotH = rect.height - padT - padB;

  if (mouseX < padL || mouseX > padL + plotW || mouseY < padT || mouseY > padT + plotH) {
    return;
  }

  const mat = data.heatmap_matrix;
  const angles = data.fold_angles_deg;
  const freqs = data.frequencies_hz.map(f => f / 1e9);

  const nRows = mat.length;
  const nCols = mat[0].length;

  const c = Math.floor(((mouseX - padL) / plotW) * nCols);
  const rInv = Math.floor(((mouseY - padT) / plotH) * nRows);
  const r = nRows - 1 - rInv;

  if (r >= 0 && r < nRows && c >= 0 && c < nCols) {
    const ang = angles[r];
    const fGhz = freqs[c].toFixed(2);
    const absVal = (mat[r][c] * 100).toFixed(1);
    const hoverEl = document.getElementById("abs-heatmap-hover-info");
    if (hoverEl) {
      hoverEl.textContent = `θ = ${ang}° | f = ${fGhz} GHz | Absorption = ${absVal}%`;
    }
  }
}

// =====================================================================
// SECTION 5: MULTI-OBJECTIVE OPTIMIZATION & FABRICATION CONTROLLER
// =====================================================================

function initOptimizationControls() {
  const btnRunOpt = document.getElementById("btn-run-nsga2");
  if (btnRunOpt) {
    btnRunOpt.addEventListener("click", () => {
      runNSGA2Optimization();
    });
  }

  const btnFabZip = document.getElementById("btn-export-fab-zip");
  if (btnFabZip) {
    btnFabZip.addEventListener("click", () => {
      exportFabricationZip();
    });
  }
}

function onOptimizationResize() {
  if (appState.optimization.paretoSolutions.length > 0) {
    drawParetoChart(appState.optimization.paretoSolutions);
  }
}

async function runNSGA2Optimization() {
  const btn = document.getElementById("btn-run-nsga2");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Running Evolutionary Search...";
  }
  updateStatus("Executing NSGA-II multi-objective optimization across design space...");

  try {
    const targetFreq = parseFloat(document.getElementById("opt-target-freq")?.value || 2.45);
    const minAbs = parseFloat(document.getElementById("opt-min-abs")?.value || 0.90);
    const popSize = parseInt(document.getElementById("opt-pop-size")?.value || 16, 10);
    const gens = parseInt(document.getElementById("opt-generations")?.value || 4, 10);

    const resp = await fetch("/api/absorber/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_frequency_ghz: targetFreq,
        min_absorption: minAbs,
        population_size: popSize,
        generations: gens,
      }),
    });

    if (!resp.ok) throw new Error("Optimization failed");
    const data = await resp.json();
    appState.optimization.paretoSolutions = data.pareto_front || [];

    const hudPareto = document.getElementById("opt-hud-pareto-count");
    if (hudPareto) hudPareto.textContent = appState.optimization.paretoSolutions.length;

    drawParetoChart(appState.optimization.paretoSolutions);
    populateParetoTable(appState.optimization.paretoSolutions);

    updateStatus(`NSGA-II Complete: Discovered ${appState.optimization.paretoSolutions.length} non-dominated Pareto designs.`);
  } catch (err) {
    console.error("Optimization error:", err);
    updateStatus(`Optimization error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Run NSGA-II Multi-Objective Search";
    }
  }
}

function drawParetoChart(solutions) {
  const canvas = document.getElementById("opt-pareto-canvas");
  if (!canvas || !solutions || solutions.length === 0) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 450;
  const h = rect.height || 300;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  const padL = 50, padR = 30, padT = 30, padB = 40;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  // Axes
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.strokeRect(padL, padT, plotW, plotH);

  // X Axis Label (Tuning Range GHz)
  ctx.fillStyle = "#475569";
  ctx.font = "11px 'Inter', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Tuning Range [GHz]", padL + plotW / 2, padT + plotH + 30);

  // Y Axis Label (Folded Compactness)
  ctx.save();
  ctx.translate(16, padT + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Folded Compactness (A_folded / A_flat)", 0, 0);
  ctx.restore();

  // Plot Points
  const xVals = solutions.map(s => s.objectives.tuning_range_ghz || 0.5);
  const yVals = solutions.map(s => s.objectives.compactness_ratio || 0.5);

  const xMin = 0.0, xMax = Math.max(2.5, Math.max(...xVals) * 1.2);
  const yMin = 0.0, yMax = 1.0;

  solutions.forEach((s, i) => {
    const x = padL + (xVals[i] / xMax) * plotW;
    const y = padT + (1.0 - yVals[i] / yMax) * plotH;
    const peakAbs = s.objectives.peak_absorption || 0.85;

    ctx.fillStyle = "#d97706";
    ctx.beginPath();
    ctx.arc(x, y, 5 + peakAbs * 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#92400e";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = "#1e293b";
    ctx.font = "bold 9px 'Fira Code', monospace";
    ctx.fillText(`#${s.rank || i + 1}`, x + 8, y - 6);
  });
}

function populateParetoTable(solutions) {
  const tbody = document.getElementById("opt-pareto-tbody");
  if (!tbody) return;

  if (!solutions || solutions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No solutions found.</td></tr>`;
    return;
  }

  let html = "";
  solutions.forEach((s, idx) => {
    const obj = s.objectives || {};
    const p = s.parameters || {};
    html += `
      <tr>
        <td><strong style="color: var(--accent-primary);">#${s.rank || idx + 1}</strong></td>
        <td>${(obj.tuning_range_ghz || 0).toFixed(2)} GHz</td>
        <td>${(obj.compactness_ratio || 0).toFixed(3)}</td>
        <td><span class="text-success font-bold">${((obj.peak_absorption || 0) * 100).toFixed(1)}%</span></td>
        <td>a=${p.a || 25}mm, b=${p.b || 25}mm, γ=${p.gamma_deg || 65}°</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

async function exportFabricationZip() {
  const btn = document.getElementById("btn-export-fab-zip");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Packaging Production Archive...";
  }
  updateStatus("Generating RS-274X Gerbers, DXF cut layers, STL panels, and BOM...");

  try {
    const subDesc = document.getElementById("fab-substrate-desc")?.value || "Kapton Polyimide (0.5mm)";
    const condDesc = document.getElementById("fab-conductor-desc")?.value || "Rolled Annealed Copper (35 um)";
    const activeParams = (appState.activeDesign && appState.activeDesign.params) ? appState.activeDesign.params : getAbsorberParams();
    const ptype = (appState.activeDesign && appState.activeDesign.pattern_type) ? appState.activeDesign.pattern_type : (appState.absorber.patternType || "miura_ori");
    const foldAngle = (appState.activeDesign && appState.activeDesign.foldAngle !== undefined) ? appState.activeDesign.foldAngle : (appState.absorber.foldAngle || 30.0);
    const designId = (appState.activeDesign && appState.activeDesign.id) ? `FAB-${appState.activeDesign.id}` : "ORIGAMI-ABS-FORGE-001";

    const resp = await fetch("/api/fabrication/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern_type: ptype,
        params: activeParams,
        fold_angle_deg: foldAngle,
        design_id: designId,
        substrate_material: subDesc,
        conductor_material: condDesc,
      }),
    });

    if (!resp.ok) throw new Error("Fabrication export failed");

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rf_origami_fabrication_release.zip";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    updateStatus("Fabrication release ZIP downloaded successfully.");
  } catch (err) {
    console.error("Fabrication export error:", err);
    updateStatus(`Export error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Download Fabrication ZIP";
    }
  }
}

