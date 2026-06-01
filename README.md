<p align="center">
  <h1 align="center">🧠 Codebase Brain</h1>
  <p align="center"><b>AI 编程工具的大型项目增强方案</b></p>
  <p align="center">让 AI 理解项目约定 · 记住会话上下文 · 追溯历史决策</p>
</p>

# Codebase Brain

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](https://modelcontextprotocol.io)
[![Milvus](https://img.shields.io/badge/Milvus-Lite-orange)](https://milvus.io)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> 3 个 MCP Server + codebase-memory-mcp，覆盖 AI 编程在大型项目中的全部 7 个核心痛点。

---

## 解决的问题

使用 AI 编程工具（Qoder / Windsurf / Codex / Claude Code / OpenCode）开发大型项目时，AI 面临七个核心问题：

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
│           AI 编程工具 (Qoder/Windsurf/Codex/...)   │
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
    │  ~/.codebrain/milvus.db     │
    └─────────────────────────────┘
    
    ┌──────────────────────────────┐
    │   codebase-memory-mcp        │  ← 结构层 (开箱即用)
    │   14 tools · 155 语言        │
    │   SQLite 知识图谱            │
    └──────────────────────────────┘
```

- **知识层和结构层分离** — codebase-brain 负责"项目知识"，codebase-memory-mcp 负责"代码结构"
- **向量 + 图互补** — Milvus 存语义知识（约定/会话/历史），SQLite 存代码图谱（函数/调用/依赖）
- **模块独立** — 4 个 MCP 各司其职，可按需启用，独立升级

---

## 借鉴项目

| 项目 | Stars | 借鉴了什么 |
|------|:---:|-----------|
| [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | 1.4K | 代码结构索引底座，直接部署使用 |
| [claude-context](https://github.com/zilliztech/claude-context) | 11.6K | 混合搜索(BM25+向量RRF)、多Provider Embedder、文件监听触发同步 |
| [codebase-context](https://github.com/PatrickSys/codebase-context) | — | 约定模式频率检测思路 |

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/jjjojoj/codebase-brain.git ~/codebase-brain
cd ~/codebase-brain

# 2. 安装依赖（首次约 2-3 分钟）
python3 -m venv .venv
.venv/bin/pip install mcp "pymilvus[milvus_lite]" sentence-transformers pyyaml openai httpx

# 3. 配置 AI 编程工具（WSL 内直连）
# 将下面的 JSON 添加到 Qoder/Windsurf 的 MCP 设置中
```

## MCP 配置

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "/home/zkys/.local/bin/codebase-memory-mcp",
      "args": []
    },
    "conventions": {
      "command": "/home/zkys/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/zkys/codebase-brain/packages'); from conventions_mcp.server import main; main()"]
    },
    "session-memory": {
      "command": "/home/zkys/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/zkys/codebase-brain/packages'); from session_memory_mcp.server import main; main()"]
    },
    "history": {
      "command": "/home/zkys/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'/home/zkys/codebase-brain/packages'); from history_mcp.server import main; main()"]
    }
  }
}
```

## 首次使用

```
1. 索引代码："用 index_repository 索引项目"              ← codebase-memory
2. 创建约定：mkdir .codebrain/conventions/，写 .md 约定文件
3. 索引约定："用 index_convention_files 索引约定文件"    ← conventions-mcp
4. 索引历史："用 index_git_history 索引最近 500 个提交"  ← history-mcp
```

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
├── AGENTS.md                        AI 工具自动调用规则
└── pyproject.toml
```

## 14 个 MCP 工具

### conventions-mcp (4)
| 工具 | 用途 |
|------|------|
| `add_convention(module, title, content)` | 添加约定 |
| `search_conventions(query, keywords, module_filter)` | 混合搜索 (BM25+向量) |
| `list_conventions(module)` | 列出所有约定 |
| `index_convention_files(path)` | 批量索引 `.md` 约定文件 |

### session-memory-mcp (6)
| 工具 | 用途 |
|------|------|
| `start_session(task)` | 开始会话 + 召回历史 |
| `record_decision(decision, reason)` | 记录决策 |
| `record_problem(problem, solution, files)` | 记录问题和解决方案 |
| `record_file_change(file, type, desc)` | 记录文件变更 |
| `end_session(summary)` | 结束会话 + 向量化存储 |
| `recall_context(task, top_k)` | 召回相似历史会话 |

### history-mcp (5)
| 工具 | 用途 |
|------|------|
| `search_history(query, file_filter)` | 语义搜索 git 历史 |
| `get_blame(file, start, end)` | 查看代码作者和修改时间 |
| `get_co_changed_files(file)` | 经常一起修改的文件 |
| `get_recent_changes(file, limit)` | 文件最近变更 |
| `index_git_history(repo_path, max_commits)` | 索引 git log |

## 设计原则

1. **模块独立** — 4 个 MCP 各自独立，按需启用，独立升级
2. **知识层与结构层分离** — 代码结构用图（SQLite），项目知识用向量（Milvus）
3. **本地优先** — 默认 sentence-transformers + Milvus Lite，零外部依赖
4. **渐进增强** — 可以从 conventions-mcp 开始，逐步加入 session/history
5. **可复现** — embedding 模型、搜索参数可配置，结果可追溯
6. **中文友好** — bge-m3 模型 + 中文约定模板，完整中文文档

## 常见问题

**Q: 必须全部部署吗？**
A: 不需要。每个 MCP 独立运行，可按需启用。

**Q: 数据安全吗？**
A: 完全本地。`~/.codebrain/milvus.db`，不上传任何数据。

**Q: 支持中文吗？**
A: 完全支持。bge-m3 中文友好，约定模板也是中文。

**Q: 和 codebase-memory-mcp 冲突吗？**
A: 不冲突。codebase-memory 做代码结构（图），codebase-brain 做项目知识（向量）。

## 文档

完整使用文档见 [Codebase-Brain-使用文档.md](docs/使用文档.md)

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/jjjojoj">jjjojoj</a></sub>
</p>
