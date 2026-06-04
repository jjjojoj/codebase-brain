# Codebase Brain

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP Server](https://img.shields.io/badge/MCP-server-purple)
![Local First](https://img.shields.io/badge/default-local--first-green)
![Status](https://img.shields.io/badge/status-composition_MVP-orange)

Codebase Brain 是给 AI 编程工具使用的项目知识层 MCP Server。它把团队约定、轻量任务记忆和安全的 Git 只读上下文暴露给 Cursor、Qoder、Codex、OpenCode、Claude Code、Windsurf、Cline、Hermes 以及其它支持 MCP 的客户端。

它现在采用“组合式 MCP 门面”：Codebase Brain 自己负责团队知识、任务记忆、Git 只读上下文和统一工具入口；结构化代码图谱优先复用 `codebase-memory-mcp` 这样的成熟 sidecar，而不是在 Python 里重写一套不成熟的图谱引擎。

> **安全边界**：默认本地运行、本地 SQLite 存储、本地 embedding。稳定版不提供 OpenAI / 云端 embedding 入口，Git 历史向量索引默认关闭。`codebase-memory-mcp` 是可选本地 sidecar；没有安装时，`brain_*` 工具会返回清晰的降级状态，不会导致 MCP 服务不可用。

## 为什么需要它

- **项目约定可检索**：把测试、错误处理、模块边界、命名、提交规范等规则写成 Markdown，AI 修改代码前可以检索。
- **任务上下文可延续**：手动记录关键决策、踩坑、文件变更，下次类似任务可以召回。
- **Git 上下文低风险可用**：读取 blame、最近提交、经常一起修改的文件，不需要把 Git 历史全文入库。
- **代码图谱可接入**：安装 `codebase-memory-mcp` 后，AI 可以通过同一个 Codebase Brain MCP 入口索引项目、搜索符号、追踪调用关系。
- **团队可共享，个人可本地化**：约定文件可以提交到业务仓库，数据库和个人记忆留在每个开发者本机。

## 当前稳定范围

当前版本默认交付 21 个 MCP 工具：

| 分组 | 工具 |
| --- | --- |
| 状态 | `health` |
| 组合式入口 | `brain_context_for_task`, `brain_status`, `brain_sync_status`, `brain_sync_project`, `brain_index_job_status`, `brain_index_project`, `brain_explain_symbol` |
| 项目约定 | `add_convention`, `search_conventions`, `list_conventions`, `index_convention_files` |
| 会话记忆 | `start_session`, `record_decision`, `record_problem`, `record_file_change`, `end_session`, `recall_context` |
| Git 只读上下文 | `get_blame`, `get_recent_changes`, `get_co_changed_files` |

默认关闭这些实验能力：

- Git 历史向量索引和已索引 Git 历史的语义搜索；只有设置 `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED=true` 才会注册 `index_git_history` / `search_history`。
- legacy `packages/*` 多 MCP Server 入口。
- 自动 watch 常驻文件监听。
- 自动改写各类 AI 客户端配置。
- 内置重写 `codebase-memory-mcp` 的图谱引擎。
- 把 Milvus 设为默认向量后端。

这些能力不是永远不做，而是等安全过滤、文件过滤、真实客户端验证成熟后再讨论是否进入实验分支。

明确不做：

- OpenAI / 云端 embedding provider。Codebase Brain 的 embedding 路线只采用本地 `sentence-transformers` 或本地/内网批准的 Ollama；这不是等待成熟的实验能力。

## Quick Start

需要 Python 3.11+，推荐 Python 3.12。Linux/WSL 上不要假设 `python3` 一定满足版本要求；很多发行版的 `python3` 仍可能指向 Python 3.10，所以 Quick Start 明确使用 `python3.12`。

```bash
git clone https://github.com/jjjojoj/codebase-brain.git
cd codebase-brain
python3.12 -m venv .venv
.venv/bin/pip install -e ".[local]"
.venv/bin/codebrain info
```

Windows PowerShell:

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git C:\codebase-brain
cd C:\codebase-brain
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -e ".[local]"
.\.venv\Scripts\codebrain.exe info
```

`local` extra 会安装 `sentence-transformers`。第一次启动时模型可能需要下载；公司私有代码或敏感仓库建议保持这个本地方案。

首次运行可能提示 `unauthenticated requests to HF Hub`。可以设置 `HF_TOKEN` 提高 Hugging Face Hub 下载稳定性和限额，但不是必需项；默认模型 `all-MiniLM-L6-v2` 约 90MB。

`minimal` extra 不安装 embedding 依赖，只适合 CI、查看配置、启动 MCP 工具面或验证空项目路径。真实索引约定、语义搜索和会话记忆召回仍然需要 `.[local]`，或把 `CODEBRAIN_EMBEDDER_PROVIDER` 显式配置为团队批准的本地 Ollama。

稳定版只支持本地 embedding provider：默认 `sentence-transformers`，也可以显式设置 `CODEBRAIN_EMBEDDER_PROVIDER=ollama` 使用本机 Ollama 服务。不支持 `openai` provider。

如果团队想接入已有的 Milvus Standalone 或 Zilliz Cloud，可以安装轻量客户端依赖：

```bash
.venv/bin/python -m pip install -e ".[local,milvus]"
```

如果团队想在本机试用 Milvus Lite，再安装包含本地引擎的依赖：

```bash
.venv/bin/python -m pip install -e ".[local,milvus-lite]"
```

然后在 MCP 配置里显式启用：

```json
{
  "env": {
    "CODEBRAIN_VECTOR_STORE_BACKEND": "milvus",
    "CODEBRAIN_MILVUS_URI": "/ABS/PATH/your-project/.codebrain/milvus_lite.db",
    "CODEBRAIN_MILVUS_COLLECTION_PREFIX": "codebrain"
  }
}
```

不设置 `CODEBRAIN_VECTOR_STORE_BACKEND=milvus` 时，默认仍使用 SQLite。

注意：Milvus Lite 依赖本地原生包，不同系统可能需要额外构建工具。若安装 `milvus-lite` 被 `faiss-cpu`、`swig` 或平台 wheel 卡住，先使用远程 Milvus/Zilliz 或继续用默认 SQLite。

如果需要代码图谱能力，再安装 `codebase-memory-mcp`，并确保它在 `PATH` 里：

```bash
codebase-memory-mcp --version
```

如果二进制不在 `PATH`，在 MCP 配置里设置：

```json
{
  "env": {
    "CODEBRAIN_CODEBASE_MEMORY_BINARY": "/ABS/PATH/codebase-memory-mcp"
  }
}
```

## 本地可视化 Dashboard

可以启动一个只读本地页面，用来查看当前项目状态、文件过滤快照、sync-trigger 状态、Milvus 配置状态，并生成一份 MCP JSON 配置：

```bash
.venv/bin/codebrain dashboard --repo-path /ABS/PATH/your-project --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

这个 dashboard 不会自动改写 Cursor、Qoder、Codex、OpenCode 或 Hermes 的配置文件。它只展示状态和可复制的配置，避免误改每个开发者自己的本地环境。

## 初始化项目约定

在你的业务仓库里创建约定目录：

```text
your-project/
  .codebrain/
    conventions/
      testing.md
      error-handling.md
      module-boundaries.md
```

每个 Markdown 文件可以使用 YAML frontmatter：

```markdown
---
module: auth
title: 认证模块错误处理约定
tags: [auth, errors]
---

认证相关代码返回明确的 AuthError 类型，不要跨模块边界抛出通用异常。
```

让 Qoder、Cursor、Codex 或其它 AI 从框架/业务源码提取约定前，先让它读取 `templates/conventions/EXTRACTION-GUIDE.md`。这个模板要求只提取开发者应该遵守的模式，不把框架内部实现细节写成约定，并且必须从测试文件中提取测试编写模式。

索引约定：

```bash
CODEBRAIN_DB_PATH=/ABS/PATH/your-project/.codebrain/codebrain.db \
  .venv/bin/codebrain index --path /ABS/PATH/your-project/.codebrain/conventions
```

也可以在 MCP 客户端里调用 `index_convention_files`。如果客户端不是从业务仓库根目录启动，请传入 `.codebrain/conventions` 的绝对路径。索引结果里的 `warnings` 不会阻断入库，但应该认真处理；它们通常表示约定太长，或包含框架内部实现关键词。

## MCP 配置

只需要配置一个 MCP Server，名字建议叫 `codebase-brain`。所有路径建议写绝对路径，因为不同客户端对 `~`、工作目录和环境变量的处理不完全一致。

Qoder + Windows 的完整部署、升级、验收和回滚流程见
[`docs/Qoder-Windows部署与验收.md`](docs/Qoder-Windows部署与验收.md)。
纯 Windows 11 安装流程见
[`docs/Windows安装指南.md`](docs/Windows安装指南.md)。
Cursor 配置流程见
[`docs/Cursor-Windows部署指南.md`](docs/Cursor-Windows部署指南.md)。
第一次接触 MCP 时先阅读
[`docs/使用指南.md`](docs/使用指南.md)。
项目能力是否真正解决问题，应按
[`docs/七项能力验收矩阵.md`](docs/七项能力验收矩阵.md) 留存证据。

### 通用 JSON 配置

适用于使用 `mcpServers` JSON 结构的客户端，或可以在 UI 里粘贴同等字段的客户端。

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "/ABS/PATH/codebase-brain/.venv/bin/codebrain",
      "args": ["serve"],
      "env": {
        "CODEBRAIN_DB_PATH": "/ABS/PATH/your-project/.codebrain/codebrain.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "/ABS/PATH/your-project/.codebrain/conventions"
      }
    }
  }
}
```

Windows:

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "C:\\codebase-brain\\.venv\\Scripts\\codebrain.exe",
      "args": ["serve"],
      "env": {
        "CODEBRAIN_DB_PATH": "C:\\path\\to\\your-project\\.codebrain\\codebrain.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "C:\\path\\to\\your-project\\.codebrain\\conventions"
      }
    }
  }
}
```

