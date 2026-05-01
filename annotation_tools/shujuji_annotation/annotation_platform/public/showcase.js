const ACCESS_TOKEN_STORAGE_KEY = "shujuji_access_token";
const params = new URLSearchParams(window.location.search);
const datasetKey = params.get("dataset") || (window.location.pathname.startsWith("/practice") ? "practice10" : "formal300");

const els = {
  chartMeta: document.querySelector("#chartMeta"),
  chartSelect: document.querySelector("#chartSelect"),
  chartInput: document.querySelector("#chartInput"),
  loadChartBtn: document.querySelector("#loadChartBtn"),
  editAnnotationLink: document.querySelector("#editAnnotationLink"),
  legSelect: document.querySelector("#legSelect"),
  showAllLegs: document.querySelector("#showAllLegs"),
  viewerShell: document.querySelector("#viewerShell"),
  chartPane: document.querySelector("#chartPane"),
  chartFrame: document.querySelector("#chartFrame"),
  chartImage: document.querySelector("#chartImage"),
  boxOverlay: document.querySelector("#boxOverlay"),
  leaderOverlay: document.querySelector("#leaderOverlay"),
  chartZoomOut: document.querySelector("#chartZoomOut"),
  chartZoomIn: document.querySelector("#chartZoomIn"),
  chartZoomFit: document.querySelector("#chartZoomFit"),
  chartZoomActual: document.querySelector("#chartZoomActual"),
  chartZoomValue: document.querySelector("#chartZoomValue"),
  resizeHandle: document.querySelector("#showcaseResizeHandle"),
  panelTitle: document.querySelector("#panelTitle"),
  resultSource: document.querySelector("#resultSource"),
  recordPanel: document.querySelector("#recordPanel"),
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
  unreviewed: "未标注",
  pending: "待确认",
  direct_visible: "一处直接能看出",
  visible_joint: "多处合起来能看出",
  rule_default_completion: "图上证据 + 规则补全",
  insufficient_for_encoding: "图上看不够",
  not_applicable: "不适用"
};

const COLORS = ["#176f5b", "#315f9e", "#a96e14", "#9a4d7a", "#b34b4b", "#4d6f23", "#6a5b9e", "#95623c"];

const EVIDENCE_CATEGORIES = {
  ma_text: { label: "复飞文字", color: "#176f5b", dash: "", marker: "text" },
  chart_text: { label: "图中文字", color: "#315f9e", dash: "", marker: "text" },
  chart_graphic: { label: "图形/路径", color: "#a96e14", dash: "9 5", marker: "diamond" },
  icon_detail: { label: "图标/细节区", color: "#9a4d7a", dash: "4 4", marker: "triangle" },
  plan_view: { label: "平面图区域", color: "#4d6f23", dash: "2 5", marker: "circle" },
  other: { label: "其他证据", color: "#62706b", dash: "6 5", marker: "square" }
};

const state = {
  charts: [],
  current: null,
  regions: [],
  rows: [],
  fieldReviews: {},
  currentLeg: 1,
  activeFieldKey: "",
  chartZoom: 1,
  fitZoom: 1,
  zoomMode: "fit",
  resizing: null
};

const CHART_ZOOM_MIN = 0.25;
const CHART_ZOOM_MAX = 3;
const CHART_ZOOM_STEP = 0.12;

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
  if (!Object.prototype.hasOwnProperty.call(extra, "annotator")) {
    const annotator = params.get("annotator") || "";
    if (annotator) url.searchParams.set("annotator", annotator);
  }
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

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, Number(value)));
}

