const http = require("http");
const crypto = require("crypto");
const fs = require("fs/promises");
const fss = require("fs");
const os = require("os");
const path = require("path");
const { URL } = require("url");

const workspaceRoot = path.resolve(__dirname, "..");
const runtimeRoot = process.env.SHUJUJI_DATA_ROOT
  ? path.resolve(process.env.SHUJUJI_DATA_ROOT)
  : workspaceRoot;
const publicRoot = path.resolve(__dirname, "public");
const port = Number(process.env.PORT || 8787);
const publicBaseUrl = String(process.env.PUBLIC_BASE_URL || "").replace(/\/+$/, "");
const accessToken = String(process.env.SHUJUJI_ACCESS_TOKEN || "").trim();
const adminToken = String(process.env.SHUJUJI_ADMIN_TOKEN || "").trim();
const expertToken = String(process.env.SHUJUJI_EXPERT_TOKEN || "").trim();

const datasets = {
  practice10: {
    key: "practice10",
    label: "练习集 10 张",
    finalDataset: false,
    root: path.join(workspaceRoot, "datasets", "practice10"),
    annotationRoot: path.join(runtimeRoot, "datasets", "practice10", "annotations"),
    urlPath: "/practice/"
  },
  formal300: {
    key: "formal300",
    label: "正式集 300 张",
    finalDataset: true,
    root: path.join(workspaceRoot, "datasets", "formal300"),
    annotationRoot: path.join(runtimeRoot, "datasets", "formal300", "annotations"),
    urlPath: "/formal/"
  }
};

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store"
};

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml; charset=utf-8"
};

let claimQueue = Promise.resolve();

function safeJoin(root, ...parts) {
  const resolvedRoot = path.resolve(root);
  const target = path.resolve(root, ...parts);
  const rootWithSep = resolvedRoot.endsWith(path.sep) ? resolvedRoot : resolvedRoot + path.sep;
  if (target !== resolvedRoot && !target.startsWith(rootWithSep)) {
    throw new Error(`Unsafe path outside root: ${target}`);
  }
  return target;
}

function stripBom(text) {
  return text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
}

function datasetFromRequest(requestUrl, pathname) {
  const requested = requestUrl.searchParams.get("dataset");
  if (datasets[requested]) return datasets[requested];
  if (pathname.startsWith("/practice")) return datasets.practice10;
  if (pathname.startsWith("/formal")) return datasets.formal300;
  return datasets.formal300;
}

function isSafeChartId(chartId) {
  return /^[A-Za-z0-9_.-]+$/.test(chartId || "");
}

function imageBasename(imagePath) {
  return String(imagePath || "").split(/[\\/]/).pop();
}

