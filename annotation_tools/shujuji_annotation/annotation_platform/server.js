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

function hashText(value) {
  return crypto.createHash("sha256").update(String(value || "")).digest();
}

function hasValidAccess(req, requestUrl) {
  if (!accessToken) return true;
  const supplied = String(
    req.headers["x-shujuji-token"]
    || requestUrl.searchParams.get("token")
    || ""
  ).trim();
  if (!supplied) return false;
  return crypto.timingSafeEqual(hashText(supplied), hashText(accessToken));
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
  return crypto.timingSafeEqual(hashText(supplied), hashText(adminToken));
}

function requireAdminAccess(req, requestUrl) {
  if (hasValidAdminAccess(req, requestUrl)) return;
  const error = new Error(adminToken ? "Admin token required" : "Admin export is not enabled");
  error.statusCode = adminToken ? 401 : 503;
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
  const drafts = await readAnnotationEntries(annotationPath(dataset, "drafts"));
  const byAnnotator = await readAnnotationEntries(annotationPath(dataset, "by_annotator"));
  const submissions = await readAnnotationEntries(annotationPath(dataset, "submissions"));
  return {
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    exported_at: new Date().toISOString(),
    summary: {
      claims_count: Object.keys(claims || {}).length,
      draft_json_count: drafts.length,
      final_json_count: byAnnotator.length,
      submission_json_count: submissions.length
    },
    annotations: {
      claims,
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

async function readClaims(dataset) {
  if (!dataset.finalDataset) return {};
  return readAnnotationJson(dataset, "claims.json", {});
}

async function writeClaims(dataset, claims) {
  if (!dataset.finalDataset) return;
  await writeJsonFileAtomic(annotationPath(dataset, "claims.json"), claims);
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
    if (existing?.status === "returned_for_expert_review") {
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

async function markSubmitted(dataset, chartId, annotator) {
  if (!dataset.finalDataset) return null;
  return withClaimLock(async () => {
    const claims = await readClaims(dataset);
    const now = new Date().toISOString();
    claims[chartId] = {
      ...(claims[chartId] || {}),
      chart_id: chartId,
      annotator,
      status: "submitted",
      last_saved_at: now
    };
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

async function loadCharts(dataset, annotator) {
  const manifest = await readDatasetJson(dataset, "manifest.json", []);
  const targets = await readDatasetJson(dataset, "targets/canonical_targets.json", []);
  const targetById = new Map(targets.map((item) => [item.chart_id, item]));
  const claims = await readClaims(dataset);

  return Promise.all(manifest.map(async (item) => {
    const chartId = item.chart_id;
    const target = targetById.get(chartId) || {};
    const prelabelPath = safeJoin(dataset.root, "prelabels", `${chartId}.json`);
    const claim = claims[chartId] || null;
    const mine = Boolean(annotator && claim?.annotator === annotator);
    const claimStatus = !dataset.finalDataset
      ? "practice"
      : !claim
        ? "unassigned"
        : claim.status === "returned_for_expert_review"
          ? "returned_for_expert_review"
          : mine
            ? claim.status || "claimed_by_me"
          : "claimed_by_other";
    const myAnnotationPath = annotator
      ? annotationPath(dataset, "by_annotator", annotator, `${chartId}.json`)
      : "";
    const myDraftPath = annotator
      ? annotationPath(dataset, "drafts", "by_annotator", annotator, `${chartId}.json`)
      : "";
    const draft = myDraftPath ? await readJsonFile(myDraftPath, null) : null;
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
      claimed_by: claim?.annotator || "",
      claimed_at: claim?.claimed_at || "",
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

async function loadChartDetail(dataset, chartId, annotator) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }

  const charts = await loadCharts(dataset, annotator);
  const manifestItem = charts.find((item) => item.chart_id === chartId);
  if (!manifestItem) {
    const error = new Error(`Unknown chart_id: ${chartId}`);
    error.statusCode = 404;
    throw error;
  }

  const claims = await readClaims(dataset);
  const claim = claims[chartId] || null;
  const targets = await readDatasetJson(dataset, "targets/canonical_targets.json", []);
  const target = targets.find((item) => item.chart_id === chartId) || null;
  const prelabel = await readDatasetJson(dataset, `prelabels/${chartId}.json`, null);
  const canonicalGt = await readDatasetJson(dataset, `targets/canonical_proxy_gt/${chartId}.json`, null);
  const annotation = annotator
    ? await readAnnotationJson(dataset, `by_annotator/${annotator}/${chartId}.json`, null)
    : null;
  const draft = annotator
    ? await readAnnotationJson(dataset, `drafts/by_annotator/${annotator}/${chartId}.json`, null)
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
      claim_status: claim?.status || manifestItem.claim_status,
      claimed_by: claim?.annotator || manifestItem.claimed_by,
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
    image_url: `/api/image?dataset=${encodeURIComponent(dataset.key)}&file=${encodeURIComponent(manifestItem.image_file)}`
  };
}

async function claimChartForRequest(requestUrl, dataset, chartId) {
  if (!isSafeChartId(chartId)) {
    const error = new Error("Invalid chart_id");
    error.statusCode = 400;
    throw error;
  }
  const annotator = getAnnotator(requestUrl);
  const claim = await claimChart(dataset, chartId, annotator || (dataset.finalDataset ? "" : "practice_user"));
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
  const stat = await fs.stat(filePath);
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
  const practiceHref = landingLink("/practice/", requestUrl);
  const formalHref = landingLink("/formal/", requestUrl);
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
      <h2>练习网页：10 张</h2>
      <p>用于新手熟悉流程，保存结果不进入正式 300 张数据集。</p>
      <a href="${escapeHtml(practiceHref)}">进入练习标注</a>
    </section>
    <section class="card">
      <h2>正式网页：300 张</h2>
      <p>正式入口会按“标注人领取航图”防止重复。可以在链接中预置 <code>annotator=A06</code>，也可以进入后在右上角填写标注人再领取未分配航图。</p>
      <a href="${escapeHtml(formalHref)}">进入正式标注</a>
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
  <title>标注结果管理员导出</title>
  <style>
    body{margin:0;background:#f6efe1;color:#10241f;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif}
    main{max-width:980px;margin:7vh auto;padding:0 24px 48px}
    .card{background:#fffaf0;border:1px solid #dfceb0;border-radius:22px;padding:24px;margin:18px 0;box-shadow:0 18px 50px rgba(26,55,46,.12)}
    h1{margin:0 0 10px;font-size:30px}
    p{line-height:1.7;color:#405a54}
    input{box-sizing:border-box;width:100%;padding:13px 14px;border:1px solid #cdbf9f;border-radius:12px;background:#fff;font-size:16px}
    button,a.download{display:inline-block;margin:12px 10px 0 0;padding:12px 18px;border:0;border-radius:12px;background:#176f5b;color:white;text-decoration:none;font-size:15px;font-weight:700;cursor:pointer}
    button.secondary{background:#efe4cf;color:#10241f;border:1px solid #d8ccb7}
    table{width:100%;border-collapse:collapse;margin-top:16px;background:white;border-radius:14px;overflow:hidden}
    th,td{padding:12px;border-bottom:1px solid #eadcc4;text-align:left;font-size:14px;vertical-align:top}
    code{background:#efe4cf;padding:2px 6px;border-radius:6px}
    .status{white-space:pre-wrap;background:#10241f;color:#e6fff8;border-radius:14px;padding:14px;min-height:44px}
  </style>
</head>
<body>
  <main>
    <h1>标注结果管理员导出</h1>
    <p>这个页面只给管理员使用。普通标注人员继续使用正式标注链接，不需要进入这里。</p>
    <section class="card">
      <h2>管理员 token</h2>
      <input id="token" type="password" placeholder="请输入管理员导出 token">
      <button type="button" onclick="saveToken()">保存 token</button>
      <button class="secondary" type="button" onclick="createExport()">生成并保存新导出</button>
      <button class="secondary" type="button" onclick="loadExports()">刷新导出列表</button>
      <p>导出文件会同时保存在服务器 <code>/data/shujuji_annotation/exports</code>，并可在本页下载。</p>
      <div id="status" class="status">等待操作...</div>
    </section>
    <section class="card">
      <h2>已有导出</h2>
      <div id="exports"></div>
    </section>
  </main>
  <script>
    const tokenInput = document.getElementById("token");
    const statusBox = document.getElementById("status");
    const params = new URLSearchParams(location.search);
    const tokenFromUrl = params.get("admin_token");
    if (tokenFromUrl) {
      sessionStorage.setItem("shujuji_admin_token", tokenFromUrl);
      params.delete("admin_token");
      history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
    }
    tokenInput.value = sessionStorage.getItem("shujuji_admin_token") || "";

    function token() {
      return tokenInput.value.trim();
    }
    function saveToken() {
      sessionStorage.setItem("shujuji_admin_token", token());
      statusBox.textContent = "管理员 token 已保存在当前浏览器会话。";
    }
    function show(value) {
      statusBox.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }
    async function adminFetch(url, options = {}) {
      if (!token()) throw new Error("请先填写管理员 token");
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
    async function loadExports() {
      try {
        saveToken();
        const data = await adminFetch("/api/admin/exports");
        const rows = data.exports.map((item) => {
          const summary = item.summary?.formal300 || {};
          const href = "/api/admin/export/download?file=" + encodeURIComponent(item.file_name) + "&admin_token=" + encodeURIComponent(token());
          return "<tr><td>" + item.created_at + "</td><td>" + item.file_name + "</td><td>" +
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
    if (token()) loadExports();
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
  const annotator = safeAnnotator(payload.annotator || getAnnotator(requestUrl) || (dataset.finalDataset ? "" : "practice_user"));
  if (dataset.finalDataset && !annotator) {
    const error = new Error("正式标注必须先填写标注人。");
    error.statusCode = 400;
    throw error;
  }

  if (dataset.finalDataset) {
    const claims = await readClaims(dataset);
    const claim = claims[chartId];
    if (claim?.status === "returned_for_expert_review") {
      const error = new Error("这张图已退回专家复审，不能继续保存普通人工标注。");
      error.statusCode = 409;
      throw error;
    }
    if (claim?.annotator && claim.annotator !== annotator) {
      const error = new Error(`这张图已由 ${claim.annotator} 领取，不能用 ${annotator} 保存，避免重复覆盖。`);
      error.statusCode = 409;
      throw error;
    }
    if (!claim) {
      const error = new Error("请先点击“领取当前图”，领取成功后再保存，避免多人重复标注同一张图。");
      error.statusCode = 409;
      throw error;
    }
  }

  const savedAt = new Date().toISOString();
  const submissionName = `${timestampForFile()}__${annotator}.json`;
  const enrichedPayload = {
    ...payload,
    chart_id: chartId,
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    annotator,
    saved_at: savedAt,
    saved_by: "shujuji_annotation_platform",
    saved_from_ip: clientIp(req)
  };

  const currentPath = annotationPath(dataset, "by_annotator", annotator, `${chartId}.json`);
  const submissionPath = annotationPath(dataset, "submissions", chartId, submissionName);
  await writeJsonFileAtomic(currentPath, enrichedPayload);
  await writeJsonFileAtomic(submissionPath, enrichedPayload);
  await markSubmitted(dataset, chartId, annotator);

  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    annotator,
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
  const annotator = safeAnnotator(payload.annotator || getAnnotator(requestUrl) || (dataset.finalDataset ? "" : "practice_user"));
  if (dataset.finalDataset && !annotator) {
    const error = new Error("正式标注必须先填写标注人。");
    error.statusCode = 400;
    throw error;
  }

  if (dataset.finalDataset) {
    const claims = await readClaims(dataset);
    const claim = claims[chartId];
    if (claim?.status === "returned_for_expert_review") {
      const error = new Error("这张图已退回专家复审，不能继续暂存普通人工标注。");
      error.statusCode = 409;
      throw error;
    }
    if (claim?.annotator && claim.annotator !== annotator) {
      const error = new Error(`这张图已由 ${claim.annotator} 领取，不能用 ${annotator} 暂存。`);
      error.statusCode = 409;
      throw error;
    }
    if (!claim) {
      const error = new Error("请先领取当前航图，再进行暂存。");
      error.statusCode = 409;
      throw error;
    }
  }

  const savedAt = new Date().toISOString();
  const snapshotName = `${timestampForFile()}__${annotator}.json`;
  const enrichedPayload = {
    ...payload,
    chart_id: chartId,
    dataset_key: dataset.key,
    final_dataset: dataset.finalDataset,
    annotator,
    review_status: payload.review_status || "draft_saved",
    saved_at: savedAt,
    saved_by: "shujuji_annotation_platform_draft",
    saved_from_ip: clientIp(req)
  };

  const currentPath = annotationPath(dataset, "drafts", "by_annotator", annotator, `${chartId}.json`);
  const snapshotPath = annotationPath(dataset, "drafts", "snapshots", chartId, snapshotName);
  await writeJsonFileAtomic(currentPath, enrichedPayload);
  await writeJsonFileAtomic(snapshotPath, enrichedPayload);

  return {
    ok: true,
    dataset: dataset.key,
    chart_id: chartId,
    annotator,
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

  if (req.method === "GET" && (pathname === "/practice/" || pathname === "/formal/")) {
    await serveStatic(res, "/index.html");
    return;
  }

  if (req.method === "GET" && pathname === "/api/charts") {
    requireAccess(req, requestUrl);
    sendJson(res, 200, {
      dataset: {
        key: dataset.key,
        label: dataset.label,
        final_dataset: dataset.finalDataset,
        url_path: dataset.urlPath
      },
      charts: await loadCharts(dataset, annotator)
    });
    return;
  }

  if (req.method === "GET" && pathname === "/api/chart") {
    requireAccess(req, requestUrl);
    sendJson(res, 200, await loadChartDetail(dataset, requestUrl.searchParams.get("chart_id"), annotator));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/claims/") && pathname.endsWith("/return")) {
    requireAccess(req, requestUrl);
    const parts = pathname.split("/");
    const chartId = parts[3];
    sendJson(res, 200, await returnClaimForRequest(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/claims/")) {
    requireAccess(req, requestUrl);
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
    requireAccess(req, requestUrl);
    const chartId = pathname.split("/").pop();
    sendJson(res, 200, await saveAnnotation(req, requestUrl, dataset, chartId));
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/drafts/")) {
    requireAccess(req, requestUrl);
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
  }
  console.log(`Local practice: http://127.0.0.1:${port}/practice/`);
  console.log(`Local formal:   http://127.0.0.1:${port}/formal/`);
  Object.values(os.networkInterfaces())
    .flat()
    .filter((item) => item && item.family === "IPv4" && !item.internal)
    .forEach((item) => {
      console.log(`LAN practice:   http://${item.address}:${port}/practice/`);
      console.log(`LAN formal:     http://${item.address}:${port}/formal/`);
    });
  console.log(`Workspace root: ${workspaceRoot}`);
  console.log(`Runtime data root: ${runtimeRoot}`);
});
