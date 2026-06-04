# Qoder Windows 部署与验收

本文面向负责部署 Codebase Brain 的维护者。目标是在 Windows Qoder 中只配置一个
stdio MCP Server，并用可重复的步骤确认代码、依赖、sidecar、数据路径和工具面都正确。

使用端只需要 Windows 11，不需要 WSL。WSL/Hermes 仅属于可选开发环境，不进入
Windows 部署架构。首次安装请使用 [`Windows安装指南.md`](Windows安装指南.md)。

## 1. 组件和数据流

```text
Qoder
  |
  | MCP stdio: JSON-RPC
  v
D:\cb\.venv\Scripts\codebrain.exe serve
  |
  +-- SQLite: 项目约定、会话记忆、可选 Git 历史向量
  |
  +-- 本地 embedding: sentence-transformers 或批准的 Ollama
  |
  +-- D:\cb\sidecar\codebase-memory-mcp.exe
      代码结构图谱、符号搜索、调用链
```

MCP 是 AI 客户端调用外部工具的协议。Qoder 是客户端，`codebrain.exe serve` 是 MCP
Server。Codebase Brain 不替代模型，也不直接修改代码；它向模型返回经过检索的项目上下文。

## 2. 推荐目录

```text
D:\cb\
├── .venv\Scripts\codebrain.exe
├── sidecar\codebase-memory-mcp.exe
├── src\codebrain\
└── tests\

D:\qoder工作区\django-test\
└── .codebrain\
    ├── codebrain_full.db
    └── conventions\
```

代码和业务数据分开存放。`.codebrain\codebrain_full.db` 是开发者本机数据，不应提交到业务仓库；
`.codebrain\conventions\*.md` 是团队知识，审核后可以提交。

## 3. 首次部署

先关闭 Qoder、Cursor 和其它 MCP 客户端，确保没有 `codebrain.exe` 正在运行。然后在
Windows PowerShell 中执行安装脚本：

安装脚本支持 Python 3.11+，优先使用 3.12；Windows 只有 Python 3.11 时也可以正常部署。

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git D:\cb
cd D:\cb

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\qoder工作区\django-test" `
  -SidecarPath "D:\安装包\codebase-memory-mcp-windows-amd64.zip" `
  -InstallDev
```

然后运行只读验收：

```powershell
powershell -ExecutionPolicy Bypass -File D:\cb\scripts\verify-qoder-windows.ps1 `
  -ProjectRoot "D:\qoder工作区\django-test"
```

发布前需要让脚本同时运行测试时，加 `-RunTests`。这要求部署虚拟环境已安装 `.[dev]`；
否则脚本会明确提示安装开发测试依赖。验证 sidecar 能否索引中文路径业务仓库时，加
`-RunSidecarIndex`；该选项会执行一次 `fast` 图谱索引。

中文路径验收必须从 Windows PowerShell 原生执行。WSL 不属于 Windows 部署方案，也不要从 WSL
调用 `powershell.exe` 进行发布验收。

## 4. Qoder 配置

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "D:\\cb\\.venv\\Scripts\\codebrain.exe",
      "args": ["serve"],
      "timeout": 300000,
      "env": {
        "CODEBRAIN_DB_PATH": "D:\\qoder工作区\\django-test\\.codebrain\\codebrain_full.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "D:\\qoder工作区\\django-test\\.codebrain\\conventions",
        "CODEBRAIN_CODEBASE_MEMORY_BINARY": "D:\\cb\\sidecar\\codebase-memory-mcp.exe",
        "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
      }
    }
  }
}
```

Qoder 可能同时存在 SharedClientCache 和 `extension/local/mcp.json`。当前实测真正生效的是
`extension/local/mcp.json`，其中 `"timeout": 300` 表示 300 秒，而共享配置中的
`300000` 表示毫秒。升级或排障时必须检查实际生效文件，不能只看 UI 或共享缓存。

不要把数据库、模型缓存或业务仓库放到 `D:\cb`。不要启用远程 embedding，除非团队已经完成
隐私评审。

## 5. 首次验收

重启 Qoder 后按顺序让 AI 调用：

1. `health`
2. `brain_status`，传业务仓库绝对路径
3. `brain_index_project`，传业务仓库绝对路径
4. `brain_context_for_task`，使用一个真实任务
5. `brain_explain_symbol`，使用一个已知函数或类
6. `get_recent_changes`，使用一个已提交文件

通过标准：

| 检查 | 通过标准 |
| --- | --- |
| 服务 | `health.ok=true`，`stable_profile=mvp`，数据库路径正确 |
| 工具面 | 默认 21 个工具 |
| 图谱 | `brain_status.graph` 显示 sidecar 可用 |
| 仓库路径 | 完整图谱验收使用纯英文路径；sidecar `v0.7.0` 暂不支持中文仓库路径 |
| 约定 | `index_convention_files` 后能用 `search_conventions` 命中 |
| 异步任务 | queued 后可用 `brain_index_job_status(job_id)` 得到 succeeded/failed |
| 降级 | sidecar 不可用时，约定、记忆和 Git 只读工具仍可用 |

默认 21 个工具不包括 `index_git_history` 和 `search_history`。只有设置
`CODEBRAIN_GIT_HISTORY_INDEX_ENABLED=true` 后才会注册这两个实验工具，总数变为 23。

## 6. 异步工具

以下调用默认异步，目的是避免 Qoder 工具调用超时：

- `brain_sync_project`
- `brain_context_for_task`
- `get_co_changed_files`
- `index_git_history`，仅实验开关启用时存在

异步调用先返回 `job.id`。之后调用：

```text
brain_index_job_status(job_id="<返回的 job.id>")
```

直到 `status` 为 `succeeded` 或 `failed`。job 只保存在当前 MCP 进程内；重启 Qoder 后 job
列表会丢失。`brain_sync_project` 成功后的索引快照会保存在业务仓库
`.codebrain/index-state.json`。

## 7. 升级和回滚

升级前记录当前提交：

```powershell
cd D:\cb
git rev-parse --short HEAD
git status --short
```

保持工作树干净后升级：

```powershell
git fetch origin main
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m pip install -e ".[local,dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

重启 Qoder，再执行第 5 节验收。不要用 `git reset --hard` 回滚包含本地改动的部署目录。
需要回滚时，先保留本地文件，再切换到已验证提交并重新安装：

```powershell
git switch --detach <已验证提交>
.\.venv\Scripts\python.exe -m pip install -e ".[local,dev]"
```

## 8. 常见故障

| 症状 | 检查 |
| --- | --- |
| Qoder 看不到工具 | 检查实际生效的 `extension/local/mcp.json`、绝对路径和 JSON 转义 |
| 调用约 30 秒后失败 | 检查 Qoder 生效配置的 timeout；长任务使用默认异步模式 |
| 图谱失败但其它工具正常 | 检查 sidecar 路径和版本；中文仓库路径在 sidecar `v0.7.0` 下会降级 |
| 第一次语义检索很慢 | 本地模型首次下载或冷启动；部署验收时提前预热 |
| job 一直找不到 | MCP 进程可能已重启；重新发起异步任务 |
| 数据写错项目 | 检查 `CODEBRAIN_DB_PATH` 和 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` 绝对路径 |

## 9. 发布门禁

- GitHub `origin/main` 提交已记录。
- `python -m pytest -q` 全部通过。
- Windows 验收脚本通过。
- Qoder 中真实调用链通过，不只是在命令行导入成功。
- 中文路径业务仓库通过图谱索引。
- 默认保持 Git 历史向量索引关闭。
- 团队约定已评审，数据库和敏感数据未提交。