function scrubServerPaths(text) {
  let value = String(text || "");
  for (const root of [workspaceRoot, runtimeRoot, publicRoot]) {
    if (root) value = value.split(root).join("[server-path]");
  }
  value = value.replace(/(?<![A-Za-z])[A-Za-z]:[\\/][^\s"'<>]+/g, "[server-path]");
  value = value.replace(/\/(?:app|data|home|var|tmp)\/[^\s"'<>]+/g, "[server-path]");
  return value;
}

function scrubClientValue(value) {
  if (Array.isArray(value)) return value.map(scrubClientValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, scrubClientValue(item)]));
  }
  if (typeof value !== "string") return value;
  if (/^[A-Za-z]:[\\/]/.test(value)) return imageBasename(value);
  return scrubServerPaths(value);
}

function safeAnnotator(value) {
  const cleaned = String(value || "")
    .trim()
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .replace(/\s+/g, "_");
  return cleaned || "";
}

function getAnnotator(requestUrl) {
  return safeAnnotator(requestUrl.searchParams.get("annotator") || "");
}

function getExpertReviewer(requestUrl) {
  return safeAnnotator(
    requestUrl.searchParams.get("expert")
    || requestUrl.searchParams.get("reviewer")
    || requestUrl.searchParams.get("annotator")
    || ""
  );
}

function isExpertRole(requestUrl) {
  return requestUrl.searchParams.get("role") === "expert"
    || requestUrl.searchParams.get("expert_mode") === "1";
}

function hashText(value) {
  return crypto.createHash("sha256").update(String(value || "")).digest();
}

function tokenMatches(supplied, expected) {
  return Boolean(supplied && expected)
    && crypto.timingSafeEqual(hashText(supplied), hashText(expected));
}

function hasValidAccess(req, requestUrl) {
  if (!accessToken) return true;
  const supplied = String(
    req.headers["x-shujuji-token"]
    || requestUrl.searchParams.get("token")
    || ""
  ).trim();
  if (!supplied) return false;
  if (tokenMatches(supplied, accessToken)) return true;
  if (tokenMatches(supplied, expertToken)) return true;
  return tokenMatches(supplied, adminToken);
}

function requireAccess(req, requestUrl) {
  if (hasValidAccess(req, requestUrl)) return;
  const error = new Error("Access token required");
  error.statusCode = 401;
  throw error;
}

function hasValidAdminAccess(req, requestUrl) {
  if (!adminToken) return false;
  const supplied = String(
    req.headers["x-shujuji-admin-token"]
    || requestUrl.searchParams.get("admin_token")
    || ""
  ).trim();
  if (!supplied) return false;
  return tokenMatches(supplied, adminToken);
}

function requireAdminAccess(req, requestUrl) {
  if (hasValidAdminAccess(req, requestUrl)) return;
  const error = new Error(adminToken ? "Admin token required" : "Admin export is not enabled");
  error.statusCode = adminToken ? 401 : 503;
  throw error;
}

function hasValidExpertAccess(req, requestUrl) {
  const supplied = String(
    req.headers["x-shujuji-expert-token"]
    || req.headers["x-shujuji-token"]
    || requestUrl.searchParams.get("expert_token")
    || requestUrl.searchParams.get("token")
    || requestUrl.searchParams.get("admin_token")
    || ""
  ).trim();
  if (tokenMatches(supplied, expertToken)) return true;
  if (tokenMatches(supplied, adminToken)) return true;
  return !expertToken && !adminToken && hasValidAccess(req, requestUrl);
}

function requireExpertAccess(req, requestUrl) {
  if (hasValidExpertAccess(req, requestUrl)) return;
  const error = new Error(expertToken || adminToken ? "Expert review token required" : "Expert review is not enabled");
  error.statusCode = expertToken || adminToken ? 401 : 503;
  throw error;
}

function timestampForFile() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function clientIp(req) {
  const forwarded = req.headers["x-forwarded-for"];
  if (forwarded) return String(forwarded).split(",")[0].trim();
  return req.socket.remoteAddress || "";
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonFile(filePath, fallback = null) {
  try {
    return JSON.parse(stripBom(await fs.readFile(filePath, "utf8")));
  } catch (error) {
    if (error.code === "ENOENT") return fallback;
    throw error;
  }
}

async function readDatasetJson(dataset, relativePath, fallback = null) {
  return readJsonFile(safeJoin(dataset.root, relativePath), fallback);
}

async function readAnnotationJson(dataset, relativePath, fallback = null) {
  return readJsonFile(safeJoin(dataset.annotationRoot, relativePath), fallback);
}

function annotationPath(dataset, ...parts) {
  return safeJoin(dataset.annotationRoot, ...parts);
}

function exportPath(...parts) {
  return safeJoin(runtimeRoot, "exports", ...parts);
}

async function writeJsonFileAtomic(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  await fs.writeFile(tmpPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(tmpPath, filePath);
}

function withClaimLock(fn) {
  const run = claimQueue.then(fn, fn);
  claimQueue = run.catch(() => {});
  return run;
}

async function walkJsonFiles(root, relativeRoot = "") {
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }

  const results = [];
  for (const entry of entries) {
    const relativePath = relativeRoot ? `${relativeRoot}/${entry.name}` : entry.name;
    const fullPath = safeJoin(root, entry.name);
    if (entry.isDirectory()) {
      results.push(...await walkJsonFiles(fullPath, relativePath));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith(".json")) {
      results.push(relativePath);
    }
  }
  return results.sort((a, b) => a.localeCompare(b));
}

async function readAnnotationEntry(root, relativePath) {
  const filePath = safeJoin(root, ...relativePath.split("/"));
  try {
    return {
      relative_path: relativePath,
      data: JSON.parse(stripBom(await fs.readFile(filePath, "utf8")))
    };
  } catch (error) {
    return {
      relative_path: relativePath,
      error: scrubServerPaths(error.message || "Failed to read JSON")
    };
  }
}

async function readAnnotationEntries(root) {
  const files = await walkJsonFiles(root);
  return Promise.all(files.map((file) => readAnnotationEntry(root, file)));
}

async function buildDatasetExport(dataset) {
  const claims = dataset.finalDataset ? await readClaims(dataset) : {};
  const difficultCases = await readDifficultCases(dataset);
  const drafts = await readAnnotationEntries(annotationPath(dataset, "drafts"));
  const byAnnotator = await readAnnotationEntries(annotationPath(dataset, "by_annotator"));
  const submissions = await readAnnotationEntries(annotationPath(dataset, "submissions"));
  return {
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    exported_at: new Date().toISOString(),
    summary: {
      claims_count: Object.keys(claims || {}).length,
      difficult_case_count: difficultCaseCount(difficultCases),
      draft_json_count: drafts.length,
      final_json_count: byAnnotator.length,
      submission_json_count: submissions.length
    },
    annotations: {
      claims,
      difficult_cases: difficultCases,
      drafts,
      by_annotator: byAnnotator,
      submissions
    }
  };
}

async function createAnnotationExport() {
  const exportedAt = new Date().toISOString();
  const stamp = timestampForFile();
  const payload = {
    schema: "shujuji_annotation_export_v1",
    exported_at: exportedAt,
    source: {
      service: "shujuji_annotation_platform",
      runtime_storage: "server"
    },
    datasets: {
      practice10: await buildDatasetExport(datasets.practice10),
      formal300: await buildDatasetExport(datasets.formal300)
    }
  };

  const exportDir = exportPath();
  await fs.mkdir(exportDir, { recursive: true });
  const fileName = `shujuji_annotation_export_${stamp}.json`;
  const filePath = exportPath(fileName);
  await writeJsonFileAtomic(filePath, payload);
  const stat = await fs.stat(filePath);
  const summary = {
    practice10: payload.datasets.practice10.summary,
    formal300: payload.datasets.formal300.summary
  };
  const manifest = {
    ok: true,
    file_name: fileName,
    created_at: exportedAt,
    size_bytes: stat.size,
    summary
  };
  await writeJsonFileAtomic(exportPath(`shujuji_annotation_export_${stamp}.manifest.json`), manifest);
  return manifest;
}

async function listAnnotationExports() {
  let entries;
  try {
    entries = await fs.readdir(exportPath(), { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }

  const files = [];
  for (const entry of entries) {
    if (!entry.isFile() || !/^shujuji_annotation_export_.+\.json$/i.test(entry.name) || entry.name.endsWith(".manifest.json")) continue;
    const filePath = exportPath(entry.name);
    const stat = await fs.stat(filePath);
    const manifestName = entry.name.replace(/\.json$/i, ".manifest.json");
    const manifest = await readJsonFile(exportPath(manifestName), null);
    files.push({
      file_name: entry.name,
      created_at: manifest?.created_at || stat.mtime.toISOString(),
      size_bytes: stat.size,
      summary: manifest?.summary || null
    });
  }
  return files.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

function chartIdFromAnnotationEntry(entry) {
  const data = entry?.data || {};
  const explicit = data.chart_id || data.manifest?.chart_id || "";
  if (explicit) return explicit;
  const name = path.basename(String(entry?.relative_path || ""), ".json");
  return isSafeChartId(name) ? name : "";
}

function uniqueChartCount(entries) {
  const chartIds = new Set();
  for (const entry of entries || []) {
    const chartId = chartIdFromAnnotationEntry(entry);
    if (chartId) chartIds.add(chartId);
  }
  return chartIds.size;
}

function fieldReviewsFromAnnotation(data) {
  const reviews = data?.field_reviews;
  if (Array.isArray(reviews)) return reviews;
  if (reviews && typeof reviews === "object") return Object.values(reviews);
  return [];
}

function annotationSavedAt(entry) {
  const data = entry?.data || {};
  return data.saved_at || data.reviewed_at || data.generated_at || "";
}

function latestEntry(entries) {
  return [...(entries || [])].sort((left, right) => {
    const leftTime = annotationSavedAt(left) || "";
    const rightTime = annotationSavedAt(right) || "";
    return rightTime.localeCompare(leftTime) || String(right.relative_path || "").localeCompare(String(left.relative_path || ""));
  })[0] || null;
}

function annotationSummary(entry) {
  if (!entry || entry.error) return null;
  const data = entry.data || {};
  const reviews = fieldReviewsFromAnnotation(data);
  const statusCounts = {};
  let evidenceRegionCount = 0;
  for (const review of reviews) {
    const status = review.support_mode || review.review_status || "unknown";
    statusCounts[status] = (statusCounts[status] || 0) + 1;
    const evidenceIds = new Set([
      ...(review.evidence_region_ids || []),
      ...(review.required_evidence_region_ids || []),
      ...(review.secondary_evidence_region_ids || [])
    ].filter(Boolean).map(String));
    evidenceRegionCount += evidenceIds.size;
  }
  const pendingFieldCount = statusCounts.pending || 0;
  return {
    relative_path: entry.relative_path || "",
    annotator: data.annotator || data.reviewed_by || "",
    saved_at: annotationSavedAt(entry),
    review_status: data.review_status || "",
    save_mode: data.save_mode || "",
    field_review_count: reviews.length,
    pending_field_count: pendingFieldCount,
    completed_field_count: Math.max(0, reviews.length - pendingFieldCount),
    evidence_region_count: evidenceRegionCount,
    review_status_counts: statusCounts
  };
}

function entriesGroupedByChart(entries) {
  const grouped = new Map();
  for (const entry of entries || []) {
    const chartId = chartIdFromAnnotationEntry(entry);
    if (!chartId) continue;
    if (!grouped.has(chartId)) grouped.set(chartId, []);
    grouped.get(chartId).push(entry);
  }
  return grouped;
}

function entryCountsByChart(entries) {
  const counts = {};
  for (const entry of entries || []) {
    const chartId = chartIdFromAnnotationEntry(entry);
    if (!chartId) continue;
    counts[chartId] = (counts[chartId] || 0) + 1;
  }
  return counts;
}

function latestTimestamp(values) {
  return values.filter(Boolean).map(String).sort().at(-1) || "";
}

function isExpertReviewClaimStatus(status) {
  return ["returned_for_expert_review", "expert_review_claimed"].includes(status || "");
}

function orderedAfterChart(manifest, afterChartId = "") {
  if (!afterChartId) return manifest;
  const index = manifest.findIndex((item) => item?.chart_id === afterChartId);
  if (index < 0) return manifest;
  return manifest.slice(index + 1).concat(manifest.slice(0, index));
}

async function buildDatasetProgress(dataset) {
  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  const claims = dataset.finalDataset ? await readClaims(dataset) : {};
  const difficultCases = await readDifficultCases(dataset);
  const currentDrafts = await readAnnotationEntries(annotationPath(dataset, "drafts", "by_annotator"));
  const draftSnapshots = await readAnnotationEntries(annotationPath(dataset, "drafts", "snapshots"));
  const byAnnotator = await readAnnotationEntries(annotationPath(dataset, "by_annotator"));
  const submissions = await readAnnotationEntries(annotationPath(dataset, "submissions"));
  const statusCounts = {};
  for (const claim of Object.values(claims || {})) {
    const status = claim?.status || "claimed";
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  }
  const totalCharts = manifest.length;
  const submittedCount = statusCounts.submitted || 0;
  const returnedCount = (statusCounts.returned_for_expert_review || 0) + (statusCounts.expert_review_claimed || 0);
  const activeClaimCount = Object.values(claims || {}).filter((claim) => {
    const status = claim?.status || "claimed";
    return !["submitted", "returned_for_expert_review", "expert_review_claimed"].includes(status);
  }).length;
  return {
    dataset_key: dataset.key,
    label: dataset.label,
    final_dataset: dataset.finalDataset,
    total_charts: totalCharts,
    claims_count: Object.keys(claims || {}).length,
    unassigned_count: dataset.finalDataset ? Math.max(0, totalCharts - Object.keys(claims || {}).length) : null,
    difficult_case_count: difficultCaseCount(difficultCases),
    active_claim_count: activeClaimCount,
    submitted_claim_count: submittedCount,
    returned_for_expert_review_count: returnedCount,
    current_draft_json_count: currentDrafts.length,
    current_draft_chart_count: uniqueChartCount(currentDrafts),
    draft_snapshot_json_count: draftSnapshots.length,
    final_json_count: byAnnotator.length,
    final_chart_count: uniqueChartCount(byAnnotator),
    submission_json_count: submissions.length,
    submission_chart_count: uniqueChartCount(submissions),
    progress_percent: totalCharts ? Math.round((submittedCount / totalCharts) * 100) : 0,
    claim_status_counts: statusCounts,
    updated_at: new Date().toISOString()
  };
}

async function buildDatasetOverview(dataset) {
  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  const claims = dataset.finalDataset ? await readClaims(dataset) : {};
  const difficultCases = await readDifficultCases(dataset);
  const currentDrafts = await readAnnotationEntries(annotationPath(dataset, "drafts", "by_annotator"));
  const byAnnotator = await readAnnotationEntries(annotationPath(dataset, "by_annotator"));
  const submissions = await readAnnotationEntries(annotationPath(dataset, "submissions"));
  const draftsByChart = entriesGroupedByChart(currentDrafts);
  const finalsByChart = entriesGroupedByChart(byAnnotator);
  const submissionCounts = entryCountsByChart(submissions);

  const rows = manifest.map((item, index) => {
    const chartId = item.chart_id;
    const claim = claims[chartId] || null;
    const difficultCase = difficultCases[chartId] || null;
    const draftEntry = latestEntry(draftsByChart.get(chartId));
    const finalEntry = latestEntry(finalsByChart.get(chartId));
    const draft = annotationSummary(draftEntry);
    const final = annotationSummary(finalEntry);
    const hasAnnotation = Boolean(finalEntry);
    const hasDraft = Boolean(draftEntry);
    const rawClaimStatus = dataset.finalDataset ? (claim?.status || "unassigned") : "";
    let status = "unassigned";
    if (dataset.finalDataset && isExpertReviewClaimStatus(rawClaimStatus)) {
      status = rawClaimStatus;
    } else if (hasAnnotation || rawClaimStatus === "submitted") {
      status = "submitted";
    } else if (hasDraft) {
      status = "draft_saved";
    } else if (dataset.finalDataset && claim) {
      status = rawClaimStatus || "claimed";
    } else if (!dataset.finalDataset && hasDraft) {
      status = "draft_saved";
    } else if (!dataset.finalDataset && hasAnnotation) {
      status = "submitted";
    }
    const annotator = final?.annotator || draft?.annotator || claim?.annotator || "";
    return {
      row_index: index + 1,
      dataset_key: dataset.key,
      chart_id: chartId,
      airport: item.airport || "",
      proc_ident: item.proc_ident || "",
      chart_name: item.chart_name || "",
      kind: item.kind || "",
      ma_leg_count: item.ma_leg_count ?? item.source_ma_leg_count ?? null,
      status,
      claim_status: rawClaimStatus,
      annotator,
      claimed_at: claim?.claimed_at || "",
      last_opened_at: claim?.last_opened_at || "",
      last_saved_at: claim?.last_saved_at || "",
      returned_at: claim?.returned_at || "",
      returned_by: claim?.returned_by || "",
      return_reason: claim?.return_reason || "",
      is_difficult_case: Boolean(difficultCase?.difficult),
      difficult_case: difficultCase?.difficult ? scrubClientValue(difficultCase) : null,
      original_annotator: claim?.annotator || "",
      expert_reviewer: claim?.expert_reviewer || "",
      expert_review_claimed_at: claim?.expert_review_claimed_at || "",
      expert_reviewed_at: claim?.expert_reviewed_at || "",
      expert_review_required: Boolean(claim?.expert_review_required || isExpertReviewClaimStatus(status)),
      has_draft: hasDraft,
      has_annotation: hasAnnotation,
      draft,
      final,
      submission_count: submissionCounts[chartId] || 0,
      updated_at: latestTimestamp([
        claim?.last_saved_at,
        claim?.returned_at,
        claim?.last_opened_at,
        claim?.claimed_at,
        draft?.saved_at,
        final?.saved_at
      ])
    };
  });
  const statusCounts = {};
  for (const row of rows) statusCounts[row.status] = (statusCounts[row.status] || 0) + 1;
  return {
    dataset_key: dataset.key,
    label: dataset.label,
    final_dataset: dataset.finalDataset,
    updated_at: new Date().toISOString(),
    total_charts: rows.length,
    status_counts: statusCounts,
    rows
  };
}

async function buildAdminProgress() {
  return {
    ok: true,
    updated_at: new Date().toISOString(),
    datasets: {
      practice10: await buildDatasetProgress(datasets.practice10),
      formal300: await buildDatasetProgress(datasets.formal300)
    }
  };
}

async function buildAdminOverview(datasetKey) {
  const dataset = datasets[datasetKey] || datasets.formal300;
  return {
    ok: true,
    updated_at: new Date().toISOString(),
    dataset: await buildDatasetOverview(dataset)
  };
}

async function readClaims(dataset) {
  if (!dataset.finalDataset) return {};
  return readAnnotationJson(dataset, "claims.json", {});
}

async function writeClaims(dataset, claims) {
  if (!dataset.finalDataset) return;
  await writeJsonFileAtomic(annotationPath(dataset, "claims.json"), claims);
}

async function readDifficultCases(dataset) {
  return readAnnotationJson(dataset, "difficult_cases.json", {});
}

async function writeDifficultCases(dataset, difficultCases) {
  await writeJsonFileAtomic(annotationPath(dataset, "difficult_cases.json"), difficultCases);
}

function difficultCaseCount(difficultCases) {
  return Object.values(difficultCases || {}).filter((item) => item?.difficult).length;
}

async function ensureChartExists(dataset, chartId) {
  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  if ((manifest || []).some((item) => item?.chart_id === chartId)) return;
  const error = new Error(`Unknown chart_id: ${chartId}`);
  error.statusCode = 404;
  throw error;
}

async function setDifficultCase(dataset, chartId, options = {}) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  await ensureChartExists(dataset, chartId);
  const difficult = options.difficult !== false;
  const markedBy = safeAnnotator(options.markedBy || "showcase_user") || "showcase_user";
  const note = String(options.note || "").trim().slice(0, 1000);
  return withClaimLock(async () => {
    const difficultCases = await readDifficultCases(dataset);
    const previous = difficultCases[chartId] || {};
    const now = new Date().toISOString();
    const event = {
      action: difficult ? "mark" : "unmark",
      by: markedBy,
      at: now,
      note
    };
    const history = [...(previous.history || []), event].slice(-30);
    difficultCases[chartId] = {
      ...previous,
      chart_id: chartId,
      dataset_key: dataset.key,
      difficult,
      note: difficult ? note : (note || previous.note || ""),
      marked_by: difficult ? markedBy : (previous.marked_by || markedBy),
      marked_at: difficult ? (previous.marked_at || now) : (previous.marked_at || ""),
      updated_by: markedBy,
      updated_at: now,
      source: "showcase",
      history
    };
    if (!difficult) {
      difficultCases[chartId].unmarked_by = markedBy;
      difficultCases[chartId].unmarked_at = now;
    } else {
      delete difficultCases[chartId].unmarked_by;
      delete difficultCases[chartId].unmarked_at;
    }
    await writeDifficultCases(dataset, difficultCases);
    return difficultCases[chartId];
  });
}

async function removePathIfExists(filePath, removed, label) {
  if (!await fileExists(filePath)) return;
  await fs.rm(filePath, { recursive: true, force: true });
  removed.push(label);
}

async function removeEmptyDirIfPossible(dirPath) {
  try {
    await fs.rmdir(dirPath);
  } catch (error) {
    if (!["ENOENT", "ENOTEMPTY"].includes(error.code)) throw error;
  }
}

async function removeChartJsonFromAnnotatorRoot(dataset, rootParts, chartId, removed, labelPrefix) {
  const root = annotationPath(dataset, ...rootParts);
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const filePath = safeJoin(root, entry.name, `${chartId}.json`);
    if (!await fileExists(filePath)) continue;
    await fs.rm(filePath, { force: true });
    removed.push(`${labelPrefix}/${entry.name}/${chartId}.json`);
    await removeEmptyDirIfPossible(safeJoin(root, entry.name));
  }
}

async function removeChartAnnotationArtifacts(dataset, chartId) {
  const removed = [];
  await removeChartJsonFromAnnotatorRoot(dataset, ["by_annotator"], chartId, removed, "by_annotator");
  await removeChartJsonFromAnnotatorRoot(dataset, ["drafts", "by_annotator"], chartId, removed, "drafts/by_annotator");
  await removePathIfExists(annotationPath(dataset, "drafts", "snapshots", chartId), removed, `drafts/snapshots/${chartId}`);
  await removePathIfExists(annotationPath(dataset, "submissions", chartId), removed, `submissions/${chartId}`);
  return removed;
}

async function latestFinalAnnotationForChart(dataset, chartId) {
  const entries = await readAnnotationEntries(annotationPath(dataset, "by_annotator"));
  return latestEntry(entries.filter((entry) => chartIdFromAnnotationEntry(entry) === chartId));
}

async function adminReturnChart(dataset, chartId, options = {}) {
  if (!dataset.finalDataset) {
    const error = new Error("只有正式集支持管理员打回。");
    error.statusCode = 400;
    throw error;
  }
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const target = options.target === "ordinary" ? "ordinary" : "expert";
  const returnedBy = safeAnnotator(options.returnedBy || "admin") || "admin";
  const reason = String(options.reason || "").trim().slice(0, 1000);

  if (target === "ordinary") {
    return withClaimLock(async () => {
      const claims = await readClaims(dataset);
      const previousClaim = claims[chartId] || null;
      const removed_artifacts = await removeChartAnnotationArtifacts(dataset, chartId);
      delete claims[chartId];
      await writeClaims(dataset, claims);
      return {
        target,
        claim: null,
        previous_claim: previousClaim,
        removed_artifacts
      };
    });
  }

  const latestFinal = await latestFinalAnnotationForChart(dataset, chartId);
  const finalSummary = annotationSummary(latestFinal);
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const previous = claims[chartId] || {};
    const now = new Date().toISOString();
    const annotator = previous.annotator
      || finalSummary?.annotator
      || safeAnnotator(options.annotator || "");
    claims[chartId] = {
      ...previous,
      chart_id: chartId,
      annotator,
      status: "returned_for_expert_review",
      expert_review_required: true,
      expert_reviewer: "",
      expert_review_claimed_at: "",
      expert_last_opened_at: "",
      returned_by: returnedBy,
      returned_at: now,
      return_reason: reason,
      previous_status: previous.status || (latestFinal ? "submitted" : "unassigned")
    };
    await writeClaims(dataset, claims);
    return {
      target,
      claim: claims[chartId],
      previous_claim: previous || null,
      preserved_annotation: Boolean(latestFinal)
    };
  });
}

async function claimChart(dataset, chartId, annotator) {
  if (!dataset.finalDataset) return null;
  if (!annotator) {
    const error = new Error("正式标注请先填写标注人，再领取航图。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const existing = claims[chartId];
    if (isExpertReviewClaimStatus(existing?.status)) {
      const error = new Error("这张图已被退回并标记为专家复审，不再分配给普通标注流程。");
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    if (existing?.annotator && existing.annotator !== annotator) {
      const error = new Error(`这张图已由 ${existing.annotator} 领取，请换一张未领取的图，避免重复标注。`);
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    const now = new Date().toISOString();
    claims[chartId] = {
      chart_id: chartId,
      annotator,
      status: existing?.status === "submitted" ? "submitted" : "claimed",
      claimed_at: existing?.claimed_at || now,
      last_opened_at: now,
      last_saved_at: existing?.last_saved_at || ""
    };
    await writeClaims(dataset, claims);
    return claims[chartId];
  });
}

async function claimExpertReviewChart(dataset, chartId, reviewer) {
  if (!dataset.finalDataset) return null;
  if (!reviewer) {
    const error = new Error("专家复核请先填写复核人。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const existing = claims[chartId];
    if (!existing || !isExpertReviewClaimStatus(existing.status)) {
      const error = new Error("这张图不在专家复核队列中。");
      error.statusCode = 409;
      error.claim = existing || null;
      throw error;
    }
    if (existing.expert_reviewer && existing.expert_reviewer !== reviewer) {
      const error = new Error(`这张图已由专家 ${existing.expert_reviewer} 领取复核。`);
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    const now = new Date().toISOString();
    claims[chartId] = {
      ...existing,
      chart_id: chartId,
      status: "expert_review_claimed",
      expert_review_required: true,
      expert_reviewer: reviewer,
      expert_review_claimed_at: existing.expert_review_claimed_at || now,
      expert_last_opened_at: now
    };
    await writeClaims(dataset, claims);
    return claims[chartId];
  });
}

async function returnClaim(dataset, chartId, annotator, reason) {
  if (!dataset.finalDataset) return null;
  if (!annotator) {
    const error = new Error("正式标注请先填写标注人，再退回航图。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const existing = claims[chartId];
    if (!existing) {
      const error = new Error("这张图尚未领取，不能退回。");
      error.statusCode = 409;
      throw error;
    }
    if (existing.annotator !== annotator) {
      const error = new Error(`这张图由 ${existing.annotator} 领取，不能用 ${annotator} 退回。`);
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    const now = new Date().toISOString();
    claims[chartId] = {
      ...existing,
      chart_id: chartId,
      annotator,
      status: "returned_for_expert_review",
      expert_review_required: true,
      returned_by: annotator,
      returned_at: now,
      return_reason: String(reason || "").trim().slice(0, 1000),
      previous_status: existing.status || "claimed"
    };
    await writeClaims(dataset, claims);
    return claims[chartId];
  });
}

async function releaseClaim(dataset, chartId, annotator) {
  if (!dataset.finalDataset) return null;
  if (!annotator) {
    const error = new Error("正式标注请先填写标注人，再换一张图。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const existing = claims[chartId];
    if (!existing) return null;
    if (existing.annotator !== annotator) {
      const error = new Error(`这张图由 ${existing.annotator} 领取，不能用 ${annotator} 换图。`);
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    if (["submitted", "returned_for_expert_review", "expert_review_claimed"].includes(existing.status || "")) {
      const error = new Error("这张图已经提交或进入专家复核，不能当作普通换图释放。");
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    delete claims[chartId];
    await writeClaims(dataset, claims);
    return {
      ...existing,
      chart_id: chartId,
      released_by: annotator,
      released_at: new Date().toISOString(),
      previous_status: existing.status || "claimed"
    };
  });
}

async function releaseExpertReviewClaim(dataset, chartId, reviewer) {
  if (!dataset.finalDataset) return null;
  if (!reviewer) {
    const error = new Error("专家复核请先填写复核人。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const existing = claims[chartId];
    if (!existing || existing.status !== "expert_review_claimed") return null;
    if (existing.expert_reviewer && existing.expert_reviewer !== reviewer) {
      const error = new Error(`这张图已由专家 ${existing.expert_reviewer} 领取复核，不能用 ${reviewer} 跳过。`);
      error.statusCode = 409;
      error.claim = existing;
      throw error;
    }
    claims[chartId] = {
      ...existing,
      status: "returned_for_expert_review",
      expert_reviewer: "",
      expert_last_released_by: reviewer,
      expert_last_released_at: new Date().toISOString()
    };
    await writeClaims(dataset, claims);
    return claims[chartId];
  });
}

async function markSubmitted(dataset, chartId, annotator, options = {}) {
  if (!dataset.finalDataset) return null;
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const now = new Date().toISOString();
    const previous = claims[chartId] || {};
    claims[chartId] = {
      ...previous,
      chart_id: chartId,
      annotator,
      status: "submitted",
      last_saved_at: now
    };
    if (options.expertReviewer) {
      claims[chartId].expert_review_required = false;
      claims[chartId].expert_reviewer = options.expertReviewer;
      claims[chartId].expert_reviewed_at = now;
      claims[chartId].expert_review_previous_status = previous.status || "";
    }
    if (!claims[chartId].claimed_at) claims[chartId].claimed_at = now;
    await writeClaims(dataset, claims);
    return claims[chartId];
  });
}

async function submissionCount(dataset, chartId) {
  const folder = annotationPath(dataset, "submissions", chartId);
  try {
    const entries = await fs.readdir(folder);
    return entries.filter((name) => name.toLowerCase().endsWith(".json")).length;
  } catch (error) {
    if (error.code === "ENOENT") return 0;
    throw error;
  }
}

function claimStatusFor(dataset, claim, annotator, options = {}) {
  const expertMode = Boolean(options.expertMode);
  const mine = Boolean(annotator && claim?.annotator === annotator);
  const expertMine = Boolean(annotator && claim?.expert_reviewer === annotator);
  return !dataset.finalDataset
    ? "practice"
    : !claim
      ? (expertMode ? "not_in_expert_queue" : "unassigned")
      : expertMode
        ? claim.status === "returned_for_expert_review"
          ? "expert_review_available"
          : claim.status === "expert_review_claimed"
            ? (expertMine ? "expert_review_claimed_by_me" : "expert_review_claimed_by_other")
            : claim.status === "submitted"
              ? "submitted"
              : "not_in_expert_queue"
      : isExpertReviewClaimStatus(claim.status)
        ? "returned_for_expert_review"
        : mine
          ? claim.status || "claimed_by_me"
        : "claimed_by_other";
}

async function loadCharts(dataset, annotator, options = {}) {
  const lite = Boolean(options.lite);
  const expertMode = Boolean(options.expertMode);
  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  const targets = lite ? [] : await readDatasetJson(dataset, "targets/canonical_targets.json", []);
  const targetById = new Map(targets.map((item) => [item.chart_id, item]));
  const claims = await readClaims(dataset);
  const difficultCases = await readDifficultCases(dataset);

  return Promise.all(manifest.map(async (item) => {
    const chartId = item.chart_id;
    const claim = claims[chartId] || null;
    const difficultCase = difficultCases[chartId] || null;
    const claimStatus = claimStatusFor(dataset, claim, annotator, { expertMode });
    if (lite) {
      return scrubClientValue({
        chart_id: chartId,
        claim_status: claimStatus,
        is_difficult_case: Boolean(difficultCase?.difficult),
        difficult_case: difficultCase?.difficult ? difficultCase : null,
        claimed_by: expertMode ? (claim?.expert_reviewer || "") : (claim?.annotator || ""),
        original_annotator: claim?.annotator || "",
        expert_reviewer: claim?.expert_reviewer || "",
        has_my_annotation: claimStatus === "submitted",
        has_my_draft: false
      });
    }

    const target = targetById.get(chartId) || {};
    const prelabelPath = safeJoin(dataset.root, "prelabels", `${chartId}.json`);
    const storageAnnotator = expertMode && claim?.annotator ? claim.annotator : annotator;
    const myAnnotationPath = storageAnnotator
      ? annotationPath(dataset, "by_annotator", storageAnnotator, `${chartId}.json`)
      : "";
    const myDraftPath = storageAnnotator
      ? annotationPath(dataset, "drafts", "by_annotator", storageAnnotator, `${chartId}.json`)
      : "";
    const draft = !lite && myDraftPath ? await readJsonFile(myDraftPath, null) : null;
    return scrubClientValue({
      ...item,
      dataset_key: dataset.key,
      final_dataset: dataset.finalDataset,
      image_file: imageBasename(item.image_file || item.image_path),
      has_prelabel: await fileExists(prelabelPath),
      has_my_annotation: myAnnotationPath ? await fileExists(myAnnotationPath) : false,
      has_my_draft: Boolean(draft),
      draft_saved_at: draft?.saved_at || draft?.updated_at || "",
      submission_count: await submissionCount(dataset, chartId),
      claim_status: claimStatus,
      is_difficult_case: Boolean(difficultCase?.difficult),
      difficult_case: difficultCase?.difficult ? difficultCase : null,
      claimed_by: expertMode ? (claim?.expert_reviewer || "") : (claim?.annotator || ""),
      original_annotator: claim?.annotator || "",
      expert_reviewer: claim?.expert_reviewer || "",
      claimed_at: claim?.claimed_at || "",
      expert_review_claimed_at: claim?.expert_review_claimed_at || "",
      expert_reviewed_at: claim?.expert_reviewed_at || "",
      last_saved_at: claim?.last_saved_at || "",
      returned_at: claim?.returned_at || "",
      returned_by: claim?.returned_by || "",
      return_reason: claim?.return_reason || "",
      expert_review_required: Boolean(claim?.expert_review_required),
      target_leg_count: target.candidate_missed_approach_leg_count || 0,
      review_priority: item.needs_priority_review || item.sample_type === "anomaly" ? "high" : "normal"
    });
  }));
}

async function loadChartDetail(dataset, chartId, annotator, options = {}) {
  const expertMode = Boolean(options.expertMode);
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }

  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  const rawManifestItem = manifest.find((item) => item.chart_id === chartId);
  if (!rawManifestItem) {
    const error = new Error(`Unknown chart_id: ${chartId}`);
    error.statusCode = 404;
    throw error;
  }

  const claims = await readClaims(dataset);
  const claim = claims[chartId] || null;
  const manifestItem = {
    ...rawManifestItem,
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    image_file: imageBasename(rawManifestItem.image_file || rawManifestItem.image_path),
    claim_status: claimStatusFor(dataset, claim, annotator, { expertMode }),
    claimed_by: expertMode ? (claim?.expert_reviewer || "") : (claim?.annotator || ""),
    original_annotator: claim?.annotator || "",
    expert_reviewer: claim?.expert_reviewer || "",
    claimed_at: claim?.claimed_at || "",
    expert_review_claimed_at: claim?.expert_review_claimed_at || "",
    expert_reviewed_at: claim?.expert_reviewed_at || "",
    last_saved_at: claim?.last_saved_at || "",
    returned_at: claim?.returned_at || "",
    returned_by: claim?.returned_by || "",
    return_reason: claim?.return_reason || "",
    expert_review_required: Boolean(claim?.expert_review_required)
  };
  const targets = await readDatasetJson(dataset, "targets/canonical_targets.json", []);
  const rawTarget = targets.find((item) => item.chart_id === chartId) || null;
  const legIndex = await readDatasetJson(dataset, "targets/canonical_leg_index.json", {});
  const indexedLegs = legIndex?.[chartId] || {};
  const target = rawTarget
    ? {
      ...rawTarget,
      candidate_legs: (rawTarget.candidate_legs || []).map((leg) => ({
        ...leg,
        ...(indexedLegs[leg.candidate_leg_id] || {})
      }))
    }
    : null;
  const prelabel = await readDatasetJson(dataset, `prelabels/${chartId}.json`, null);
  const canonicalGt = await readDatasetJson(dataset, `targets/canonical_proxy_gt/${chartId}.json`, null);
  const difficultCases = await readDifficultCases(dataset);
  const difficultCase = difficultCases[chartId] || null;
  const effectiveAnnotator = expertMode && dataset.finalDataset && claim?.annotator
    ? claim.annotator
    : annotator || (dataset.finalDataset && claim?.annotator ? claim.annotator : "");
  const annotation = effectiveAnnotator
    ? await readAnnotationJson(dataset, `by_annotator/${effectiveAnnotator}/${chartId}.json`, null)
    : null;
  const draft = effectiveAnnotator
    ? await readAnnotationJson(dataset, `drafts/by_annotator/${effectiveAnnotator}/${chartId}.json`, null)
    : null;

  return {
    dataset: {
      key: dataset.key,
      label: dataset.label,
      final_dataset: dataset.finalDataset,
      url_path: dataset.urlPath
    },
    manifest: scrubClientValue({
      ...manifestItem,
      returned_at: claim?.returned_at || manifestItem.returned_at || "",
      returned_by: claim?.returned_by || manifestItem.returned_by || "",
      return_reason: claim?.return_reason || manifestItem.return_reason || "",
      expert_review_required: Boolean(claim?.expert_review_required || manifestItem.expert_review_required)
    }),
    target: scrubClientValue(target),
    canonical_gt: scrubClientValue(canonicalGt),
    prelabel: scrubClientValue(prelabel),
    annotation: scrubClientValue(annotation),
    draft: scrubClientValue(draft),
    difficult_case: scrubClientValue(difficultCase),
    annotation_annotator: effectiveAnnotator,
    image_url: `/api/image?dataset=${encodeURIComponent(dataset.key)}&file=${encodeURIComponent(manifestItem.image_file)}`
  };
}

async function claimChartForRequest(requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const expertMode = isExpertRole(requestUrl);
  const annotator = expertMode ? getExpertReviewer(requestUrl) : getAnnotator(requestUrl);
  const claim = expertMode
    ? await claimExpertReviewChart(dataset, chartId, annotator)
    : await claimChart(dataset, chartId, annotator || (dataset.finalDataset ? "" : "practice_user"));
  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    claim
  };
}

async function returnClaimForRequest(req, requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const payload = JSON.parse(stripBom(await readRequestBody(req)) || "{}");
  const annotator = getAnnotator(requestUrl) || safeAnnotator(payload.annotator || "");
  const claim = await returnClaim(dataset, chartId, annotator, payload.reason || "");
  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    claim
  };
}

async function releaseClaimForRequest(req, requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const payload = JSON.parse(stripBom(await readRequestBody(req)) || "{}");
  const expertMode = isExpertRole(requestUrl);
  const annotator = expertMode
    ? (getExpertReviewer(requestUrl) || safeAnnotator(payload.expert || payload.reviewer || payload.annotator || ""))
    : (getAnnotator(requestUrl) || safeAnnotator(payload.annotator || ""));
  const claim = expertMode
    ? await releaseExpertReviewClaim(dataset, chartId, annotator)
    : await releaseClaim(dataset, chartId, annotator);
  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    claim
  };
}

async function adminReturnChartForRequest(req, requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const payload = JSON.parse(stripBom(await readRequestBody(req)) || "{}");
  const result = await adminReturnChart(dataset, chartId, {
    target: payload.target,
    reason: payload.reason,
    annotator: payload.annotator,
    returnedBy: payload.returned_by || requestUrl.searchParams.get("admin") || "admin"
  });
  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    ...result
  };
}