### Codex CLI TOML 配置

Codex CLI 可以在 `~/.codex/config.toml` 中加入：

```toml
[mcp_servers.codebase-brain]
command = "/ABS/PATH/codebase-brain/.venv/bin/codebrain"
args = ["serve"]

[mcp_servers.codebase-brain.env]
CODEBRAIN_DB_PATH = "/ABS/PATH/your-project/.codebrain/codebrain.db"
CODEBRAIN_DEFAULT_CONVENTIONS_PATH = "/ABS/PATH/your-project/.codebrain/conventions"
```

### 中文 / 多语言约定模型配置

如果团队主要写中文约定，但任务描述里混有英文技术术语，可以把模型切到多语言版本。

JSON:

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "/ABS/PATH/codebase-brain/.venv/bin/codebrain",
      "args": ["serve"],
      "env": {
        "CODEBRAIN_DB_PATH": "/ABS/PATH/your-project/.codebrain/codebrain.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "/ABS/PATH/your-project/.codebrain/conventions",
        "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
      }
    }
  }
}
```

Codex CLI TOML:

```toml
[mcp_servers.codebase-brain.env]
CODEBRAIN_DB_PATH = "/ABS/PATH/your-project/.codebrain/codebrain.db"
CODEBRAIN_DEFAULT_CONVENTIONS_PATH = "/ABS/PATH/your-project/.codebrain/conventions"
CODEBRAIN_EMBEDDER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