function zoomText(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function normalizeFieldReviews(source) {
  if (!source) return {};
  if (Array.isArray(source)) {
    return Object.fromEntries(source.map((item) => [item.field_key, item]).filter(([key]) => key));
  }
  return typeof source === "object" ? JSON.parse(JSON.stringify(source)) : {};
}

function normalizeRegion(region) {
  const regionId = region.region_id || region.final_region_id || region.source_region_id || "";
  return {
    ...region,
    region_id: regionId,
    final_region_id: region.final_region_id || regionId,
    source_region_id: region.source_region_id || regionId,
    bbox: region.bbox || { x_center: 0.5, y_center: 0.5, width: 0.1, height: 0.1 },
    candidate_mappings: Array.isArray(region.candidate_mappings)
      ? region.candidate_mappings
      : Array.isArray(region.candidate_mappings_reviewed)
        ? region.candidate_mappings_reviewed
        : []
  };
}

function regionMatchesId(region, regionId) {
  const target = String(regionId || "");
  if (!target) return false;
  return uniqueList([region?.region_id, region?.final_region_id, region?.source_region_id]).includes(target);
}

function findRegion(regionId) {
  return state.regions.find((region) => regionMatchesId(region, regionId)) || null;
}

function canonicalRegionId(regionId) {
  const region = findRegion(regionId);
  return region?.region_id || String(regionId || "");
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
        raw_record: leg.raw_record || "",
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

function padNumber(value, width) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return String(Math.round(number)).padStart(width, "0");
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
  const label = String(region.ocr_text || region.label || region.region_type || region.region_id || "");
  return label.length > 48 ? `${label.slice(0, 45)}...` : label;
}

function evidenceCategoryForRegion(region) {
  const type = region?.region_type || "";
  if (region?.evidence_source && EVIDENCE_CATEGORIES[region.evidence_source]) return region.evidence_source;
  if (type === "MISSED_APPROACH_TEXT") return "ma_text";
  if (type === "PLAN_VIEW") return "plan_view";
  if (["MISSED_APPROACH_DETAIL_AREA", "MISSED_APPROACH_ICON", "MISSED_APPROACH_STEP_BOX", "CLIMB_ARROW"].includes(type)) {
    return "icon_detail";
  }
  if (["FIX_SYMBOL", "PATH_SEGMENT", "HOLDING_ARC", "HOLDING_PATTERN", "OUTBOUND_INBOUND_MARK"].includes(type)) {
    return "chart_graphic";
  }
  if (["FIX_TEXT", "NAVAID_TEXT", "ALTITUDE_TEXT", "TURN_PHRASE", "HEADING_TEXT", "RADIAL_TEXT", "TRACK_OR_RADIAL_TEXT", "HOLDING_TIME_TEXT", "DME_DISTANCE_TEXT"].includes(type)) {
    return "chart_text";
  }
  return "other";
}

function evidenceCategoryMeta(region) {
  return EVIDENCE_CATEGORIES[evidenceCategoryForRegion(region)] || EVIDENCE_CATEGORIES.other;
}

function evidenceIdsForRow(row) {
  const saved = state.fieldReviews[row.key];
  if (!saved) return [];
  if (Array.isArray(saved.evidence_region_ids)) return uniqueList(saved.evidence_region_ids);
  return uniqueList([
    ...(saved.required_evidence_region_ids || []),
    ...(saved.secondary_evidence_region_ids || [])
  ]);
}

function reviewStatusForRow(row, evidenceIds) {
  const saved = state.fieldReviews[row.key];
  if (saved?.support_mode || saved?.review_status) return saved.support_mode || saved.review_status;
  if (!answerIsPresent(row)) return "not_applicable";
  return "unreviewed";
}

function colorForRow(row) {
  const index = Math.max(0, Number(row.canonical_leg_index || 1) - 1) * 6
    + Math.max(0, Object.keys(FIELD_LABELS).indexOf(row.field_name));
  return COLORS[index % COLORS.length];
}

function activeRows() {
  if (!Object.keys(state.fieldReviews).length) return [];
  return state.rows.filter((row) => {
    if (!els.showAllLegs.checked && row.canonical_leg_index !== state.currentLeg) return false;
    return answerIsPresent(row) && Boolean(state.fieldReviews[row.key]);
  });
}

function legRowsForIndex(legIndex) {
  return state.rows.filter((row) => row.canonical_leg_index === legIndex);
}

function activeLegIndexes() {
  return Array.from(new Set(activeRows()
    .filter((row) => els.showAllLegs.checked || row.canonical_leg_index === state.currentLeg)
    .map((row) => row.canonical_leg_index)
    .filter(Boolean)));
}

function rawRecordForLeg(legIndex) {
  return legRowsForIndex(legIndex).find((row) => row.raw_record)?.raw_record || "";
}

function findToken(record, token, options = {}) {
  const source = String(record || "");
  const text = String(token || "");
  if (!source || !text) return null;
  const from = Math.max(0, Number(options.from || 0));
  const position = source.indexOf(text, from);
  if (position < 0) return null;
  return { start: position, end: position + text.length };
}

function mergedSegment(segments) {
  const valid = segments.filter(Boolean);
  if (!valid.length) return null;
  return {
    start: Math.min(...valid.map((segment) => segment.start)),
    end: Math.max(...valid.map((segment) => segment.end))
  };
}

function arincSegmentForRow(row) {
  const record = row.raw_record || rawRecordForLeg(row.canonical_leg_index);
  const answer = row.expected_answer?.value;
  if (!record || !answerIsPresent(row)) return null;
  if (row.field_name === "Q_terminator") {
    const segment = findToken(record, row.leg_type, { from: 38 });
    return segment ? { ...segment, label: "PATH TERMINATOR" } : null;
  }
  if (row.field_name === "Q1_fix_ident") {
    const segment = findToken(record, answer, { from: 24 });
    return segment ? { ...segment, label: "FIX IDENT" } : null;
  }
  if (row.field_name === "Q2_altitude_constraint") {
    const token = padNumber(answer?.altitude_ft, 5);
    const segment = findToken(record, token, { from: 70 });
    return segment ? { ...segment, label: "ALTITUDE" } : null;
  }
  if (row.field_name === "Q4_course_or_radial") {
    if (answer?.type === "course_deg") {
      const token = padNumber(Number(answer.course_deg) * 10, 4);
      const segment = findToken(record, token, { from: 54 });
      return segment ? { ...segment, label: "COURSE" } : null;
    }
    if (answer?.type === "navaid_radial") {
      const navaid = findToken(record, answer.navaid, { from: 48 });
      const radial = findToken(record, padNumber(Number(answer.radial_deg) * 10, 4), { from: 54 });
      const segment = mergedSegment([navaid, radial]);
      return segment ? { ...segment, label: "NAVAID/RADIAL" } : null;
    }
  }
  if (row.field_name === "Q5_hold_params") {
    const course = findToken(record, padNumber(Number(answer?.inbound_course_deg) * 10, 4), { from: 54 });
    const time = answer?.leg_time_min ? findToken(record, `T${padNumber(Number(answer.leg_time_min) * 10, 3)}`, { from: 60 }) : null;
    const segment = mergedSegment([course, time]);
    return segment ? { ...segment, label: "HOLD" } : null;
  }
  return null;
}

function activeArincRows() {
  return activeRows().filter((row) => Boolean(arincSegmentForRow(row)));
}

function displayItems() {
  return activeRows().map((row) => ({ type: "field", key: row.key, row, rows: [row] }));
}

function ensureActiveField(items = displayItems()) {
  if (!items.length) {
    state.activeFieldKey = "";
    return "";
  }
  if (!items.some((item) => item.key === state.activeFieldKey)) {
    state.activeFieldKey = items[0].key;
  }
  return state.activeFieldKey;
}

function evidenceIdsForItem(item) {
  if (item.type === "field") return evidenceIdsForRow(item.row);
  return uniqueList((item.rows || [])
    .filter(answerIsPresent)
    .flatMap((row) => evidenceIdsForRow(row)));
}

function sourceLabel() {
  if (state.current?.annotation) return `人工结果：${state.current.annotation_annotator || "unknown"}`;
  if (state.current?.draft) return `暂存草稿：${state.current.annotation_annotator || "unknown"}`;
  return "没有人工标注结果";
}

function editAnnotationHref() {
  const manifest = state.current?.manifest || {};
  const chartId = manifest.chart_id || els.chartInput.value.trim();
  const expertStatus = ["returned_for_expert_review", "expert_review_claimed", "expert_review_available", "expert_review_claimed_by_me"].includes(manifest.claim_status || "");
  const path = datasetKey === "practice10"
    ? "/practice/"
    : expertStatus
      ? "/expert/"
      : "/formal/";
  const url = new URL(path, window.location.origin);
  url.searchParams.set("dataset", datasetKey);
  if (chartId) url.searchParams.set("chart_id", chartId);
  if (expertStatus) {
    url.searchParams.set("role", "expert");
    url.searchParams.set("expert", params.get("expert") || params.get("reviewer") || manifest.expert_reviewer || "admin");
  } else {
    const annotator = state.current?.annotation_annotator
      || params.get("annotator")
      || manifest.original_annotator
      || manifest.claimed_by
      || "";
    if (annotator) url.searchParams.set("annotator", annotator);
  }
  const token = currentAccessToken();
  if (token) url.searchParams.set("token", token);
  return `${url.pathname}${url.search}`;
}

function updateEditAnnotationLink() {
  if (!els.editAnnotationLink) return;
  const expertStatus = ["returned_for_expert_review", "expert_review_claimed", "expert_review_available", "expert_review_claimed_by_me"].includes(state.current?.manifest?.claim_status || "");
  els.editAnnotationLink.href = editAnnotationHref();
  els.editAnnotationLink.textContent = expertStatus ? "去复核页修改" : "去标注页修改";
}

function renderLegOptions() {
  const rowsForLegs = Object.keys(state.fieldReviews).length
    ? state.rows.filter((row) => state.fieldReviews[row.key])
    : state.rows;
  const legs = Array.from(new Map(rowsForLegs.map((row) => [row.canonical_leg_index, row])).values())
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
  const items = displayItems();
  const activeKey = ensureActiveField(items);
  els.panelTitle.textContent = els.showAllLegs.checked
    ? "全部航段 · 证据结论"
    : `航段 ${state.currentLeg} · 证据结论`;
  els.resultSource.textContent = sourceLabel();
  if (!items.length) {
    els.fieldList.innerHTML = "<p class='muted'>这张图还没有可展示的人工标注结果。</p>";
    return;
  }
  els.fieldList.innerHTML = activeLegIndexes().map((legIndex) => renderLegEvidenceGroup(legIndex)).join("");
  els.fieldList.querySelectorAll(".field-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.fieldKey === activeKey);
    card.addEventListener("mouseenter", () => {
      state.activeFieldKey = card.dataset.fieldKey || "";
      els.fieldList.querySelectorAll(".field-card").forEach((item) => {
        item.classList.toggle("active", item.dataset.fieldKey === state.activeFieldKey);
      });
      renderRecordPanel();
      renderOverlays();
    });
    card.addEventListener("click", () => {
      state.activeFieldKey = card.dataset.fieldKey || "";
      renderFieldCards();
      renderRecordPanel();
      renderOverlays();
    });
  });
}