async function setDifficultCaseForRequest(req, requestUrl, dataset, chartId) {
  const payload = JSON.parse(stripBom(await readRequestBody(req)) || "{}");
  const markedBy = payload.marked_by
    || requestUrl.searchParams.get("admin")
    || getAnnotator(requestUrl)
    || getExpertReviewer(requestUrl)
    || "showcase_user";
  const difficultCase = await setDifficultCase(dataset, chartId, {
    difficult: payload.difficult !== false,
    note: payload.note || "",
    markedBy
  });
  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    difficult_case: scrubClientValue(difficultCase)
  };
}

async function claimNextExpertReviewChart(dataset, reviewer, afterChartId = "") {
  if (!dataset.finalDataset) return { chartId: "", claim: null };
  if (!reviewer) {
    const error = new Error("专家复核请先填写复核人。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const manifest = await readDatasetJson(dataset, "manifest.json", []);
    const orderedManifest = orderedAfterChart(manifest, afterChartId);
    const claims = await readClaims(dataset);
    const now = new Date().toISOString();
    const openForMe = orderedManifest.find((item) => {
      const chartId = item.chart_id;
      const claim = claims[chartId];
      return chartId !== afterChartId
        && claim?.status === "expert_review_claimed"
        && claim.expert_reviewer === reviewer;
    });
    if (openForMe) {
      const chartId = openForMe.chart_id;
      claims[chartId] = {
        ...claims[chartId],
        expert_last_opened_at: now
      };
      await writeClaims(dataset, claims);
      return { chartId, claim: claims[chartId] };
    }

    const available = orderedManifest.find((item) => {
      const chartId = item.chart_id;
      const claim = claims[chartId];
      return chartId !== afterChartId && claim?.status === "returned_for_expert_review";
    });
    if (!available) return { chartId: "", claim: null };

    const chartId = available.chart_id;
    claims[chartId] = {
      ...claims[chartId],
      chart_id: chartId,
      status: "expert_review_claimed",
      expert_review_required: true,
      expert_reviewer: reviewer,
      expert_review_claimed_at: now,
      expert_last_opened_at: now
    };
    await writeClaims(dataset, claims);
    return { chartId, claim: claims[chartId] };
  });
}