### 多客户端使用建议

| 客户端 | 建议方式 | 说明 |
| --- | --- | --- |
| Cursor | 在 MCP 设置里添加通用 JSON 配置 | 团队成员最容易复制粘贴。 |
| Qoder | 在 MCP 配置入口添加同样的 `command` / `args` / `env` | 先手动配置，避免脚本误改个人设置。 |
| Codex CLI | 使用上面的 TOML 配置 | 适合重度终端工作流。 |
| OpenCode | 使用客户端支持的 MCP JSON / 配置文件 | 字段保持同一组：`command`, `args`, `env`。 |
| Hermes / 其它 MCP 客户端 | 按客户端文档添加 stdio MCP server | 只要支持 stdio MCP，就可以接入。 |

配置后重启客户端，先调用 `health`。如果能看到 `stable_profile: "mvp"` 和正确的 `db_path`，说明服务连通。

随后建议调用 `brain_status`。它会同时告诉你：

- Codebase Brain 本地数据库和 embedding 是否可用。
- `codebase-memory-mcp` sidecar 是否可用。
- 当前 embedding 策略和 Git 历史向量索引开关。

## 推荐工作流

个人使用：

1. 给常见任务写 5 到 20 条约定，比如测试、错误处理、目录结构、提交信息。
2. 调用 `index_convention_files`。
3. 如果安装了 `codebase-memory-mcp`，调用 `brain_index_project` 索引代码图谱和约定。
4. 后续修改代码后调用 `brain_sync_status`，如果返回 `needs_sync: true`，再调用 `brain_sync_project`。
5. 开始复杂任务时调用 `start_session`。
6. 修改不熟悉的符号前调用 `brain_explain_symbol`，再按需调用 `get_recent_changes`、`get_blame` 或 `get_co_changed_files`。
7. 遇到重要决策或问题时调用 `record_decision` / `record_problem`。
8. 任务结束时调用 `end_session`。

团队落地：

