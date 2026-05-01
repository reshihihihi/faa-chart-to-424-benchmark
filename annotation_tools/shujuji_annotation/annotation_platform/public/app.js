const DATASET_CONFIG = {
  practice10: {
    key: "practice10",
    label: "练习集 10 张",
    finalDataset: false,
    storageKey: "shujuji_practice_annotator"
  },
  formal300: {
    key: "formal300",
    label: "正式集 300 张",
    finalDataset: true,
    storageKey: "shujuji_formal_annotator"
  }
};

function detectDatasetKey() {
  const params = new URLSearchParams(window.location.search);
  const explicit = params.get("dataset");
  if (DATASET_CONFIG[explicit]) return explicit;
  if (window.location.pathname.startsWith("/practice")) return "practice10";
  if (window.location.pathname.startsWith("/formal") || window.location.pathname.startsWith("/expert")) return "formal300";
  return "formal300";
}

const datasetKey = detectDatasetKey();
const datasetConfig = DATASET_CONFIG[datasetKey] || DATASET_CONFIG.formal300;
const ACCESS_TOKEN_STORAGE_KEY = "shujuji_access_token";

function expertReviewMode() {
  return window.location.pathname.startsWith("/expert");
}

function initializeAccessToken() {
  const url = new URL(window.location.href);
  const token = url.searchParams.get("token");
  if (token) {
    sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
    url.searchParams.delete("token");
    window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`);
  }
}

initializeAccessToken();

function currentAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || "";
}

const state = {
  charts: [],
  current: null,
  dataset: datasetConfig,
  regions: [],
  fieldReviews: {},
  confirmModeDrafts: {},
  participantSource: "",
  selectedFieldKey: null,
  pendingLinkFieldKey: null,
  selectedRegionId: null,
  activeSaveMode: "final",
  drawMode: false,
  draft: null,
  drag: null,
  undoStack: [],
  flashRegionId: null,
  flashTimer: null,
  columnResize: null,
  layoutWidths: null,
  lastQuickAcceptSnapshot: null,
  formalQueueAdvancing: false,
  zooms: {
    left: 1,
    center: 0.72,
    right: 1,
    workflow: 1
  }
};

const els = {
  layout: document.querySelector(".layout"),
  workspaceToolbar: document.querySelector(".workspace-toolbar"),
  sidebarPanel: document.querySelector(".sidebar"),
  sideActionPanel: document.querySelector(".side-action-panel"),
  sideActionHint: document.querySelector(".side-action-panel .hint"),
  workspacePanel: document.querySelector(".workspace"),
  inspectorPanel: document.querySelector(".inspector"),
  workflowPanel: document.querySelector(".workflow-rail"),
  resizeHandles: document.querySelectorAll("[data-resize-handle]"),
  helpBtn: document.querySelector("#helpBtn"),
  helpOverlay: document.querySelector("#helpOverlay"),
  helpCloseBtn: document.querySelector("#helpCloseBtn"),
  fullTutorialBtn: document.querySelector("#fullTutorialBtn"),
  detailBoxTutorialBtn: document.querySelector("#detailBoxTutorialBtn"),
  identityLabel: document.querySelector(".identity-editor span"),
  participantBadge: document.querySelector("#participantBadge"),
  undoBtn: document.querySelector("#undoBtn"),
  workflowUndoBtn: document.querySelector("#workflowUndoBtn"),
  returnClaimBtn: document.querySelector("#returnClaimBtn"),
  returnWorkflowBtn: document.querySelector("#returnWorkflowBtn"),
  skipClaimBtn: document.querySelector("#skipClaimBtn"),
  saveDraftBtn: document.querySelector("#saveDraftBtn"),
  applyAnnotatorBtn: document.querySelector("#applyAnnotatorBtn"),
  pageTitle: document.querySelector(".topbar h1"),
  datasetEyebrow: document.querySelector(".eyebrow"),
  sideTitle: document.querySelector(".side-title"),
  chartList: document.querySelector("#chartList"),
  chartFilter: document.querySelector("#chartFilter"),
  currentTitle: document.querySelector("#currentTitle"),
  currentMeta: document.querySelector("#currentMeta"),
  imageStage: document.querySelector("#imageStage"),
  chartImage: document.querySelector("#chartImage"),
  overlay: document.querySelector("#overlay"),
  drawBtn: document.querySelector("#drawBtn"),
  newRegionType: document.querySelector("#newRegionType"),
  newRegionTypeHint: document.querySelector("#newRegionTypeHint"),
  saveBtn: document.querySelector("#saveBtn"),
  workflowSummary: document.querySelector("#workflowSummary"),
  workflowNextList: document.querySelector("#workflowNextList"),
  quickAcceptBtn: document.querySelector("#quickAcceptBtn"),
  undoQuickAcceptBtn: document.querySelector("#undoQuickAcceptBtn"),
  nextPendingBtn: document.querySelector("#nextPendingBtn"),
  claimCurrentBtn: document.querySelector("#claimCurrentBtn"),
  openTargetsBtn: document.querySelector("#openTargetsBtn"),
  linkSelectedFieldBtn: document.querySelector("#linkSelectedFieldBtn"),
  addRegionForFieldBtn: document.querySelector("#addRegionForFieldBtn"),
  markNoEvidenceBtn: document.querySelector("#markNoEvidenceBtn"),
  markImplicitBtn: document.querySelector("#markImplicitBtn"),
  markFieldUnsureBtn: document.querySelector("#markFieldUnsureBtn"),
  workflowDraftBtn: document.querySelector("#workflowDraftBtn"),
  workflowSaveBtn: document.querySelector("#workflowSaveBtn"),
  annotatorInput: document.querySelector("#annotatorInput"),
  emptyRegion: document.querySelector("#emptyRegion"),
  regionForm: document.querySelector("#regionForm"),
  regionRoleHint: document.querySelector("#regionRoleHint"),
  regionIdInput: document.querySelector("#regionIdInput"),
  regionTypeInput: document.querySelector("#regionTypeInput"),
  labelInput: document.querySelector("#labelInput"),
  ocrInput: document.querySelector("#ocrInput"),
  bboxX: document.querySelector("#bboxX"),
  bboxY: document.querySelector("#bboxY"),
  bboxW: document.querySelector("#bboxW"),
  bboxH: document.querySelector("#bboxH"),
  reviewActionInput: document.querySelector("#reviewActionInput"),
  notesInput: document.querySelector("#notesInput"),
  deleteRegionBtn: document.querySelector("#deleteRegionBtn"),
  acceptFrameAndNextBtn: document.querySelector("#acceptFrameAndNextBtn"),
  markFrameUnsureBtn: document.querySelector("#markFrameUnsureBtn"),
  mappingList: document.querySelector("#mappingList"),
  targetPanel: document.querySelector("#targetPanel"),
  targetList: document.querySelector("#targetList"),
  canonicalSummary: document.querySelector("#canonicalSummary"),
  canonicalCompare: document.querySelector("#canonicalCompare"),
  annotationJsonPreview: document.querySelector("#annotationJsonPreview"),
  canonicalJsonPreview: document.querySelector("#canonicalJsonPreview"),
  leftZoomOut: document.querySelector("#leftZoomOut"),
  leftZoomIn: document.querySelector("#leftZoomIn"),
  leftZoomReset: document.querySelector("#leftZoomReset"),
  leftZoomValue: document.querySelector("#leftZoomValue"),
  centerZoomOut: document.querySelector("#centerZoomOut"),
  centerZoomIn: document.querySelector("#centerZoomIn"),
  centerZoomReset: document.querySelector("#centerZoomReset"),
  centerZoomValue: document.querySelector("#centerZoomValue"),
  rightZoomOut: document.querySelector("#rightZoomOut"),
  rightZoomIn: document.querySelector("#rightZoomIn"),
  rightZoomReset: document.querySelector("#rightZoomReset"),
  rightZoomValue: document.querySelector("#rightZoomValue"),
  workflowZoomOut: document.querySelector("#workflowZoomOut"),
  workflowZoomIn: document.querySelector("#workflowZoomIn"),
  workflowZoomReset: document.querySelector("#workflowZoomReset"),
  workflowZoomValue: document.querySelector("#workflowZoomValue"),
  toast: document.querySelector("#toast")
};

const zoomDefaults = {
  left: 1,
  center: 0.72,
  right: 1,
  workflow: 1
};

const zoomLimits = {
  left: { min: 0.65, max: 1.8, step: 0.1, wheelStep: 0.05 },
  center: { min: 0.35, max: 3, step: 0.1, wheelStep: 0.08 },
  right: { min: 0.65, max: 1.8, step: 0.1, wheelStep: 0.05 },
  workflow: { min: 0.65, max: 1.8, step: 0.1, wheelStep: 0.05 }
};

const panelAreas = ["left", "center", "right", "workflow"];

const panelMinWidths = {
  left: 180,
  center: 420,
  right: 280,
  workflow: 240
};

const panelWidthVars = {
  left: "--left-panel-width",
  center: "--center-panel-width",
  right: "--inspector-panel-width",
  workflow: "--workflow-panel-width"
};

const resizePairs = {
  "left-center": ["left", "center"],
  "center-inspector": ["center", "right"],
  "inspector-workflow": ["right", "workflow"]
};

const PR28_FIELDS = [
  "Q_terminator",
  "Q1_fix_ident",
  "Q2_altitude_constraint",
  "Q3_turn",
  "Q4_course_or_radial",
  "Q5_hold_params"
];

const FIELD_LABELS = {
  Q_terminator: "航段类型",
  Q1_fix_ident: "定位点 / 导航台",
  Q2_altitude_constraint: "高度限制",
  Q3_turn: "转弯方向 / 转弯证据",
  Q4_course_or_radial: "航向 / 径向 / 航迹",
  Q5_hold_params: "等待参数"
};

const FIELD_REVIEW_LABELS = {
  pending: "待确认",
  direct_visible: "一处直接能看出",
  visible_joint: "多处合起来能看出",
  rule_default_completion: "图上证据 + 规则补全",
  insufficient_for_encoding: "图上看不够",
  supported_by_chart: "一处直接能看出",
  no_direct_chart_evidence: "图上看不够",
  implicit_or_derived: "图上证据 + 规则补全",
  not_applicable: "不适用",
  uncertain: "不确定"
};

const FIELD_REVIEW_DONE = new Set([
  "direct_visible",
  "visible_joint",
  "rule_default_completion",
  "insufficient_for_encoding",
  "supported_by_chart",
  "no_direct_chart_evidence",
  "implicit_or_derived",
  "not_applicable",
  "uncertain"
]);

const FIELD_SUPPORT_REQUIRES_EVIDENCE = new Set([
  "direct_visible",
  "visible_joint",
  "rule_default_completion"
]);

const FIELD_CONFIRM_MODES = [
  { mode: "direct_visible", label: "一处直接能看出" },
  { mode: "visible_joint", label: "多处合起来能看出" },
  { mode: "rule_default_completion", label: "图上证据 + 规则补全" },
  { mode: "insufficient_for_encoding", label: "图上看不够" },
  { mode: "uncertain", label: "不确定 / 交复核" }
];

const LEG_TYPE_LABELS = {
  CA: "爬升到高度",
  CF: "飞向指定点",
  DF: "直飞定位点",
  FM: "从定位点飞出",
  HM: "等待航段",
  IF: "初始定位点",
  RF: "半径转弯",
  TF: "航迹到定位点",
  VI: "按航向拦截"
};

const REGION_TYPE_LABELS = {
  MISSED_APPROACH_TEXT: "上方复飞文字大框",
  PLAN_VIEW: "平面图复飞相关区域",
  MISSED_APPROACH_DETAIL_AREA: "下方复飞细节总框",
  FIX_TEXT: "定位点文字",
  FIX_SYMBOL: "定位点符号",
  MISSED_APPROACH_ICON: "复飞图标",
  MISSED_APPROACH_STEP_BOX: "复飞步骤格",
  ALTITUDE_TEXT: "高度文字",
  CLIMB_ARROW: "爬升箭头",
  HEADING_TEXT: "航向文字",
  NAVAID_TEXT: "导航台文字",
  PATH_SEGMENT: "路径/转弯线段",
  RADIAL_TEXT: "径向文字",
  TURN_PHRASE: "转弯文字",
  HOLDING_ARC: "等待弧线",
  HOLDING_PATTERN: "等待图形",
  TRACK_OR_RADIAL_TEXT: "航迹/径向文字",
  OUTBOUND_INBOUND_MARK: "出航/入航标记",
  HOLDING_TIME_TEXT: "等待时间",
  DME_DISTANCE_TEXT: "DME/距离文字"
};

function metaForRegionType(type) {
  const option = Array.from(els.newRegionType?.options || []).find((item) => item.value === type);
  const sourceFieldName = option?.dataset.field || "";
  const elementRole = option?.dataset.role || "";
  const annotationScope = sourceFieldName === "REGION_CONTEXT" ? "coarse_region" : "detail_element";
  const labelText = option?.textContent?.trim() || type;
  return {
    annotation_scope: annotationScope,
    element_role: elementRole,
    source_field_name: sourceFieldName === "REGION_CONTEXT" ? "" : sourceFieldName,
    label: labelText
  };
}

function updateNewRegionTypeHint() {
  if (!els.newRegionTypeHint || !els.newRegionType) return;
  const type = els.newRegionType.value;
  const meta = metaForRegionType(type);
  const scope = meta.annotation_scope === "coarse_region" ? "大框/区域证据" : "小框/字段证据";
  const field = meta.source_field_name || "区域上下文";
  els.newRegionTypeHint.innerHTML = `
    <strong>${escapeText(type)}</strong>
    <span>保存后对应：${escapeText(field)}</span>
    <span>${escapeText(scope)} · ${escapeText(meta.element_role || "-")}</span>
  `;
}

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function escapeText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function deepClone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function unknownAnswer() {
  return { status: "unknown", value: null };
}

function answerKey(answer) {
  return JSON.stringify(answer ?? null);
}

function answerEqual(left, right) {
  return answerKey(left) === answerKey(right);
}

function isPresentAnswer(answer) {
  return answer?.status === "present";
}

function formatAnswer(answer) {
  if (!answer) return "unknown";
  if (answer.status !== "present") return answer.status || "unknown";
  if (answer.value === null || typeof answer.value === "undefined") return "present:null";
  if (typeof answer.value === "object") return JSON.stringify(answer.value);
  return String(answer.value);
}

function friendlyStatus(status) {
  const labels = {
    present: "需要图上证据",
    not_applicable: "本航图/本航段没有这个字段，无需画框",
    not_observable: "图上不可见，保留为空",
    implicit_or_derived: "图上间接/程序关系可推导",
    unknown: "编码无法确定，先不要求人工框"
  };
  return labels[status] || status || "未知";
}

function friendlyFieldName(field) {
  return FIELD_LABELS[field] ? `${field} · ${FIELD_LABELS[field]}` : field || "字段";
}

function taskFieldName(field) {
  return FIELD_LABELS[field] || field || "字段";
}

function taskLegContext(row) {
  const legIndex = row?.canonical_leg_index || canonicalLegIndexForMapping(row);
  return legIndex ? `第 ${legIndex} 段` : "";
}

function friendlyLegName(legOrMapping) {
  const legIndex = legOrMapping?.canonical_leg_index || canonicalLegIndexForMapping(legOrMapping) || "?";
  const legType = legOrMapping?.leg_type || "";
  const legTypeText = legType ? `${legType}${LEG_TYPE_LABELS[legType] ? `（${LEG_TYPE_LABELS[legType]}）` : ""}` : "未知类型";
  return `航段 ${legIndex} · ${legTypeText}`;
}

function friendlyRegionType(type) {
  return REGION_TYPE_LABELS[type] || type || "未知框类型";
}

function evidenceRegionSummary(region) {
  if (!region) return "已删除框";
  const text = String(region.ocr_text || region.label || "").trim();
  if (!text) return "点击在航图上定位";
  return text.length > 30 ? `${text.slice(0, 30)}...` : text;
}

function friendlyAnswerValue(answer, fallback = "") {
  if (!answer) return fallback || "未知";
  if (answer.status !== "present") return friendlyStatus(answer.status);
  const value = answer.value;
  if (value === null || typeof value === "undefined") return "空值";
  if (typeof value !== "object") return String(value);
  if ("altitude_ft" in value) {
    const desc = value.desc === "AT_OR_ABOVE" ? "不低于" : value.desc || "高度";
    const second = value.altitude_2_ft ? ` / ${value.altitude_2_ft} ft` : "";
    return `${desc} ${value.altitude_ft} ft${second}`;
  }
  if (value.type === "navaid_radial") {
    const dir = value.direction ? `，${value.direction}` : "";
    const chartRadial = formatChartDegree(value.radial_deg);
    return `${value.navaid || ""} R-${chartRadial}${dir}（424: ${value.radial_deg}°）`;
  }
  if (value.type === "course_deg") return `${formatChartDegree(value.course_deg)}°（424: ${value.course_deg}°）`;
  if ("inbound_course_deg" in value) {
    const parts = [];
    if (value.inbound_course_deg !== null) parts.push(`入航 ${formatChartDegree(value.inbound_course_deg)}°（424: ${value.inbound_course_deg}°）`);
    if (value.leg_time_min !== null) parts.push(`${value.leg_time_min} 分钟`);
    if (value.leg_distance_nm !== null) parts.push(`${value.leg_distance_nm} NM`);
    if (value.turn) parts.push(`${value.turn === "RIGHT" ? "右转" : value.turn}`);
    return parts.join("，") || JSON.stringify(value);
  }
  return JSON.stringify(value);
}

function formatChartDegree(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "");
  return String(Math.round(number)).padStart(3, "0");
}

function friendlyBasis(text) {
  const source = String(text || "");
  if (!source) return "";
  if (source.includes("generic candidate from CIFP424 target")) {
    return "候选来源：CIFP/424 复飞编码字段。请人工确认当前框能否在航图上证明这个字段；如果不能，请选择“不属于此框”或改挂到正确小框。";
  }
  if (source.includes("human must verify")) {
    return "操作提示：需要人工核对航图证据。";
  }
  if (source.includes("fine-grained")) {
    return "操作提示：如果这个大框太粗，请改用更精细的小框确认。";
  }
  if (source.includes("PDF text token")) return "候选来源：自动识别到的航图文字，请人工核对是否属于复飞字段。";
  if (source.includes("detected climb") || source.includes("cv_icon_component")) return "候选来源：自动识别到的复飞符号/图标，请人工核对。";
  if (source.includes("copied reviewed pilot10")) return "候选来源：从练习样本预标注迁移，请人工复核。";
  if (source.includes("MISSED_APPROACH_TEXT")) return "证据来源：上方复飞文字大框";
  if (source.includes("PLAN_VIEW")) return "证据来源：平面图复飞区域";
  if (source.includes("DETAIL") || source.includes("lower") || source.includes("profile")) return "证据来源：下方复飞细节框";
  if (source.includes("target panel") || source.includes("human-added")) return "证据来源：人工从候选字段挂接";
  return "候选来源：系统自动生成。请人工核对航图证据后再确认。";
}

function friendlyRegionNote(region) {
  if (!region) return "";
  if (region.region_type === "MISSED_APPROACH_TEXT") {
    return "这是上方复飞文字的大框。为了减少标注量，不需要把这段文字拆成很多小框；只要确认它确实覆盖完整复飞文字说明即可。";
  }
  if (region.region_type === "PLAN_VIEW") {
    return "这是平面图中与复飞有关的大区域。用于说明复飞路径、定位点、径向/航向、等待图形等上下文。";
  }
  if (region.region_type === "MISSED_APPROACH_DETAIL_AREA") {
    return "这是下方复飞细节总框。它只圈住复飞小表格/剖面复飞区域；里面的高度、箭头、fix、radial、holding 等仍要用小框单独确认。";
  }
  return `这是一个细节小框，应尽量贴紧一个可见符号或文字：${friendlyRegionType(region.region_type)}。`;
}

function canonicalAnswerAt(canonicalLegs, legIndex, field) {
  const leg = canonicalLegs.find((item) => item.leg_index === legIndex);
  return leg?.answers?.[field] || null;
}

function canonicalLegById(candidateLegId) {
  const target = state.current?.target;
  return (target?.candidate_legs || []).find((leg) => leg.candidate_leg_id === candidateLegId) || null;
}

function canonicalFieldForMapping(mapping) {
  if (mapping.expected_answer) return mapping.expected_answer;
  const leg = canonicalLegById(mapping.candidate_leg_id);
  const field = (leg?.target_fields || []).find((item) => (item.field_name || item.name) === mapping.field_name);
  return field?.expected_answer || null;
}

function canonicalLegIndexForMapping(mapping) {
  if (Number.isInteger(mapping.canonical_leg_index)) return mapping.canonical_leg_index;
  const leg = canonicalLegById(mapping.candidate_leg_id);
  if (Number.isInteger(leg?.canonical_leg_index)) return leg.canonical_leg_index;
  const match = String(mapping.candidate_leg_id || "").match(/__ma(\d+)$/);
  return match ? Number(match[1]) : null;
}

function fieldKey(legIndex, fieldName) {
  return `leg${legIndex}.${fieldName}`;
}

function fieldKeyForMapping(mapping) {
  const legIndex = canonicalLegIndexForMapping(mapping);
  return legIndex && mapping.field_name ? fieldKey(legIndex, mapping.field_name) : "";
}

function normalizeFieldReviews(source) {
  if (!source) return {};
  if (Array.isArray(source)) {
    return Object.fromEntries(source.map((item) => [item.field_key, item]).filter(([key]) => key));
  }
  if (typeof source === "object") return deepClone(source);
  return {};
}

function buildFieldRows() {
  const target = state.current?.target;
  if (!target) return [];
  return (target.candidate_legs || []).flatMap((leg) => {
    return (leg.target_fields || []).map((field) => {
      const fieldName = field.field_name || field.name || "";
      const legIndex = leg.canonical_leg_index || canonicalLegIndexForMapping({ candidate_leg_id: leg.candidate_leg_id });
      const answer = field.expected_answer || null;
      return {
        key: fieldKey(legIndex, fieldName),
        candidate_leg_id: leg.candidate_leg_id || "",
        canonical_leg_index: legIndex,
        leg_type: leg.leg_type || "",
        field_name: fieldName,
        expected_value: field.expected_value ?? field.value ?? "",
        expected_answer: answer,
        requires_review: answer?.status === "present",
        auto_status: answer?.status && answer.status !== "present"
      };
    });
  });
}

function acceptedMappingsForField(row) {
  return state.regions.flatMap((region) => {
    return (region.candidate_mappings || [])
      .filter((mapping) => mapping.human_decision === "accepted" && fieldKeyForMapping(mapping) === row.key)
      .map((mapping) => ({ region, mapping }));
  });
}

function candidateMappingsForField(row) {
  return state.regions.flatMap((region) => {
    return (region.candidate_mappings || [])
      .filter((mapping) => fieldKeyForMapping(mapping) === row.key)
      .map((mapping) => ({ region, mapping }));
  });
}

function candidateMappingsForLeg(row) {
  const legIndex = Number(row?.canonical_leg_index || 0);
  if (!legIndex) return [];
  return state.regions.flatMap((region) => {
    return (region.candidate_mappings || [])
      .filter((mapping) => {
        return canonicalLegIndexForMapping(mapping) === legIndex
          && mapping.field_name
          && mapping.field_name !== "Q_terminator"
          && !["rejected", "needs_discussion"].includes(mapping.human_decision || "pending");
      })
      .map((mapping) => ({ region, mapping }));
  });
}

function expectedAnswerValue(row) {
  return row?.expected_answer?.value ?? null;
}

function sameSourceLeg(row, region) {
  if (!row || !region) return false;
  if (region.source_candidate_leg_id && row.candidate_leg_id) {
    return region.source_candidate_leg_id === row.candidate_leg_id;
  }
  return (region.candidate_mappings || []).some((mapping) => canonicalLegIndexForMapping(mapping) === row.canonical_leg_index);
}

function regionText(region) {
  return ["region_type", "label", "ocr_text", "expected_visual_value", "element_role"]
    .map((key) => String(region?.[key] || ""))
    .join(" ")
    .toUpperCase();
}

function isHoldingParamRegion(region) {
  const regionType = region?.region_type || "";
  return ["HOLDING_PATTERN", "HOLDING_ARC", "HOLDING_TIME_TEXT", "DME_DISTANCE_TEXT", "TRACK_OR_RADIAL_TEXT", "RADIAL_TEXT", "OUTBOUND_INBOUND_MARK"].includes(regionType);
}

function isCoarseMissedApproachText(region) {
  return (region?.region_type || "") === "MISSED_APPROACH_TEXT"
    && (
      region.annotation_scope === "upper_coarse_formal_annotation"
      || regionText(region).includes("UPPER COARSE FORMAL ANNOTATION")
    );
}

function fieldEvidenceRank(row, region) {
  const regionType = region?.region_type || "";
  const value = expectedAnswerValue(row);
  if (!row || !region) return 99;
  if (regionType === "MISSED_APPROACH_TEXT") return isCoarseMissedApproachText(region) ? 99 : 60;
  if (row.field_name === "Q1_fix_ident") {
    if (["FIX_TEXT", "NAVAID_TEXT"].includes(regionType)) return 0;
    if (regionType === "FIX_SYMBOL") return 8;
    return 99;
  }
  if (row.field_name === "Q2_altitude_constraint") {
    if (regionType === "ALTITUDE_TEXT") return 0;
    if (regionType === "CLIMB_ARROW") return 8;
    return 99;
  }
  if (row.field_name === "Q3_turn") {
    if (["PATH_SEGMENT", "TURN_PHRASE"].includes(regionType)) return 0;
    if (["HOLDING_PATTERN", "HOLDING_ARC"].includes(regionType)) return 20;
    return 99;
  }
  if (row.field_name === "Q4_course_or_radial") {
    if (value?.type === "navaid_radial") {
      if (["NAVAID_TEXT", "RADIAL_TEXT", "OUTBOUND_INBOUND_MARK"].includes(regionType)) return 0;
      if (["PATH_SEGMENT", "FIX_SYMBOL"].includes(regionType)) return 12;
      return 99;
    }
    if (["HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"].includes(regionType)) return 0;
    if (regionType === "PATH_SEGMENT") return 12;
    return 99;
  }
  if (row.field_name === "Q5_hold_params") {
    if (["HOLDING_PATTERN", "HOLDING_ARC"].includes(regionType)) return 0;
    if (["HOLDING_TIME_TEXT", "DME_DISTANCE_TEXT", "TRACK_OR_RADIAL_TEXT", "RADIAL_TEXT", "OUTBOUND_INBOUND_MARK"].includes(regionType)) return 4;
    return 99;
  }
  return 50;
}

function compatibleEvidenceRegionsForField(row) {
  if (!row) return [];
  return state.regions
    .filter((region) => sameSourceLeg(row, region))
    .filter((region) => {
      const rank = fieldEvidenceRank(row, region);
      if (rank >= 50) return false;
      if (row.field_name === "Q4_course_or_radial" && expectedAnswerValue(row)?.type !== "navaid_radial") {
        return ["HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"].includes(region.region_type);
      }
      return true;
    })
    .map((region) => ({ region, rank: fieldEvidenceRank(row, region), source: "compatible-region" }));
}

function suggestedEvidenceEntriesForField(row) {
  const direct = candidateMappingsForField(row)
    .filter(({ mapping }) => !["rejected", "needs_discussion"].includes(mapping.human_decision || "pending"))
    .map(({ region, mapping }) => ({
      region,
      mapping,
      rank: fieldEvidenceRank(row, region),
      source: "candidate-mapping"
    }))
    .filter((item) => item.rank < 90);
  const compatible = compatibleEvidenceRegionsForField(row);
  const byRegion = new Map();
  [...direct, ...compatible].forEach((item) => {
    const existing = byRegion.get(item.region.region_id);
    if (!existing || item.rank < existing.rank) byRegion.set(item.region.region_id, item);
  });
  const ranked = Array.from(byRegion.values()).sort((left, right) => {
    const decisionRank = { accepted: 0, changed: 1, pending: 2 };
    const leftDecision = decisionRank[left.mapping?.human_decision || "pending"] ?? 3;
    const rightDecision = decisionRank[right.mapping?.human_decision || "pending"] ?? 3;
    return left.rank - right.rank || leftDecision - rightDecision;
  });
  const fine = ranked.filter((item) => item.rank < 50);
  return fine.length ? fine : ranked;
}

function holdingEvidenceEntriesForField(row) {
  const holdRankRow = { ...row, field_name: "Q5_hold_params" };
  const direct = candidateMappingsForField(row)
    .filter(({ region }) => isHoldingParamRegion(region))
    .map(({ region, mapping }) => ({
      region,
      mapping,
      rank: fieldEvidenceRank(holdRankRow, region),
      source: "candidate-mapping"
    }));
  const compatible = state.regions
    .filter((region) => sameSourceLeg(row, region) && isHoldingParamRegion(region))
    .map((region) => ({
      region,
      rank: fieldEvidenceRank(holdRankRow, region),
      source: "compatible-region"
    }));
  const byRegion = new Map();
  [...direct, ...compatible].forEach((item) => {
    const existing = byRegion.get(item.region.region_id);
    if (!existing || item.rank < existing.rank) byRegion.set(item.region.region_id, item);
  });
  return Array.from(byRegion.values())
    .filter((item) => item.rank < 50)
    .sort((left, right) => left.rank - right.rank);
}

function uniqueList(values) {
  return Array.from(new Set((values || []).filter(Boolean).map(String)));
}

function regionById(regionId) {
  return state.regions.find((region) => region.region_id === regionId) || null;
}

function evidenceSourceForRegion(region) {
  const type = region?.region_type || "";
  if (region?.evidence_source) return region.evidence_source;
  if (type === "MISSED_APPROACH_TEXT") return "ma_text";
  if (type === "PLAN_VIEW") return "plan_view";
  if (["MISSED_APPROACH_DETAIL_AREA", "MISSED_APPROACH_ICON", "MISSED_APPROACH_STEP_BOX", "CLIMB_ARROW"].includes(type)) {
    return "icon_detail";
  }
  if (["FIX_SYMBOL", "PATH_SEGMENT", "HOLDING_ARC", "HOLDING_PATTERN", "OUTBOUND_INBOUND_MARK"].includes(type)) {
    return "chart_graphic";
  }
  if (type) return "chart_text";
  return "other_chart_evidence";
}

function sourcesForRegionIds(regionIds) {
  return uniqueList(regionIds.map((regionId) => evidenceSourceForRegion(regionById(regionId))));
}

function supportModeFromReview(raw, evidenceIds = []) {
  const status = raw?.support_mode || raw?.review_status || "pending";
  if (status === "supported_by_chart") return evidenceIds.length ? (evidenceIds.length > 1 ? "visible_joint" : "direct_visible") : "pending";
  if (status === "no_direct_chart_evidence") return "insufficient_for_encoding";
  if (status === "implicit_or_derived") return "rule_default_completion";
  return status;
}

function suggestedEvidenceIdsForField(row) {
  if (row.field_name === "Q5_hold_params") {
    return uniqueList(holdingEvidenceEntriesForField(row).map(({ region }) => region.region_id));
  }
  if (row.leg_type === "HM" && ["Q1_fix_ident", "Q2_altitude_constraint"].includes(row.field_name)) {
    const directIds = suggestedEvidenceEntriesForField(row).map(({ region }) => region.region_id);
    const holdingIds = holdingEvidenceEntriesForField(row).map(({ region }) => region.region_id);
    return uniqueList([...directIds, ...holdingIds]);
  }
  if (row.field_name === "Q_terminator") {
    const legFieldIds = buildFieldRows()
      .filter((item) => item.requires_review && item.canonical_leg_index === row.canonical_leg_index && item.field_name !== "Q_terminator")
      .flatMap((item) => suggestedEvidenceIdsForField(item));
    if (legFieldIds.length) return uniqueList(legFieldIds);
    return uniqueList(candidateMappingsForLeg(row).map(({ region }) => region.region_id));
  }
  const candidates = suggestedEvidenceEntriesForField(row).map(({ region }) => region.region_id);
  if (candidates.length) return uniqueList(candidates);
  return uniqueList(state.regions
    .filter((region) => region.source_field_name && region.source_field_name === row.field_name)
    .map((region) => region.region_id));
}

function reviewForField(row) {
  const saved = state.fieldReviews[row.key] || {};
  const savedRequired = uniqueList(saved.required_evidence_region_ids || saved.evidence_region_ids || []);
  const savedSecondary = uniqueList(saved.secondary_evidence_region_ids || []);
  const savedHasEvidenceList = Array.isArray(saved.required_evidence_region_ids) || Array.isArray(saved.evidence_region_ids);
  const acceptedIds = uniqueList(acceptedMappingsForField(row).map(({ region }) => region.region_id));
  const hasSavedReview = Boolean(
    saved.review_status
    || saved.support_mode
    || savedRequired.length
    || savedSecondary.length
  );
  const suggestedIds = suggestedEvidenceIdsForField(row);
  let requiredIds = savedHasEvidenceList
    ? savedRequired
    : acceptedIds.length
      ? acceptedIds
      : suggestedIds;
  let supportMode = supportModeFromReview(saved, requiredIds);
  if (!hasSavedReview) supportMode = row.requires_review ? "pending" : "not_applicable";
  if (supportMode === "direct_visible" && requiredIds.length > 1 && saved.review_status === "supported_by_chart") {
    supportMode = "visible_joint";
  }
  if (supportMode === "not_applicable" || !row.requires_review) {
    requiredIds = [];
  }
  const evidenceIds = uniqueList([...requiredIds, ...savedSecondary]);
  const evidenceSource = saved.evidence_source?.length ? saved.evidence_source : sourcesForRegionIds(evidenceIds);
  return {
    ...saved,
    field_key: row.key,
    schema: saved.schema || "field_review_v2",
    review_status: supportMode,
    support_mode: supportMode,
    required_evidence_region_ids: requiredIds,
    secondary_evidence_region_ids: savedSecondary,
    evidence_region_ids: evidenceIds,
    evidence_source: evidenceSource,
    checked_scopes: saved.checked_scopes || saved.checked_sources || sourcesForRegionIds(evidenceIds),
    checked_sources: saved.checked_sources || saved.checked_scopes || sourcesForRegionIds(evidenceIds),
    reviewed_answer: row.expected_answer || null,
    notes: saved.notes || "",
    autofilled_evidence: !hasSavedReview && suggestedIds.length > 0
  };
}

function setFieldReview(row, reviewStatus, notes = "", options = {}) {
  if (typeof notes === "object" && notes !== null) {
    options = notes;
    notes = options.notes || "";
  }
  const current = reviewForField(row);
  const requiredIds = uniqueList(
    options.requiredIds
    || options.required_evidence_region_ids
    || current.required_evidence_region_ids
    || []
  );
  const secondaryIds = uniqueList(
    options.secondaryIds
    || options.secondary_evidence_region_ids
    || current.secondary_evidence_region_ids
    || []
  );
  const evidenceIds = uniqueList([...requiredIds, ...secondaryIds]);
  const supportMode = supportModeFromReview({ review_status: reviewStatus }, evidenceIds);
  const checkedScopes = uniqueList(options.checkedScopes || options.checked_scopes || sourcesForRegionIds(evidenceIds));
  const existing = state.fieldReviews[row.key] || {};
  state.fieldReviews[row.key] = {
    ...existing,
    schema: "field_review_v2",
    field_key: row.key,
    chart_id: state.current?.manifest?.chart_id || "",
    candidate_leg_id: row.candidate_leg_id,
    canonical_leg_index: row.canonical_leg_index,
    leg_type: row.leg_type,
    field_name: row.field_name,
    canonical_answer: row.expected_answer || null,
    review_status: supportMode,
    support_mode: supportMode,
    required_evidence_region_ids: supportMode === "insufficient_for_encoding" ? [] : requiredIds,
    secondary_evidence_region_ids: supportMode === "insufficient_for_encoding" ? [] : secondaryIds,
    evidence_region_ids: supportMode === "insufficient_for_encoding" ? [] : evidenceIds,
    evidence_source: supportMode === "insufficient_for_encoding" ? [] : sourcesForRegionIds(evidenceIds),
    checked_scopes: checkedScopes,
    checked_sources: checkedScopes,
    notes: notes || existing.notes || "",
    reviewed_by: currentAnnotator() || "",
    reviewed_at: supportMode === "pending" ? (existing.reviewed_at || "") : new Date().toISOString()
  };
  if (supportMode !== "pending") delete state.confirmModeDrafts[row.key];
}

function selectedFieldRow() {
  const rows = buildFieldRows();
  return rows.find((row) => row.key === state.selectedFieldKey) || rows.find((row) => reviewForField(row).review_status === "pending") || null;
}

function selectField(rowOrKey) {
  const row = typeof rowOrKey === "string"
    ? buildFieldRows().find((item) => item.key === rowOrKey)
    : rowOrKey;
  if (!row) return;
  state.selectedFieldKey = row.key;
  const review = reviewForField(row);
  const firstEvidenceRegionId = review.evidence_region_ids?.[0];
  if (firstEvidenceRegionId) state.selectedRegionId = firstEvidenceRegionId;
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
}

function recommendedRegionTypeForField(fieldName) {
  return {
    Q_terminator: "MISSED_APPROACH_ICON",
    Q1_fix_ident: "FIX_TEXT",
    Q2_altitude_constraint: "ALTITUDE_TEXT",
    Q3_turn: "PATH_SEGMENT",
    Q4_course_or_radial: "TRACK_OR_RADIAL_TEXT",
    Q5_hold_params: "HOLDING_PATTERN"
  }[fieldName] || "MISSED_APPROACH_TEXT";
}

function mappingFromFieldRow(row, accepted = true) {
  return {
    candidate_leg_id: row.candidate_leg_id || "",
    canonical_leg_index: row.canonical_leg_index || null,
    leg_type: row.leg_type || "",
    field_name: row.field_name,
    expected_value: row.expected_value,
    expected_answer: row.expected_answer || null,
    match_basis: "human field-review queue",
    confidence: null,
    human_decision: accepted ? "accepted" : "pending",
    human_notes: ""
  };
}

function setFieldEvidenceDraft(row, requiredIds) {
  setFieldReview(row, "pending", {
    requiredIds,
    checkedScopes: sourcesForRegionIds(requiredIds)
  });
}

function ensureMappingForRegion(row, region, decision = "pending") {
  const existing = (region.candidate_mappings || []).find((mapping) => fieldKeyForMapping(mapping) === row.key);
  if (existing) {
    existing.human_decision = decision || existing.human_decision || "pending";
    return existing;
  }
  const mapping = mappingFromFieldRow(row, decision === "accepted");
  mapping.human_decision = decision;
  region.candidate_mappings.push(mapping);
  return mapping;
}

function updateRegionMappingDecision(row, regionId, decision, note = "") {
  const region = regionById(regionId);
  if (!region) return;
  (region.candidate_mappings || []).forEach((mapping) => {
    if (fieldKeyForMapping(mapping) !== row.key) return;
    mapping.human_decision = decision;
    if (note) mapping.human_notes = note;
  });
}

function applyEvidenceSelectionToMappings(row, requiredIds, supportMode) {
  const requiredSet = new Set(requiredIds);
  const createdMappings = [];
  state.regions.forEach((region) => {
    const mappings = region.candidate_mappings || [];
    mappings.forEach((mapping) => {
      if (fieldKeyForMapping(mapping) !== row.key) return;
      if (requiredSet.has(region.region_id)) {
        mapping.human_decision = "accepted";
        mapping.human_notes = supportMode === "visible_joint"
          ? "Selected as necessary evidence for multi-evidence support."
          : supportMode === "rule_default_completion"
            ? "Selected as premise evidence for rule/default completion."
            : mapping.human_notes || "";
      } else if (mapping.human_decision === "accepted") {
        mapping.human_decision = "rejected";
        mapping.human_notes = mapping.human_notes || "Removed from the field evidence basket.";
      }
    });
    if (requiredSet.has(region.region_id)) {
      const existed = (region.candidate_mappings || []).some((mapping) => fieldKeyForMapping(mapping) === row.key);
      const created = ensureMappingForRegion(row, region, "accepted");
      if (!existed) createdMappings.push({ region, mapping: created });
      region.human_review.review_action = "accept";
    }
  });
  return createdMappings;
}

function linkSelectedFieldToRegion({ accept = true } = {}) {
  const row = selectedFieldRow();
  const region = selectedRegion();
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return false;
  }
  if (!row) {
    showToast("当前没有选中的待审字段。");
    return false;
  }
  if (!region) {
    showToast("先在航图上选中一个证据框。");
    return false;
  }
  pushUndo("调整图上依据");
  const review = reviewForField(row);
  const evidenceIds = uniqueList(review.required_evidence_region_ids || []);
  const alreadySelected = evidenceIds.includes(region.region_id);
  const nextIds = alreadySelected
    ? evidenceIds.filter((regionId) => regionId !== region.region_id)
    : [...evidenceIds, region.region_id];
  if (alreadySelected) {
    updateRegionMappingDecision(row, region.region_id, "rejected", "Removed from the field evidence basket.");
  } else {
    ensureMappingForRegion(row, region, "pending");
  }
  setFieldEvidenceDraft(row, nextIds);
  flashRegion(region.region_id);
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  showToast(alreadySelected
    ? "已移除这处依据。请选择这些地方怎么支持判断。"
    : "已加入这处依据。请选择这些地方怎么支持判断。");
  return true;
}

function startDrawRegionForSelectedField() {
  const row = selectedFieldRow();
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return;
  }
  if (!row) {
    showToast("请先选择一个待审字段。");
    return;
  }
  const type = recommendedRegionTypeForField(row.field_name);
  if (els.newRegionType) {
    els.newRegionType.value = type;
    updateNewRegionTypeHint();
  }
  state.pendingLinkFieldKey = row.key;
  state.drawMode = true;
  els.drawBtn.classList.add("primary");
  els.drawBtn.textContent = "正在画证据框";
  showToast("请在航图上拖出能支持这个判断的位置。");
}

function removeEvidenceFromSelectedField(regionId) {
  const row = selectedFieldRow();
  if (!row || !canAnnotateCurrent()) return;
  const review = reviewForField(row);
  const nextIds = uniqueList(review.required_evidence_region_ids || []).filter((item) => item !== regionId);
  pushUndo("移除图上依据");
  updateRegionMappingDecision(row, regionId, "rejected", "Removed from the field evidence basket.");
  setFieldEvidenceDraft(row, nextIds);
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  showToast("已移除这处依据。");
}

function recommendedSupportModeForField(row, evidenceIds) {
  if (!row) return "";
  if (row.field_name === "Q_terminator") return "visible_joint";
  if (!evidenceIds.length) return "";
  if (row.leg_type === "HM" && ["Q1_fix_ident", "Q2_altitude_constraint"].includes(row.field_name)) {
    return "rule_default_completion";
  }
  if (row.field_name === "Q5_hold_params") return "rule_default_completion";
  return evidenceIds.length > 1 ? "visible_joint" : "direct_visible";
}

function selectedSupportModeForField(row, evidenceIds, reviewStatus = "pending") {
  if (!row) return "";
  const drafted = state.confirmModeDrafts[row.key];
  if (drafted) return drafted;
  const saved = supportModeFromReview({ review_status: reviewStatus }, evidenceIds);
  if (reviewStatus !== "pending" && FIELD_REVIEW_DONE.has(saved)) return saved;
  return recommendedSupportModeForField(row, evidenceIds);
}

function setSupportModeDraft(row, supportMode) {
  if (!row || !supportMode) return;
  state.confirmModeDrafts[row.key] = supportMode;
  renderWorkflowPanel();
}

function renderSupportModeChoices(row, evidenceIds, reviewStatus, disabled) {
  const selectedMode = selectedSupportModeForField(row, evidenceIds, reviewStatus);
  const recommendedMode = recommendedSupportModeForField(row, evidenceIds);
  return FIELD_CONFIRM_MODES.map(({ mode, label }) => {
    const selected = mode === selectedMode;
    const recommended = mode === recommendedMode;
    const classes = [
      "support-mode-option",
      selected ? "selected" : "",
      recommended ? "recommended" : ""
    ].filter(Boolean).join(" ");
    return `
      <button type="button" class="${classes}" data-support-mode="${mode}" aria-pressed="${selected ? "true" : "false"}" ${disabled}>
        <span>${escapeText(label)}</span>
        ${recommended ? '<small>推荐</small>' : ""}
      </button>
    `;
  }).join("");
}

function confirmSelectedField(supportMode) {
  const row = selectedFieldRow();
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return;
  }
  if (!row) {
    showToast("当前没有选中的待审字段。");
    return;
  }
  if (!supportMode) {
    showToast("请先选择这些地方怎么支持判断。");
    return;
  }
  const review = reviewForField(row);
  const requiredIds = uniqueList(review.required_evidence_region_ids || []);
  if (FIELD_SUPPORT_REQUIRES_EVIDENCE.has(supportMode) && !requiredIds.length) {
    showToast("这个判断需要先选至少一处图上依据。若图上确实看不够，请选“图上看不够”。");
    return;
  }
  const notes = supportMode === "insufficient_for_encoding" || supportMode === "uncertain"
    ? (window.prompt("可选：写一句判断依据或复核备注。", review.notes || "") || "")
    : review.notes || "";
  pushUndo("确认图上依据");
  const idsUsedAsSupport = FIELD_SUPPORT_REQUIRES_EVIDENCE.has(supportMode) ? requiredIds : [];
  applyEvidenceSelectionToMappings(row, idsUsedAsSupport, supportMode);
  setFieldReview(row, supportMode, {
    requiredIds,
    secondaryIds: review.secondary_evidence_region_ids || [],
    checkedScopes: requiredIds.length ? sourcesForRegionIds(requiredIds) : ["ma_text", "plan_view", "icon_detail"],
    notes
  });
  advanceAfterFieldCommit(row, `已记录：${FIELD_REVIEW_LABELS[supportMode] || supportMode}。`);
}

function markSelectedField(reviewStatus) {
  confirmSelectedField(supportModeFromReview({ review_status: reviewStatus }));
}

function nextPendingField(afterKey = state.selectedFieldKey) {
  const rows = buildFieldRows().filter((row) => row.requires_review);
  if (!rows.length) return null;
  const foundIndex = rows.findIndex((row) => row.key === afterKey);
  const startIndex = foundIndex >= 0 ? foundIndex : -1;
  for (let offset = 1; offset <= rows.length; offset += 1) {
    const row = rows[(startIndex + offset) % rows.length];
    if (reviewForField(row).review_status === "pending") return row;
  }
  return null;
}

function advanceAfterFieldCommit(row, message) {
  const next = nextPendingField(row.key);
  if (next && next.key !== row.key) {
    state.selectedFieldKey = next.key;
    const nextReview = reviewForField(next);
    if (nextReview.evidence_region_ids?.[0]) state.selectedRegionId = nextReview.evidence_region_ids[0];
    showToast(`${message} 已自动进入下一个待审字段。`);
  } else {
    state.selectedFieldKey = row.key;
    showToast(`${message} 本图没有更多待审字段。`);
  }
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
}

function buildAnnotationCanonicalJson() {
  const canonical = state.current?.canonical_gt;
  const target = state.current?.target;
  const chartId = state.current?.manifest?.chart_id || "";
  const procedure = canonical?.procedure || {
    airport: chartId.slice(0, 4),
    approach_ident: chartId.split("_")[1] || "",
    chart_name: state.current?.manifest?.procedure_key || ""
  };
  const canonicalLegs = canonical?.missed_approach?.legs || [];
  const targetLegs = target?.candidate_legs || [];
  const legCount = canonicalLegs.length || targetLegs.length;
  const legs = Array.from({ length: legCount }, (_, index) => ({
    leg_index: index + 1,
    answers: Object.fromEntries(PR28_FIELDS.map((field) => {
      const canonicalAnswer = canonicalAnswerAt(canonicalLegs, index + 1, field);
      // Non-present fields have no direct visual evidence task. Present fields,
      // including Q_terminator, stay unknown until the field-review queue gives
      // either a supporting box or an explicit no-direct-evidence conclusion.
      const initialAnswer = canonicalAnswer && !isPresentAnswer(canonicalAnswer)
        ? deepClone(canonicalAnswer)
        : unknownAnswer();
      return [field, initialAnswer];
    }))
  }));
  const acceptedMappings = [];

  buildFieldRows().forEach((row) => {
    if (!row.requires_review || !legs[row.canonical_leg_index - 1]) return;
    const review = reviewForField(row);
    const supportMode = review.support_mode || review.review_status;
    if (["direct_visible", "visible_joint", "rule_default_completion"].includes(supportMode)) {
      legs[row.canonical_leg_index - 1].answers[row.field_name] = deepClone(row.expected_answer || unknownAnswer());
    } else if (supportMode === "insufficient_for_encoding" || supportMode === "no_direct_chart_evidence") {
      legs[row.canonical_leg_index - 1].answers[row.field_name] = { status: "not_observable", value: null };
    } else if (supportMode === "not_applicable") {
      legs[row.canonical_leg_index - 1].answers[row.field_name] = { status: "not_applicable", value: null };
    }
  });

  state.regions.forEach((region) => {
    (region.candidate_mappings || []).forEach((mapping) => {
      if (mapping.human_decision !== "accepted") return;
      if (!PR28_FIELDS.includes(mapping.field_name)) return;
      const mappedFieldKey = fieldKeyForMapping(mapping);
      const mappedRow = buildFieldRows().find((row) => row.key === mappedFieldKey);
      if (mappedRow?.requires_review) return;
      const legIndex = canonicalLegIndexForMapping(mapping);
      const answer = mapping.human_answer || canonicalFieldForMapping(mapping);
      if (!legIndex || !answer || !legs[legIndex - 1]) return;
      legs[legIndex - 1].answers[mapping.field_name] = deepClone(answer);
      acceptedMappings.push(mapping);
    });
  });

  return {
    chart_id: chartId,
    procedure,
    missed_approach: {
      leg_count: { status: "present", value: legCount },
      legs
    }
  };
}

function flattenCanonicalAnswers(doc) {
  const rows = [];
  const legCount = doc?.missed_approach?.leg_count;
  rows.push({ key: "leg_count", answer: legCount });
  (doc?.missed_approach?.legs || []).forEach((leg) => {
    PR28_FIELDS.forEach((field) => {
      rows.push({
        key: `leg${leg.leg_index}.${field}`,
        leg_index: leg.leg_index,
        field,
        answer: leg.answers?.[field]
      });
    });
  });
  return rows;
}

function compareCanonicalJson(predicted, canonical) {
  const gtRows = flattenCanonicalAnswers(canonical);
  const predByKey = new Map(flattenCanonicalAnswers(predicted).map((row) => [row.key, row.answer]));
  let matched = 0;
  let observable = 0;
  let presentTotal = 0;
  let presentMatched = 0;
  let presentCovered = 0;
  let autoStatusTotal = 0;
  const rows = gtRows.map((row) => {
    const predictedAnswer = predByKey.get(row.key) || unknownAnswer();
    const isCovered = predictedAnswer.status !== "unknown";
    const isMatch = answerEqual(predictedAnswer, row.answer);
    const requiresBoxEvidence = row.key !== "leg_count" && row.field !== "Q_terminator" && isPresentAnswer(row.answer);
    const autoStatusField = row.key !== "leg_count" && (row.field === "Q_terminator" || !isPresentAnswer(row.answer));
    if (isCovered) observable += 1;
    if (isMatch) matched += 1;
    if (requiresBoxEvidence) {
      presentTotal += 1;
      if (isCovered) presentCovered += 1;
      if (isMatch) presentMatched += 1;
    }
    if (autoStatusField) autoStatusTotal += 1;
    return {
      ...row,
      predicted: predictedAnswer,
      match: isMatch,
      covered: isCovered,
      requiresBoxEvidence,
      autoStatusField
    };
  });
  return {
    total: gtRows.length,
    matched,
    covered: observable,
    present_total: presentTotal,
    present_matched: presentMatched,
    present_covered: presentCovered,
    auto_status_total: autoStatusTotal,
    full_alignment_rate: gtRows.length ? matched / gtRows.length : 0,
    overall_evidence_coverage: gtRows.length ? observable / gtRows.length : 0,
    present_alignment_rate: presentTotal ? presentMatched / presentTotal : 1,
    present_coverage: presentTotal ? presentCovered / presentTotal : 1,
    rows
  };
}

function cleanParticipantId(value) {
  return String(value || "")
    .trim()
    .replace(/[^\w.-]+/g, "_")
    .slice(0, 64);
}

function generatedParticipantId() {
  const randomPart = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `P${randomPart}`;
}

function participantIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return cleanParticipantId(
    params.get("expert")
    || params.get("reviewer")
    || params.get("participant")
    || params.get("annotator")
    || params.get("user")
    || ""
  );
}

function participantStorageKey() {
  return expertReviewMode() ? "shujuji_expert_reviewer" : datasetConfig.storageKey;
}

function ensureParticipantId() {
  const fromUrl = participantIdFromUrl();
  const stored = cleanParticipantId(localStorage.getItem(participantStorageKey()) || "");
  const participantId = fromUrl || stored || generatedParticipantId();
  state.participantSource = fromUrl ? "链接身份" : stored ? "本机保存身份" : "临时本机身份";
  localStorage.setItem(participantStorageKey(), participantId);
  if (els.annotatorInput) els.annotatorInput.value = participantId;
  updateParticipantBadge(participantId);
  return participantId;
}

function currentAnnotator() {
  return cleanParticipantId(els.annotatorInput?.value || localStorage.getItem(participantStorageKey()) || "");
}

function updateParticipantBadge(participantId = currentAnnotator()) {
  if (!els.participantBadge) return;
  const source = state.participantSource || (participantIdFromUrl() ? "链接身份" : "本机保存身份");
  els.participantBadge.textContent = expertReviewMode()
    ? `当前复核人：${participantId || "未填写"} · ${source}`
    : datasetConfig.finalDataset
    ? `当前参与者：${participantId || "未填写"} · ${source}`
    : `练习身份：${participantId || "未填写"}`;
}

function replaceUrlAnnotator(participantId) {
  const url = new URL(window.location.href);
  if (expertReviewMode()) {
    url.searchParams.set("role", "expert");
    url.searchParams.set("expert", participantId);
    url.searchParams.delete("annotator");
  } else {
    url.searchParams.set("annotator", participantId);
    url.searchParams.delete("expert");
    url.searchParams.delete("reviewer");
  }
  url.searchParams.delete("participant");
  url.searchParams.delete("user");
  window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`);
}