async function claimNextChart(dataset, annotator, afterChartId = "") {
  if (!dataset.finalDataset) {
    const manifest = await readDatasetJson(dataset, "manifest.json", []);
    return { chartId: manifest[0]?.chart_id || "", claim: null };
  }
  if (!annotator) {
    const error = new Error("正式标注请先填写标注人，再领取航图。");
    error.statusCode = 400;
    throw error;
  }
  return withClaimLock(async () => {
    const manifest = await readDatasetJson(dataset, "manifest.json", []);
    const orderedManifest = orderedAfterChart(manifest, afterChartId);
    const claims = await readClaims(dataset);
    const now = new Date().toISOString();
    const openForMe = orderedManifest.find((item) => {
      const chartId = item.chart_id;
      const claim = claims[chartId];
      return chartId !== afterChartId
        && claim?.annotator === annotator
        && !["submitted", "returned_for_expert_review", "expert_review_claimed"].includes(claim.status || "");
    });
    if (openForMe) {
      const chartId = openForMe.chart_id;
      claims[chartId] = {
        ...claims[chartId],
        chart_id: chartId,
        annotator,
        status: claims[chartId].status || "claimed",
        claimed_at: claims[chartId].claimed_at || now,
        last_opened_at: now
      };
      await writeClaims(dataset, claims);
      return { chartId, claim: claims[chartId] };
    }

    const unassigned = orderedManifest.find((item) => item.chart_id !== afterChartId && !claims[item.chart_id]);
    if (!unassigned) return { chartId: "", claim: null };

    const chartId = unassigned.chart_id;
    claims[chartId] = {
      chart_id: chartId,
      annotator,
      status: "claimed",
      claimed_at: now,
      last_opened_at: now,
      last_saved_at: ""
    };
    await writeClaims(dataset, claims);
    return { chartId, claim: claims[chartId] };
  });
}