function evidenceChipsForIds(evidenceIds) {
  return evidenceIds.map((regionId) => {
    const region = findRegion(regionId);
    const meta = evidenceCategoryMeta(region);
    return `<span class="evidence-chip" style="--cat:${meta.color}">
      <i class="chip-mark ${escapeText(meta.marker)}"></i>${escapeText(meta.label)} · ${escapeText(shortRegionLabel(region || { region_id: regionId }))}
    </span>`;
  }).join("");
}

function recordAnnotationsForLeg(legIndex) {
  const rows = activeArincRows().filter((row) => row.canonical_leg_index === legIndex);
  return rows.map((row, index) => ({
    row,
    number: index + 1,
    segment: arincSegmentForRow(row)
  })).filter((item) => item.segment);
}

function recordAnnotationForRow(row) {
  return recordAnnotationsForLeg(row.canonical_leg_index).find((item) => item.row.key === row.key) || null;
}

function renderRecordTag(row) {
  const annotation = recordAnnotationForRow(row);
  if (!annotation) return "";
  return `<span class="record-tag">[${annotation.number}] 424 ${escapeText(annotation.segment.label)}</span>`;
}

function renderEvidenceCard(row) {
  const evidenceIds = evidenceIdsForRow(row);
  const status = reviewStatusForRow(row, evidenceIds);
  const color = colorForRow(row);
  const dimmed = answerIsPresent(row) ? "" : " dimmed";
  return `<article class="field-card${dimmed}" data-field-key="${escapeText(row.key)}" style="--accent:${color}">
    <div class="meta">证据结论航段 ${escapeText(row.canonical_leg_index)} · ${escapeText(row.leg_type || "-")}</div>
    <h2>${renderRecordTag(row)}${escapeText(FIELD_LABELS[row.field_name] || row.field_name)}</h2>
    <p class="value">${escapeText(formatAnswer(row.expected_answer))}</p>
    <div class="meta">${escapeText(STATUS_LABELS[status] || status)} · ${evidenceIds.length} 处证据</div>
    <div class="evidence-list">${evidenceChipsForIds(evidenceIds)}</div>
  </article>`;
}