function currentChartStatus() {
  return state.current?.manifest?.claim_status || "";
}

function currentChartClaimedByMe() {
  if (expertReviewMode()) {
    return Boolean(
      state.current
      && state.current.manifest?.claimed_by === currentAnnotator()
      && ["expert_review_claimed", "expert_review_claimed_by_me"].includes(currentChartStatus())
    );
  }
  return Boolean(
    state.current
    && state.current.manifest?.claimed_by === currentAnnotator()
    && ["claimed", "claimed_by_me", "submitted"].includes(currentChartStatus())
  );
}

function canAnnotateCurrent() {
  if (!state.current) return false;
  if (!datasetConfig.finalDataset) return true;
  return currentChartClaimedByMe();
}

function canClaimCurrent() {
  if (expertReviewMode()) {
    return Boolean(
      state.current
      && datasetConfig.finalDataset
      && currentChartStatus() === "expert_review_available"
      && currentAnnotator()
    );
  }
  return Boolean(
    state.current
    && datasetConfig.finalDataset
    && currentChartStatus() === "unassigned"
    && currentAnnotator()
  );
}

function currentChartIsPreview() {
  return Boolean(
    state.current
    && datasetConfig.finalDataset
    && (expertReviewMode()
      ? currentChartStatus() === "expert_review_available"
      : currentChartStatus() === "unassigned")
  );
}

