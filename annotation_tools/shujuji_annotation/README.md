# 复飞航图多人协同标注工作区

本目录提供 FAA missed approach 复飞实验的人工校准数据集与多人协同标注平台。平台是浏览器前端 + Node.js 服务端结构，既可以在本机/局域网使用，也可以部署为公网网页，把链接发给标注人直接使用。

## 目录结构

- `annotation_platform/`：标注网页与 Node.js 服务端代码。
- `datasets/practice10/`：10 张练习航图，用于熟悉标注流程，不进入正式统计。
- `datasets/formal300/`：300 张正式航图、预标注、PR #28 canonical target 与 manifest。
- `docs/`：人工标注教程、多人协同说明、字段对应规则。
- `scripts/`：数据集构建和预标注生成脚本。
- `config/`：CIFP 最大集合与样本构建相关配置。

## 本地或局域网启动

在本目录运行：

```bat
启动标注平台.bat
```

或手动运行：

```powershell
cd tools\shujuji_annotation\annotation_platform
node server.js
```

启动后访问：

- 练习集：`http://127.0.0.1:8787/practice/`
- 正式集：`http://127.0.0.1:8787/formal/`
- 局域网协作：`http://主机IP:8787/formal/`

## 公网网页部署

公网部署时不要直接暴露无口令接口，建议至少设置：

```powershell
$env:SHUJUJI_ACCESS_TOKEN="换成一段随机口令"
$env:SHUJUJI_DATA_ROOT="持久化数据目录"
$env:PUBLIC_BASE_URL="https://你的公网域名"
node annotation_platform\server.js
```

发给标注人的正式入口格式：

```text
https://你的公网域名/formal/?token=换成一段随机口令
```

前端会把 token 存在浏览器 sessionStorage 中，并从地址栏移除，后续 API、图片、领取、暂存、正式提交都会自动携带 token。

## 数据保存

只读素材始终来自本目录下的相对路径：

- 航图 PNG：`datasets/*/images/`
- 预标注：`datasets/*/prelabels/`
- canonical targets：`datasets/*/targets/`

人工运行时数据默认写回本目录的 `datasets/*/annotations/`。如果设置了 `SHUJUJI_DATA_ROOT`，人工数据会写入该持久化目录下对应的：

- 暂存：`datasets/formal300/annotations/drafts/by_annotator/<annotator>/<chart_id>.json`
- 暂存快照：`datasets/formal300/annotations/drafts/snapshots/<chart_id>/...json`
- 正式提交：`datasets/formal300/annotations/by_annotator/<annotator>/<chart_id>.json`
- 正式提交快照：`datasets/formal300/annotations/submissions/<chart_id>/...json`

浏览器端不会显示服务器本机绝对路径，API 响应也会对内部路径做脱敏处理。

## 安全注意

- 公网部署必须设置 `SHUJUJI_ACCESS_TOKEN`，不要把无 token 的公网地址发给标注人。
- 不要提交 `.env`、运行日志、`runtime_data/`、真实人工标注结果或服务器私有路径。
- 如果使用云服务，必须启用持久化磁盘或卷，并把 `SHUJUJI_DATA_ROOT` 指向该磁盘，否则重新部署可能丢失人工暂存和提交。