function renderRawRecordMarkers(annotations) {
  return annotations.map((item, lane) => {
    const start = Math.max(0, Number(item.segment.start || 0));
    const length = Math.max(1, Number(item.segment.end || 0) - start);
    const active = state.activeFieldKey === item.row.key;
    const dimmed = state.activeFieldKey && !active ? " dimmed" : "";
    const label = `[${item.number}] ${item.segment.label}`;
    return `<div class="record-marker${active ? " active" : ""}${dimmed}" title="${escapeText(label)}" style="--grid-start:${start + 1};--len:${length};--lane:${lane}">
      <span class="record-underline"></span>
      <span class="record-stem"></span>
      <span class="record-label">[${item.number}]</span>
    </div>`;
  }).join("");
}

function renderRecordChars(record) {
  const text = String(record || "").padEnd(132, " ").slice(0, 132);
  return Array.from(text).map((char, index) => {
    const content = char === " " ? "&nbsp;" : escapeText(char);
    return `<span class="record-char" style="--col:${index + 1}">${content}</span>`;
  }).join("");
}

function renderRawRecordBlock(legIndex) {
  const record = rawRecordForLeg(legIndex);
  const first = legRowsForIndex(legIndex)[0] || {};
  const annotations = recordAnnotationsForLeg(legIndex);
  const markerHeight = Math.max(1, annotations.length) * 28 + 18;
  return `<section class="raw-record-card">
    <div class="meta">424 132 位编码文本 · 映射到证据结论航段 ${escapeText(legIndex)}</div>
    <h2>SEQ ${escapeText(first.source_seq_no || "-")} · ${escapeText(first.source_trans_ident || "-")} · ${escapeText(first.leg_type || "-")}</h2>
    <div class="raw-record-visual" style="--marker-height:${markerHeight}px">
      <div class="raw-record-canvas">
        <code class="raw-record-text" aria-label="${escapeText(record || "No raw 424 record")}">${renderRecordChars(record)}</code>
        ${renderRawRecordMarkers(annotations)}
      </div>
    </div>
  </section>`;
}

