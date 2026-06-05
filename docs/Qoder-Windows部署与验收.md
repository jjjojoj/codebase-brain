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

D:\projects\django-test\
└── ...  # 可选：给 sidecar 使用的英文路径副本或 junction
```

代码和业务数据分开存放。`.codebrain\codebrain_full.db` 是开发者本机数据，不应提交到业务仓库；
`.codebrain\conventions\*.md` 是团队知识，审核后可以提交。

## 3. 首次部署

先关闭 Qoder、Cursor 和其它 MCP 客户端，确保没有 `codebrain.exe` 正在运行。然后在
Windows PowerShell 中执行安装脚本：

安装脚本支持 Python 3.11+，优先使用 3.12；Windows 只有 Python 3.11 时也可以正常部署。
脚本默认 embedding 模型是 `paraphrase-multilingual-MiniLM-L12-v2`，约 470MB，适合中文或中英混合项目；
如果只需要英文轻量模型，传 `-EmbedderModel all-MiniLM-L6-v2`。

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git D:\cb
cd D:\cb

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\qoder工作区\django-test" `
  -GraphProjectRoot "D:\projects\django-test" `
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

验证 Qoder 敏感的异步工作流时，传入一个仓库内文件：

```powershell
powershell -ExecutionPolicy Bypass -File D:\cb\scripts\verify-qoder-windows.ps1 `
  -ProjectRoot "D:\projects\django-test" `
  -AsyncSmokeFile "django/contrib/auth/__init__.py"
```

中文路径验收必须从 Windows PowerShell 原生执行。WSL 不属于 Windows 部署方案，也不要从 WSL
调用 `powershell.exe` 进行发布验收。

## 4. Qoder 配置

推荐优先使用项目级配置：在业务仓库根目录创建 `.qoder\mcp.json`，把安装脚本生成的
`D:\cb\.local-configs\<业务仓库名>-mcp.json` 内容复制进去。这样每个业务项目可以带自己的
`CODEBRAIN_DB_PATH`、`CODEBRAIN_DEFAULT_PROJECT` 和 repo alias，多项目切换时不需要反复改全局设置。

如果当前 Qoder 版本没有自动加载项目级 `.qoder\mcp.json`，再把同一段配置放到 Qoder 实际生效的全局
MCP 配置文件中。无论放在哪个位置，AI 客户端只应配置一个 `codebase-brain` MCP Server。

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
	        "CODEBRAIN_DEFAULT_PROJECT": "D:\\qoder工作区\\django-test",
	        "CODEBRAIN_CODEBASE_MEMORY_BINARY": "D:\\cb\\sidecar\\codebase-memory-mcp.exe",
	        "CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES": "D:\\qoder工作区\\django-test=D:\\projects\\django-test",
	        "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
	      }
    }
  }
}
```

Qoder 可能同时存在 SharedClientCache 和 `extension/local/mcp.json`。当前实测真正生效的是
`extension/local/mcp.json`，其中 `"timeout": 300` 表示 300 秒，而共享配置中的
`300000` 表示毫秒。升级或排障时必须检查实际生效文件，不能只看 UI 或共享缓存。

`"timeout": 300000` 是 Qoder 专用字段，用于避免长索引任务被过早切断。不要把带 `timeout` 的
Qoder 配置原样复制到 Cursor；Cursor 配置只保留 `command`、`args` 和 `env`。

不要把数据库、模型缓存或业务仓库放到 `D:\cb`。不要启用远程 embedding，除非团队已经完成
隐私评审。

如果业务仓库本身在纯英文路径，例如 Java 测试项目 `D:\projects\ruoyi-vue-pro`，可以省略
`CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES`，但仍建议设置：

```json
"CODEBRAIN_DEFAULT_PROJECT": "D:\\projects\\ruoyi-vue-pro"
```

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
| 仓库路径 | 不显式传 `repo_path` 时也应解析到业务仓库，不应落到 `D:\Qoder` |
| 中文路径图谱 | `repo_aliases` 非空时，`project_alias_used` 应命中英文图谱 project |
| 约定 | `index_convention_files` 后能用 `search_conventions` 命中 |
| 异步任务 | queued 后可用 `brain_index_job_status(job_id)` 得到 succeeded/failed |
| 降级 | sidecar 不可用时，约定、记忆和 Git 只读工具仍可用 |

默认 21 个工具不包括 `index_git_history` 和 `search_history`。只有设置
`CODEBRAIN_GIT_HISTORY_INDEX_ENABLED=true` 后才会注册这两个实验工具，总数变为 23。

## 6. 异步工具

以下调用默认异步，目的是避免 Qoder 工具调用超时：

- `brain_sync_project`
- `brain_context_for_task`
- `get_blame`
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
| graph 查到 Qoder/IDE 自身符号 | 设置 `CODEBRAIN_DEFAULT_PROJECT`；中文路径再设置 `CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES` |
| repo_aliases 为空 | Qoder MCP 配置的 `env` 未传入，修改实际生效的 `extension/local/mcp.json` 后重启 Qoder |
| 第一次语义检索很慢 | 本地模型首次下载或冷启动；部署验收时提前预热 |
| 显存占用过高 | 默认保持 `CODEBRAIN_EMBEDDER_DEVICE=cpu`；仅在明确需要时设置 `cuda` 或 `auto` |
| job 一直找不到 | MCP 进程可能已重启；重新发起异步任务 |
| 数据写错项目 | 检查 `CODEBRAIN_DB_PATH` 和 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` 绝对路径 |

## 9. 发布门禁

- GitHub `origin/main` 提交已记录。
- `python -m pytest -q` 全部通过。
- Windows 验收脚本通过。
- Qoder 中真实调用链通过，不只是在命令行导入成功。
- 中文路径业务仓库通过 repo alias 命中图谱；纯英文 Java 项目无需 alias 也能命中。
- 默认保持 Git 历史向量索引关闭。
- 团队约定已评审，数据库和敏感数据未提交。

## 10. Java / 芋道项目验收样例

可用 Java 项目验证跨语言图谱能力，例如：

```powershell
git clone --depth 1 https://github.com/YunaiV/ruoyi-vue-pro.git D:\projects\ruoyi-vue-pro

powershell -ExecutionPolicy Bypass -File D:\cb\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\projects\ruoyi-vue-pro" `
  -SidecarPath "D:\安装包\codebase-memory-mcp-windows-amd64.zip" `
  -InstallDev
```

Qoder MCP `env` 至少应包含：

```json
{
  "CODEBRAIN_DB_PATH": "D:\\projects\\ruoyi-vue-pro\\.codebrain\\codebrain_full.db",
  "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "D:\\projects\\ruoyi-vue-pro\\.codebrain\\conventions",
  "CODEBRAIN_DEFAULT_PROJECT": "D:\\projects\\ruoyi-vue-pro",
  "CODEBRAIN_CODEBASE_MEMORY_BINARY": "D:\\cb\\sidecar\\codebase-memory-mcp.exe",
  "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

重启 Qoder 后，不传 `repo_path` 调用：

```text
brain_context_for_task(task="理解用户登录和权限校验流程", async_mode=true, top_k=5)
brain_explain_symbol(symbol="AdminAuthServiceImpl")
```

通过标准：`repo_path` 指向 `D:\projects\ruoyi-vue-pro`，graph 为 `ready`，相关符号来自
`yudao-*` Java 模块，而不是 Qoder/IDE 安装目录。
