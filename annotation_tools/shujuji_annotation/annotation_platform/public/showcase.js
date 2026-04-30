const ACCESS_TOKEN_STORAGE_KEY = "shujuji_access_token";
const params = new URLSearchParams(window.location.search);
const datasetKey = params.get("dataset") || (window.location.pathname.startsWith("/practice") ? "practice10" : "formal300");

const els = {
  chartMeta: document.querySelector("#chartMeta"),
  chartSelect: document.querySelector("#chartSelect"),
  chartInput: document.querySelector("#chartInput"),
  loadChartBtn: document.querySelector("#loadChartBtn"),
  legSelect: document.querySelector("#legSelect"),
  evidenceModeBtn: document.querySelector("#evidenceModeBtn"),
  arincModeBtn: document.querySelector("#arincModeBtn"),
  showAllLegs: document.querySelector("#showAllLegs"),
  viewerShell: document.querySelector("#viewerShell"),
  chartPane: document.querySelector("#chartPane"),
  chartFrame: document.querySelector("#chartFrame"),
  chartImage: document.querySelector("#chartImage"),
  boxOverlay: document.querySelector("#boxOverlay"),
  leaderOverlay: document.querySelector("#leaderOverlay"),
  panelTitle: document.querySelector("#panelTitle"),
  resultSource: document.querySelector("#resultSource"),
  fieldList: document.querySelector("#fieldList"),
  toast: document.querySelector("#toast")
};

const FIELD_LABELS = {
  Q_terminator: "航段类型",
  Q1_fix_ident: "定位点 / 导航台",
  Q2_altitude_constraint: "高度限制",
  Q3_turn: "转弯方向",
  Q4_course_or_radial: "航向 / 径向 / 航迹",
  Q5_hold_params: "等待参数"
};

const ARINC_LABELS = {
  Q_terminator: "PATH TERMINATOR",
  Q1_fix_ident: "FIX IDENT",
  Q2_altitude_constraint: "ALTITUDE / ALT DESC",
  Q3_turn: "TURN / PATH",
  Q4_course_or_radial: "COURSE / RADIAL",
  Q5_hold_params: "HOLDING"
};

const STATUS_LABELS = {
  pending: "待确认",
  direct_visible: "一处直接能看出",
  visible_joint: "多处合起来能看出",
  rule_default_completion: "图上证据 + 规则补全",
  insufficient_for_encoding: "图上看不够",
  not_applicable: "不适用"
};

const COLORS = ["#176f5b", "#315f9e", "#a96e14", "#9a4d7a", "#b34b4b", "#4d6f23", "#6a5b9e", "#95623c"];

const state = {
  charts: [],
  current: null,
  regions: [],
  rows: [],
  fieldReviews: {},
  currentLeg: 1,
  mode: params.get("mode") === "424" ? "arinc" : "evidence",
  activeFieldKey: ""
};

function initializeAccessToken() {
  const token = params.get("token");
  if (!token) return;
  sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  params.delete("token");
  window.history.replaceState({}, document.title, `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}${window.location.hash}`);
}

function currentAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || "";
}

function apiUrl(path, extra = {}) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("dataset", datasetKey);
  const token = currentAccessToken();
  if (token) url.searchParams.set("token", token);
  const annotator = params.get("annotator") || "";
  if (annotator) url.searchParams.set("annotator", annotator);
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return url;
}

function withAccessToken(urlValue) {
  const token = currentAccessToken();
  if (!token || !urlValue) return urlValue;
  const url = new URL(urlValue, window.location.origin);
  url.searchParams.set("token", token);
  return `${url.pathname}${url.search}`;
}