function renderRecordPanel() {
  if (!els.recordPanel) return;
  const legs = activeLegIndexes();
  if (!legs.length) {
    els.recordPanel.innerHTML = "";
    return;
  }
  els.recordPanel.innerHTML = legs.map((legIndex) => renderRawRecordBlock(legIndex)).join("");
}

function renderLegEvidenceGroup(legIndex) {
  const rows = activeRows().filter((row) => row.canonical_leg_index === legIndex);
  if (!rows.length) return "";
  return `<section class="evidence-group">
    <div class="numbered-field-list">
      ${rows.map((row) => renderEvidenceCard(row)).join("")}
    </div>
  </section>`;
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
  for (const item of displayItems()) {
    for (const regionId of evidenceIdsForItem(item)) {
      const mapKey = canonicalRegionId(regionId);
      if (!mapKey) continue;
      if (!map.has(mapKey)) map.set(mapKey, []);
      map.get(mapKey).push(item);
    }
  }
  return map;
}

function markerSvg(meta, x, y, size = 18) {
  const color = meta.color;
  if (meta.marker === "diamond") {
    const mid = size / 2;
    return `<path d="M ${x + mid} ${y} L ${x + size} ${y + mid} L ${x + mid} ${y + size} L ${x} ${y + mid} Z" fill="${color}" fill-opacity="0.92"></path>`;
  }
  if (meta.marker === "triangle") {
    return `<path d="M ${x + size / 2} ${y} L ${x + size} ${y + size} L ${x} ${y + size} Z" fill="${color}" fill-opacity="0.92"></path>`;
  }
  if (meta.marker === "circle") {
    return `<circle cx="${x + size / 2}" cy="${y + size / 2}" r="${size / 2}" fill="${color}" fill-opacity="0.92"></circle>`;
  }
  if (meta.marker === "text") {
    return `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="3" fill="${color}" fill-opacity="0.92"></rect>
      <text x="${x + size / 2}" y="${y + size * 0.7}" text-anchor="middle" font-size="${size * 0.7}" font-weight="700" fill="white">T</text>`;
  }
  return `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="2" fill="${color}" fill-opacity="0.92"></rect>`;
}