async function nextChartForRequest(req, requestUrl, dataset) {
  const payload = req.method === "POST"
    ? JSON.parse(stripBom(await readRequestBody(req)) || "{}")
    : {};
  const expertMode = isExpertRole(requestUrl);
  const annotator = expertMode
    ? (getExpertReviewer(requestUrl) || safeAnnotator(payload.expert || payload.reviewer || payload.annotator || ""))
    : (getAnnotator(requestUrl) || safeAnnotator(payload.annotator || ""));
  const afterChartId = isSafeChartId(payload.after_chart_id) ? payload.after_chart_id : "";
  const next = expertMode
    ? await claimNextExpertReviewChart(dataset, annotator, afterChartId)
    : await claimNextChart(dataset, annotator, afterChartId);
  const charts = await loadCharts(dataset, annotator, { lite: dataset.finalDataset, expertMode });
  const chart = next.chartId
    ? await loadChartDetail(dataset, next.chartId, annotator, { expertMode })
    : null;
  return {
    ok: true,
    dataset: {
      key: dataset.key,
      label: dataset.label,
      final_dataset: dataset.finalDataset,
      url_path: dataset.urlPath
    },
    chart_id: next.chartId,
    claim: next.claim,
    charts,
    chart
  };
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, jsonHeaders);
  res.end(JSON.stringify(payload, null, 2));
}

function sendHtml(res, statusCode, html) {
  res.writeHead(statusCode, {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "no-store"
  });
  res.end(html);
}

async function sendTextFile(res, filePath, contentType = "text/plain; charset=utf-8") {
  const text = await fs.readFile(filePath, "utf8");
  res.writeHead(200, {
    "content-type": contentType,
    "cache-control": "no-store"
  });
  res.end(text);
}

async function sendDownloadFile(res, filePath, downloadName, contentType = "application/json; charset=utf-8") {
  const stat = await fs.stat(filePath);
  if (!stat.isFile()) {
    const error = new Error("Not found");
    error.statusCode = 404;
    throw error;
  }
  res.writeHead(200, {
    "content-type": contentType,
    "content-length": stat.size,
    "content-disposition": `attachment; filename="${downloadName.replace(/"/g, "")}"`,
    "cache-control": "no-store"
  });
  fss.createReadStream(filePath).pipe(res);
}

function sendRedirect(res, location) {
  res.writeHead(302, { location });
  res.end();
}

function sendError(res, error) {
  const statusCode = error.statusCode || 500;
  sendJson(res, statusCode, {
    error: statusCode >= 500 ? "Internal server error" : scrubServerPaths(error.message || "Request failed"),
    claim: error.claim || null
  });
}

async function readRequestBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 20 * 1024 * 1024) {
      const error = new Error("Request body too large");
      error.statusCode = 413;
      throw error;
    }
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

async function serveStatic(res, pathname) {
  const cleanPath = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const filePath = safeJoin(publicRoot, cleanPath);
  let stat;
  try {
    stat = await fs.stat(filePath);
  } catch (error) {
    if (error.code === "ENOENT") {
      const notFound = new Error("Not found");
      notFound.statusCode = 404;
      throw notFound;
    }
    throw error;
  }
  if (!stat.isFile()) {
    const error = new Error("Not found");
    error.statusCode = 404;
    throw error;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "content-type": mimeTypes[ext] || "application/octet-stream",
    "cache-control": ext === ".html" ? "no-store" : "public, max-age=60"
  });
  fss.createReadStream(filePath).pipe(res);
}

function landingLink(pathname, requestUrl) {
  const token = requestUrl.searchParams.get("token");
  if (!token) return pathname;
  const params = new URLSearchParams({ token });
  return `${pathname}?${params.toString()}`;
}