1. 先选一个真实业务仓库试点，不要一开始铺到所有项目。
2. 把 `.codebrain/conventions/*.md` 提交到业务仓库。
3. 把 `.codebrain/codebrain.db` 保留在每个人本机，不提交数据库。
4. 保持本地 embedding；稳定版不接入云端 embedding provider。
5. 先使用 `brain_context_for_task` 和 Git 只读工具，不启用 Git 历史向量索引。
6. 每周让团队删掉过期约定，避免知识库变成噪音。

记忆内容要短、事实化。不要写入密钥、凭据、客户数据、生产日志或其它敏感信息。

## 工具说明

### 状态

| 工具 | 说明 |
| --- | --- |
| `health` | 查看服务、存储、embedding provider、安全开关和数据库路径。 |

### 组合式入口

| 工具 | 说明 |
| --- | --- |
| `brain_context_for_task` | 根据自然语言任务生成 Context Pack；默认异步返回 job，轮询 `brain_index_job_status` 获取结果，避免客户端超时。 |
| `brain_status` | 面向 AI 客户端的一站式能力检查：本地知识层、sidecar 图谱、隐私开关。 |
| `brain_sync_status` | 根据文件过滤快照判断项目是否需要重新索引。 |
| `brain_sync_project` | sync-trigger 式索引入口；默认异步排队，也可以设置 `async_mode=false` 同步执行。 |
| `brain_index_job_status` | 查看当前 MCP 进程内异步 job 状态、线程存活状态和运行时长。 |
| `brain_index_project` | 索引当前项目：可调用 `codebase-memory-mcp` 建图，同时索引 `.codebrain/conventions`；支持 `graph_mode` (`full` / `moderate` / `fast`) 和 `graph_persistence`。 |
| `brain_explain_symbol` | 解释函数、类或其它符号：组合图谱搜索、调用链追踪和团队约定搜索。 |

### 项目约定

| 工具 | 说明 |
| --- | --- |
| `add_convention` | 手动添加一条项目约定。 |
| `search_conventions` | 按任务描述检索已索引约定。 |
| `list_conventions` | 列出约定元信息。 |
| `index_convention_files` | 索引 `.codebrain/conventions` 下的 Markdown 约定文件。 |

### 会话记忆

| 工具 | 说明 |
| --- | --- |
| `start_session` | 开始一个轻量会话，并召回相似历史会话。 |
| `record_decision` | 记录关键实现或架构决策。 |
| `record_problem` | 记录遇到的问题和解决方案。 |
| `record_file_change` | 记录本次会话修改过的文件。 |
| `end_session` | 保存本次会话记忆。 |
| `recall_context` | 根据任务描述召回相似会话。 |

### Git 只读上下文

| 工具 | 说明 |
| --- | --- |
| `get_blame` | 读取文件某段代码的 Git blame 信息。 |
| `get_recent_changes` | 读取某个文件的最近提交记录。 |
| `get_co_changed_files` | 查找历史上经常和某文件一起修改的文件。 |

## 配置项

环境变量统一使用 `CODEBRAIN_` 前缀。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CODEBRAIN_EMBEDDER_PROVIDER` | `sentence-transformers` | 稳定版只支持本地 provider：`sentence-transformers` 或 `ollama`。 |
| `CODEBRAIN_EMBEDDER_MODEL` | `all-MiniLM-L6-v2` | 英文为主的小模型（384 维，约 90MB）。中文为主的约定推荐 `paraphrase-multilingual-MiniLM-L12-v2`（384 维，约 470MB）。 |
| `CODEBRAIN_OLLAMA_URL` | `http://localhost:11434` | 本机 Ollama embedding 服务地址；保持 localhost，除非团队明确批准内网服务。 |
| `CODEBRAIN_DB_PATH` | `.codebrain/codebrain.db` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` | `.codebrain/conventions` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_CONVENTION_QUALITY_KEYWORDS` | 空 | 逗号分隔的自定义低信号关键词；命中时 `index_convention_files` 返回 warning，不阻断入库。 |
| `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED` | `false` | 稳定版建议保持 false。 |
| `CODEBRAIN_VECTOR_STORE_BACKEND` | `sqlite` | 可选 `sqlite` 或 `milvus`；不显式设置时保持本地 SQLite。 |
| `CODEBRAIN_CODEBASE_MEMORY_BINARY` | `codebase-memory-mcp` | 可选图谱 sidecar 二进制路径。 |
| `CODEBRAIN_CODEBASE_MEMORY_TIMEOUT_SEC` | `120` | 调用图谱 sidecar 的超时时间。 |
| `CODEBRAIN_INDEX_MAX_FILE_SIZE_MB` | `5` | 文件过滤快照中纳入索引判断的单文件大小上限。 |
| `CODEBRAIN_MILVUS_URI` | `.codebrain/milvus_lite.db` | Milvus Lite 本地文件路径，或远程 Milvus / Zilliz URI。 |
| `CODEBRAIN_MILVUS_TOKEN` | 空 | 远程 Milvus / Zilliz 需要 token 时再设置。 |
| `CODEBRAIN_MILVUS_COLLECTION_PREFIX` | `codebrain` | Milvus collection 前缀，避免和已有 collection 冲突。 |