function renderBoxes() {
  const naturalWidth = els.chartImage.naturalWidth || state.current?.manifest?.image_dimensions?.width || 1;
  const naturalHeight = els.chartImage.naturalHeight || state.current?.manifest?.image_dimensions?.height || 1;
  els.boxOverlay.setAttribute("viewBox", `0 0 ${naturalWidth} ${naturalHeight}`);
  const evidenceMap = activeEvidenceMap();
  const activeKey = ensureActiveField();
  els.boxOverlay.innerHTML = Array.from(evidenceMap.entries()).map(([regionId, items]) => {
    const region = findRegion(regionId);
    if (!region) return "";
    const rect = regionRect(region, naturalWidth, naturalHeight);
    const active = Boolean(activeKey && items.some((item) => item.key === activeKey));
    const meta = evidenceCategoryMeta(region);
    const opacity = active ? 0.96 : 0.16;
    const markerX = Math.max(2, rect.x - 4);
    const markerY = Math.max(2, rect.y - 22);
    return `<g opacity="${active ? 1 : 0.28}">
      <rect x="${rect.x}" y="${rect.y}" width="${rect.w}" height="${rect.h}" rx="4"
        fill="${meta.color}" fill-opacity="0.11" stroke="${meta.color}" stroke-width="${active ? 3 : 2}" stroke-opacity="${opacity}" stroke-dasharray="${meta.dash}"></rect>
      ${markerSvg(meta, markerX, markerY, 18)}
    </g>`;
  }).join("");
}

function renderLeaders() {
  const shellRect = els.viewerShell.getBoundingClientRect();
  const imageRect = els.chartImage.getBoundingClientRect();
  const shellWidth = els.viewerShell.clientWidth;
  const shellHeight = els.viewerShell.clientHeight;
  els.leaderOverlay.setAttribute("viewBox", `0 0 ${shellWidth} ${shellHeight}`);
  const paths = [];
  const activeKey = ensureActiveField();
  for (const item of displayItems()) {
    const card = els.fieldList.querySelector(`[data-field-key="${CSS.escape(item.key)}"]`);
    if (!card) continue;
    const cardRect = card.getBoundingClientRect();
    if (cardRect.bottom < shellRect.top || cardRect.top > shellRect.bottom) continue;
    const endX = cardRect.left - shellRect.left + 2;
    const endY = cardRect.top - shellRect.top + Math.min(52, Math.max(30, cardRect.height / 2));
    const active = Boolean(activeKey && activeKey === item.key);
    for (const regionId of evidenceIdsForItem(item)) {
      const region = findRegion(regionId);
      if (!region) continue;
      const meta = evidenceCategoryMeta(region);
      const box = region.bbox || {};
      const startX = imageRect.left - shellRect.left + (Number(box.x_center || 0.5) + Number(box.width || 0) / 2) * imageRect.width;
      const startY = imageRect.top - shellRect.top + Number(box.y_center || 0.5) * imageRect.height;
      const midX = startX + Math.max(80, (endX - startX) * 0.48);
      const path = `M ${startX.toFixed(1)} ${startY.toFixed(1)} C ${midX.toFixed(1)} ${startY.toFixed(1)}, ${midX.toFixed(1)} ${endY.toFixed(1)}, ${endX.toFixed(1)} ${endY.toFixed(1)}`;
      paths.push(`<path d="${path}" fill="none" stroke="${meta.color}" stroke-width="${active ? 2.4 : 1.2}" stroke-opacity="${active ? 0.76 : 0.14}" stroke-dasharray="${meta.dash}"></path>`);
      if (active) paths.push(`<circle cx="${startX.toFixed(1)}" cy="${startY.toFixed(1)}" r="3.5" fill="${meta.color}" fill-opacity="0.9"></circle>`);
    }
  }
  els.leaderOverlay.innerHTML = paths.join("");
}