function formalQueueMode() {
  return datasetConfig.finalDataset;
}

function apiUrl(path, params = {}) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("dataset", datasetKey);
  if (expertReviewMode()) {
    url.searchParams.set("role", "expert");
  }
  const token = currentAccessToken();
  if (token) url.searchParams.set("token", token);
  const annotator = params.annotator ?? currentAnnotator();
  if (annotator) {
    if (expertReviewMode()) url.searchParams.set("expert", annotator);
    url.searchParams.set("annotator", annotator);
  }
  Object.entries(params).forEach(([key, value]) => {
    if (key !== "annotator" && value !== undefined && value !== null) {
      url.searchParams.set(key, value);
    }
  });
  return `${url.pathname}${url.search}`;
}

function withAccessToken(urlValue) {
  const token = currentAccessToken();
  if (!token || !urlValue) return urlValue;
  const url = new URL(urlValue, window.location.origin);
  url.searchParams.set("token", token);
  return `${url.pathname}${url.search}`;
}

async function parseResponseError(response) {
  const text = await response.text();
  try {
    const payload = JSON.parse(text);
    const error = new Error(payload.error || text || `HTTP ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    return error;
  } catch {
    const error = new Error(text || `HTTP ${response.status}`);
    error.status = response.status;
    return error;
  }
}

async function getJson(url) {
  const headers = {};
  const token = currentAccessToken();
  if (token) headers["x-shujuji-token"] = token;
  const response = await fetch(url, { headers });
  if (!response.ok) throw await parseResponseError(response);
  return response.json();
}

async function postJson(url, payload) {
  const token = currentAccessToken();
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(token ? { "x-shujuji-token": token } : {})
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw await parseResponseError(response);
  return response.json();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.add("hidden"), 2800);
}

function flashRegion(regionId) {
  state.flashRegionId = regionId || null;
  window.clearTimeout(state.flashTimer);
  renderOverlay();
  state.flashTimer = window.setTimeout(() => {
    state.flashRegionId = null;
    renderOverlay();
  }, 1400);
}

function syncUndoButtons() {
  const enabled = state.undoStack.length > 0;
  if (els.undoBtn) els.undoBtn.disabled = !enabled;
  if (els.workflowUndoBtn) els.workflowUndoBtn.disabled = !enabled;
}

function pushUndo(label) {
  if (!state.current) return;
  state.undoStack.push({
    label,
    regions: deepClone(state.regions),
    fieldReviews: deepClone(state.fieldReviews),
    confirmModeDrafts: deepClone(state.confirmModeDrafts),
    selectedRegionId: state.selectedRegionId,
    selectedFieldKey: state.selectedFieldKey
  });
  if (state.undoStack.length > 40) state.undoStack.shift();
  syncUndoButtons();
}

function undoLastAction() {
  const snapshot = state.undoStack.pop();
  if (!snapshot) return;
  state.regions = deepClone(snapshot.regions || []);
  state.fieldReviews = deepClone(snapshot.fieldReviews || {});
  state.confirmModeDrafts = deepClone(snapshot.confirmModeDrafts || {});
  state.selectedRegionId = snapshot.selectedRegionId || state.regions[0]?.region_id || null;
  state.selectedFieldKey = snapshot.selectedFieldKey || null;
  state.pendingLinkFieldKey = null;
  state.drawMode = false;
  if (els.drawBtn) {
    els.drawBtn.classList.remove("primary");
    els.drawBtn.textContent = "为当前字段画证据框";
  }
  syncUndoButtons();
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  showToast(`已撤销：${snapshot.label || "上一步"}`);
}

function zoomText(value) {
  return `${Math.round(value * 100)}%`;
}

function updateZoomLabels() {
  if (els.leftZoomValue) els.leftZoomValue.textContent = zoomText(state.zooms.left);
  if (els.centerZoomValue) els.centerZoomValue.textContent = zoomText(state.zooms.center);
  if (els.rightZoomValue) els.rightZoomValue.textContent = zoomText(state.zooms.right);
  if (els.workflowZoomValue) els.workflowZoomValue.textContent = zoomText(state.zooms.workflow);
}

function applyPanelZooms() {
  document.documentElement.style.setProperty("--left-zoom", String(state.zooms.left));
  document.documentElement.style.setProperty("--right-zoom", String(state.zooms.right));
  document.documentElement.style.setProperty("--workflow-zoom", String(state.zooms.workflow));
  updateZoomLabels();
}

function applyImageZoom({ render = true } = {}) {
  if (!els.chartImage.naturalWidth) {
    updateZoomLabels();
    return;
  }
  els.chartImage.style.width = `${Math.round(els.chartImage.naturalWidth * state.zooms.center)}px`;
  els.chartImage.style.height = "auto";
  els.chartImage.style.maxWidth = "none";
  els.chartImage.style.maxHeight = "none";
  updateZoomLabels();
  if (render) window.requestAnimationFrame(renderOverlay);
}

function applyZooms({ render = true } = {}) {
  applyPanelZooms();
  applyImageZoom({ render });
}

function setPanelZoom(area, value) {
  const limit = zoomLimits[area];
  if (!limit) return;
  state.zooms[area] = Number(clamp(value, limit.min, limit.max).toFixed(2));
  applyZooms();
}

function adjustPanelZoom(area, direction) {
  const limit = zoomLimits[area];
  setPanelZoom(area, state.zooms[area] + limit.step * direction);
}

function resetPanelZoom(area) {
  setPanelZoom(area, zoomDefaults[area]);
}

function panelElement(area) {
  return {
    left: els.sidebarPanel,
    center: els.workspacePanel,
    right: els.inspectorPanel,
    workflow: els.workflowPanel
  }[area] || null;
}

function readPanelWidths() {
  return Object.fromEntries(panelAreas.map((area) => {
    const rect = panelElement(area)?.getBoundingClientRect();
    return [area, Math.round(rect?.width || panelMinWidths[area])];
  }));
}

function applyLayoutWidths(widths = state.layoutWidths) {
  if (!widths) return;
  panelAreas.forEach((area) => {
    const width = Number(widths[area]);
    if (Number.isFinite(width)) {
      document.documentElement.style.setProperty(panelWidthVars[area], `${Math.round(width)}px`);
    }
  });
  window.requestAnimationFrame(renderOverlay);
}

function beginColumnResize(event) {
  const pair = resizePairs[event.currentTarget?.dataset.resizeHandle];
  if (!pair) return;
  const widths = readPanelWidths();
  state.layoutWidths = widths;
  applyLayoutWidths(widths);
  state.columnResize = {
    pair,
    startX: event.clientX,
    startWidths: widths,
    handle: event.currentTarget
  };
  els.layout?.classList.add("resizing");
  event.currentTarget.classList.add("dragging");
  event.currentTarget.setPointerCapture?.(event.pointerId);
  event.preventDefault();
}

function updateColumnResize(event) {
  if (!state.columnResize) return;
  const { pair, startX, startWidths } = state.columnResize;
  const [before, after] = pair;
  const total = startWidths[before] + startWidths[after];
  const minBefore = Math.min(panelMinWidths[before], total * 0.45);
  const minAfter = Math.min(panelMinWidths[after], total * 0.45);
  const maxBefore = Math.max(minBefore, total - minAfter);
  const beforeWidth = clamp(startWidths[before] + event.clientX - startX, minBefore, maxBefore);
  const nextWidths = {
    ...startWidths,
    [before]: beforeWidth,
    [after]: total - beforeWidth
  };
  state.layoutWidths = nextWidths;
  applyLayoutWidths(nextWidths);
}

function endColumnResize() {
  if (!state.columnResize) return;
  state.columnResize.handle?.classList.remove("dragging");
  els.layout?.classList.remove("resizing");
  state.columnResize = null;
}

function bindCtrlWheelZoom() {
  [
    ["left", els.sidebarPanel],
    ["center", els.workspacePanel],
    ["right", els.inspectorPanel],
    ["workflow", els.workflowPanel]
  ].forEach(([area, element]) => {
    if (!element) return;
    element.addEventListener("wheel", (event) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      const limit = zoomLimits[area];
      const direction = event.deltaY < 0 ? 1 : -1;
      setPanelZoom(area, state.zooms[area] + direction * (limit.wheelStep || limit.step));
    }, { passive: false });
  });
}

function openHelp() {
  els.helpOverlay?.classList.remove("hidden");
  document.body.classList.add("help-open");
}

function closeHelp() {
  els.helpOverlay?.classList.add("hidden");
  document.body.classList.remove("help-open");
}

function resetCurrentChartView() {
  state.current = null;
  state.regions = [];
  state.fieldReviews = {};
  state.confirmModeDrafts = {};
  state.selectedRegionId = null;
  state.selectedFieldKey = null;
  state.pendingLinkFieldKey = null;
  state.lastQuickAcceptSnapshot = null;
  setUndoQuickAcceptEnabled(false);
  if (els.currentTitle) els.currentTitle.textContent = "请选择航图";
  if (els.currentMeta) els.currentMeta.textContent = "";
  if (els.chartImage) {
    els.chartImage.removeAttribute("src");
    els.chartImage.alt = "暂无航图";
  }
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  updateClaimButton();
}

async function applyAnnotatorIdentity() {
  const participantId = cleanParticipantId(els.annotatorInput?.value || "");
  if (!participantId) {
    showToast("请填写标注人身份，例如 A06。");
    if (els.annotatorInput) els.annotatorInput.value = currentAnnotator();
    return;
  }
  if (els.annotatorInput) els.annotatorInput.value = participantId;
  localStorage.setItem(participantStorageKey(), participantId);
  state.participantSource = "手动输入身份";
  replaceUrlAnnotator(participantId);
  updateParticipantBadge(participantId);
  resetCurrentChartView();
  if (formalQueueMode()) {
    await advanceFormalQueue({ successPrefix: `已切换到标注人：${participantId}` });
    return;
  }
  await refreshCharts();
  const first = firstOpenableChart();
  if (first) await loadChart(first.chart_id);
  showToast(`已切换到标注人：${participantId}`);
}

function makeRegionId(chartId, index) {
  return `${chartId}_r${String(index + 1).padStart(3, "0")}`;
}

function normalizeRegion(region, index) {
  const sourceId = region.region_id || region.final_region_id || region.source_region_id || makeRegionId(state.current.manifest.chart_id, index);
  const reviewedMappings = region.candidate_mappings || region.candidate_mappings_reviewed;
  const legacyAcceptedMappings = (region.accepted_mappings || []).map((mapping) => ({
    ...mapping,
    expected_answer: mapping.expected_answer || mapping.canonical_answer || null,
    human_decision: "accepted"
  }));
  return {
    region_id: sourceId,
    source_region_id: region.source_region_id || sourceId,
    region_type: region.region_type || "MISSED_APPROACH_TEXT",
    bbox: {
      x_center: Number(region.bbox?.x_center ?? 0.5),
      y_center: Number(region.bbox?.y_center ?? 0.5),
      width: Number(region.bbox?.width ?? 0.25),
      height: Number(region.bbox?.height ?? 0.12)
    },
    label: region.label || "",
    ocr_text: region.ocr_text || "",
    confidence: region.confidence ?? null,
    annotation_scope: region.annotation_scope || "",
    element_role: region.element_role || "",
    expected_visual_value: region.expected_visual_value || "",
    step_id: region.step_id || "",
    parent_step_region_id: region.parent_step_region_id || "",
    source_candidate_leg_id: region.source_candidate_leg_id || "",
    source_leg_type: region.source_leg_type || "",
    source_field_name: region.source_field_name || "",
    is_formal_annotation_candidate: Boolean(region.is_formal_annotation_candidate),
    candidate_mappings: reviewedMappings || legacyAcceptedMappings,
    needs_human_decision: region.needs_human_decision ?? true,
    human_review: {
      review_action: region.review_action || region.human_review?.review_action || "pending",
      adjusted_bbox: region.human_review?.adjusted_bbox || null,
      final_region_type: region.human_review?.final_region_type || region.region_type || "",
      notes: region.notes || region.human_review?.notes || ""
    }
  };
}

function selectedRegion() {
  return state.regions.find((region) => region.region_id === state.selectedRegionId) || null;
}

function mappingIsPending(mapping) {
  return !mapping.human_decision || mapping.human_decision === "pending";
}

function regionHasPendingMappings(region) {
  return Boolean(region?.candidate_mappings?.some(mappingIsPending));
}

function selectRegionById(regionId) {
  state.selectedRegionId = regionId;
  renderOverlay();
  renderRegionForm();
  renderTargets();
}

function findNextPendingRegionId(afterRegionId = state.selectedRegionId) {
  if (!state.regions.length) return null;
  const startIndex = Math.max(0, state.regions.findIndex((region) => region.region_id === afterRegionId));
  for (let offset = 1; offset <= state.regions.length; offset += 1) {
    const region = state.regions[(startIndex + offset) % state.regions.length];
    if (regionHasPendingMappings(region)) return region.region_id;
  }
  return null;
}

function acceptPendingMappings(region) {
  if (!region) return 0;
  let changed = 0;
  (region.candidate_mappings || []).forEach((mapping) => {
    if (mappingIsPending(mapping)) {
      if (!changed) pushUndo("确认字段对应");
      mapping.human_decision = "accepted";
      changed += 1;
    }
  });
  if (changed) region.human_review.review_action = "accept";
  return changed;
}

function acceptCurrentAndAdvance() {
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return;
  }
  const region = selectedRegion();
  const changed = acceptPendingMappings(region);
  const nextRegionId = findNextPendingRegionId(region?.region_id);
  if (nextRegionId) {
    selectRegionById(nextRegionId);
    showToast(`已确认当前框 ${changed} 条候选，并切换到下一个待处理框。`);
  } else {
    renderRegionForm();
    renderTargets();
    renderCanonicalPanel();
    showToast(`已确认当前框 ${changed} 条候选。`);
  }
}

function setUndoQuickAcceptEnabled(enabled) {
  if (els.undoQuickAcceptBtn) {
    els.undoQuickAcceptBtn.disabled = !enabled;
  }
}

function acceptAllChartPendingMappings() {
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return;
  }
  pushUndo("采纳已有候选");
  const mappingSnapshot = [];
  const fieldReviewSnapshot = [];
  const changedRegions = new Set();
  state.regions.forEach((region) => {
    const previousReviewAction = region.human_review?.review_action;
    (region.candidate_mappings || []).forEach((mapping) => {
      if (!mappingIsPending(mapping)) return;
      mappingSnapshot.push({
        region,
        mapping,
        previousDecision: mapping.human_decision,
        previousReviewAction
      });
      mapping.human_decision = "accepted";
      changedRegions.add(region);
    });
  });
  changedRegions.forEach((region) => {
    region.human_review.review_action = "accept";
  });
  buildFieldRows().filter((row) => row.requires_review).forEach((row) => {
    const review = reviewForField(row);
    if (review.review_status !== "pending") return;
    const evidenceIds = uniqueList(review.required_evidence_region_ids || []);
    if (!evidenceIds.length) return;
    fieldReviewSnapshot.push({
      key: row.key,
      previousReview: state.fieldReviews[row.key] ? deepClone(state.fieldReviews[row.key]) : undefined
    });
    const supportMode = recommendedSupportModeForField(row, evidenceIds) || (evidenceIds.length > 1 ? "visible_joint" : "direct_visible");
    setFieldReview(row, supportMode, {
      requiredIds: evidenceIds,
      checkedScopes: sourcesForRegionIds(evidenceIds),
      notes: row.field_name === "Q_terminator" ? "快速采纳：同一航段的图面证据共同支持航段类型。" : review.notes || ""
    });
    const createdMappings = applyEvidenceSelectionToMappings(row, evidenceIds, supportMode);
    createdMappings.forEach((created) => {
      mappingSnapshot.push({
        ...created,
        previousDecision: undefined,
        previousReviewAction: created.region.human_review?.review_action,
        createdByQuickAccept: true
      });
    });
  });
  const snapshot = { mappings: mappingSnapshot, fieldReviews: fieldReviewSnapshot };
  state.lastQuickAcceptSnapshot = (mappingSnapshot.length || fieldReviewSnapshot.length) ? snapshot : null;
  setUndoQuickAcceptEnabled(Boolean(state.lastQuickAcceptSnapshot));
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  const completedFields = fieldReviewSnapshot.length;
  const message = mappingSnapshot.length || completedFields
    ? `已快速确认本图已有候选 ${mappingSnapshot.length} 条，并完成 ${completedFields} 个字段；误点可先点“撤销快速确认”。`
    : "当前没有待快速确认的候选。";
  showToast(message);
}

function undoQuickAccept() {
  const snapshot = state.lastQuickAcceptSnapshot;
  const mappingSnapshot = Array.isArray(snapshot) ? snapshot : snapshot?.mappings;
  const fieldReviewSnapshot = Array.isArray(snapshot) ? [] : snapshot?.fieldReviews;
  if (!mappingSnapshot?.length && !fieldReviewSnapshot?.length) {
    showToast("没有可撤销的快速确认。");
    return;
  }
  mappingSnapshot.forEach(({ region, mapping, previousDecision, previousReviewAction, createdByQuickAccept }) => {
    if (createdByQuickAccept && region?.candidate_mappings) {
      region.candidate_mappings = region.candidate_mappings.filter((item) => item !== mapping);
    } else if (previousDecision === undefined) {
      delete mapping.human_decision;
    } else {
      mapping.human_decision = previousDecision;
    }
    if (region?.human_review) region.human_review.review_action = previousReviewAction || "pending";
  });
  fieldReviewSnapshot.forEach(({ key, previousReview }) => {
    if (previousReview === undefined) {
      delete state.fieldReviews[key];
    } else {
      state.fieldReviews[key] = previousReview;
    }
  });
  state.lastQuickAcceptSnapshot = null;
  setUndoQuickAcceptEnabled(false);
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  showToast("已撤销上次快速确认；保存前不会写入那次批量确认。");
}

function markCurrentFrameUnsure() {
  const region = selectedRegion();
  if (!region) return;
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再标注。");
    return;
  }
  pushUndo("标记当前框不确定");
  (region.candidate_mappings || []).forEach((mapping) => {
    if (mappingIsPending(mapping)) mapping.human_decision = "needs_discussion";
  });
  region.human_review.review_action = "pending";
  region.human_review.notes = region.human_review.notes || "不确定，需要复核。";
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  showToast("已把当前框标记为不确定。");
}

function openTargetPanel() {
  if (!els.targetPanel) return;
  els.targetPanel.open = true;
  els.targetPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fieldAcceptedForLeg(leg, field) {
  const legId = leg?.candidate_leg_id || "";
  const fieldName = field.field_name || field.name || "";
  return state.regions.some((region) => (region.candidate_mappings || []).some((mapping) => {
    return mapping.human_decision === "accepted"
      && mapping.candidate_leg_id === legId
      && mapping.field_name === fieldName;
  }));
}

function renderWorkflowPanel() {
  if (!els.workflowSummary || !els.workflowNextList) return;
  const rows = buildFieldRows().filter((row) => row.requires_review);
  const reviews = rows.map((row) => ({ row, review: reviewForField(row) }));
  const pending = reviews.filter((item) => item.review.review_status === "pending");
  if (!state.selectedFieldKey && pending[0]) state.selectedFieldKey = pending[0].row.key;
  const uncertain = reviews.filter((item) => item.review.review_status === "uncertain");
  const selected = selectedFieldRow();
  const completion = rows.length ? Math.round(((rows.length - pending.length) / rows.length) * 100) : 100;
  const selectedReview = selected ? reviewForField(selected) : null;
  const canEdit = canAnnotateCurrent();
  const canFinish = canEdit;
  const preview = currentChartIsPreview();
  const modeText = !state.current
    ? "请先从左侧选择航图。"
    : preview
      ? "预览模式：可以查看航图和字段队列，领取后才能标注。"
      : canEdit
        ? "标注模式：按字段逐项给出结论。"
        : "当前航图不能由该参与者编辑。";

  const selectedEvidenceIds = selectedReview?.required_evidence_region_ids || [];
  const selectedFieldTitle = selected
    ? taskFieldName(selected.field_name)
    : "请选择航图";
  const selectedFieldContext = selected ? taskLegContext(selected) : "";
  const selectedFieldAnswer = selected
    ? friendlyAnswerValue(selected.expected_answer, selected.expected_value)
    : "左侧选择航图后，这里会显示要判断的字段。";
  const selectedStatus = selectedReview
    ? FIELD_REVIEW_LABELS[selectedReview.review_status] || selectedReview.review_status
    : "未选择";
  const selectedEvidenceText = selectedEvidenceIds.length
    ? `已选 ${selectedEvidenceIds.length} 处依据`
    : "还没选依据";
  const fieldActionDisabled = !selected || !state.current || !canEdit;
  const confirmDisabled = fieldActionDisabled ? "disabled" : "";
  const selectedSupportMode = selected
    ? selectedSupportModeForField(selected, selectedEvidenceIds, selectedReview?.review_status || "pending")
    : "";
  const selectedSupportNeedsEvidence = FIELD_SUPPORT_REQUIRES_EVIDENCE.has(selectedSupportMode);
  const confirmSelectionDisabled = fieldActionDisabled
    || !selectedSupportMode
    || (selectedSupportNeedsEvidence && !selectedEvidenceIds.length)
    ? "disabled"
    : "";
  const selectedRegionForBasket = selectedRegion();
  const selectedRegionInBasket = Boolean(
    selectedRegionForBasket && selectedEvidenceIds.includes(selectedRegionForBasket.region_id)
  );
  const basketToggleDisabled = fieldActionDisabled || !selectedRegionForBasket ? "disabled" : "";
  const basketToggleLabel = selectedRegionInBasket ? "移除这处依据" : "加入为依据";
  const basketToggleTitle = selectedRegionForBasket
    ? `${basketToggleLabel}：${selectedRegionForBasket.region_id}`
    : "先在航图上选中一个证据框";
  const selectedSupportText = selectedSupportMode
    ? FIELD_REVIEW_LABELS[selectedSupportMode] || selectedSupportMode
    : "未选择";
  const confirmHint = !selectedSupportMode
    ? "请选择这些地方怎么支持判断。"
    : selectedSupportNeedsEvidence && !selectedEvidenceIds.length
      ? "当前选择需要至少一处图上依据。"
      : "";
  const evidenceHint = selectedReview?.autofilled_evidence
    ? "系统先放入了可能相关的位置；请删掉不支持判断的部分。"
    : selectedEvidenceIds.length
      ? "这些位置会作为这个判断的依据保存。"
      : "先在图上选中能支持判断的位置；如果图上确实看不够，再选“图上看不够”。";
  const evidenceRows = selectedEvidenceIds.length
    ? selectedEvidenceIds.map((regionId) => {
        const region = regionById(regionId);
        const active = regionId === state.selectedRegionId ? " active" : "";
        return `
          <div class="evidence-basket-row${active}">
            <button type="button" data-select-evidence="${escapeText(regionId)}">
              <strong>${escapeText(region ? friendlyRegionType(region.region_type) : "已删除框")}</strong>
              <span>${escapeText(evidenceRegionSummary(region))}</span>
            </button>
            <button type="button" class="evidence-remove" data-remove-evidence="${escapeText(regionId)}" ${confirmDisabled}>移除</button>
          </div>
        `;
      }).join("")
    : '<p class="empty compact-empty">还没有选出支持这个判断的位置。</p>';

  els.workflowSummary.innerHTML = `
    <div class="current-task-card">
      <div class="task-kicker">当前判断</div>
      <div class="task-title-row">
        <h2>${escapeText(selectedFieldTitle)}</h2>
        ${selectedFieldContext ? `<span>${escapeText(selectedFieldContext)}</span>` : ""}
      </div>
      <div class="task-answer">要从图上证明：<strong>${escapeText(selectedFieldAnswer)}</strong></div>
      <p>先找出图上哪些位置支持这个判断，再说明这些位置是直接支持、还是需要多处综合或规则补全。</p>
      <div class="task-status-row">
        <span class="field-status status-${escapeText(selectedReview?.review_status || "pending")}">${escapeText(selectedStatus)}</span>
        <span>${escapeText(selectedEvidenceText)}</span>
      </div>
      <div class="evidence-basket">
        <div class="basket-head">
          <strong>从哪些地方可以看出？</strong>
          <span>${escapeText(evidenceHint)}</span>
        </div>
        <div class="basket-actions">
          <button type="button" data-link-selected-evidence title="${escapeText(basketToggleTitle)}" ${basketToggleDisabled}>${escapeText(basketToggleLabel)}</button>
          <button type="button" data-draw-support-evidence ${confirmDisabled}>画一处依据</button>
        </div>
        ${evidenceRows}
      </div>
      <div class="source-choice-block">
        <div class="source-choice-head">
          <strong>这些地方怎么支持判断？</strong>
          <span>当前选择：${escapeText(selectedSupportText)}</span>
        </div>
        <div class="field-confirm-grid">
          ${renderSupportModeChoices(selected, selectedEvidenceIds, selectedReview?.review_status || "pending", confirmDisabled)}
        </div>
        <div class="confirm-selection-row">
          ${confirmHint ? `<span>${escapeText(confirmHint)}</span>` : "<span></span>"}
          <button type="button" class="primary" data-confirm-selected-field ${confirmSelectionDisabled}>确认并看下一项</button>
        </div>
      </div>
    </div>
    <div class="workflow-metric">
      <strong>${pending.length}</strong>
      <span>尚未确认</span>
    </div>
    <div class="workflow-metric">
      <strong>${completion}%</strong>
      <span>判断完成</span>
    </div>
    <div class="workflow-metric">
      <strong>${reviews.filter((item) => ["visible_joint", "rule_default_completion"].includes(item.review.review_status)).length}</strong>
      <span>综合/补全</span>
    </div>
    <p class="metric-note">${escapeText(modeText)}</p>
  `;

  els.workflowSummary.querySelectorAll("[data-support-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!selected) return;
      setSupportModeDraft(selected, button.dataset.supportMode);
    });
  });
  els.workflowSummary.querySelector("[data-confirm-selected-field]")?.addEventListener("click", () => {
    const row = selectedFieldRow();
    if (!row) return;
    const review = reviewForField(row);
    const evidenceIds = review.required_evidence_region_ids || [];
    confirmSelectedField(selectedSupportModeForField(row, evidenceIds, review.review_status));
  });
  els.workflowSummary.querySelector("[data-link-selected-evidence]")?.addEventListener("click", () => {
    linkSelectedFieldToRegion({ accept: true });
  });
  els.workflowSummary.querySelector("[data-draw-support-evidence]")?.addEventListener("click", () => {
    startDrawRegionForSelectedField();
  });
  els.workflowSummary.querySelectorAll("[data-select-evidence]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedRegionId = button.dataset.selectEvidence;
      renderOverlay();
      renderRegionForm();
      renderTargets();
      renderCanonicalPanel();
    });
  });
  els.workflowSummary.querySelectorAll("[data-remove-evidence]").forEach((button) => {
    button.addEventListener("click", () => removeEvidenceFromSelectedField(button.dataset.removeEvidence));
  });

  [els.linkSelectedFieldBtn, els.addRegionForFieldBtn, els.markNoEvidenceBtn, els.markImplicitBtn, els.markFieldUnsureBtn].forEach((button) => {
    if (button) button.disabled = fieldActionDisabled;
  });
  if (els.nextPendingBtn) els.nextPendingBtn.disabled = !state.current;
  if (els.workflowSaveBtn) els.workflowSaveBtn.disabled = !canFinish || pending.length > 0;
  if (els.saveBtn) els.saveBtn.disabled = !canFinish || pending.length > 0;
  if (els.saveDraftBtn) els.saveDraftBtn.disabled = !canEdit;
  if (els.skipClaimBtn) els.skipClaimBtn.disabled = !canEdit || currentChartStatus() === "submitted";
  if (els.quickAcceptBtn) els.quickAcceptBtn.disabled = !canEdit;
  if (els.openTargetsBtn) els.openTargetsBtn.disabled = !state.current;
  if (els.drawBtn) els.drawBtn.disabled = !canEdit || !selected;
  if (els.deleteRegionBtn) els.deleteRegionBtn.disabled = !canEdit || !selectedRegion();
  const canReturn = !expertReviewMode() && canEdit && currentChartStatus() !== "submitted";
  if (els.returnClaimBtn) els.returnClaimBtn.disabled = !canReturn;
  if (els.returnWorkflowBtn) els.returnWorkflowBtn.disabled = !canReturn;
  if (els.claimCurrentBtn) {
    els.claimCurrentBtn.classList.toggle("hidden", formalQueueMode() || !state.current || !datasetConfig.finalDataset || !["unassigned", "claimed_by_other", "returned_for_expert_review"].includes(currentChartStatus()));
    els.claimCurrentBtn.disabled = !canClaimCurrent();
    els.claimCurrentBtn.textContent = canClaimCurrent()
      ? "领取并开始"
      : currentChartStatus() === "returned_for_expert_review" || currentChartStatus() === "expert_review_claimed_by_other"
        ? "已退回专家复审"
        : currentChartStatus() === "claimed_by_other"
          ? "他人处理中"
          : "不可领取";
  }

  els.workflowNextList.innerHTML = "";
  if (!rows.length) {
    els.workflowNextList.innerHTML = '<p class="empty">当前航图没有需要人工判断的 present 字段。</p>';
    return;
  }

  const appendFieldRow = (container, { row, review }) => {
    const item = document.createElement("div");
    item.className = `workflow-missing-row field-review-row status-${review.review_status} ${row.key === state.selectedFieldKey ? "active" : ""}`;
    item.innerHTML = `
      <span>${escapeText([taskLegContext(row), taskFieldName(row.field_name)].filter(Boolean).join(" · "))}</span>
      <b>${escapeText(friendlyAnswerValue(row.expected_answer, row.expected_value))}</b>
      <small>${escapeText(FIELD_REVIEW_LABELS[review.review_status] || review.review_status)}</small>
    `;
    item.addEventListener("click", () => selectField(row));
    container.appendChild(item);
  };

  const pendingPanel = document.createElement("details");
  pendingPanel.className = "field-list-panel pending-fields";
  pendingPanel.open = true;
  pendingPanel.innerHTML = `<summary>尚未确认字段 ${pending.length} 项</summary>`;
  const pendingBody = document.createElement("div");
  pendingBody.className = "field-list-scroll";
  if (!pending.length) {
    pendingBody.innerHTML = '<p class="empty compact-empty">没有尚未确认字段，可以完成本图。</p>';
  } else {
    pending.forEach((item) => appendFieldRow(pendingBody, item));
  }
  pendingPanel.appendChild(pendingBody);
  els.workflowNextList.appendChild(pendingPanel);

  const completed = reviews.filter((item) => item.review.review_status !== "pending");
  const completedPanel = document.createElement("details");
  completedPanel.className = "field-list-panel completed-fields-panel";
  completedPanel.innerHTML = `<summary>已处理字段 ${completed.length} 项</summary>`;
  const completedBody = document.createElement("div");
  completedBody.className = "field-list-scroll";
  completed.forEach((item) => appendFieldRow(completedBody, item));
  completedPanel.appendChild(completedBody);
  els.workflowNextList.appendChild(completedPanel);

  if (uncertain.length) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = `还有 ${uncertain.length} 个字段被标为不确定，完成后应进入复核。`;
    els.workflowNextList.appendChild(note);
  }
}

function renderChartList() {
  if (!els.chartList) return;
  if (formalQueueMode()) {
    els.chartList.innerHTML = "";
    updateFormalQueueStatus();
    return;
  }
  const query = els.chartFilter.value.trim().toLowerCase();
  els.chartList.innerHTML = "";
  state.charts
    .filter((chart) => {
      const text = `${chart.chart_id} ${chart.sample_type} ${chart.priority_reason || ""} ${chart.claim_status || ""} ${chart.claimed_by || ""}`.toLowerCase();
      return !query || text.includes(query);
    })
    .forEach((chart) => {
      const card = document.createElement("div");
      const claimedByOther = datasetConfig.finalDataset && chart.claim_status === "claimed_by_other";
      const returnedForExpert = datasetConfig.finalDataset && chart.claim_status === "returned_for_expert_review";
      const mine = !datasetConfig.finalDataset || ["claimed", "claimed_by_me", "submitted"].includes(chart.claim_status || "");
      const unassigned = datasetConfig.finalDataset && chart.claim_status === "unassigned";
      const canOpen = !datasetConfig.finalDataset || mine || unassigned;
      const claimLabel = !datasetConfig.finalDataset
        ? "练习"
        : unassigned
          ? "未领取"
          : returnedForExpert
            ? "退回专家复审"
            : chart.claim_status === "submitted"
              ? "我已完成"
              : chart.claim_status === "claimed" || chart.claim_status === "claimed_by_me"
                ? "我已领取"
                : `他人处理中`;
      const openLabel = !datasetConfig.finalDataset
        ? "打开"
        : unassigned
          ? "预览"
          : chart.claim_status === "submitted"
            ? "查看"
            : mine
              ? "继续"
              : "不可打开";
      const cardDisabled = claimedByOther || returnedForExpert;
      card.className = `chart-card ${state.current?.manifest?.chart_id === chart.chart_id ? "active" : ""} ${cardDisabled ? "disabled" : ""} ${returnedForExpert ? "returned" : ""}`;
      card.title = returnedForExpert
        ? `这张图已退回专家复审。${chart.return_reason ? `原因：${chart.return_reason}` : ""}`
        : claimedByOther
          ? "这张图已被其他参与者领取，请选择未领取的图。"
          : unassigned
            ? "点击预览航图；确认可做后在左侧领取。"
            : "点击打开这张图。";
      card.innerHTML = `
        <button class="chart-open" type="button" ${canOpen && !returnedForExpert && !claimedByOther ? "" : "disabled"}>
          <strong>${escapeText(chart.chart_id)}</strong>
          <span class="muted">${escapeText(chart.procedure_key || "")}</span>
          <span class="chart-open-label">${escapeText(openLabel)}</span>
        </button>
        <div class="badge-row">
          <span class="badge ${chart.sample_type === "anomaly" ? "hot" : ""}">${escapeText(chart.sample_type)}</span>
          <span class="badge">legs ${chart.target_leg_count}</span>
          <span class="badge ${claimedByOther || returnedForExpert ? "hot" : ""}">${escapeText(claimLabel)}</span>
          ${chart.has_prelabel ? '<span class="badge">prelabel</span>' : ""}
          ${chart.has_my_draft ? '<span class="badge">暂存</span>' : ""}
          ${chart.has_my_annotation ? '<span class="badge hot">已完成</span>' : ""}
          ${chart.submission_count ? `<span class="badge">提交 ${escapeText(chart.submission_count)}</span>` : ""}
        </div>
      `;
      card.querySelector(".chart-open")?.addEventListener("click", () => loadChart(chart.chart_id).catch((error) => showToast(error.message)));
      els.chartList.appendChild(card);
    });
}

function updateClaimButton() {
  renderChartList();
}

async function claimChartFromList(chartId, { openAfter = false, silent = false } = {}) {
  ensureParticipantId();
  const result = await postJson(apiUrl(`/api/claims/${encodeURIComponent(chartId)}`), {});
  const claim = result.claim || {};
  const chart = state.charts.find((item) => item.chart_id === chartId);
  if (chart) {
    chart.claim_status = claim.status || "claimed";
    chart.claimed_by = expertReviewMode() ? (claim.expert_reviewer || currentAnnotator()) : (claim.annotator || currentAnnotator());
    chart.original_annotator = claim.annotator || chart.original_annotator || "";
    chart.expert_reviewer = claim.expert_reviewer || chart.expert_reviewer || "";
    chart.claimed_at = claim.claimed_at || "";
  }
  if (state.current?.manifest?.chart_id === chartId) {
    state.current.manifest.claim_status = claim.status || "claimed";
    state.current.manifest.claimed_by = expertReviewMode() ? (claim.expert_reviewer || currentAnnotator()) : (claim.annotator || currentAnnotator());
    state.current.manifest.original_annotator = claim.annotator || state.current.manifest.original_annotator || "";
    state.current.manifest.expert_reviewer = claim.expert_reviewer || state.current.manifest.expert_reviewer || "";
    state.current.manifest.claimed_at = claim.claimed_at || "";
    const claimText = state.current.manifest.claimed_by ? ` · 领取人 ${state.current.manifest.claimed_by}` : "";
    if (els.currentMeta) {
      els.currentMeta.textContent = ` ${state.current.manifest.sample_type || ""} · ${expertReviewMode() ? "复核模式" : "标注模式"}${claimText}`;
    }
  }
  renderChartList();
  updateFormalQueueStatus();
  if (!silent) showToast(`已领取：${chartId}`);
  if (openAfter) await loadChart(chartId);
  renderCanonicalPanel();
}

async function claimCurrentChart() {
  if (!state.current) {
    showToast(formalQueueMode() ? "当前没有可领取航图。" : "请先从左侧预览一张航图。");
    return;
  }
  if (!canClaimCurrent()) {
    showToast("当前航图不可领取。");
    return;
  }
  await claimChartFromList(state.current.manifest.chart_id, { openAfter: true });
}

async function returnCurrentClaim() {
  if (!state.current) {
    showToast("请先打开一张已领取航图。");
    return;
  }
  if (!datasetConfig.finalDataset) {
    showToast("练习集不需要退回。");
    return;
  }
  if (expertReviewMode()) {
    showToast("专家复核页不再二次退回；可以暂存或提交复核结果。");
    return;
  }
  const chartId = state.current.manifest.chart_id;
  const claimedBy = state.current.manifest.claimed_by || "";
  if (claimedBy !== currentAnnotator()) {
    showToast("只能退回自己领取的航图。");
    return;
  }
  const reason = window.prompt("请写明需要专家复核的原因，例如“holding 结构复杂，需要专家复审”。", "");
  if (reason === null) return;
  await saveCurrentDraftSnapshot({
    reason,
    reviewStatus: "submitted_for_expert_review",
    silent: true
  });
  const result = await postJson(apiUrl(`/api/claims/${encodeURIComponent(chartId)}/return`), {
    annotator: currentAnnotator(),
    reason
  });
  const claim = result.claim || {};
  const chart = state.charts.find((item) => item.chart_id === chartId);
  if (chart) {
    chart.claim_status = "returned_for_expert_review";
    chart.claimed_by = claim.annotator || currentAnnotator();
    chart.returned_at = claim.returned_at || "";
    chart.returned_by = claim.returned_by || currentAnnotator();
    chart.return_reason = claim.return_reason || reason || "";
    chart.expert_review_required = true;
  }
  state.current.manifest.claim_status = "returned_for_expert_review";
  state.current.manifest.returned_at = claim.returned_at || "";
  state.current.manifest.returned_by = claim.returned_by || currentAnnotator();
  state.current.manifest.return_reason = claim.return_reason || reason || "";
  renderChartList();
  renderCanonicalPanel();
  if (formalQueueMode()) {
    await advanceFormalQueue({ afterChartId: chartId, successPrefix: "已提交专家复核" });
  } else {
    showToast("已提交专家复核。");
  }
}

async function skipCurrentClaim() {
  if (!state.current) {
    showToast("请先打开一张已领取航图。");
    return;
  }
  if (!datasetConfig.finalDataset) {
    showToast("练习集不需要换图。");
    return;
  }
  const chartId = state.current.manifest.chart_id;
  const claimedBy = state.current.manifest.claimed_by || "";
  if (claimedBy !== currentAnnotator()) {
    showToast(expertReviewMode() ? "只能跳过自己领取的复核航图。" : "只能释放自己领取的航图。");
    return;
  }
  const ok = window.confirm(expertReviewMode()
    ? "跳过会把当前航图放回复核队列，不会提交复核结果。需要保留当前改动时，请先取消并暂存。继续吗？"
    : "换一张只释放当前领取，不会提交专家复核。需要保留当前改动时，请先取消并点击“暂存当前图”。继续换图吗？");
  if (!ok) return;

  await postJson(apiUrl(`/api/claims/${encodeURIComponent(chartId)}/release`), {
    annotator: currentAnnotator()
  });
  const chart = state.charts.find((item) => item.chart_id === chartId);
  if (chart) {
    chart.claim_status = expertReviewMode() ? "expert_review_available" : "unassigned";
    chart.claimed_by = "";
    chart.claimed_at = "";
    chart.last_saved_at = "";
  }
  state.current.manifest.claim_status = expertReviewMode() ? "expert_review_available" : "unassigned";
  state.current.manifest.claimed_by = "";
  state.current.manifest.claimed_at = "";
  renderChartList();
  renderCanonicalPanel();
  if (formalQueueMode()) {
    await advanceFormalQueue({ afterChartId: chartId, successPrefix: expertReviewMode() ? "已跳过当前复核" : "已换一张" });
  } else {
    showToast("当前图已释放。");
  }
}

async function loadChart(chartId) {
  ensureParticipantId();
  const listItem = state.charts.find((item) => item.chart_id === chartId);
  if (datasetConfig.finalDataset && listItem && !expertReviewMode() && ["claimed_by_other", "returned_for_expert_review"].includes(listItem.claim_status || "")) {
    showToast(listItem.claim_status === "returned_for_expert_review" ? "这张图已退回专家复审。" : "这张图已被其他参与者领取。");
    return;
  }
  if (datasetConfig.finalDataset && listItem && expertReviewMode() && ["expert_review_claimed_by_other", "not_in_expert_queue"].includes(listItem.claim_status || "")) {
    showToast(listItem.claim_status === "expert_review_claimed_by_other" ? "这张图已由其他专家领取复核。" : "这张图不在专家复核队列中。");
    return;
  }
  const chartData = await getJson(apiUrl("/api/chart", { chart_id: chartId }));
  applyLoadedChart(chartData, chartId);
}

function applyLoadedChart(chartData, fallbackChartId = "") {
  state.current = chartData;
  state.dataset = state.current.dataset || datasetConfig;
  const chartId = state.current.manifest?.chart_id || fallbackChartId;
  const withdrawnBatchAnnotation = /AI batch submission withdrawn/i.test(state.current.manifest?.return_reason || "");
  const usableAnnotation = withdrawnBatchAnnotation ? null : state.current.annotation;
  const sourceRegions = state.current.draft?.regions || usableAnnotation?.regions || state.current.prelabel?.regions || [];
  state.regions = sourceRegions.map(normalizeRegion);
  state.fieldReviews = normalizeFieldReviews(state.current.draft?.field_reviews || usableAnnotation?.field_reviews || {});
  state.confirmModeDrafts = {};
  state.selectedFieldKey = null;
  state.pendingLinkFieldKey = null;
  state.undoStack = [];
  syncUndoButtons();
  state.selectedRegionId = state.regions[0]?.region_id || null;
  state.lastQuickAcceptSnapshot = null;
  setUndoQuickAcceptEnabled(false);

  els.currentTitle.textContent = chartId;
  const statusText = currentChartIsPreview()
    ? "预览模式"
    : canAnnotateCurrent()
      ? (expertReviewMode() ? "复核模式" : "标注模式")
      : (state.current.manifest.claim_status || "");
  const claimText = state.current.manifest.claimed_by ? ` · ${expertReviewMode() ? "复核人" : "领取人"} ${state.current.manifest.claimed_by}` : "";
  const originalText = expertReviewMode() && state.current.manifest.original_annotator ? ` · 原标注 ${state.current.manifest.original_annotator}` : "";
  els.currentMeta.textContent = ` ${state.current.manifest.sample_type || ""} · ${statusText}${claimText}${originalText}`;
  els.overlay.style.width = "1px";
  els.overlay.style.height = "1px";
  els.chartImage.onload = () => {
    applyImageZoom({ render: false });
    renderOverlay();
  };
  els.chartImage.alt = `航图 ${chartId}`;
  els.chartImage.src = withAccessToken(state.current.image_url);

  renderChartList();
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
  updateClaimButton();
  updateFormalQueueStatus();
}

function getStageSize() {
  const rect = els.chartImage.getBoundingClientRect();
  return {
    width: rect.width || 1,
    height: rect.height || 1
  };
}

function syncOverlayToImage(size = getStageSize()) {
  // Keep overlay coordinates tied to the rendered image, not the wrapper.
  // Browser zoom can make the image smaller than the stage and otherwise
  // creates apparent bbox drift.
  els.overlay.style.width = `${size.width}px`;
  els.overlay.style.height = `${size.height}px`;
  els.overlay.setAttribute("width", String(size.width));
  els.overlay.setAttribute("height", String(size.height));
}

function normalizedPoint(event) {
  const rect = els.overlay.getBoundingClientRect();
  return {
    x: clamp((event.clientX - rect.left) / Math.max(rect.width, 1)),
    y: clamp((event.clientY - rect.top) / Math.max(rect.height, 1))
  };
}

function bboxToPixels(bbox) {
  const size = getStageSize();
  return {
    x: (bbox.x_center - bbox.width / 2) * size.width,
    y: (bbox.y_center - bbox.height / 2) * size.height,
    width: bbox.width * size.width,
    height: bbox.height * size.height
  };
}

function roundUnit(value) {
  return Number(clamp(value).toFixed(4));
}

function bboxEdges(bbox) {
  const width = clamp(Number(bbox.width) || 0.001, 0.001, 1);
  const height = clamp(Number(bbox.height) || 0.001, 0.001, 1);
  const xCenter = clamp(Number(bbox.x_center) || 0.5, width / 2, 1 - width / 2);
  const yCenter = clamp(Number(bbox.y_center) || 0.5, height / 2, 1 - height / 2);
  return {
    left: clamp(xCenter - width / 2),
    right: clamp(xCenter + width / 2),
    top: clamp(yCenter - height / 2),
    bottom: clamp(yCenter + height / 2)
  };
}

function bboxFromEdges(left, top, right, bottom) {
  const safeLeft = clamp(Math.min(left, right));
  const safeRight = clamp(Math.max(left, right));
  const safeTop = clamp(Math.min(top, bottom));
  const safeBottom = clamp(Math.max(top, bottom));
  return {
    x_center: roundUnit((safeLeft + safeRight) / 2),
    y_center: roundUnit((safeTop + safeBottom) / 2),
    width: roundUnit(Math.max(0.001, safeRight - safeLeft)),
    height: roundUnit(Math.max(0.001, safeBottom - safeTop))
  };
}

function boxHandleForPoint(point, bbox) {
  const size = getStageSize();
  const edges = bboxEdges(bbox);
  const width = Math.max(0.001, edges.right - edges.left);
  const height = Math.max(0.001, edges.bottom - edges.top);
  const thresholdX = Math.min(10 / Math.max(size.width, 1), width / 3);
  const thresholdY = Math.min(10 / Math.max(size.height, 1), height / 3);
  const nearLeft = Math.abs(point.x - edges.left) <= thresholdX;
  const nearRight = Math.abs(point.x - edges.right) <= thresholdX;
  const nearTop = Math.abs(point.y - edges.top) <= thresholdY;
  const nearBottom = Math.abs(point.y - edges.bottom) <= thresholdY;
  if (nearTop && nearLeft) return "nw";
  if (nearTop && nearRight) return "ne";
  if (nearBottom && nearLeft) return "sw";
  if (nearBottom && nearRight) return "se";
  if (nearTop) return "n";
  if (nearBottom) return "s";
  if (nearLeft) return "w";
  if (nearRight) return "e";
  return "move";
}

function cursorForBoxHandle(handle) {
  return {
    n: "ns-resize",
    s: "ns-resize",
    e: "ew-resize",
    w: "ew-resize",
    ne: "nesw-resize",
    sw: "nesw-resize",
    nw: "nwse-resize",
    se: "nwse-resize",
    move: "move"
  }[handle] || "default";
}

function resetOverlayCursor() {
  if (!els.overlay) return;
  els.overlay.style.cursor = state.drawMode ? "crosshair" : "default";
}

function markRegionAdjusted(region) {
  if (!region.human_review) region.human_review = {};
  region.human_review.adjusted_bbox = { ...region.bbox };
  if (!region.human_review.review_action || region.human_review.review_action === "pending") {
    region.human_review.review_action = "adjust";
  }
}

function resizedBbox(startBbox, mode, dx, dy) {
  const minWidth = 0.004;
  const minHeight = 0.004;
  let { left, right, top, bottom } = bboxEdges(startBbox);
  if (mode.includes("w")) left += dx;
  if (mode.includes("e")) right += dx;
  if (mode.includes("n")) top += dy;
  if (mode.includes("s")) bottom += dy;

  if (right - left < minWidth) {
    if (mode.includes("w")) left = right - minWidth;
    else right = left + minWidth;
  }
  if (bottom - top < minHeight) {
    if (mode.includes("n")) top = bottom - minHeight;
    else bottom = top + minHeight;
  }

  left = clamp(left);
  right = clamp(right);
  top = clamp(top);
  bottom = clamp(bottom);

  if (right - left < minWidth) {
    if (mode.includes("w")) left = Math.max(0, right - minWidth);
    else right = Math.min(1, left + minWidth);
  }
  if (bottom - top < minHeight) {
    if (mode.includes("n")) top = Math.max(0, bottom - minHeight);
    else bottom = Math.min(1, top + minHeight);
  }

  return bboxFromEdges(left, top, right, bottom);
}

function movedBbox(startBbox, dx, dy) {
  const width = clamp(Number(startBbox.width) || 0.001, 0.001, 1);
  const height = clamp(Number(startBbox.height) || 0.001, 0.001, 1);
  return {
    x_center: roundUnit(clamp((Number(startBbox.x_center) || 0.5) + dx, width / 2, 1 - width / 2)),
    y_center: roundUnit(clamp((Number(startBbox.y_center) || 0.5) + dy, height / 2, 1 - height / 2)),
    width: roundUnit(width),
    height: roundUnit(height)
  };
}

function updateDraggedRegionBox(point) {
  if (!state.drag || state.drag.type !== "region-box") return false;
  const region = state.regions.find((item) => item.region_id === state.drag.regionId);
  if (!region) return false;
  if (!state.drag.undoSaved) {
    pushUndo("调整证据框");
    state.drag.undoSaved = true;
  }
  const dx = point.x - state.drag.startPoint.x;
  const dy = point.y - state.drag.startPoint.y;
  region.bbox = state.drag.mode === "move"
    ? movedBbox(state.drag.startBbox, dx, dy)
    : resizedBbox(state.drag.startBbox, state.drag.mode, dx, dy);
  markRegionAdjusted(region);
  return true;
}

function regionClassName(regionType) {
  return `region-${String(regionType || "").toLowerCase().replace(/_/g, "-")}`;
}

function svgEl(name) {
  return document.createElementNS("http://www.w3.org/2000/svg", name);
}

function labelWidthEstimate(text) {
  const width = Array.from(String(text || "")).reduce((sum, char) => {
    return sum + (/[\u4e00-\u9fff]/.test(char) ? 13 : 7);
  }, 18);
  return Math.min(260, Math.max(72, width));
}

function appendSelectedRegionLabel(box, region, size) {
  const label = friendlyRegionType(region.region_type);
  const labelWidth = labelWidthEstimate(label);
  const labelHeight = 24;
  const x = Math.min(Math.max(box.x, 3), Math.max(3, size.width - labelWidth - 3));
  const y = box.y > labelHeight + 6
    ? box.y - labelHeight - 4
    : Math.min(size.height - labelHeight - 3, box.y + box.height + 6);
  const group = svgEl("g");
  group.classList.add("box-tag");
  const bg = svgEl("rect");
  bg.setAttribute("x", x);
  bg.setAttribute("y", y);
  bg.setAttribute("width", labelWidth);
  bg.setAttribute("height", labelHeight);
  bg.setAttribute("rx", 5);
  bg.classList.add("box-tag-bg");
  const text = svgEl("text");
  text.setAttribute("x", x + 8);
  text.setAttribute("y", y + 16);
  text.classList.add("box-tag-text");
  text.textContent = label;
  group.appendChild(bg);
  group.appendChild(text);
  els.overlay.appendChild(group);
}

function renderOverlay() {
  const size = getStageSize();
  syncOverlayToImage(size);
  els.overlay.setAttribute("viewBox", `0 0 ${size.width} ${size.height}`);
  els.overlay.innerHTML = "";
  const selectedRow = selectedFieldRow();
  const evidenceRegionIds = new Set(
    selectedRow ? (reviewForField(selectedRow).evidence_region_ids || []) : []
  );

  state.regions.forEach((region) => {
    const box = bboxToPixels(region.bbox);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", box.x);
    rect.setAttribute("y", box.y);
    rect.setAttribute("width", box.width);
    rect.setAttribute("height", box.height);
    rect.classList.add("box");
    rect.classList.add(regionClassName(region.region_type));
    if (region.region_id === state.selectedRegionId) rect.classList.add("selected");
    if (evidenceRegionIds.has(region.region_id)) rect.classList.add("field-evidence");
    if (state.flashRegionId === region.region_id) rect.classList.add("just-linked");
    if (state.drag?.type === "region-box" && state.drag.regionId === region.region_id) {
      rect.style.cursor = cursorForBoxHandle(state.drag.mode);
    }
    rect.addEventListener("pointerdown", (event) => {
      if (state.drawMode) return;
      event.stopPropagation();
      event.preventDefault();
      state.selectedRegionId = region.region_id;
      if (!canAnnotateCurrent()) {
        renderOverlay();
        renderRegionForm();
        renderTargets();
        return;
      }
      const point = normalizedPoint(event);
      const mode = boxHandleForPoint(point, region.bbox);
      state.drag = {
        type: "region-box",
        regionId: region.region_id,
        mode,
        startPoint: point,
        startBbox: { ...region.bbox }
      };
      els.overlay.style.cursor = cursorForBoxHandle(mode);
      rect.style.cursor = cursorForBoxHandle(mode);
      renderOverlay();
      renderRegionForm();
      renderTargets();
    });
    rect.addEventListener("pointermove", (event) => {
      if (state.drawMode || state.drag || !canAnnotateCurrent()) return;
      const cursor = cursorForBoxHandle(boxHandleForPoint(normalizedPoint(event), region.bbox));
      els.overlay.style.cursor = cursor;
      rect.style.cursor = cursor;
    });
    rect.addEventListener("pointerleave", () => {
      if (!state.drag) resetOverlayCursor();
    });
    els.overlay.appendChild(rect);

    if (region.region_id === state.selectedRegionId) {
      const ring = svgEl("rect");
      const ringX = Math.max(0, box.x - 4);
      const ringY = Math.max(0, box.y - 4);
      ring.setAttribute("x", ringX);
      ring.setAttribute("y", ringY);
      ring.setAttribute("width", Math.min(size.width - ringX, box.width + 8));
      ring.setAttribute("height", Math.min(size.height - ringY, box.height + 8));
      ring.classList.add("selection-ring");
      els.overlay.appendChild(ring);
      appendSelectedRegionLabel(box, region, size);
    }
  });

  if (state.draft) {
    const box = bboxToPixels(state.draft);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", box.x);
    rect.setAttribute("y", box.y);
    rect.setAttribute("width", box.width);
    rect.setAttribute("height", box.height);
    rect.classList.add("draft-box");
    els.overlay.appendChild(rect);
  }
}

function renderRegionForm() {
  const region = selectedRegion();
  els.emptyRegion.classList.toggle("hidden", Boolean(region));
  els.regionForm.classList.toggle("hidden", !region);

  if (!region) {
    els.mappingList.innerHTML = '<p class="empty">选中一个框后，会显示对应字段候选。</p>';
    return;
  }

  if (els.regionRoleHint) {
    els.regionRoleHint.innerHTML = `
      <strong>${escapeText(friendlyRegionType(region.region_type))}</strong>
      <p>${escapeText(friendlyRegionNote(region))}</p>
    `;
  }
  els.regionIdInput.value = region.region_id;
  els.regionIdInput.readOnly = true;
  els.regionTypeInput.value = region.region_type;
  els.regionTypeInput.readOnly = true;
  els.labelInput.value = friendlyRegionType(region.region_type);
  els.ocrInput.value = region.ocr_text;
  els.bboxX.value = region.bbox.x_center.toFixed(3);
  els.bboxY.value = region.bbox.y_center.toFixed(3);
  els.bboxW.value = region.bbox.width.toFixed(3);
  els.bboxH.value = region.bbox.height.toFixed(3);
  els.reviewActionInput.value = region.human_review.review_action || "pending";
  const note = region.human_review.notes || "";
  els.notesInput.value = /[\u4e00-\u9fff]/.test(note) ? note : friendlyRegionNote(region);
  [
    els.regionTypeInput,
    els.labelInput,
    els.ocrInput,
    els.bboxX,
    els.bboxY,
    els.bboxW,
    els.bboxH,
    els.reviewActionInput,
    els.notesInput
  ].forEach((input) => {
    if (input) input.disabled = !canAnnotateCurrent();
  });
  renderMappingsV2(region);
}

function renderMappings(region) {
  els.mappingList.innerHTML = "";
  if (!region.candidate_mappings.length) {
    els.mappingList.innerHTML = '<p class="empty">当前框还没有字段映射。可以从下方候选目标字段挂接。</p>';
    return;
  }

  region.candidate_mappings.forEach((mapping, index) => {
    const item = document.createElement("div");
    item.className = "mapping-item";
    item.innerHTML = `
      <strong>${escapeText(mapping.candidate_leg_id || "procedure")} ${mapping.leg_type ? `(${escapeText(mapping.leg_type)})` : ""}.${escapeText(mapping.field_name || "")}</strong>
      <div class="muted">expected: ${escapeText(mapping.expected_value)}</div>
      <select data-index="${index}">
        <option value="pending">pending</option>
        <option value="accepted">accepted</option>
        <option value="rejected">rejected</option>
        <option value="changed">changed</option>
        <option value="needs_discussion">needs_discussion</option>
      </select>
      <button data-remove="${index}">移除映射</button>
    `;
    const select = item.querySelector("select");
    select.value = mapping.human_decision || "pending";
    select.addEventListener("change", () => {
      mapping.human_decision = select.value;
    });
    item.querySelector("button").addEventListener("click", () => {
      region.candidate_mappings.splice(index, 1);
      renderMappings(region);
    });
    els.mappingList.appendChild(item);
  });
}

function renderMappingsV2(region) {
  els.mappingList.innerHTML = "";
  if (!region.candidate_mappings.length) {
    els.mappingList.innerHTML = '<p class="empty">当前框还没有对应到任何 PR #28 字段。先在下方“候选目标字段”里找应该由这个框证明的字段，再点“挂到当前框”。</p>';
    renderCanonicalPanel();
    return;
  }

  const actions = document.createElement("div");
  actions.className = "mapping-actions";
  actions.innerHTML = `
    <button data-action="accept-all">确认下面全部对应</button>
    <button data-action="accept-next">确认本框并跳下一个</button>
    <button data-action="pending-all">全部暂不确认</button>
    <p class="hint">如果这个框确实包含下面列出的所有信息，可以一次确认；不确定时逐条确认更稳。</p>
  `;
  actions.querySelectorAll("button").forEach((button) => {
    button.disabled = !canAnnotateCurrent();
  });
  actions.querySelector('[data-action="accept-all"]').addEventListener("click", () => {
    if (!canAnnotateCurrent()) return;
    acceptPendingMappings(region);
    renderRegionForm();
    renderTargets();
    renderCanonicalPanel();
  });
  actions.querySelector('[data-action="accept-next"]').addEventListener("click", acceptCurrentAndAdvance);
  actions.querySelector('[data-action="pending-all"]').addEventListener("click", () => {
    if (!canAnnotateCurrent()) return;
    region.candidate_mappings.forEach((mapping) => {
      mapping.human_decision = "pending";
    });
    renderRegionForm();
    renderTargets();
    renderCanonicalPanel();
  });
  els.mappingList.appendChild(actions);

  region.candidate_mappings.forEach((mapping, index) => {
    const item = document.createElement("div");
    const decision = mapping.human_decision || "pending";
    const decisionLabel = {
      accepted: "已确认",
      rejected: "不属于此框",
      pending: "待确认",
      changed: "需改值",
      needs_discussion: "不确定"
    }[decision] || decision;
    item.className = `mapping-item decision-${decision}`;
    const canonicalAnswer = mapping.human_answer || canonicalFieldForMapping(mapping);
    item.innerHTML = `
      <div class="mapping-head">
        <strong>${escapeText(friendlyLegName(mapping))}</strong>
        <span>${escapeText(decisionLabel)}</span>
      </div>
      <div><b>字段：</b>${escapeText(friendlyFieldName(mapping.field_name))}</div>
      <div><b>应看到：</b>${escapeText(friendlyAnswerValue(canonicalAnswer, mapping.expected_value))}</div>
      <div class="mapping-actions mapping-actions-compact">
        <button data-decision="accepted">确认对应</button>
        <button data-decision="rejected">不属于此框</button>
        <button data-decision="needs_discussion">不确定</button>
        <button data-remove="${index}">移除</button>
      </div>
    `;
    item.querySelectorAll("[data-decision]").forEach((button) => {
      button.addEventListener("click", () => {
        if (!canAnnotateCurrent()) return;
        pushUndo("修改字段对应");
        mapping.human_decision = button.dataset.decision;
        renderMappingsV2(region);
        renderTargets();
        renderCanonicalPanel();
      });
    });
    item.querySelector("[data-remove]").addEventListener("click", () => {
      if (!canAnnotateCurrent()) return;
      pushUndo("移除字段对应");
      region.candidate_mappings.splice(index, 1);
      renderMappingsV2(region);
      renderTargets();
      renderCanonicalPanel();
    });
    item.querySelectorAll("button").forEach((button) => {
      button.disabled = !canAnnotateCurrent();
    });
    els.mappingList.appendChild(item);
  });
  renderCanonicalPanel();
}

function renderCanonicalPanel() {
  if (!els.canonicalSummary || !els.canonicalCompare) return;
  const canonical = state.current?.canonical_gt;
  if (!canonical) {
    els.canonicalSummary.innerHTML = '<p class="empty">当前航图没有 CIFP canonical JSON，无法做 PR #28 对比。</p>';
    els.canonicalCompare.innerHTML = "";
    renderWorkflowPanel();
    if (els.annotationJsonPreview) els.annotationJsonPreview.textContent = "";
    if (els.canonicalJsonPreview) els.canonicalJsonPreview.textContent = "";
    return;
  }

  const predicted = buildAnnotationCanonicalJson();
  const comparison = compareCanonicalJson(predicted, canonical);
  const acceptedCount = state.regions.reduce(
    (sum, item) => sum + (item.candidate_mappings || []).filter((mapping) => mapping.human_decision === "accepted").length,
    0
  );
  const pendingCount = state.regions.reduce(
    (sum, item) => sum + (item.candidate_mappings || []).filter((mapping) => !mapping.human_decision || mapping.human_decision === "pending").length,
    0
  );
  const allAttentionRows = comparison.rows
    .filter((row) => row.requiresBoxEvidence && !row.match)
    .sort((left, right) => Number(left.covered) - Number(right.covered));
  renderWorkflowPanel();
  const attentionRows = allAttentionRows.slice(0, 12);

  els.canonicalSummary.innerHTML = `
    <div class="score-grid">
      <div><strong>${comparison.present_matched}/${comparison.present_total}</strong><span>present 证据对齐</span></div>
      <div><strong>${Math.round(comparison.present_coverage * 100)}%</strong><span>present 证据覆盖</span></div>
      <div><strong>${comparison.matched}/${comparison.total}</strong><span>完整 JSON 对齐</span></div>
      <div><strong>${comparison.auto_status_total}</strong><span>自动状态字段</span></div>
      <div><strong>${acceptedCount}</strong><span>accepted 映射</span></div>
      <div><strong>${pendingCount}</strong><span>pending 映射</span></div>
    </div>
    <p class="hint">这里是与 424 canonical 目标的证据对齐视图，不是独立模型抽取正确率；日常操作优先看“当前字段任务”。</p>
  `;

  els.canonicalCompare.innerHTML = "";
  const taskTitle = document.createElement("div");
  taskTitle.className = "compare-section-title";
  taskTitle.textContent = attentionRows.length
    ? "优先检查：未覆盖或不对齐的 present 字段"
    : "present 字段已全部有证据对齐";
  els.canonicalCompare.appendChild(taskTitle);

  attentionRows.forEach((row) => {
    const item = document.createElement("div");
    item.className = `compare-row ${row.match ? "match" : row.covered ? "mismatch" : "missing"}`;
    item.innerHTML = `
      <strong>${escapeText(row.key)}</strong>
      <span>${row.match ? "match" : row.covered ? "mismatch" : "missing"}</span>
      <small>人工：${escapeText(formatAnswer(row.predicted))}</small>
      <small>CIFP：${escapeText(formatAnswer(row.answer))}</small>
    `;
    item.title = `人工: ${JSON.stringify(row.predicted)}\nCIFP: ${JSON.stringify(row.answer)}`;
    els.canonicalCompare.appendChild(item);
  });

  const allTitle = document.createElement("div");
  allTitle.className = "compare-section-title";
  allTitle.textContent = "完整字段对比预览";
  els.canonicalCompare.appendChild(allTitle);

  comparison.rows.slice(0, 24).forEach((row) => {
    const item = document.createElement("div");
    item.className = `compare-row ${row.match ? "match" : row.covered ? "mismatch" : "missing"} ${row.autoStatusField ? "auto-status" : ""}`;
    item.innerHTML = `
      <strong>${escapeText(row.key)}</strong>
      <span>${row.autoStatusField && row.match ? "无需画框 · match" : row.match ? "match" : row.covered ? "mismatch" : "missing"}</span>
    `;
    item.title = `人工: ${JSON.stringify(row.predicted)}\nCIFP: ${JSON.stringify(row.answer)}`;
    els.canonicalCompare.appendChild(item);
  });

  const more = document.createElement("p");
  more.className = "hint";
  more.textContent = "完整内容见下方两个 JSON 预览；保存时会把人工框生成 JSON 和 PR #28 证据对齐摘要一起写入标注文件。";
  els.canonicalCompare.appendChild(more);

  if (els.annotationJsonPreview) {
    els.annotationJsonPreview.textContent = JSON.stringify(predicted, null, 2);
  }
  if (els.canonicalJsonPreview) {
    els.canonicalJsonPreview.textContent = JSON.stringify(canonical, null, 2);
  }
}

function targetFieldButton(target, leg, field) {
  const item = document.createElement("div");
  item.className = "target-item";
  const legId = leg?.candidate_leg_id || "procedure";
  const legType = leg?.leg_type || "";
  const fieldName = field.field_name || field.name;
  const expectedValue = field.expected_value ?? field.value ?? "";
  const answer = field.expected_answer || null;
  const region = selectedRegion();
  const alreadyLinked = Boolean(region?.candidate_mappings?.some((mapping) => {
    return mapping.candidate_leg_id === legId && mapping.field_name === fieldName;
  }));
  item.innerHTML = `
    <strong>${escapeText(friendlyFieldName(fieldName))}</strong>
    <div class="muted">${escapeText(friendlyLegName({ candidate_leg_id: legId, canonical_leg_index: leg?.canonical_leg_index, leg_type: legType }))}</div>
    <div><b>应在图上找到：</b>${escapeText(friendlyAnswerValue(answer, expectedValue))}</div>
    <div class="target-actions">
      ${alreadyLinked
        ? '<button data-action="accept-existing">加入为依据</button><button data-action="unlink-existing">取消挂接</button>'
        : '<button data-action="link">挂到当前框</button><button data-action="link-accept">加入为依据</button>'
      }
    </div>
  `;
  item.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    if (!canAnnotateCurrent()) {
      showToast("当前是预览模式，请先领取这张图再标注。");
      return;
    }
    const activeRegion = selectedRegion();
    if (!activeRegion) {
      showToast("先选中或新增一个框，再挂字段。");
      return;
    }
    if (button.dataset.action === "accept-existing") {
      const rowKey = fieldKey(leg?.canonical_leg_index || canonicalLegIndexForMapping({ candidate_leg_id: legId }), fieldName);
      const row = buildFieldRows().find((item) => item.key === rowKey);
      if (!row) return;
      pushUndo("加入图上依据");
      ensureMappingForRegion(row, activeRegion, "pending");
      const review = reviewForField(row);
      setFieldEvidenceDraft(row, uniqueList([...(review.required_evidence_region_ids || []), activeRegion.region_id]));
      state.selectedFieldKey = row.key;
      flashRegion(activeRegion.region_id);
      renderMappingsV2(activeRegion);
      renderTargets();
      renderCanonicalPanel();
      showToast("已把当前框加入为图上依据；还需要说明它怎么支持判断。");
      return;
    }
    if (button.dataset.action === "unlink-existing") {
      pushUndo("取消字段挂接");
      activeRegion.candidate_mappings = (activeRegion.candidate_mappings || []).filter((mapping) => {
        return !(mapping.candidate_leg_id === legId && mapping.field_name === fieldName);
      });
      renderMappingsV2(activeRegion);
      renderTargets();
      renderCanonicalPanel();
      showToast("已取消当前框和这个字段的挂接。");
      return;
    }
    const shouldAddToBasket = button.dataset.action === "link-accept";
    pushUndo(shouldAddToBasket ? "加入图上依据" : "挂接字段");
    activeRegion.candidate_mappings.push({
      candidate_leg_id: leg?.candidate_leg_id || "",
      canonical_leg_index: leg?.canonical_leg_index || null,
      leg_type: leg?.leg_type || "",
      field_name: fieldName,
      expected_value: expectedValue,
      expected_answer: field.expected_answer || null,
      match_basis: "human-added from target panel",
      confidence: null,
      human_decision: "pending",
      human_notes: ""
    });
    if (shouldAddToBasket) {
      const rowKey = fieldKey(leg?.canonical_leg_index || canonicalLegIndexForMapping({ candidate_leg_id: legId }), fieldName);
      const row = buildFieldRows().find((item) => item.key === rowKey);
      if (row) {
        const review = reviewForField(row);
        setFieldEvidenceDraft(row, uniqueList([...(review.required_evidence_region_ids || []), activeRegion.region_id]));
        state.selectedFieldKey = row.key;
      }
      flashRegion(activeRegion.region_id);
    }
    renderMappingsV2(activeRegion);
    renderTargets();
    renderCanonicalPanel();
    showToast(shouldAddToBasket ? "已加入为图上依据；还需要说明它怎么支持判断。" : "已加入当前框的候选映射。");
  }));
  item.querySelectorAll("button").forEach((button) => {
    button.disabled = !canAnnotateCurrent();
  });
  return item;
}

function renderTargets() {
  const target = state.current?.target;
  els.targetList.innerHTML = "";
  if (!target) {
    els.targetList.innerHTML = '<p class="empty">当前样本没有 target 文件记录。</p>';
    return;
  }

  const summary = document.createElement("div");
  summary.className = "target-item";
  summary.innerHTML = `
    <strong>当前航图的 424 复飞候选</strong>
    <div class="muted">主 transition：${escapeText(target.main_transition_candidate || "")}；候选复飞航段：${escapeText(target.candidate_missed_approach_leg_count || 0)} 个</div>
    <p class="hint">下面默认只列出需要人工框确认的 present 字段；本航图没有的字段放在“无需画框字段”里自动处理。</p>
    ${target.anomaly_note ? `<div class="badge hot">${escapeText(target.anomaly_note)}</div>` : ""}
  `;
  els.targetList.appendChild(summary);

  (target.candidate_legs || []).forEach((leg) => {
    const fields = leg.target_fields || [];
    const visualFields = fields.filter((field) => {
      return field.expected_answer?.status === "present";
    });
    const openVisualFields = visualFields.filter((field) => {
      const key = fieldKey(leg.canonical_leg_index, field.field_name || field.name);
      const row = buildFieldRows().find((item) => item.key === key);
      return row ? reviewForField(row).review_status === "pending" : !fieldAcceptedForLeg(leg, field);
    });
    const completedVisualFields = visualFields.filter((field) => {
      const key = fieldKey(leg.canonical_leg_index, field.field_name || field.name);
      const row = buildFieldRows().find((item) => item.key === key);
      return row ? FIELD_REVIEW_DONE.has(reviewForField(row).review_status) : fieldAcceptedForLeg(leg, field);
    });
    const autoFields = fields.filter((field) => !visualFields.includes(field));
    const title = document.createElement("div");
    title.className = "target-leg";
    title.textContent = `${friendlyLegName(leg)} · 待处理 ${openVisualFields.length} 项 / 已完成 ${completedVisualFields.length} 项`;
    els.targetList.appendChild(title);
    if (!openVisualFields.length) {
      const empty = document.createElement("p");
      empty.className = "empty compact-empty";
      empty.textContent = visualFields.length
        ? "这个航段的可视字段已经确认完成。"
        : "这个航段没有需要单独画框确认的可视字段。";
      els.targetList.appendChild(empty);
    }
    openVisualFields.forEach((field) => {
      els.targetList.appendChild(targetFieldButton(target, leg, field));
    });
    if (completedVisualFields.length) {
      const details = document.createElement("details");
      details.className = "auto-fields completed-fields";
      details.innerHTML = `<summary>已完成字段 ${completedVisualFields.length} 项</summary>`;
      completedVisualFields.forEach((field) => {
        const row = document.createElement("div");
        row.className = "auto-field-row";
        row.innerHTML = `
          <strong>${escapeText(friendlyFieldName(field.field_name || field.name))}</strong>
          <span>${escapeText(friendlyAnswerValue(field.expected_answer, field.expected_value || ""))}</span>
        `;
        details.appendChild(row);
      });
      els.targetList.appendChild(details);
    }
    if (autoFields.length) {
      const details = document.createElement("details");
      details.className = "auto-fields";
      details.innerHTML = `<summary>无需画框字段 / 自动状态 ${autoFields.length} 项</summary>`;
      autoFields.forEach((field) => {
        const answer = field.expected_answer || null;
        const row = document.createElement("div");
        row.className = "auto-field-row";
        row.innerHTML = `
          <strong>${escapeText(friendlyFieldName(field.field_name || field.name))}</strong>
          <span>${escapeText(friendlyAnswerValue(answer, field.expected_value || ""))}</span>
        `;
        details.appendChild(row);
      });
      els.targetList.appendChild(details);
    }
  });
}

function updateSelectedFromForm() {
  const region = selectedRegion();
  if (!region) return;
  if (!canAnnotateCurrent()) return;
  region.region_id = els.regionIdInput.value.trim() || region.region_id;
  state.selectedRegionId = region.region_id;
  region.region_type = els.regionTypeInput.value.trim() || "MISSED_APPROACH_TEXT";
  const meta = metaForRegionType(region.region_type);
  region.annotation_scope = meta.annotation_scope || region.annotation_scope;
  region.element_role = meta.element_role || region.element_role;
  region.source_field_name = meta.source_field_name;
  region.label = els.labelInput.value;
  region.ocr_text = els.ocrInput.value;
  region.bbox.x_center = clamp(Number(els.bboxX.value));
  region.bbox.y_center = clamp(Number(els.bboxY.value));
  region.bbox.width = clamp(Number(els.bboxW.value), 0.001, 1);
  region.bbox.height = clamp(Number(els.bboxH.value), 0.001, 1);
  region.human_review.review_action = els.reviewActionInput.value;
  region.human_review.notes = els.notesInput.value;
  renderOverlay();
}

function addRegion(type, bbox) {
  if (!state.current) {
    showToast("请先选择一张航图。");
    return;
  }
  if (!canAnnotateCurrent()) {
    showToast("当前是预览模式，请先领取这张图再画框。");
    return;
  }
  pushUndo("新增证据框");
  const meta = metaForRegionType(type);
  const region = normalizeRegion({
    region_id: makeRegionId(state.current.manifest.chart_id, state.regions.length),
    region_type: type,
    bbox,
    label: meta.label,
    annotation_scope: meta.annotation_scope,
    element_role: meta.element_role,
    source_field_name: meta.source_field_name,
    candidate_mappings: [],
    human_review: { review_action: "pending" }
  }, state.regions.length);
  state.regions.push(region);
  state.selectedRegionId = region.region_id;
  const pendingRow = state.pendingLinkFieldKey
    ? buildFieldRows().find((row) => row.key === state.pendingLinkFieldKey)
    : null;
  if (pendingRow) {
    region.candidate_mappings.push(mappingFromFieldRow(pendingRow, false));
    const review = reviewForField(pendingRow);
    setFieldEvidenceDraft(pendingRow, uniqueList([...(review.required_evidence_region_ids || []), region.region_id]));
    state.selectedFieldKey = pendingRow.key;
    state.pendingLinkFieldKey = null;
    state.drawMode = false;
    if (els.drawBtn) {
      els.drawBtn.classList.remove("primary");
      els.drawBtn.textContent = "为当前字段画证据框";
    }
    flashRegion(region.region_id);
    showToast("新框已加入为图上依据。请说明它怎么支持判断。");
  }
  renderOverlay();
  renderRegionForm();
  renderTargets();
  renderCanonicalPanel();
}

function buildAnnotationPayload(mode = "final") {
  const chartId = state.current.manifest.chart_id;
  const annotationPr28 = buildAnnotationCanonicalJson();
  const comparison = state.current.canonical_gt
    ? compareCanonicalJson(annotationPr28, state.current.canonical_gt)
    : null;
  const fieldReviews = buildFieldRows()
    .filter((row) => row.requires_review)
    .map((row) => {
      const review = reviewForField(row);
      return {
        field_key: row.key,
        chart_id: chartId,
        candidate_leg_id: row.candidate_leg_id,
        canonical_leg_index: row.canonical_leg_index,
        leg_type: row.leg_type,
        field_name: row.field_name,
        canonical_answer: row.expected_answer || null,
        review_status: review.review_status,
        support_mode: review.support_mode || review.review_status,
        required_evidence_region_ids: review.required_evidence_region_ids || [],
        secondary_evidence_region_ids: review.secondary_evidence_region_ids || [],
        evidence_region_ids: review.evidence_region_ids || [],
        evidence_source: review.evidence_source || [],
        checked_scopes: review.checked_scopes || [],
        checked_sources: review.checked_sources || review.checked_scopes || [],
        notes: review.notes || "",
        reviewed_by: review.reviewed_by || currentAnnotator() || "",
        reviewed_at: review.reviewed_at || "",
        schema: "field_review_v2"
      };
    });
  const pendingFieldCount = fieldReviews.filter((item) => item.review_status === "pending").length;
  const supportCount = (status) => fieldReviews.filter((item) => item.support_mode === status || item.review_status === status).length;
  const reviewStatus = mode === "draft" ? "draft_saved" : "pilot_reviewed";
  return {
    chart_id: chartId,
    dataset_key: state.current?.dataset?.key || datasetKey,
    dataset_label: state.current?.dataset?.label || datasetConfig.label,
    image_path: state.current.manifest.image_file || "",
    annotator: currentAnnotator() || (datasetConfig.finalDataset ? "" : "practice_user"),
    review_status: reviewStatus,
    save_mode: mode,
    source_prelabel_file: `prelabels/${chartId}.json`,
    canonical_targets_file: "targets/canonical_targets.json",
    canonical_proxy_gt_combined_file: "targets/canonical_proxy_gt_combined.json",
    canonical_proxy_gt_file: state.current.target?.canonical_proxy_gt_file || `targets/canonical_proxy_gt/${chartId}.json`,
    regions: state.regions.map((region) => {
      const accepted = region.candidate_mappings.filter((mapping) => mapping.human_decision === "accepted");
      const rejected = region.candidate_mappings.filter((mapping) => mapping.human_decision === "rejected");
      return {
        final_region_id: region.region_id,
        source_region_id: region.source_region_id || region.region_id,
        region_type: region.region_type,
        bbox: region.bbox,
        label: region.label,
        ocr_text: region.ocr_text,
        annotation_scope: region.annotation_scope || "",
        element_role: region.element_role || "",
        expected_visual_value: region.expected_visual_value || "",
        step_id: region.step_id || "",
        parent_step_region_id: region.parent_step_region_id || "",
        source_candidate_leg_id: region.source_candidate_leg_id || "",
        source_leg_type: region.source_leg_type || "",
        source_field_name: region.source_field_name || "",
        is_formal_annotation_candidate: region.is_formal_annotation_candidate || false,
        accepted_mappings: accepted.map((mapping) => ({
          candidate_leg_id: mapping.candidate_leg_id || "",
          canonical_leg_index: canonicalLegIndexForMapping(mapping),
          leg_type: mapping.leg_type || "",
          field_name: mapping.field_name || "",
          final_value: mapping.expected_value ?? null,
          canonical_answer: mapping.human_answer || canonicalFieldForMapping(mapping) || null,
          evidence_role: "supports_field",
          human_confidence: "medium",
          notes: mapping.human_notes || mapping.match_basis || ""
        })),
        rejected_mappings: rejected.map((mapping) => ({
          candidate_leg_id: mapping.candidate_leg_id || "",
          leg_type: mapping.leg_type || "",
          field_name: mapping.field_name || "",
          reason: mapping.human_notes || "rejected during platform review"
        })),
        candidate_mappings_reviewed: region.candidate_mappings,
        review_action: region.human_review.review_action || "pending",
        needs_discussion: region.candidate_mappings.some((mapping) => mapping.human_decision === "needs_discussion"),
        notes: region.human_review.notes || ""
      };
    }),
    unresolved_targets: [],
    field_reviews: fieldReviews,
    evidence_provenance: fieldReviews,
    field_review_summary: {
      schema: "field_review_v2",
      total_present_fields: fieldReviews.length,
      pending_fields: pendingFieldCount,
      direct_visible: supportCount("direct_visible"),
      visible_joint: supportCount("visible_joint"),
      rule_default_completion: supportCount("rule_default_completion"),
      insufficient_for_encoding: supportCount("insufficient_for_encoding"),
      uncertain_fields: supportCount("uncertain")
    },
    annotation_pr28_json: annotationPr28,
    canonical_gt_file: state.current.target?.canonical_proxy_gt_file || `targets/canonical_proxy_gt/${chartId}.json`,
    pr28_comparison_summary: comparison
      ? {
          metric_scope: "manual_evidence_alignment_against_cifp424_canonical_not_independent_extraction_accuracy",
          canonical_answer_source: "CIFP/424 canonical target",
          total: comparison.total,
          matched: comparison.matched,
          covered: comparison.covered,
          present_total: comparison.present_total,
          present_matched: comparison.present_matched,
          present_covered: comparison.present_covered,
          auto_status_total: comparison.auto_status_total,
          full_alignment_rate: comparison.full_alignment_rate,
          overall_evidence_coverage: comparison.overall_evidence_coverage,
          present_alignment_rate: comparison.present_alignment_rate,
          present_evidence_coverage: comparison.present_coverage
        }
      : null,
    sample_notes: mode === "draft"
      ? "Draft saved from local annotation platform."
      : "Saved from local annotation platform."
  };
}

async function saveCurrentDraftSnapshot({ reason = "", reviewStatus = "draft_saved", silent = false } = {}) {
  if (!state.current) return null;
  updateSelectedFromForm();
  const chartId = state.current.manifest.chart_id;
  const payload = buildAnnotationPayload("draft");
  payload.review_status = reviewStatus;
  if (reason) payload.return_reason = reason;
  if (reviewStatus === "submitted_for_expert_review") {
    payload.sample_notes = "Draft auto-saved before submitting this chart to expert review.";
  }
  const result = await postJson(apiUrl(`/api/drafts/${encodeURIComponent(chartId)}`), payload);
  state.current.draft = { ...payload, saved_at: result.saved_at || payload.saved_at || "" };
  const chart = state.charts.find((item) => item.chart_id === chartId);
  if (chart) {
    chart.has_my_draft = true;
    chart.draft_saved_at = result.saved_at || payload.saved_at || new Date().toISOString();
  }
  if (!silent) showToast("已暂存。");
  return result;
}

async function saveCurrentWork(mode = "final") {
  if (!state.current) {
    showToast("请先选择一张航图。");
    return;
  }
  updateSelectedFromForm();
  const chartId = state.current.manifest.chart_id;
  if (datasetConfig.finalDataset && !currentAnnotator()) {
    showToast("当前参与者身份缺失，请刷新页面。");
    return;
  }
  if (datasetConfig.finalDataset) {
    const claimedBy = state.current.manifest.claimed_by || "";
    const claimStatus = state.current.manifest.claim_status || "unassigned";
    if (!expertReviewMode() && claimStatus === "returned_for_expert_review") {
      showToast("这张图已退回专家复审，不能继续保存。");
      return;
    }
    const editableStatuses = expertReviewMode()
      ? ["expert_review_claimed", "expert_review_claimed_by_me"]
      : ["claimed", "claimed_by_me", "submitted"];
    if (claimedBy !== currentAnnotator() || !editableStatuses.includes(claimStatus)) {
      showToast(formalQueueMode()
        ? expertReviewMode()
          ? "当前复核任务尚未领取成功，请刷新或重新进入专家复核。"
          : "当前图尚未领取成功，请刷新或重新进入正式标注。"
        : "请先在左侧点击“领取并开始”，领取成功后再保存。");
      updateClaimButton();
      return;
    }
  }
  if (mode !== "draft") {
    const pendingFields = buildFieldRows()
      .filter((row) => row.requires_review)
      .filter((row) => reviewForField(row).review_status === "pending");
    if (pendingFields.length) {
      showToast(`还有 ${pendingFields.length} 个待审字段。请逐项给出结论后再完成本图。`);
      selectField(pendingFields[0]);
      return;
    }
  }

  const payload = buildAnnotationPayload(mode);
  const endpoint = mode === "draft"
    ? `/api/drafts/${encodeURIComponent(chartId)}`
    : `/api/annotations/${encodeURIComponent(chartId)}`;
  const result = await postJson(apiUrl(endpoint), payload);
  const chart = state.charts.find((item) => item.chart_id === chartId);

  if (mode === "draft") {
    showToast("已暂存。");
    state.current.draft = { ...payload, saved_at: result.saved_at || payload.saved_at || "" };
    if (chart) {
      chart.has_my_draft = true;
      chart.draft_saved_at = result.saved_at || payload.saved_at || new Date().toISOString();
    }
  } else {
    if (!formalQueueMode()) showToast("已提交。");
    if (datasetConfig.finalDataset) {
      state.current.manifest.claim_status = "submitted";
      state.current.manifest.claimed_by = currentAnnotator();
    }
    state.current.annotation = payload;
    if (chart) {
      chart.has_my_annotation = true;
      chart.claim_status = datasetConfig.finalDataset ? "submitted" : "practice";
      chart.claimed_by = currentAnnotator();
      if (expertReviewMode()) chart.expert_reviewer = currentAnnotator();
      chart.submission_count = Number(chart.submission_count || 0) + 1;
    }
  }

  updateClaimButton();
  renderChartList();
  if (mode !== "draft" && formalQueueMode()) {
    await advanceFormalQueue({ afterChartId: chartId, successPrefix: expertReviewMode() ? "已提交复核结果" : "已提交" });
  }
}

async function saveDraft() {
  return saveCurrentWork("draft");
}

async function saveAnnotation() {
  return saveCurrentWork("final");
}

function ensureSaveButtons() {
  if (!els.saveDraftBtn && els.saveBtn?.parentElement) {
    const button = document.createElement("button");
    button.id = "saveDraftBtn";
    button.type = "button";
    button.textContent = "暂存";
    els.saveBtn.parentElement.insertBefore(button, els.saveBtn);
    els.saveDraftBtn = button;
  }

  if (!els.workflowDraftBtn && els.workflowSaveBtn?.parentElement) {
    const button = document.createElement("button");
    button.id = "workflowDraftBtn";
    button.type = "button";
    button.textContent = "暂存当前检查状态";
    els.workflowSaveBtn.parentElement.insertBefore(button, els.workflowSaveBtn);
    els.workflowDraftBtn = button;
  }
}

function bindEvents() {
  els.chartFilter?.addEventListener("input", renderChartList);
  els.annotatorInput?.addEventListener("input", () => {
    if (els.applyAnnotatorBtn) els.applyAnnotatorBtn.disabled = !cleanParticipantId(els.annotatorInput.value);
  });
  els.annotatorInput?.addEventListener("change", () => {
    if (els.annotatorInput) els.annotatorInput.value = cleanParticipantId(els.annotatorInput.value);
  });
  els.annotatorInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    applyAnnotatorIdentity().catch((error) => showToast(error.message));
  });
  els.applyAnnotatorBtn?.addEventListener("click", () => {
    applyAnnotatorIdentity().catch((error) => showToast(error.message));
  });
  if (els.newRegionType) {
    els.newRegionType.addEventListener("change", updateNewRegionTypeHint);
  }
  [
    ["left", els.leftZoomOut, -1],
    ["left", els.leftZoomIn, 1],
    ["center", els.centerZoomOut, -1],
    ["center", els.centerZoomIn, 1],
    ["right", els.rightZoomOut, -1],
    ["right", els.rightZoomIn, 1],
    ["workflow", els.workflowZoomOut, -1],
    ["workflow", els.workflowZoomIn, 1]
  ].forEach(([area, button, direction]) => {
    if (button) button.addEventListener("click", () => adjustPanelZoom(area, direction));
  });
  [
    ["left", els.leftZoomReset],
    ["center", els.centerZoomReset],
    ["right", els.rightZoomReset],
    ["workflow", els.workflowZoomReset]
  ].forEach(([area, button]) => {
    if (button) button.addEventListener("click", () => resetPanelZoom(area));
  });
  bindCtrlWheelZoom();
  els.resizeHandles.forEach((handle) => handle.addEventListener("pointerdown", beginColumnResize));
  window.addEventListener("pointermove", updateColumnResize);
  els.helpBtn?.addEventListener("click", openHelp);
  els.helpCloseBtn?.addEventListener("click", closeHelp);
  els.fullTutorialBtn?.addEventListener("click", () => {
    window.open("/tutorial/", "_blank", "noopener");
  });
  els.detailBoxTutorialBtn?.addEventListener("click", () => {
    window.open("/detail-box-tutorial/", "_blank", "noopener");
  });
  els.helpOverlay?.addEventListener("click", (event) => {
    if (event.target === els.helpOverlay) closeHelp();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.helpOverlay?.classList.contains("hidden")) {
      closeHelp();
    }
  });
  els.drawBtn.addEventListener("click", () => {
    if (!canAnnotateCurrent()) {
      showToast("当前是预览模式，请先领取这张图再画框。");
      return;
    }
    if (state.drawMode) {
      state.drawMode = false;
      state.pendingLinkFieldKey = null;
      els.drawBtn.classList.remove("primary");
      resetOverlayCursor();
      els.drawBtn.textContent = "为当前字段画证据框";
      return;
    }
    const row = selectedFieldRow();
    if (!row) {
      showToast("请先选择一个待审字段。");
      return;
    }
    const type = recommendedRegionTypeForField(row.field_name);
    if (els.newRegionType) {
      els.newRegionType.value = type;
      updateNewRegionTypeHint();
    }
    state.pendingLinkFieldKey = row.key;
    state.drawMode = true;
    els.drawBtn.classList.toggle("primary", state.drawMode);
    resetOverlayCursor();
    els.drawBtn.textContent = "正在画证据框";
    showToast("请在航图上拖出能支持这个判断的位置。");
  });
  els.saveDraftBtn?.addEventListener("click", () => saveDraft().catch((error) => showToast(error.message)));
  els.saveBtn?.addEventListener("click", () => saveAnnotation().catch((error) => showToast(error.message)));
  els.workflowDraftBtn?.addEventListener("click", () => saveDraft().catch((error) => showToast(error.message)));
  els.workflowSaveBtn?.addEventListener("click", () => saveAnnotation().catch((error) => showToast(error.message)));
  els.undoBtn?.addEventListener("click", undoLastAction);
  els.workflowUndoBtn?.addEventListener("click", undoLastAction);
  els.returnClaimBtn?.addEventListener("click", () => returnCurrentClaim().catch((error) => showToast(error.message)));
  els.returnWorkflowBtn?.addEventListener("click", () => returnCurrentClaim().catch((error) => showToast(error.message)));
  els.skipClaimBtn?.addEventListener("click", () => skipCurrentClaim().catch((error) => showToast(error.message)));
  els.claimCurrentBtn?.addEventListener("click", () => claimCurrentChart().catch((error) => showToast(error.message)));
  els.quickAcceptBtn?.addEventListener("click", acceptAllChartPendingMappings);
  els.undoQuickAcceptBtn?.addEventListener("click", undoQuickAccept);
  els.nextPendingBtn?.addEventListener("click", () => {
    const next = nextPendingField();
    if (next) {
      selectField(next);
      showToast("仅切换查看：当前字段没有被记录。");
    } else {
      showToast("没有 pending 字段了，可以完成本图。");
    }
  });
  els.linkSelectedFieldBtn?.addEventListener("click", () => linkSelectedFieldToRegion({ accept: true }));
  els.addRegionForFieldBtn?.addEventListener("click", startDrawRegionForSelectedField);
  els.markNoEvidenceBtn?.addEventListener("click", () => markSelectedField("insufficient_for_encoding"));
  els.markImplicitBtn?.addEventListener("click", () => markSelectedField("rule_default_completion"));
  els.markFieldUnsureBtn?.addEventListener("click", () => markSelectedField("uncertain"));
  els.openTargetsBtn?.addEventListener("click", openTargetPanel);
  els.acceptFrameAndNextBtn?.addEventListener("click", acceptCurrentAndAdvance);
  els.markFrameUnsureBtn?.addEventListener("click", markCurrentFrameUnsure);
  els.deleteRegionBtn?.addEventListener("click", () => {
    if (!canAnnotateCurrent()) {
      showToast("当前是预览模式，请先领取这张图再删除框。");
      return;
    }
    if (!selectedRegion()) {
      showToast("请先选中一个证据框。");
      return;
    }
    if (!window.confirm("确认删除选中的证据框？")) return;
    pushUndo("删除证据框");
    const deletedRegionId = state.selectedRegionId;
    state.regions = state.regions.filter((region) => region.region_id !== deletedRegionId);
    Object.values(state.fieldReviews || {}).forEach((review) => {
      review.required_evidence_region_ids = (review.required_evidence_region_ids || []).filter((regionId) => regionId !== deletedRegionId);
      review.secondary_evidence_region_ids = (review.secondary_evidence_region_ids || []).filter((regionId) => regionId !== deletedRegionId);
      review.evidence_region_ids = uniqueList([
        ...(review.required_evidence_region_ids || []),
        ...(review.secondary_evidence_region_ids || [])
      ]);
      review.evidence_source = sourcesForRegionIds(review.evidence_region_ids || []);
    });
    state.selectedRegionId = state.regions[0]?.region_id || null;
    renderOverlay();
    renderRegionForm();
    renderTargets();
    renderCanonicalPanel();
  });

  [
    els.regionIdInput,
    els.regionTypeInput,
    els.labelInput,
    els.ocrInput,
    els.bboxX,
    els.bboxY,
    els.bboxW,
    els.bboxH,
    els.reviewActionInput,
    els.notesInput
  ].forEach((input) => input.addEventListener("input", updateSelectedFromForm));

  els.overlay.addEventListener("pointerdown", (event) => {
    if (!state.drawMode || !state.current || !canAnnotateCurrent()) return;
    const point = normalizedPoint(event);
    state.draft = {
      x_center: point.x,
      y_center: point.y,
      width: 0.001,
      height: 0.001,
      startX: point.x,
      startY: point.y
    };
    renderOverlay();
  });

  els.overlay.addEventListener("pointermove", (event) => {
    if (state.draft) {
      const point = normalizedPoint(event);
      const x1 = state.draft.startX;
      const y1 = state.draft.startY;
      state.draft.x_center = (x1 + point.x) / 2;
      state.draft.y_center = (y1 + point.y) / 2;
      state.draft.width = Math.abs(point.x - x1);
      state.draft.height = Math.abs(point.y - y1);
      renderOverlay();
      return;
    }

    if (state.drag?.type === "region-box") {
      const point = normalizedPoint(event);
      if (updateDraggedRegionBox(point)) {
        els.overlay.style.cursor = cursorForBoxHandle(state.drag.mode);
        renderOverlay();
        renderRegionForm();
      }
    }
  });

  window.addEventListener("pointerup", () => {
    endColumnResize();
    const finishedBoxDrag = state.drag?.type === "region-box";
    if (state.draft) {
      const draft = state.draft;
      state.draft = null;
      if (draft.width > 0.01 && draft.height > 0.01) {
        addRegion(els.newRegionType.value, {
          x_center: draft.x_center,
          y_center: draft.y_center,
          width: draft.width,
          height: draft.height
        });
      } else {
        renderOverlay();
      }
    }
    state.drag = null;
    resetOverlayCursor();
    if (finishedBoxDrag) {
      renderOverlay();
      renderRegionForm();
    }
  });

  window.addEventListener("resize", renderOverlay);
  if ("ResizeObserver" in window) {
    const imageResizeObserver = new ResizeObserver(() => renderOverlay());
    imageResizeObserver.observe(els.chartImage);
  }
}

function formalQueueCandidates({ afterChartId = "" } = {}) {
  if (!formalQueueMode()) return [];
  return state.charts.filter((chart) => {
    if (!chart || chart.chart_id === afterChartId) return false;
    if (chart.has_my_annotation || chart.claim_status === "submitted") return false;
    if (expertReviewMode()) {
      return ["expert_review_available", "expert_review_claimed", "expert_review_claimed_by_me"].includes(chart.claim_status || "");
    }
    return ["claimed", "claimed_by_me", "unassigned"].includes(chart.claim_status || "");
  });
}

function nextFormalQueueChart({ afterChartId = "" } = {}) {
  const candidates = formalQueueCandidates({ afterChartId });
  return expertReviewMode()
    ? candidates.find((chart) => ["expert_review_claimed", "expert_review_claimed_by_me"].includes(chart.claim_status || ""))
      || candidates.find((chart) => chart.claim_status === "expert_review_available")
      || null
    : candidates.find((chart) => ["claimed", "claimed_by_me"].includes(chart.claim_status || ""))
    || candidates.find((chart) => chart.claim_status === "unassigned")
    || null;
}

function updateFormalQueueStatus() {
  if (!formalQueueMode() || !els.sideActionHint) return;
  const remaining = formalQueueCandidates().length;
  const current = state.current?.manifest?.chart_id
    ? `当前 ${state.current.manifest.chart_id}`
    : "等待下一张";
  els.sideActionHint.textContent = `${current} · ${expertReviewMode() ? "复核队列" : "队列"}剩余 ${remaining} 张；提交后自动进入下一张。`;
}

function setupFormalQueueUi() {
  if (!formalQueueMode()) return;
  document.documentElement.classList.add("formal-queue-mode");
  document.body.classList.add("formal-queue-mode");
  if (els.sideActionPanel && els.workspaceToolbar && !els.sideActionPanel.classList.contains("toolbar-action-panel")) {
    els.sideActionPanel.classList.add("toolbar-action-panel");
    const toolbarActions = els.workspaceToolbar.querySelector(".toolbar-actions");
    els.workspaceToolbar.insertBefore(els.sideActionPanel, toolbarActions || null);
  }
  if (els.sideActionPanel?.querySelector("h2")) {
    els.sideActionPanel.querySelector("h2").textContent = expertReviewMode() ? "本图复核" : "本图操作";
  }
  if (els.saveDraftBtn) els.saveDraftBtn.textContent = expertReviewMode() ? "暂存复核" : "暂存当前图";
  if (els.skipClaimBtn) els.skipClaimBtn.textContent = expertReviewMode() ? "跳过复核" : "换一张";
  if (els.returnClaimBtn) {
    els.returnClaimBtn.textContent = "提交专家复核";
    els.returnClaimBtn.classList.toggle("hidden", expertReviewMode());
  }
  if (els.saveBtn) els.saveBtn.textContent = expertReviewMode() ? "提交复核结果" : "提交";
  els.claimCurrentBtn?.classList.add("hidden");
  updateFormalQueueStatus();
}

function showFormalQueueEmpty(successPrefix = "") {
  resetCurrentChartView();
  if (els.currentTitle) els.currentTitle.textContent = "暂无可分配航图";
  if (els.currentMeta) els.currentMeta.textContent = "队列已清空，或剩余航图正在由其他参与者处理。";
  updateFormalQueueStatus();
  showToast(`${successPrefix ? `${successPrefix}，` : ""}暂无下一张可做航图。`);
}

async function advanceFormalQueue({ afterChartId = "", successPrefix = "" } = {}) {
  if (!formalQueueMode()) return;
  if (state.formalQueueAdvancing) return;
  state.formalQueueAdvancing = true;
  try {
    const data = await postJson(apiUrl("/api/queue/next"), { after_chart_id: afterChartId });
    state.dataset = data.dataset || datasetConfig;
    state.charts = data.charts || [];
    renderChartList();
    if (!data.chart) {
      showFormalQueueEmpty(successPrefix);
      return;
    }
    applyLoadedChart(data.chart, data.chart_id);
    const chartId = data.chart?.manifest?.chart_id || data.chart_id;
    showToast(`${successPrefix ? `${successPrefix}，` : ""}已进入下一张：${chartId}`);
  } finally {
    state.formalQueueAdvancing = false;
  }
}

function setupDatasetUi() {
  ensureSaveButtons();
  setupFormalQueueUi();
  const participantId = ensureParticipantId();
  document.title = `${datasetConfig.label} - 复飞航图字段证据标注`;
  if (els.pageTitle) {
    els.pageTitle.textContent = expertReviewMode() ? "复飞航图专家复核" : "复飞航图字段证据标注";
  }
  if (els.datasetEyebrow) {
    els.datasetEyebrow.textContent = expertReviewMode()
      ? "专家复核队列"
      : datasetConfig.finalDataset
      ? "正式集 300 张"
      : "练习集 10 张";
  }
  if (els.sideTitle) {
    els.sideTitle.textContent = expertReviewMode() ? "专家复核任务" : datasetConfig.finalDataset ? "正式航图任务" : "练习航图任务";
  }
  if (els.identityLabel) {
    els.identityLabel.textContent = expertReviewMode() ? "复核人" : "标注人";
  }
  updateParticipantBadge(participantId);
}

async function refreshCharts() {
  const data = await getJson(apiUrl("/api/charts", formalQueueMode() ? { scope: "queue" } : {}));
  state.dataset = data.dataset || datasetConfig;
  state.charts = data.charts || [];
  renderChartList();
}

function firstOpenableChart() {
  if (!state.charts.length) return null;
  if (!datasetConfig.finalDataset) return state.charts[0];
  return nextFormalQueueChart();
}

async function openInitialFormalChart(chartId) {
  if (!chartId) return false;
  await refreshCharts();
  const chart = state.charts.find((item) => item.chart_id === chartId);
  const status = chart?.claim_status || "";
  if (expertReviewMode()) {
    if (["expert_review_available", "expert_review_claimed", "expert_review_claimed_by_me"].includes(status)) {
      await claimChartFromList(chartId, { openAfter: true, silent: true });
      showToast(`已打开复核任务：${chartId}`);
      return true;
    }
    showToast(status === "expert_review_claimed_by_other" ? "这张图已由其他专家领取复核。" : "这张图不在专家复核队列中。");
    return true;
  }
  if (status === "unassigned") {
    await claimChartFromList(chartId, { openAfter: true, silent: true });
    showToast(`已打开并领取：${chartId}`);
    return true;
  }
  if (["claimed", "claimed_by_me", "submitted"].includes(status)) {
    await loadChart(chartId);
    showToast(`已打开：${chartId}`);
    return true;
  }
  showToast(status === "returned_for_expert_review" ? "这张图已进入专家复核，请从复核页修改。" : "这张图由其他参与者处理中。");
  return true;
}

async function init() {
  setupDatasetUi();
  bindEvents();
  updateNewRegionTypeHint();
  updateClaimButton();
  renderWorkflowPanel();
  applyZooms({ render: false });
  if (formalQueueMode()) {
    const initialChartId = new URLSearchParams(window.location.search).get("chart_id");
    if (await openInitialFormalChart(initialChartId)) {
      return;
    }
    await advanceFormalQueue();
    return;
  }
  await refreshCharts();
  const first = firstOpenableChart();
  if (first) {
    await loadChart(first.chart_id);
  } else if (datasetConfig.finalDataset) {
    showToast("暂无可分配航图。");
  }
}

init().catch((error) => showToast(error.message));