## 安全与信任

- Codebase Brain 会读取你提供的约定文件和 Git 元数据，并写入本地 SQLite 数据库。
- 默认数据库路径是 `.codebrain/codebrain.db`，团队仓库应该忽略这个数据库文件。
- 默认 embedding provider 是本地 `sentence-transformers`；可选 `ollama` 也必须指向本机或团队批准的内网服务。
- OpenAI / 云端 embedding provider 不在稳定版工具链中。
- Git 历史向量索引默认禁用；只有设置 `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED=true` 才注册 `index_git_history` 和 `search_history`。
- 当前没有自动安装脚本，也不会自动改写 Cursor、Qoder、Codex、OpenCode 等客户端配置。
- `codebase-memory-mcp` sidecar 由你本机安装和升级；Codebase Brain 只通过 CLI 调用它，不复制它的源码。
- `brain_sync_project` 的异步 job 是 MCP 进程内状态；MCP 服务重启后历史 job 列表不会保留，但 `.codebrain/index-state.json` 会保留最后一次索引快照。
- Dashboard 是本地只读页面，不是 Attu 代码，也不是 Milvus 管理台替代品。
- Milvus 后端是显式 opt-in；远程 Milvus/Zilliz 安装 `.[milvus]`，本机 Milvus Lite 安装 `.[milvus-lite]`。

## 与代码图谱型 MCP 的关系

像 [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) 这类项目更偏结构化代码图谱、索引速度、跨语言分析和自动客户端配置。Codebase Brain 的定位不是和它抢底层能力，而是把它接到一个更适合团队 AI 编程工作流的统一入口里。

当前取舍：

- 底层图谱：优先复用 `codebase-memory-mcp`。
- 团队知识：继续由 Codebase Brain 管理 `.codebrain/conventions`、会话记忆和 Git 只读上下文。
- AI 客户端体验：优先让 Cursor、Qoder、Codex、OpenCode、Hermes 等都只配置一个 `codebase-brain` MCP Server。
- 当前已有：只读本地 dashboard、文件过滤快照、sync-trigger 状态、异步索引 job。
- 后续增强：Claude Context 风格混合检索、远程 Milvus / Zilliz 运行手册、Attu 类管理体验和更完整的任务前上下文编排。

## Troubleshooting

| 问题 | 处理方式 |
| --- | --- |
| MCP 客户端看不到工具 | 检查 `command` 是否是绝对路径，重启客户端，再调用 `health`。 |
| 数据库写到错误目录 | 显式设置 `CODEBRAIN_DB_PATH` 为业务仓库下的绝对路径。 |
| `index_convention_files` 找不到文件 | 设置 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH`，或调用工具时传绝对路径。 |
| dashboard 打不开 | 确认 `codebrain dashboard` 进程还在运行，或换一个未被占用的端口。 |
| `brain_sync_status` 总是需要同步 | 检查是否有生成文件未被过滤；可传 `exclude_patterns` 增加忽略规则。 |
| 设置 `CODEBRAIN_VECTOR_STORE_BACKEND=milvus` 后启动失败 | 远程 Milvus/Zilliz 先安装 `.venv/bin/python -m pip install -e ".[milvus]"`；本地 Milvus Lite 安装 `.venv/bin/python -m pip install -e ".[milvus-lite]"`，并确认 `CODEBRAIN_MILVUS_URI` 指向可写本地路径或可访问的远程 Milvus。 |
| 首次安装下载超过 2GB | `.[local]` 依赖 PyTorch + CUDA 相关 wheel 时体积可能很大，属于正常现象。安装完成后 `.venv/` 可能占用约 3-4GB。 |
| 第一次启动慢 | `sentence-transformers` 第一次加载或下载模型会比较慢。 |
| 不想任何文本离开本机 | 使用默认 `sentence-transformers`；不要配置远程 Milvus/Zilliz 或远程 Ollama URL。 |

## 开发与测试

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

当前稳定分支是 `main`。原实验版保存在 `dev` 分支。