function renderOverlays() {
  renderBoxes();
  renderLeaders();
}

function chartNaturalSize() {
  const dimensions = state.current?.manifest?.image_dimensions || {};
  return {
    width: els.chartImage.naturalWidth || Number(dimensions.width || 0),
    height: els.chartImage.naturalHeight || Number(dimensions.height || 0)
  };
}

function computeFitZoom() {
  const { width, height } = chartNaturalSize();
  if (!width || !height) return 1;
  const paneWidth = Math.max(320, els.chartPane.clientWidth - 24);
  const paneHeight = Math.max(360, els.chartPane.clientHeight - 24);
  return clamp(Math.min(paneWidth / width, paneHeight / height), CHART_ZOOM_MIN, CHART_ZOOM_MAX);
}

function applyChartZoom({ render = true } = {}) {
  const { width, height } = chartNaturalSize();
  if (!width || !height) return;
  state.chartZoom = clamp(state.chartZoom || state.fitZoom || 1, CHART_ZOOM_MIN, CHART_ZOOM_MAX);
  els.chartFrame.style.width = `${Math.round(width * state.chartZoom)}px`;
  els.chartFrame.style.height = `${Math.round(height * state.chartZoom)}px`;
  els.chartPane.classList.toggle("zoomed", state.chartZoom > state.fitZoom * 1.01);
  if (els.chartZoomValue) els.chartZoomValue.textContent = zoomText(state.chartZoom);
  if (render) window.requestAnimationFrame(renderOverlays);
}

function fitChartToPane() {
  state.fitZoom = computeFitZoom();
  if (state.zoomMode === "fit") state.chartZoom = state.fitZoom;
  applyChartZoom();
}

function setChartZoom(value, mode = "manual") {
  state.zoomMode = mode;
  state.chartZoom = clamp(value, CHART_ZOOM_MIN, CHART_ZOOM_MAX);
  applyChartZoom();
}

function adjustChartZoom(direction) {
  setChartZoom((state.chartZoom || state.fitZoom || 1) + direction * CHART_ZOOM_STEP);
}

function fitChartZoom() {
  state.zoomMode = "fit";
  fitChartToPane();
}

function actualSizeChartZoom() {
  setChartZoom(1, "manual");
}

function clampPanelWidth(width) {
  const shellWidth = els.viewerShell.clientWidth || window.innerWidth;
  const maxWidth = Math.max(360, shellWidth - 470);
  return Math.round(Math.max(360, Math.min(maxWidth, width)));
}

function applyRightPanelWidth(width) {
  const nextWidth = clampPanelWidth(width);
  document.documentElement.style.setProperty("--showcase-right-width", `${nextWidth}px`);
  localStorage.setItem("shujuji_showcase_right_width", String(nextWidth));
  fitChartToPane();
  renderOverlays();
}

function renderAll() {
  const manifest = state.current?.manifest || {};
  els.chartMeta.textContent = `${manifest.chart_id || ""} · ${manifest.chart_name || ""}`;
  els.chartInput.value = manifest.chart_id || "";
  els.chartSelect.value = manifest.chart_id || "";
  updateEditAnnotationLink();
  renderLegOptions();
  fitChartToPane();
  renderFieldCards();
  renderRecordPanel();
  renderOverlays();
}

async function loadCharts() {
  const data = await getJson(apiUrl("/api/charts", { scope: "queue", annotator: "" }));
  state.charts = data.charts || [];
  els.chartSelect.innerHTML = state.charts.map((chart) => {
    const extra = chart.claim_status === "submitted" ? " · 已提交" : chart.claimed_by ? ` · ${chart.claimed_by}` : "";
    return `<option value="${escapeText(chart.chart_id)}">${escapeText(chart.chart_id + extra)}</option>`;
  }).join("");
}