function redirectWithQuery(pathname, requestUrl) {
  const query = requestUrl.searchParams.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function landingHtml(requestUrl) {
  const formalHref = landingLink("/formal/", requestUrl);
  const expertHref = landingLink("/expert/", requestUrl);
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>复飞航图标注平台入口</title>
  <style>
    body{margin:0;font-family:"Microsoft YaHei",sans-serif;background:#f6efe1;color:#10241f}
    main{max-width:980px;margin:8vh auto;padding:32px}
    .card{background:#fffaf0;border:1px solid #dfceb0;border-radius:24px;padding:28px;margin:18px 0;box-shadow:0 18px 50px rgba(26,55,46,.12)}
    a{display:inline-block;margin:10px 10px 0 0;padding:14px 22px;border-radius:14px;background:#176f5b;color:white;text-decoration:none;font-weight:700}
    .secondary{background:#efe4cf;color:#10241f}
    code{background:#efe4cf;padding:2px 6px;border-radius:6px}
    .muted{color:#48645d;line-height:1.7}
  </style>
</head>
<body>
  <main>
    <p>FAA MISSED APPROACH DATASET</p>
    <h1>复飞航图多人协同标注平台</h1>
    <section class="card">
      <h2>正式网页：300 张</h2>
      <p>正式入口会按“标注人领取航图”防止重复。可以在链接中预置 <code>annotator=A06</code>，也可以进入后在右上角填写标注人再领取未分配航图。</p>
      <a href="${escapeHtml(formalHref)}">进入正式标注</a>
    </section>
    <section class="card">
      <h2>专家复核</h2>
      <p>普通标注人点击“提交专家复核”后，已做的标注会保留为草稿；专家在这里逐张领取复核并提交正式结果。</p>
      <a href="${escapeHtml(expertHref)}">进入专家复核</a>
    </section>
    <section class="card">
      <h2>公网网页 / 局域网都可用</h2>
      <p class="muted">如果部署到云服务器或 Render/Railway/VPS，直接把公网域名发给标注人即可，例如 <code>https://你的域名/formal/</code>。如果在本机运行，也可以继续用局域网地址 <code>http://主机IP:${port}/formal/</code>。</p>
      <p class="muted">公网部署时建议设置 <code>SHUJUJI_DATA_ROOT</code> 指向持久化磁盘，人工暂存和正式提交会写入该目录，航图和预标注仍从项目相对路径读取。</p>
      <a class="secondary" href="/README.md">查看说明</a>
    </section>
  </main>
</body>
</html>`;
}

function adminHtml() {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>标注管理员控制台</title>
  <style>
    body{margin:0;background:#f6efe1;color:#10241f;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif}
    main{max-width:1120px;margin:7vh auto;padding:0 24px 48px}
    .card{background:#fffaf0;border:1px solid #dfceb0;border-radius:22px;padding:24px;margin:18px 0;box-shadow:0 18px 50px rgba(26,55,46,.12)}
    h1{margin:0 0 10px;font-size:30px}
    h2{margin:0 0 12px}
    h3{margin:0 0 12px}
    p{line-height:1.7;color:#405a54}
    input,select{box-sizing:border-box;width:100%;padding:13px 14px;border:1px solid #cdbf9f;border-radius:12px;background:#fff;font-size:16px}
    button,a.download{display:inline-block;margin:12px 10px 0 0;padding:12px 18px;border:0;border-radius:12px;background:#176f5b;color:white;text-decoration:none;font-size:15px;font-weight:700;cursor:pointer}
    button.secondary{background:#efe4cf;color:#10241f;border:1px solid #d8ccb7}
    a.table-link{color:#176f5b;font-weight:700;text-decoration:none}
    table{width:100%;border-collapse:collapse;margin-top:16px;background:white;border-radius:14px;overflow:hidden}
    th,td{padding:12px;border-bottom:1px solid #eadcc4;text-align:left;font-size:14px;vertical-align:top}
    code{background:#efe4cf;padding:2px 6px;border-radius:6px}
    .status{white-space:pre-wrap;background:#10241f;color:#e6fff8;border-radius:14px;padding:14px;min-height:44px}
    .muted{color:#64746f;font-size:14px}
    .dataset-card{background:white;border:1px solid #eadcc4;border-radius:16px;padding:16px;margin-top:14px}
    .metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:14px}
    .metric{background:#f8f1e3;border:1px solid #eadcc4;border-radius:14px;padding:12px}
    .metric strong{display:block;font-size:24px;line-height:1.2;color:#0f513f}
    .metric span{display:block;margin-top:4px;color:#4a5d58;font-size:13px}
    .progress-bar{height:10px;background:#eadcc4;border-radius:999px;overflow:hidden}
    .progress-fill{display:block;height:100%;background:#176f5b;border-radius:999px}
    .toolbar{display:grid;grid-template-columns:1.1fr 1fr 1.5fr auto;gap:12px;align-items:end;margin:16px 0}
    .summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:12px 0}
    .pill{background:#f8f1e3;border:1px solid #eadcc4;border-radius:999px;padding:9px 12px;font-size:13px;color:#405a54}
    .pill strong{color:#0f513f}
    .overview-table-wrap{max-height:68vh;overflow:auto;border:1px solid #eadcc4;border-radius:14px;background:white}
    .overview-table{margin:0;border-radius:0}
    .overview-table thead th{position:sticky;top:0;background:#fff4df;z-index:1}
    .status-badge{display:inline-block;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:700;background:#efe4cf;color:#10241f;white-space:nowrap}
    .status-submitted{background:#d9efe7;color:#0f513f}
    .status-draft_saved{background:#fff0c7;color:#745200}
    .status-claimed{background:#e2ecff;color:#244d91}
    .status-returned_for_expert_review{background:#ffe0dc;color:#9a2f22}
    .status-expert_review_claimed{background:#ffe9b8;color:#805100}
    .status-unassigned{background:#ece7dc;color:#5d5a51}
    .field-progress{white-space:nowrap;color:#405a54}
    .row-actions{white-space:nowrap}
    @media (max-width:800px){.toolbar{grid-template-columns:1fr}.overview-table-wrap{max-height:none}}
  </style>
</head>
<body>
  <main>
    <h1>标注管理员控制台</h1>
    <p>这个页面只给管理员使用。普通标注人员继续使用正式标注链接，不需要进入这里。</p>
    <section class="card">
      <h2>访问凭证</h2>
      <p class="muted"><code>admin_token</code> 是后台管理凭证，用于刷新进度、逐图总览、导出，也可以作为专家复核凭证打开复核页。</p>
      <input id="token" type="password" placeholder="后台管理 token">
      <button type="button" onclick="saveToken()">保存凭证</button>
      <button class="secondary" type="button" onclick="loadProgress()">刷新当前进度</button>
      <button class="secondary" type="button" onclick="loadOverview()">刷新逐图总览</button>
      <button class="secondary" type="button" onclick="createExport()">生成并保存新导出</button>
      <button class="secondary" type="button" onclick="loadExports()">刷新导出列表</button>
      <p>导出文件会同时保存在服务器 <code>/data/shujuji_annotation/exports</code>，并可在本页下载。</p>
      <div id="status" class="status">等待操作...</div>
    </section>
    <section class="card">
      <h2>当前进度</h2>
      <p class="muted">这里是实时读取服务器当前标注文件和领取状态，不需要先生成导出。</p>
      <div id="progress">请输入后台管理 token 后刷新。</div>
    </section>
    <section class="card">
      <h2>逐图总览</h2>
      <p class="muted">只展示正式集服务器里已经保存的领取、草稿、正式提交状态；点击“展示页”检查那张图，展示页里可以继续跳回标注页修改。</p>
      <div class="toolbar">
        <label>数据集<select id="overviewDataset"><option value="formal300">正式集 300 张</option></select></label>
        <label>状态筛选<select id="overviewStatus"><option value="">全部状态</option><option value="__difficult__">难例</option><option value="submitted">已提交</option><option value="draft_saved">有草稿</option><option value="claimed">已领取未提交</option><option value="returned_for_expert_review">待专家复核</option><option value="expert_review_claimed">专家复核中</option><option value="unassigned">未领取/未标</option></select></label>
        <label>搜索<input id="overviewSearch" type="search" placeholder="chart_id / 机场 / 程序 / 标注人"></label>
        <button type="button" onclick="loadOverview()">刷新</button>
      </div>
      <div id="overview">请输入后台管理 token 后刷新。</div>
    </section>
    <section class="card">
      <h2>已有导出</h2>
      <div id="exports"></div>
    </section>
  </main>
  <script>
    const tokenInput = document.getElementById("token");
    const statusBox = document.getElementById("status");
    const progressBox = document.getElementById("progress");
    const overviewBox = document.getElementById("overview");
    const overviewDataset = document.getElementById("overviewDataset");
    const overviewStatus = document.getElementById("overviewStatus");
    const overviewSearch = document.getElementById("overviewSearch");
    let overviewRows = [];
    let overviewMeta = null;
    const params = new URLSearchParams(location.search);
    const tokenFromUrl = params.get("admin_token");
    if (tokenFromUrl) {
      sessionStorage.setItem("shujuji_admin_token", tokenFromUrl);
      params.delete("admin_token");
    }
    if (tokenFromUrl) {
      history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
    }
    tokenInput.value = sessionStorage.getItem("shujuji_admin_token") || "";

    function token() {
      return tokenInput.value.trim();
    }
    function saveToken() {
      sessionStorage.setItem("shujuji_admin_token", token());
      statusBox.textContent = "凭证已保存在当前浏览器会话。";
    }
    function show(value) {
      statusBox.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }
    function escapeCell(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }
    function numberCell(value) {
      return Number.isFinite(Number(value)) ? Number(value).toLocaleString("zh-CN") : "-";
    }
    function metric(label, value, hint) {
      return "<div class='metric'><strong>" + numberCell(value) + "</strong><span>" + escapeCell(label) + (hint ? "<br>" + escapeCell(hint) : "") + "</span></div>";
    }
    function renderDatasetProgress(item) {
      const progress = Math.max(0, Math.min(100, Number(item.progress_percent || 0)));
      const assigned = Math.max(0, Number(item.claims_count || 0) - Number(item.returned_for_expert_review_count || 0));
      return "<div class='dataset-card'><h3>" + escapeCell(item.label || item.dataset_key) + "</h3>" +
        "<div class='progress-bar'><span class='progress-fill' style='width:" + progress + "%'></span></div>" +
        "<p class='muted'>已提交 " + numberCell(item.submitted_claim_count) + " / " + numberCell(item.total_charts) +
        "，完成率 " + progress + "%；更新时间 " + escapeCell(item.updated_at || "") + "</p>" +
        "<div class='metric-grid'>" +
        metric("总航图", item.total_charts) +
        metric("已领取/有状态", assigned, "不含退回复核") +
        metric("未领取", item.unassigned_count) +
        metric("暂存过的图", item.current_draft_chart_count, item.current_draft_json_count + " 个当前草稿文件") +
        metric("已提交", item.submitted_claim_count, item.final_json_count + " 个正式结果文件") +
        metric("难例", item.difficult_case_count) +
        metric("提交快照", item.submission_chart_count, item.submission_json_count + " 个历史快照") +
        metric("专家复核", item.returned_for_expert_review_count) +
        metric("进行中领取", item.active_claim_count) +
        "</div></div>";
    }
    const STATUS_LABELS = {
      submitted: "已提交",
      draft_saved: "有草稿",
      claimed: "已领取",
      claimed_by_me: "已领取",
      returned_for_expert_review: "待专家复核",
      expert_review_claimed: "专家复核中",
      unassigned: "未领取",
      practice_unstarted: "未标"
    };
    function statusLabel(status) {
      return STATUS_LABELS[status] || status || "-";
    }
    function formatTime(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("zh-CN", { hour12: false });
    }
    function fieldSummary(summary) {
      if (!summary) return "-";
      const total = Number(summary.field_review_count || 0);
      const done = Number(summary.completed_field_count || 0);
      const pending = Number(summary.pending_field_count || 0);
      return "<span class='field-progress'>" + done + "/" + total + " 完成" + (pending ? "，待 " + pending : "") + "</span>";
    }
    function overviewSummaryHtml(dataset) {
      const counts = dataset.status_counts || {};
      return "<div class='summary-grid'>" +
        "<div class='pill'><strong>" + numberCell(dataset.total_charts) + "</strong> 总图数</div>" +
        "<div class='pill'><strong>" + numberCell(counts.submitted || 0) + "</strong> 已提交</div>" +
        "<div class='pill'><strong>" + numberCell(counts.draft_saved || 0) + "</strong> 有草稿</div>" +
        "<div class='pill'><strong>" + numberCell(counts.claimed || 0) + "</strong> 已领取</div>" +
        "<div class='pill'><strong>" + numberCell((counts.returned_for_expert_review || 0) + (counts.expert_review_claimed || 0)) + "</strong> 专家复核</div>" +
        "<div class='pill'><strong>" + numberCell((dataset.rows || []).filter((row) => row.is_difficult_case).length) + "</strong> 难例</div>" +
        "<div class='pill'><strong>" + numberCell(counts.unassigned || 0) + "</strong> 未领取</div>" +
      "</div>";
    }
    function showcaseHref(row) {
      const url = new URL("/showcase/", location.origin);
      url.searchParams.set("dataset", row.dataset_key);
      url.searchParams.set("chart_id", row.chart_id);
      if (row.annotator) url.searchParams.set("annotator", row.annotator);
      if (token()) url.searchParams.set("token", token());
      return url.pathname + url.search;
    }
    function formalHref(row) {
      const expertRow = row.dataset_key !== "practice10" && (row.status === "returned_for_expert_review" || row.status === "expert_review_claimed");
      const url = new URL(row.dataset_key === "practice10" ? "/practice/" : expertRow ? "/expert/" : "/formal/", location.origin);
      url.searchParams.set("dataset", row.dataset_key);
      url.searchParams.set("chart_id", row.chart_id);
      if (expertRow) {
        url.searchParams.set("role", "expert");
        url.searchParams.set("expert", row.expert_reviewer || "admin");
      } else if (row.annotator) {
        url.searchParams.set("annotator", row.annotator);
      }
      if (token()) url.searchParams.set("token", token());
      return url.pathname + url.search;
    }
    function filteredOverviewRows() {
      const wantedStatus = overviewStatus.value;
      const query = overviewSearch.value.trim().toUpperCase();
      return overviewRows.filter((row) => {
        if (wantedStatus === "__difficult__" && !row.is_difficult_case) return false;
        if (wantedStatus && wantedStatus !== "__difficult__" && row.status !== wantedStatus) return false;
        if (!query) return true;
        return [row.chart_id, row.airport, row.proc_ident, row.chart_name, row.annotator, row.kind]
          .some((value) => String(value || "").toUpperCase().includes(query));
      });
    }
    function renderOverviewRows() {
      if (!overviewMeta) {
        overviewBox.textContent = "请输入后台管理 token 后刷新。";
        return;
      }
      const rows = filteredOverviewRows();
      const body = rows.map((row) => {
        const summary = row.final || row.draft;
        const reason = row.return_reason ? "<div class='muted'>原因：" + escapeCell(row.return_reason) + "</div>" : "";
        const reviewer = row.expert_reviewer ? "<div class='muted'>复核人：" + escapeCell(row.expert_reviewer) + "</div>" : "";
        const difficult = row.is_difficult_case ? "<div class='muted'>难例：" + escapeCell(row.difficult_case?.marked_by || row.difficult_case?.updated_by || "已标记") + "</div>" : "";
        return "<tr><td><strong>" + escapeCell(row.chart_id) + "</strong><div class='muted'>" + escapeCell([row.airport, row.proc_ident, row.chart_name].filter(Boolean).join(" · ")) + "</div></td>" +
          "<td><span class='status-badge status-" + escapeCell(row.status) + "'>" + escapeCell(statusLabel(row.status)) + "</span>" + reason + reviewer + difficult + "</td>" +
          "<td>" + escapeCell(row.annotator || "-") + "</td>" +
          "<td>" + fieldSummary(summary) + "<div class='muted'>草稿 " + (row.has_draft ? "有" : "无") + "；正式 " + (row.has_annotation ? "有" : "无") + "；快照 " + numberCell(row.submission_count) + "</div></td>" +
          "<td>" + formatTime(row.updated_at) + "</td>" +
          "<td class='row-actions'><a class='table-link' target='_blank' rel='noopener' href='" + escapeCell(showcaseHref(row)) + "'>展示页</a><br><a class='table-link' target='_blank' rel='noopener' href='" + escapeCell(formalHref(row)) + "'>" + ((row.status === "returned_for_expert_review" || row.status === "expert_review_claimed") ? "复核页" : "标注页") + "</a></td></tr>";
      }).join("");
      overviewBox.innerHTML = overviewSummaryHtml(overviewMeta) +
        "<p class='muted'>当前显示 " + rows.length + " / " + overviewRows.length + " 张；更新时间 " + escapeCell(overviewMeta.updated_at || "") + "</p>" +
        "<div class='overview-table-wrap'><table class='overview-table'><thead><tr><th>航图</th><th>状态</th><th>标注人</th><th>字段进度</th><th>最近更新</th><th>操作</th></tr></thead><tbody>" +
        (body || "<tr><td colspan='6'>没有匹配结果。</td></tr>") +
        "</tbody></table></div>";
    }
    async function adminFetch(url, options = {}) {
      if (!token()) throw new Error("请先填写后台管理 token");
      const headers = new Headers(options.headers || {});
      headers.set("x-shujuji-admin-token", token());
      const response = await fetch(url, { ...options, headers });
      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
      if (!response.ok) throw new Error(data.error || response.statusText);
      return data;
    }
    async function createExport() {
      try {
        saveToken();
        show("正在生成导出文件...");
        const data = await adminFetch("/api/admin/export", { method: "POST" });
        show(data);
        await loadExports();
      } catch (error) {
        show("导出失败：" + error.message);
      }
    }
    async function loadProgress() {
      try {
        saveToken();
        const data = await adminFetch("/api/admin/progress");
        progressBox.innerHTML = renderDatasetProgress(data.datasets.formal300);
        show("当前进度已刷新。");
      } catch (error) {
        progressBox.textContent = "刷新失败：" + error.message;
        show("刷新进度失败：" + error.message);
      }
    }
    async function loadOverview() {
      try {
        saveToken();
        overviewBox.textContent = "正在读取逐图总览...";
        const datasetKey = overviewDataset.value || "formal300";
        const data = await adminFetch("/api/admin/overview?dataset=" + encodeURIComponent(datasetKey));
        overviewMeta = data.dataset;
        overviewRows = overviewMeta.rows || [];
        renderOverviewRows();
        show("逐图总览已刷新，共 " + overviewRows.length + " 张。");
      } catch (error) {
        overviewBox.textContent = "刷新失败：" + error.message;
        show("刷新逐图总览失败：" + error.message);
      }
    }
    async function loadExports() {
      try {
        saveToken();
        const data = await adminFetch("/api/admin/exports");
        const rows = data.exports.map((item) => {
          const summary = item.summary?.formal300 || {};
          const href = "/api/admin/export/download?file=" + encodeURIComponent(item.file_name) + "&admin_token=" + encodeURIComponent(token());
          return "<tr><td>" + escapeCell(item.created_at) + "</td><td>" + escapeCell(item.file_name) + "</td><td>" +
            "暂存 " + (summary.draft_json_count || 0) + " / 正式 " + (summary.final_json_count || 0) + " / 提交快照 " + (summary.submission_json_count || 0) +
            "</td><td><a class='download' href='" + href + "'>下载 JSON</a></td></tr>";
        }).join("");
        document.getElementById("exports").innerHTML = rows
          ? "<table><thead><tr><th>时间</th><th>文件</th><th>正式集统计</th><th>操作</th></tr></thead><tbody>" + rows + "</tbody></table>"
          : "<p>还没有导出文件，点击“生成并保存新导出”。</p>";
        show("导出列表已刷新，共 " + data.exports.length + " 个文件。");
      } catch (error) {
        show("刷新失败：" + error.message);
      }
    }
    if (token()) {
      loadProgress();
      loadOverview();
      loadExports();
    }
    overviewDataset.addEventListener("change", loadOverview);
    overviewStatus.addEventListener("change", renderOverviewRows);
    overviewSearch.addEventListener("input", renderOverviewRows);
  </script>
</body>
</html>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function tutorialHtml(options = {}) {
  const manualPath = safeJoin(workspaceRoot, "docs", options.fileName || "正式标注操作手册_步骤与字段对应.md");
  const markdown = stripBom(await fs.readFile(manualPath, "utf8"));
  const title = options.title || "正式标注操作手册：步骤、框类型、字段对应";
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    body{margin:0;background:#f6efe1;color:#10241f;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif}
    header{position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 28px;border-bottom:1px solid #dfceb0;background:rgba(255,250,240,.96);box-shadow:0 10px 30px rgba(26,55,46,.08)}
    h1{margin:0;font-size:22px}
    button{border:1px solid #d8ccb7;border-radius:12px;padding:10px 16px;background:#176f5b;color:white;font-size:16px;font-weight:700;cursor:pointer}
    main{max-width:1120px;margin:24px auto;padding:0 24px 48px}
    pre{white-space:pre-wrap;word-break:break-word;line-height:1.72;margin:0;padding:26px;border:1px solid #dfceb0;border-radius:22px;background:#fffaf0;box-shadow:0 18px 50px rgba(26,55,46,.12);font-family:"Microsoft YaHei","Noto Sans SC",sans-serif;font-size:16px}
  </style>
</head>
<body>
  <header>
    <h1>${escapeHtml(title)}</h1>
    <button type="button" onclick="window.close()">关闭</button>
  </header>
  <main>
    <pre>${escapeHtml(markdown)}</pre>
  </main>
</body>
</html>`;
}

async function saveAnnotation(req, requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const payload = JSON.parse(stripBom(await readRequestBody(req)));
  const expertMode = isExpertRole(requestUrl);
  const reviewerOrAnnotator = safeAnnotator(
    expertMode
      ? (payload.expert_reviewer || payload.reviewer || payload.annotator || getExpertReviewer(requestUrl))
      : (payload.annotator || getAnnotator(requestUrl) || (dataset.finalDataset ? "" : "practice_user"))
  );
  if (dataset.finalDataset && !reviewerOrAnnotator) {
    const error = new Error("正式标注必须先填写标注人。");
    error.statusCode = 400;
    throw error;
  }

  let claim = null;
  let storageAnnotator = reviewerOrAnnotator;
  if (dataset.finalDataset) {
    const claims = await readClaims(dataset);
    claim = claims[chartId];
    if (expertMode) {
      claim = await claimExpertReviewChart(dataset, chartId, reviewerOrAnnotator);
      storageAnnotator = claim.annotator || reviewerOrAnnotator;
    } else {
      if (isExpertReviewClaimStatus(claim?.status)) {
        const error = new Error("这张图已退回专家复审，不能继续保存普通人工标注。");
        error.statusCode = 409;
        throw error;
      }
      if (claim?.annotator && claim.annotator !== reviewerOrAnnotator) {
        const error = new Error(`这张图已由 ${claim.annotator} 领取，不能用 ${reviewerOrAnnotator} 保存，避免重复覆盖。`);
        error.statusCode = 409;
        throw error;
      }
      if (!claim) {
        const error = new Error("请先点击“领取当前图”，领取成功后再保存，避免多人重复标注同一张图。");
        error.statusCode = 409;
        throw error;
      }
    }
  }

  const savedAt = new Date().toISOString();
  const submissionName = `${timestampForFile()}__${expertMode ? `expert-${reviewerOrAnnotator}` : reviewerOrAnnotator}.json`;
  const enrichedPayload = {
    ...payload,
    chart_id: chartId,
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    annotator: storageAnnotator,
    saved_at: savedAt,
    saved_by: expertMode ? "shujuji_annotation_platform_expert_review" : "shujuji_annotation_platform",
    saved_from_ip: clientIp(req)
  };
  if (expertMode) {
    enrichedPayload.review_status = "expert_reviewed";
    enrichedPayload.original_annotator = storageAnnotator;
    enrichedPayload.expert_reviewer = reviewerOrAnnotator;
    enrichedPayload.expert_review = {
      reviewer: reviewerOrAnnotator,
      reviewed_at: savedAt,
      original_annotator: storageAnnotator,
      returned_by: claim?.returned_by || "",
      returned_at: claim?.returned_at || "",
      return_reason: claim?.return_reason || ""
    };
  }

  const currentPath = annotationPath(dataset, "by_annotator", storageAnnotator, `${chartId}.json`);
  const submissionPath = annotationPath(dataset, "submissions", chartId, submissionName);
  await writeJsonFileAtomic(currentPath, enrichedPayload);
  await writeJsonFileAtomic(submissionPath, enrichedPayload);
  await markSubmitted(dataset, chartId, storageAnnotator, expertMode ? { expertReviewer: reviewerOrAnnotator } : {});

  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    annotator: storageAnnotator,
    expert_reviewer: expertMode ? reviewerOrAnnotator : "",
    saved_at: savedAt
  };
}

async function saveDraft(req, requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }

  const payload = JSON.parse(stripBom(await readRequestBody(req)));
  const expertMode = isExpertRole(requestUrl);
  const reviewerOrAnnotator = safeAnnotator(
    expertMode
      ? (payload.expert_reviewer || payload.reviewer || payload.annotator || getExpertReviewer(requestUrl))
      : (payload.annotator || getAnnotator(requestUrl) || (dataset.finalDataset ? "" : "practice_user"))
  );
  if (dataset.finalDataset && !reviewerOrAnnotator) {
    const error = new Error("正式标注必须先填写标注人。");
    error.statusCode = 400;
    throw error;
  }

  let claim = null;
  let storageAnnotator = reviewerOrAnnotator;
  if (dataset.finalDataset) {
    const claims = await readClaims(dataset);
    claim = claims[chartId];
    if (expertMode) {
      claim = await claimExpertReviewChart(dataset, chartId, reviewerOrAnnotator);
      storageAnnotator = claim.annotator || reviewerOrAnnotator;
    } else {
      if (isExpertReviewClaimStatus(claim?.status)) {
        const error = new Error("这张图已退回专家复审，不能继续暂存普通人工标注。");
        error.statusCode = 409;
        throw error;
      }
      if (claim?.annotator && claim.annotator !== reviewerOrAnnotator) {
        const error = new Error(`这张图已由 ${claim.annotator} 领取，不能用 ${reviewerOrAnnotator} 暂存。`);
        error.statusCode = 409;
        throw error;
      }
      if (!claim) {
        const error = new Error("请先领取当前航图，再进行暂存。");
        error.statusCode = 409;
        throw error;
      }
    }
  }

  const savedAt = new Date().toISOString();
  const snapshotName = `${timestampForFile()}__${expertMode ? `expert-${reviewerOrAnnotator}` : reviewerOrAnnotator}.json`;
  const enrichedPayload = {
    ...payload,
    chart_id: chartId,
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    annotator: storageAnnotator,
    review_status: payload.review_status || "draft_saved",
    saved_at: savedAt,
    saved_by: expertMode ? "shujuji_annotation_platform_expert_draft" : "shujuji_annotation_platform_draft",
    saved_from_ip: clientIp(req)
  };
  if (expertMode) {
    enrichedPayload.original_annotator = storageAnnotator;
    enrichedPayload.expert_reviewer = reviewerOrAnnotator;
    enrichedPayload.expert_review = {
      reviewer: reviewerOrAnnotator,
      reviewed_at: savedAt,
      original_annotator: storageAnnotator,
      returned_by: claim?.returned_by || "",
      returned_at: claim?.returned_at || "",
      return_reason: claim?.return_reason || ""
    };
  }

  const currentPath = annotationPath(dataset, "drafts", "by_annotator", storageAnnotator, `${chartId}.json`);
  const snapshotPath = annotationPath(dataset, "drafts", "snapshots", chartId, snapshotName);
  await writeJsonFileAtomic(currentPath, enrichedPayload);
  await writeJsonFileAtomic(snapshotPath, enrichedPayload);

  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    annotator: storageAnnotator,
    expert_reviewer: expertMode ? reviewerOrAnnotator : "",
    saved_at: savedAt
  };
}

async function route(req, res) {
  const requestUrl = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);
  const pathname = decodeURIComponent(requestUrl.pathname);
  const dataset = datasetFromRequest(requestUrl, pathname);
  const annotator = getAnnotator(requestUrl);

  if (req.method === "GET" && pathname === "/") {
    sendHtml(res, 200, landingHtml(requestUrl));
    return;
  }

  if (req.method === "GET" && pathname === "/healthz") {
    sendJson(res, 200, {
      ok: true,
      service: "shujuji_annotation_platform",
      access_control_enabled: Boolean(accessToken),
      admin_export_enabled: Boolean(adminToken),
      expert_review_enabled: Boolean(expertToken || adminToken),
      datasets: Object.fromEntries(Object.entries(datasets).map(([key, dataset]) => [
        key,
        {
          final_dataset: dataset.finalDataset,
          url_path: dataset.urlPath
        }
      ]))
    });
    return;
  }

  if (req.method === "GET" && pathname === "/README.md") {
    await sendTextFile(res, safeJoin(workspaceRoot, "README.md"), "text/markdown; charset=utf-8");
    return;
  }

  if (req.method === "GET" && pathname === "/admin") {
    sendRedirect(res, "/admin/");
    return;
  }

  if (req.method === "GET" && pathname === "/admin/") {
    sendHtml(res, 200, adminHtml());
    return;
  }

  if (req.method === "POST" && pathname === "/api/admin/export") {
    requireAdminAccess(req, requestUrl);
    sendJson(res, 200, await createAnnotationExport());
    return;
  }

  if (req.method === "GET" && pathname === "/api/admin/exports") {
    requireAdminAccess(req, requestUrl);
    sendJson(res, 200, {
      ok: true,
      exports: await listAnnotationExports()
    });
    return;
  }

  if (req.method === "GET" && pathname === "/api/admin/progress") {
    requireAdminAccess(req, requestUrl);
    sendJson(res, 200, await buildAdminProgress());
    return;
  }

  if (req.method === "GET" && pathname === "/api/admin/overview") {
    requireAdminAccess(req, requestUrl);
    sendJson(res, 200, await buildAdminOverview(requestUrl.searchParams.get("dataset")));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/admin/charts/") && pathname.endsWith("/return")) {
    requireAdminAccess(req, requestUrl);
    const parts = pathname.split("/");
    const chartId = parts[4];
    sendJson(res, 200, await adminReturnChartForRequest(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "GET" && pathname === "/api/difficult-cases") {
    requireAccess(req, requestUrl);
    const chartId = requestUrl.searchParams.get("chart_id") || "";
    const difficultCases = await readDifficultCases(dataset);
    if (chartId) {
      if (!isSafeChartId(chartId)) {
        const error = new Error("Invalid chart_id");
        error.statusCode = 400;
        throw error;
      }
      sendJson(res, 200, {
        ok: true,
        dataset: dataset.key,
        chart_id: chartId,
        difficult_case: scrubClientValue(difficultCases[chartId] || null)
      });
      return;
    }
    sendJson(res, 200, {
      ok: true,
      dataset: dataset.key,
      difficult_case_count: difficultCaseCount(difficultCases),
      difficult_cases: scrubClientValue(difficultCases)
    });
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/difficult-cases/")) {
    requireAccess(req, requestUrl);
    const chartId = pathname.split("/").pop();
    sendJson(res, 200, await setDifficultCaseForRequest(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "GET" && pathname === "/api/admin/export/download") {
    requireAdminAccess(req, requestUrl);
    const fileName = requestUrl.searchParams.get("file") || "";
    if (!/^shujuji_annotation_export_[A-Za-z0-9_.-]+\.json$/i.test(fileName) || fileName.endsWith(".manifest.json")) {
      const error = new Error("Invalid export file");
      error.statusCode = 400;
      throw error;
    }
    await sendDownloadFile(res, exportPath(fileName), fileName, "application/json; charset=utf-8");
    return;
  }

  if (req.method === "GET" && pathname === "/tutorial") {
    sendRedirect(res, "/tutorial/");
    return;
  }

  if (req.method === "GET" && pathname === "/tutorial/") {
    sendHtml(res, 200, await tutorialHtml());
    return;
  }

  if (req.method === "GET" && pathname === "/detail-box-tutorial") {
    sendRedirect(res, "/detail-box-tutorial/");
    return;
  }

  if (req.method === "GET" && pathname === "/detail-box-tutorial/") {
    sendHtml(res, 200, await tutorialHtml({
      fileName: "下方复飞框读法教程.md",
      title: "下方复飞框读法教程"
    }));
    return;
  }

  if (req.method === "GET" && pathname === "/practice") {
    sendRedirect(res, redirectWithQuery("/practice/", requestUrl));
    return;
  }

  if (req.method === "GET" && pathname === "/formal") {
    sendRedirect(res, redirectWithQuery("/formal/", requestUrl));
    return;
  }

  if (req.method === "GET" && pathname === "/expert") {
    sendRedirect(res, redirectWithQuery("/expert/", requestUrl));
    return;
  }

  if (req.method === "GET" && pathname === "/showcase") {
    sendRedirect(res, redirectWithQuery("/showcase/", requestUrl));
    return;
  }

  if (req.method === "GET" && (pathname === "/practice/" || pathname === "/formal/" || pathname === "/expert/")) {
    await serveStatic(res, "/index.html");
    return;
  }

  if (req.method === "GET" && pathname === "/showcase/") {
    await serveStatic(res, "/showcase.html");
    return;
  }

  if (req.method === "GET" && pathname === "/api/charts") {
    const expertMode = isExpertRole(requestUrl);
    if (expertMode) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    sendJson(res, 200, {
      dataset: {
        key: dataset.key,
        label: dataset.label,
        final_dataset: dataset.finalDataset,
        url_path: dataset.urlPath
      },
      charts: await loadCharts(dataset, expertMode ? getExpertReviewer(requestUrl) : annotator, {
        lite: dataset.finalDataset && requestUrl.searchParams.get("scope") === "queue",
        expertMode
      })
    });
    return;
  }

  if (req.method === "GET" && pathname === "/api/chart") {
    const expertMode = isExpertRole(requestUrl);
    if (expertMode) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    sendJson(res, 200, await loadChartDetail(
      dataset,
      requestUrl.searchParams.get("chart_id"),
      expertMode ? getExpertReviewer(requestUrl) : annotator,
      { expertMode }
    ));
    return;
  }

  if (req.method === "POST" && pathname === "/api/queue/next") {
    if (isExpertRole(requestUrl)) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    sendJson(res, 200, await nextChartForRequest(req, requestUrl, dataset));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/claims/") && pathname.endsWith("/return")) {
    requireAccess(req, requestUrl);
    const parts = pathname.split("/");
    const chartId = parts[3];
    sendJson(res, 200, await returnClaimForRequest(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/claims/") && pathname.endsWith("/release")) {
    if (isExpertRole(requestUrl)) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    const parts = pathname.split("/");
    const chartId = parts[3];
    sendJson(res, 200, await releaseClaimForRequest(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/claims/")) {
    if (isExpertRole(requestUrl)) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    const chartId = pathname.split("/").pop();
    sendJson(res, 200, await claimChartForRequest(requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "GET" && pathname === "/api/image") {
    requireAccess(req, requestUrl);
    const file = requestUrl.searchParams.get("file");
    if (!/^[A-Za-z0-9_. -]+\.(png|jpg|jpeg)$/i.test(file || "")) {
      const error = new Error("Invalid image file");
      error.statusCode = 400;
      throw error;
    }
    const filePath = safeJoin(dataset.root, "images", imageBasename(file));
    if (!await fileExists(filePath)) {
      const error = new Error("Image file not found");
      error.statusCode = 404;
      throw error;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "content-type": mimeTypes[ext] || "application/octet-stream",
      "cache-control": "public, max-age=300"
    });
    const stream = fss.createReadStream(filePath);
    stream.on("error", (error) => {
      if (!res.headersSent) sendError(res, error);
      else res.destroy(error);
    });
    stream.pipe(res);
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/annotations/")) {
    if (isExpertRole(requestUrl)) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    const chartId = pathname.split("/").pop();
    sendJson(res, 200, await saveAnnotation(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/drafts/")) {
    if (isExpertRole(requestUrl)) requireExpertAccess(req, requestUrl);
    else requireAccess(req, requestUrl);
    const chartId = pathname.split("/").pop();
    sendJson(res, 200, await saveDraft(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "GET") {
    await serveStatic(res, pathname);
    return;
  }

  const error = new Error("Method not allowed");
  error.statusCode = 405;
  throw error;
}

const server = http.createServer((req, res) => {
  route(req, res).catch((error) => sendError(res, error));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`Annotation platform running on 0.0.0.0:${port}`);
  if (publicBaseUrl) {
    console.log(`Public practice: ${publicBaseUrl}/practice/`);
    console.log(`Public formal:   ${publicBaseUrl}/formal/`);
    console.log(`Public expert:   ${publicBaseUrl}/expert/`);
  }
  console.log(`Local practice: http://127.0.0.1:${port}/practice/`);
  console.log(`Local formal:   http://127.0.0.1:${port}/formal/`);
  console.log(`Local expert:   http://127.0.0.1:${port}/expert/`);
  Object.values(os.networkInterfaces())
    .flat()
    .filter((item) => item && item.family === "IPv4" && !item.internal)
    .forEach((item) => {
      console.log(`LAN practice:   http://${item.address}:${port}/practice/`);
      console.log(`LAN formal:     http://${item.address}:${port}/formal/`);
      console.log(`LAN expert:     http://${item.address}:${port}/expert/`);
    });
  console.log(`Workspace root: ${workspaceRoot}`);
  console.log(`Runtime data root: ${runtimeRoot}`);
});
