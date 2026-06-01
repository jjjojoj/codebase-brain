<p align="center">
  <h1 align="center">🧠 Codebase Brain</h1>
  <p align="center"><b>AI 编程工具的大型项目增强方案</b></p>
  <p align="center">让 AI 理解项目约定 · 记住会话上下文 · 追溯历史决策</p>
</p>

# Codebase Brain

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](https://modelcontextprotocol.io)
[![Milvus](https://img.shields.io/badge/Milvus-Lite-orange)](https://milvus.io)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Platform](https://img.shields.io/badge/Windows%20%7C%20Linux%20%7C%20macOS-supported-lightgrey)]()

> 3 个 MCP Server + codebase-memory-mcp，覆盖 AI 编程在大型项目中的全部 7 个核心痛点。

---

## 解决的问题

使用 AI 编程工具（Qoder / Windsurf / Codex / Claude Code / OpenCode / Cursor）开发大型项目时，AI 面临七个核心问题：

| # | 痛点 | 症状 | 本项目如何解决 |
|---|------|------|--------------|
| 1 | 上下文压缩返工 | AI 看不到全貌，输出的代码需要反复改 | `search_graph` 精确定位 |
| 2 | AI 动了不该动的代码 | 改一个函数，附带改了无关逻辑 | `get_architecture` 模块边界 |
| 3 | 修改影响面不可知 | 改了底层，上层崩溃 | `trace_path` 调用链追踪 |
| 4 | 盲人摸象 | AI 只看到局部，不理解整体架构 | `get_architecture` 全景 |
| 5 | 长链条任务走丢 | 改到第 4 个文件时忘了最初的需求 | **session-memory-mcp** ← 新增 |
| 6 | 历史决策不可见 | "这段代码为什么这么写？"无从查证 | **history-mcp** ← 新增 |
| 7 | 隐式约定缺失 | 项目规范在开发者脑子里，不在代码里 | **conventions-mcp** ← 新增 |

痛点 1-4 由 [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) 覆盖。
痛点 5-7 由本项目新增的 3 个 MCP Server 覆盖。

---

## 架构

```
┌──────────────────────────────────────────────────┐
│          AI 编程工具 (Qoder/Windsurf/Cursor/...)   │
│              MCP 协议 (JSON-RPC over stdio)        │
└────────┬──────────┬──────────┬───────────────────┘
         │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
    │convent-│ │session-│ │history │  ← codebase-brain (知识层)
    │ions-mcp│ │memory  │ │-mcp    │
    │ 痛点7  │ │ 痛点5  │ │ 痛点6  │
    └───┬────┘ └───┬────┘ └───┬────┘
        │          │          │
    ┌───▼──────────▼──────────▼────┐
    │     Milvus Lite (嵌入式)      │  ← 向量数据库
    │   ~/.codebrain/milvus.db    │
    └─────────────────────────────┘
    
    ┌──────────────────────────────┐
    │  codebase-memory-mcp          │  ← 结构层 (开箱即用)
    │  14 tools · 155 语言 · 纯 C  │
    │  SQLite 知识图谱              │
    └──────────────────────────────┘
```

- **知识层和结构层分离** — codebase-brain 负责"项目知识"，codebase-memory-mcp 负责"代码结构"
- **向量 + 图互补** — Milvus 存语义知识，SQLite 存代码图谱
- **模块独立** — 4 个 MCP 各司其职，可按需启用，独立升级
- **跨平台** — 支持 Windows / Linux / macOS

---

## 借鉴项目

| 项目 | Stars | 借鉴了什么 |
|------|:---:|-----------|
| [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | 1.4K | 代码结构索引底座，直接部署使用 |
| [claude-context](https://github.com/zilliztech/claude-context) | 11.6K | 混合搜索(BM25+向量RRF)、多Provider Embedder、文件监听触发同步 |
| [codebase-context](https://github.com/PatrickSys/codebase-context) | — | 约定模式频率检测思路 |

---

## 快速开始

### 1. 安装 Python 依赖

```bash
# Windows (PowerShell)
git clone https://github.com/jjjojoj/codebase-brain.git C:\codebase-brain
cd C:\codebase-brain
python -m venv .venv
.venv\Scripts\pip install mcp "pymilvus[milvus_lite]" sentence-transformers pyyaml openai httpx

# Linux / macOS / WSL
git clone https://github.com/jjjojoj/codebase-brain.git ~/codebase-brain
cd ~/codebase-brain
python3 -m venv .venv
.venv/bin/pip install mcp "pymilvus[milvus_lite]" sentence-transformers pyyaml openai httpx
```

### 2. 下载 codebase-memory-mcp

从 [Releases](https://github.com/DeusData/codebase-memory-mcp/releases/latest) 下载对应平台的二进制，放到 PATH 或固定路径。

### 3. 配置 AI 编程工具

将下面的 JSON 添加到工具的 MCP 设置中。

---

## MCP 配置（Windows 原生 / Qoder / Windsurf / Cursor）

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "C:\\codebase-memory\\codebase-memory-mcp.exe",
      "args": []
    },
    "conventions": {
      "command": "C:\\codebase-brain\\.venv\\Scripts\\python.exe",
      "args": ["-c", "import sys; sys.path.insert(0,'C:\\codebase-brain\\packages'); from conventions_mcp.server import main; main()"]
    },
    "session-memory": {
      "command": "C:\\codebase-brain\\.venv\\Scripts\\python.exe",
      "args": ["-c", "import sys; sys.path.insert(0,'C:\\codebase-brain\\packages'); from session_memory_mcp.server import main; main()"]
    },
    "history": {
      "command": "C:\\codebase-brain\\.venv\\Scripts\\python.exe",
      "args": ["-c", "import sys; sys.path.insert(0,'C:\\codebase-brain\\packages'); from history_mcp.server import main; main()"]
    }
  }
}
```

> **提示**：如果你把 `codebase-memory-mcp.exe` 和 `python.exe` 加入了系统 PATH，`command` 可以直接写 `codebase-memory-mcp` 和 `python`，路径更简洁。

<details>
<summary>WSL / Linux / macOS 配置</summary>

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "/home/user/.local/bin/codebase-memory-mcp",
      "args": []
    },
    "conventions": {
      "command": "/home/user/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from conventions_mcp.server import main; main()"]
    },
    "session-memory": {
      "command": "/home/user/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from session_memory_mcp.server import main; main()"]
    },
    "history": {
      "command": "/home/user/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from history_mcp.server import main; main()"]
    }
  }
}
```
</details>

<details>
<summary>Windows 通过 WSL 桥接</summary>

如果 codebase-brain 部署在 WSL 内、AI 工具在 Windows 上运行：

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "wsl",
      "args": ["-e", "/home/user/.local/bin/codebase-memory-mcp"]
    },
    "conventions": {
      "command": "wsl",
      "args": ["-e", "/home/user/codebase-brain/.venv/bin/python3", "-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from conventions_mcp.server import main; main()"]
    },
    "session-memory": {
      "command": "wsl",
      "args": ["-e", "/home/user/codebase-brain/.venv/bin/python3", "-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from session_memory_mcp.server import main; main()"]
    },
    "history": {
      "command": "wsl",
      "args": ["-e", "/home/user/codebase-brain/.venv/bin/python3", "-c", "import sys; sys.path.insert(0,'/home/user/codebase-brain/packages'); from history_mcp.server import main; main()"]
    }
  }
}
```
</details>

---

## 首次使用四步走

```
1. 索引代码  → 在 AI 工具里说："用 index_repository 索引这个项目"
2. 创建约定  → mkdir .codebrain\conventions\ ，写约定 .md 文件
3. 索引约定  → "用 index_convention_files 索引约定文件"
4. 索引历史  → "用 index_git_history 索引最近 500 个提交"
```

---

## 目录结构

```
codebase-brain/
├── packages/
│   ├── core/                        共享库 (1027行)
│   │   ├── config.py                单例配置，自动检测 Embedding Provider
│   │   ├── embedder.py              策略模式: sentence-transformers/Ollama/OpenAI
│   │   ├── milvus_client.py         Milvus Lite + 混合搜索 (BM25+向量 RRF 融合)
│   │   └── mcp_base.py             FastMCP 基类 + sync-trigger 文件监听
│   │
│   ├── conventions_mcp/             痛点7: 约定知识库 (245行)
│   │   ├── server.py                4 tools: add/search/list/index
│   │   └── templates/               3套中文约定模板
│   │
│   ├── session_memory_mcp/          痛点5: 会话记忆 (233行)
│   │   └── server.py                6 tools: start/record/end/recall
│   │
│   └── history_mcp/                 痛点6: 历史索引 (467行)
│       ├── server.py                5 tools: search/blame/co-changed
│       └── git_indexer.py           git log/blame 解析引擎
│
├── docs/plan.md                     完整实施计划
├── docs/使用文档.md                  详细使用手册
├── AGENTS.md                        AI 工具自动调用规则
└── pyproject.toml
```

---

## 14 个 MCP 工具

### conventions-mcp（痛点7：约定知识库）
| 工具 | 用途 |
|------|------|
| `add_convention(module, title, content)` | 添加一条约定 |
| `search_conventions(query, keywords, module_filter)` | 混合搜索（BM25+向量） |
| `list_conventions(module)` | 列出所有约定 |
| `index_convention_files(path)` | 批量索引 `.md` 约定文件 |

### session-memory-mcp（痛点5：会话记忆）
| 工具 | 用途 |
|------|------|
| `start_session(task)` | 开始会话 + 自动召回相似历史 |
| `record_decision(decision, reason)` | 记录关键决策 |
| `record_problem(problem, solution, files)` | 记录遇到的问题和解决方案 |
| `record_file_change(file, type, desc)` | 记录文件变更及原因 |
| `end_session(summary)` | 结束会话 + 向量化持久化 |
| `recall_context(task, top_k)` | 召回语义相似的历史会话 |

### history-mcp（痛点6：历史决策）
| 工具 | 用途 |
|------|------|
| `search_history(query, file_filter)` | 语义搜索 git 提交历史 |
| `get_blame(file, start, end)` | 查看代码的作者和修改时间 |
| `get_co_changed_files(file)` | 历史上经常一起修改的文件 |
| `get_recent_changes(file, limit)` | 文件的最近变更记录 |
| `index_git_history(repo_path, max_commits)` | 索引 git log 到向量库 |

---

## 设计原则

1. **模块独立** — 4 个 MCP 各自独立，按需启用，独立升级
2. **知识层与结构层分离** — 代码结构用图（SQLite），项目知识用向量（Milvus）
3. **本地优先** — 默认 sentence-transformers + Milvus Lite，零外部依赖，不上传数据
4. **跨平台** — Python 3.12+，支持 Windows / Linux / macOS
5. **渐进增强** — 从 conventions-mcp 开始，逐步加入 session/history
6. **中文友好** — bge-m3 模型 + 中文约定模板 + 完整中文文档

---

## 常见问题

**Q: 必须全部部署吗？**
A: 不需要。每个 MCP 独立运行，可按需启用。建议从 conventions-mcp 开始。

**Q: 数据安全吗？**
A: 完全本地。数据存在 `~/.codebrain/milvus.db`（Windows 上为 `C:\Users\<用户名>\.codebrain\milvus.db`），不上传任何数据。

**Q: 支持中文吗？**
A: 完全支持。bge-m3 模型中文友好，约定模板也是中文。

**Q: 和 codebase-memory-mcp 冲突吗？**
A: 不冲突。codebase-memory 做代码结构（图），codebase-brain 做项目知识（向量）。

**Q: 需要 GPU 吗？**
A: 不需要。sentence-transformers 在 CPU 上运行 bge-m3 完全够用。

**Q: 约定文件放哪里？**
A: 项目根目录的 `.codebrain/conventions/`，Markdown 格式，带 YAML frontmatter。

**Q: 怎么验证是否正常工作？**
A: 在 AI 工具里说"用 health 检查服务状态"，应返回 `{"ok": true, "milvus": true}`。

---

## 文档

- [完整使用文档](docs/使用文档.md)
- [实施计划](docs/plan.md)

---

<p align="center">
  <sub>MIT License · Made for developers who code with AI</sub>
</p>