async function loadChart(chartId) {
  if (!chartId) throw new Error("请先选择 chart_id");
  const chartRow = state.charts.find((chart) => chart.chart_id === chartId) || {};
  const rowAnnotator = chartRow.original_annotator || chartRow.claimed_by || "";
  const data = await getJson(apiUrl("/api/chart", { chart_id: chartId, annotator: rowAnnotator }));
  state.current = data;
  state.activeFieldKey = "";
  state.zoomMode = "fit";
  const sourceRegions = data.annotation?.regions || data.draft?.regions || [];
  state.regions = sourceRegions.map(normalizeRegion);
  state.fieldReviews = normalizeFieldReviews(data.annotation?.field_reviews || data.draft?.field_reviews || {});
  state.rows = buildFieldRows();
  const requestedLeg = Number(params.get("leg") || state.currentLeg || 1);
  const reviewedRows = state.rows.filter((row) => answerIsPresent(row) && state.fieldReviews[row.key]);
  const legSourceRows = reviewedRows.length ? reviewedRows : state.rows;
  state.currentLeg = legSourceRows.some((row) => row.canonical_leg_index === requestedLeg)
    ? requestedLeg
    : (legSourceRows[0]?.canonical_leg_index || 1);
  els.chartImage.onload = () => {
    fitChartToPane();
    renderOverlays();
  };
  els.chartImage.src = withAccessToken(data.image_url);
  els.chartImage.alt = `航图 ${chartId}`;
  renderAll();
}

function bindEvents() {
  const savedWidth = Number(localStorage.getItem("shujuji_showcase_right_width") || 0);
  if (savedWidth) applyRightPanelWidth(savedWidth);
  els.chartZoomOut?.addEventListener("click", () => adjustChartZoom(-1));
  els.chartZoomIn?.addEventListener("click", () => adjustChartZoom(1));
  els.chartZoomFit?.addEventListener("click", fitChartZoom);
  els.chartZoomActual?.addEventListener("click", actualSizeChartZoom);
  els.chartPane.addEventListener("wheel", (event) => {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    adjustChartZoom(event.deltaY < 0 ? 1 : -1);
  }, { passive: false });
  els.loadChartBtn.addEventListener("click", () => loadChart(els.chartInput.value.trim()).catch((error) => showToast(error.message)));
  els.chartInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") loadChart(els.chartInput.value.trim()).catch((error) => showToast(error.message));
  });
  els.chartSelect.addEventListener("change", () => loadChart(els.chartSelect.value).catch((error) => showToast(error.message)));
  els.legSelect.addEventListener("change", () => {
    state.currentLeg = Number(els.legSelect.value || 1);
    state.activeFieldKey = "";
    renderFieldCards();
    renderRecordPanel();
    renderOverlays();
  });
  els.showAllLegs.addEventListener("change", () => {
    state.activeFieldKey = "";
    renderFieldCards();
    renderRecordPanel();
    renderOverlays();
  });
  els.resizeHandle?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const shellRect = els.viewerShell.getBoundingClientRect();
    state.resizing = {
      shellRight: shellRect.right,
      pointerId: event.pointerId
    };
    els.resizeHandle.setPointerCapture(event.pointerId);
    document.body.classList.add("resizing-columns");
  });
  els.resizeHandle?.addEventListener("pointermove", (event) => {
    if (!state.resizing) return;
    applyRightPanelWidth(state.resizing.shellRight - event.clientX - 14);
  });
  function endResize(event) {
    if (!state.resizing) return;
    try {
      els.resizeHandle.releasePointerCapture(state.resizing.pointerId);
    } catch {}
    state.resizing = null;
    document.body.classList.remove("resizing-columns");
    fitChartToPane();
    renderOverlays();
  }
  els.resizeHandle?.addEventListener("pointerup", endResize);
  els.resizeHandle?.addEventListener("pointercancel", endResize);
  els.chartPane.addEventListener("scroll", () => renderOverlays(), { passive: true });
  document.querySelector(".field-pane").addEventListener("scroll", () => renderOverlays(), { passive: true });
  window.addEventListener("resize", () => {
    const savedWidth = Number(localStorage.getItem("shujuji_showcase_right_width") || 0);
    if (savedWidth) document.documentElement.style.setProperty("--showcase-right-width", `${clampPanelWidth(savedWidth)}px`);
    fitChartToPane();
    renderOverlays();
  });
}

async function init() {
  initializeAccessToken();
  bindEvents();
  await loadCharts();
  const requestedChart = params.get("chart_id") || params.get("chart") || state.charts[0]?.chart_id || "";
  await loadChart(requestedChart);
}

init().catch((error) => showToast(error.message));
