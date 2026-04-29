# Shujuji Annotation Platform

这是复飞航图标注平台的 Node.js 服务端和浏览器前端。它不依赖数据库，运行时通过 JSON 文件保存领取、暂存和正式提交结果。

## 启动

```powershell
node server.js
```

可选环境变量：

- `PORT`：服务端口，默认 `8787`。
- `PUBLIC_BASE_URL`：公网部署后的域名，仅用于日志提示。
- `SHUJUJI_ACCESS_TOKEN`：公网访问口令。设置后所有 `/api/*` 和图片接口都需要 token。
- `SHUJUJI_DATA_ROOT`：人工标注结果的持久化根目录。未设置时写回 `../datasets/*/annotations/`。

## 入口

- `/practice/`：10 张练习集。
- `/formal/`：300 张正式集。
- `/healthz`：健康检查，不返回服务器绝对路径。

公网正式入口示例：

```text
https://你的域名/formal/?token=你的口令
```

## 设计约束

- 航图、预标注和 canonical targets 是只读实验素材。
- 人工领取、暂存、正式提交是运行时数据，公网部署时应写入持久化磁盘。
- API 响应不得返回服务器本机路径、提交文件路径或快照文件路径。