async function getJson(url) {
  const token = currentAccessToken();
  const response = await fetch(url, {
    headers: token ? { "x-shujuji-token": token } : {}
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.add("hidden"), 2800);
}

function escapeText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function uniqueList(values) {
  return Array.from(new Set((values || []).filter(Boolean).map(String)));
}

function normalizeFieldReviews(source) {
  if (!source) return {};
  if (Array.isArray(source)) {
    return Object.fromEntries(source.map((item) => [item.field_key, item]).filter(([key]) => key));
  }
  return typeof source === "object" ? JSON.parse(JSON.stringify(source)) : {};
}

function normalizeRegion(region) {
  return {
    ...region,
    bbox: region.bbox || { x_center: 0.5, y_center: 0.5, width: 0.1, height: 0.1 },
    candidate_mappings: Array.isArray(region.candidate_mappings) ? region.candidate_mappings : []
  };
}

function fieldKey(legIndex, fieldName) {
  return `leg${legIndex}.${fieldName}`;
}

function canonicalLegIndexForMapping(mapping) {
  if (Number.isInteger(mapping?.canonical_leg_index)) return mapping.canonical_leg_index;
  const match = String(mapping?.candidate_leg_id || "").match(/__ma(\d+)$/);
  return match ? Number(match[1]) : null;
}

function fieldKeyForMapping(mapping) {
  const legIndex = canonicalLegIndexForMapping(mapping);
  return legIndex && mapping?.field_name ? fieldKey(legIndex, mapping.field_name) : "";
}

function buildFieldRows() {
  const target = state.current?.target;
  if (!target) return [];
  return (target.candidate_legs || []).flatMap((leg) => {
    return (leg.target_fields || []).map((field) => {
      const fieldName = field.field_name || field.name || "";
      const legIndex = leg.canonical_leg_index || canonicalLegIndexForMapping({ candidate_leg_id: leg.candidate_leg_id });
      return {
        key: fieldKey(legIndex, fieldName),
        candidate_leg_id: leg.candidate_leg_id || "",
        canonical_leg_index: legIndex,
        leg_type: leg.leg_type || "",
        source_seq_no: leg.source_seq_no || "",
        source_trans_ident: leg.source_trans_ident || "",
        field_name: fieldName,
        expected_value: field.expected_value ?? field.value ?? "",
        expected_answer: field.expected_answer || null
      };
    });
  });
}

function answerIsPresent(row) {
  return row.expected_answer?.status === "present";
}

function formatAnswer(answer) {
  if (!answer) return "unknown";
  if (answer.status !== "present") return answer.status || "unknown";
  const value = answer.value;
  if (value === null || typeof value === "undefined") return "present";
  if (typeof value !== "object") return String(value);
  if (value.type === "course_deg") return `${Math.round(Number(value.course_deg || 0))} deg`;
  if (value.type === "navaid_radial") {
    const bits = [value.navaid, value.radial_deg ? `R-${Math.round(Number(value.radial_deg))}` : "", value.direction].filter(Boolean);
    return bits.join(" ");
  }
  if (value.desc && value.altitude_ft) return `${value.desc} ${value.altitude_ft} ft`;
  if (value.hold_fix || value.inbound_course_deg || value.turn_direction) {
    return [
      value.hold_fix,
      value.inbound_course_deg ? `inbound ${Math.round(Number(value.inbound_course_deg))} deg` : "",
      value.turn_direction,
      value.leg_time_min ? `${value.leg_time_min} min` : ""
    ].filter(Boolean).join(" · ");
  }
  return Object.entries(value).map(([key, item]) => `${key}=${item}`).join(", ");
}

function shortRegionLabel(region) {
  return region.ocr_text || region.label || region.region_type || region.region_id;
}

function evidenceIdsForRow(row) {
  const saved = state.fieldReviews[row.key] || {};
  const savedIds = uniqueList(saved.required_evidence_region_ids || saved.evidence_region_ids || []);
  if (savedIds.length) return savedIds;
  const accepted = state.regions.filter((region) => {
    return (region.candidate_mappings || []).some((mapping) => {
      const decision = mapping.human_decision || "pending";
      return fieldKeyForMapping(mapping) === row.key && decision === "accepted";
    });
  }).map((region) => region.region_id);
  if (accepted.length) return uniqueList(accepted);
  const candidates = state.regions.filter((region) => {
    return (region.candidate_mappings || []).some((mapping) => {
      const decision = mapping.human_decision || "pending";
      return fieldKeyForMapping(mapping) === row.key && !["rejected", "needs_discussion"].includes(decision);
    });
  }).map((region) => region.region_id);
  if (row.field_name === "Q_terminator" && !candidates.length) {
    return uniqueList(state.rows
      .filter((item) => item.canonical_leg_index === row.canonical_leg_index && item.field_name !== "Q_terminator" && answerIsPresent(item))
      .flatMap((item) => evidenceIdsForRow(item)));
  }
  return uniqueList(candidates);
}

function reviewStatusForRow(row, evidenceIds) {
  const saved = state.fieldReviews[row.key] || {};
  if (saved.support_mode || saved.review_status) return saved.support_mode || saved.review_status;
  if (!answerIsPresent(row)) return "not_applicable";
  return evidenceIds.length > 1 ? "visible_joint" : evidenceIds.length ? "direct_visible" : "pending";
}

function colorForRow(row) {
  const index = Math.max(0, Number(row.canonical_leg_index || 1) - 1) * 6
    + Math.max(0, Object.keys(FIELD_LABELS).indexOf(row.field_name));
  return COLORS[index % COLORS.length];
}

function activeRows() {
  return state.rows.filter((row) => {
    if (!els.showAllLegs.checked && row.canonical_leg_index !== state.currentLeg) return false;
    if (state.mode === "evidence") return answerIsPresent(row);
    return true;
  });
}

function sourceLabel() {
  if (state.current?.annotation) return `人工结果：${state.current.annotation_annotator || "unknown"}`;
  if (state.current?.draft) return `暂存草稿：${state.current.annotation_annotator || "unknown"}`;
  return "预标注 / 424 proxy";
}

function renderLegOptions() {
  const legs = Array.from(new Map(state.rows.map((row) => [row.canonical_leg_index, row])).values())
    .filter((row) => row.canonical_leg_index);
  els.legSelect.innerHTML = legs.map((row) => {
    const label = `航段 ${row.canonical_leg_index} · ${row.leg_type || "-"}`;
    return `<option value="${row.canonical_leg_index}">${escapeText(label)}</option>`;
  }).join("");
  if (!legs.some((row) => row.canonical_leg_index === state.currentLeg)) {
    state.currentLeg = legs[0]?.canonical_leg_index || 1;
  }
  els.legSelect.value = String(state.currentLeg);
}

function renderFieldCards() {
  const rows = activeRows();
  els.panelTitle.textContent = els.showAllLegs.checked
    ? (state.mode === "arinc" ? "全部航段 · 424 字段" : "全部航段 · 证据结论")
    : (state.mode === "arinc" ? `航段 ${state.currentLeg} · 424 字段` : `航段 ${state.currentLeg} · 证据结论`);
  els.resultSource.textContent = sourceLabel();
  if (!rows.length) {
    els.fieldList.innerHTML = "<p class='muted'>当前航段没有可展示字段。</p>";
    return;
  }
  els.fieldList.innerHTML = rows.map((row) => {
    const evidenceIds = evidenceIdsForRow(row);
    const status = reviewStatusForRow(row, evidenceIds);
    const color = colorForRow(row);
    const evidenceChips = evidenceIds.map((regionId) => {
      const region = state.regions.find((item) => item.region_id === regionId);
      return `<span class="evidence-chip">${escapeText(shortRegionLabel(region || { region_id: regionId }))}</span>`;
    }).join("");
    const title = state.mode === "arinc"
      ? `${ARINC_LABELS[row.field_name] || row.field_name}`
      : `${FIELD_LABELS[row.field_name] || row.field_name}`;
    const prefix = state.mode === "arinc"
      ? `SEQ ${row.source_seq_no || "-"} · ${row.source_trans_ident || "-"} · ${row.leg_type || "-"}`
      : `航段 ${row.canonical_leg_index} · ${row.leg_type || "-"}`;
    const dimmed = answerIsPresent(row) ? "" : " dimmed";
    return `<article class="field-card${dimmed}" data-field-key="${escapeText(row.key)}" style="--accent:${color}">
      <div class="meta">${escapeText(prefix)}</div>
      <h2>${escapeText(title)}</h2>
      <p class="value">${escapeText(formatAnswer(row.expected_answer))}</p>
      <div class="meta">${escapeText(STATUS_LABELS[status] || status)} · ${evidenceIds.length} 处证据</div>
      <div class="evidence-list">${evidenceChips}</div>
    </article>`;
  }).join("");
  els.fieldList.querySelectorAll(".field-card").forEach((card) => {
    card.addEventListener("mouseenter", () => {
      state.activeFieldKey = card.dataset.fieldKey || "";
      renderOverlays();
    });
    card.addEventListener("mouseleave", () => {
      state.activeFieldKey = "";
      renderOverlays();
    });
  });
}

function regionRect(region, width, height) {
  const box = region?.bbox || {};
  const w = Number(box.width || 0) * width;
  const h = Number(box.height || 0) * height;
  const x = (Number(box.x_center || 0.5) * width) - w / 2;
  const y = (Number(box.y_center || 0.5) * height) - h / 2;
  return { x, y, w, h };
}

function activeEvidenceMap() {
  const map = new Map();
  for (const row of activeRows()) {
    for (const regionId of evidenceIdsForRow(row)) {
      if (!map.has(regionId)) map.set(regionId, []);
      map.get(regionId).push(row);
    }
  }
  return map;
}

function renderBoxes() {
  const naturalWidth = els.chartImage.naturalWidth || state.current?.manifest?.image_dimensions?.width || 1;
  const naturalHeight = els.chartImage.naturalHeight || state.current?.manifest?.image_dimensions?.height || 1;
  els.boxOverlay.setAttribute("viewBox", `0 0 ${naturalWidth} ${naturalHeight}`);
  const evidenceMap = activeEvidenceMap();
  els.boxOverlay.innerHTML = Array.from(evidenceMap.entries()).map(([regionId, rows]) => {
    const region = state.regions.find((item) => item.region_id === regionId);
    if (!region) return "";
    const rect = regionRect(region, naturalWidth, naturalHeight);
    const row = rows.find((item) => item.key === state.activeFieldKey) || rows[0];
    const active = !state.activeFieldKey || rows.some((item) => item.key === state.activeFieldKey);
    const color = colorForRow(row);
    const opacity = active ? 0.96 : 0.22;
    return `<rect x="${rect.x}" y="${rect.y}" width="${rect.w}" height="${rect.h}" rx="4"
      fill="${color}" fill-opacity="0.12" stroke="${color}" stroke-width="${active ? 3 : 2}" stroke-opacity="${opacity}"></rect>`;
  }).join("");
}

function renderLeaders() {
  const shellRect = els.viewerShell.getBoundingClientRect();
  const imageRect = els.chartImage.getBoundingClientRect();
  const shellWidth = els.viewerShell.clientWidth;
  const shellHeight = els.viewerShell.clientHeight;
  els.leaderOverlay.setAttribute("viewBox", `0 0 ${shellWidth} ${shellHeight}`);
  const paths = [];
  for (const row of activeRows()) {
    const card = els.fieldList.querySelector(`[data-field-key="${CSS.escape(row.key)}"]`);
    if (!card) continue;
    const cardRect = card.getBoundingClientRect();
    if (cardRect.bottom < shellRect.top || cardRect.top > shellRect.bottom) continue;
    const endX = cardRect.left - shellRect.left + 2;
    const endY = cardRect.top - shellRect.top + Math.min(52, Math.max(30, cardRect.height / 2));
    const color = colorForRow(row);
    const active = !state.activeFieldKey || state.activeFieldKey === row.key;
    for (const regionId of evidenceIdsForRow(row)) {
      const region = state.regions.find((item) => item.region_id === regionId);
      if (!region) continue;
      const box = region.bbox || {};
      const startX = imageRect.left - shellRect.left + (Number(box.x_center || 0.5) + Number(box.width || 0) / 2) * imageRect.width;
      const startY = imageRect.top - shellRect.top + Number(box.y_center || 0.5) * imageRect.height;
      const midX = startX + Math.max(80, (endX - startX) * 0.48);
      const path = `M ${startX.toFixed(1)} ${startY.toFixed(1)} C ${midX.toFixed(1)} ${startY.toFixed(1)}, ${midX.toFixed(1)} ${endY.toFixed(1)}, ${endX.toFixed(1)} ${endY.toFixed(1)}`;
      paths.push(`<path d="${path}" fill="none" stroke="${color}" stroke-width="${active ? 2.4 : 1.2}" stroke-opacity="${active ? 0.78 : 0.16}"></path>`);
      if (active) paths.push(`<circle cx="${startX.toFixed(1)}" cy="${startY.toFixed(1)}" r="3.5" fill="${color}" fill-opacity="0.9"></circle>`);
    }
  }
  els.leaderOverlay.innerHTML = paths.join("");
}

function renderOverlays() {
  renderBoxes();
  renderLeaders();
}

function renderAll() {
  const manifest = state.current?.manifest || {};
  els.chartMeta.textContent = `${manifest.chart_id || ""} · ${manifest.chart_name || ""}`;
  els.chartInput.value = manifest.chart_id || "";
  els.chartSelect.value = manifest.chart_id || "";
  renderLegOptions();
  renderFieldCards();
  renderOverlays();
}

async function loadCharts() {
  const data = await getJson(apiUrl("/api/charts", { scope: "queue" }));
  state.charts = data.charts || [];
  els.chartSelect.innerHTML = state.charts.map((chart) => {
    const extra = chart.claim_status === "submitted" ? " · 已提交" : chart.claimed_by ? ` · ${chart.claimed_by}` : "";
    return `<option value="${escapeText(chart.chart_id)}">${escapeText(chart.chart_id + extra)}</option>`;
  }).join("");
}

async function loadChart(chartId) {
  if (!chartId) throw new Error("请先选择 chart_id");
  const data = await getJson(apiUrl("/api/chart", { chart_id: chartId }));
  state.current = data;
  const sourceRegions = data.annotation?.regions || data.draft?.regions || data.prelabel?.regions || [];
  state.regions = sourceRegions.map(normalizeRegion);
  state.fieldReviews = normalizeFieldReviews(data.annotation?.field_reviews || data.draft?.field_reviews || {});
  state.rows = buildFieldRows();
  const requestedLeg = Number(params.get("leg") || state.currentLeg || 1);
  state.currentLeg = state.rows.some((row) => row.canonical_leg_index === requestedLeg)
    ? requestedLeg
    : (state.rows[0]?.canonical_leg_index || 1);
  els.chartImage.onload = () => renderOverlays();
  els.chartImage.src = withAccessToken(data.image_url);
  els.chartImage.alt = `航图 ${chartId}`;
  renderAll();
}

function setMode(mode) {
  state.mode = mode;
  els.evidenceModeBtn.classList.toggle("active", mode === "evidence");
  els.arincModeBtn.classList.toggle("active", mode === "arinc");
  renderFieldCards();
  renderOverlays();
}

function bindEvents() {
  els.loadChartBtn.addEventListener("click", () => loadChart(els.chartInput.value.trim()).catch((error) => showToast(error.message)));
  els.chartInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") loadChart(els.chartInput.value.trim()).catch((error) => showToast(error.message));
  });
  els.chartSelect.addEventListener("change", () => loadChart(els.chartSelect.value).catch((error) => showToast(error.message)));
  els.legSelect.addEventListener("change", () => {
    state.currentLeg = Number(els.legSelect.value || 1);
    renderFieldCards();
    renderOverlays();
  });
  els.showAllLegs.addEventListener("change", () => {
    renderFieldCards();
    renderOverlays();
  });
  els.evidenceModeBtn.addEventListener("click", () => setMode("evidence"));
  els.arincModeBtn.addEventListener("click", () => setMode("arinc"));
  els.chartPane.addEventListener("scroll", () => renderOverlays(), { passive: true });
  document.querySelector(".field-pane").addEventListener("scroll", () => renderOverlays(), { passive: true });
  window.addEventListener("resize", () => renderOverlays());
}

async function init() {
  initializeAccessToken();
  bindEvents();
  setMode(state.mode);
  await loadCharts();
  const requestedChart = params.get("chart_id") || params.get("chart") || state.charts[0]?.chart_id || "";
  await loadChart(requestedChart);
}

init().catch((error) => showToast(error.message));
