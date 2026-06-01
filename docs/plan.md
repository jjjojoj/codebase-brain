# Codebase Brain — Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement task-by-task.

**Goal:** 3 个互补 MCP Server，与 codebase-memory-mcp 配合，覆盖 AI 编程在大型项目中的全部 7 个痛点。

**Architecture:**
```
codebase-brain/
├── packages/
│   ├── core/                    # 共享库
│   │   ├── milvus_client.py     # Milvus Lite 向量库封装
│   │   ├── embedder.py          # Ollama embedding (bge-m3)
│   │   ├── config.py            # 统一配置管理
│   │   └── mcp_base.py          # MCP Server 基类
│   ├── conventions-mcp/         # 痛点7: 约定知识库
│   ├── session-memory-mcp/      # 痛点5: 会话记忆
│   └── history-mcp/             # 痛点6: 历史深度索引
├── tests/
├── pyproject.toml
└── AGENTS.md
```

**Tech Stack:** Python 3.12, FastMCP, Milvus Lite, Ollama bge-m3, SentenceTransformers

---

## Task 0: 项目初始化 + 核心库

### Task 0.1: 创建项目骨架

**Objective:** 创建 monorepo 项目结构

**Files:**
- Create: `~/codebase-brain/pyproject.toml`
- Create: `~/codebase-brain/packages/core/__init__.py`
- Create: `~/codebase-brain/packages/conventions-mcp/__init__.py`
- Create: `~/codebase-brain/packages/session-memory-mcp/__init__.py`
- Create: `~/codebase-brain/packages/history-mcp/__init__.py`
- Create: `~/codebase-brain/AGENTS.md`

**Step 1: Initialize git repo**
```bash
mkdir -p ~/codebase-brain && cd ~/codebase-brain && git init
```

**Step 2: Create pyproject.toml**
```toml
[project]
name = "codebase-brain"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0.0",
    "pymilvus>=2.4.0",
    "sentence-transformers>=3.0.0",
    "pyyaml>=6.0",
]

[project.scripts]
conventions-mcp = "conventions_mcp.server:main"
session-memory-mcp = "session_memory_mcp.server:main"
history-mcp = "history_mcp.server:main"
```

**Step 3: Create AGENTS.md**
- 写清楚 3 个 MCP server 的分工和触发条件

**Step 4: Commit**
```bash
git add . && git commit -m "init: codebase-brain monorepo skeleton"
```

---

### Task 0.2: Milvus Lite 封装 + 配置管理

**Objective:** 共享的向量库客户端和配置系统

**Files:**
- Create: `~/codebase-brain/packages/core/config.py`
- Create: `~/codebase-brain/packages/core/milvus_client.py`

**config.py 要点:**
- MILVUS_DB_PATH: `~/.codebrain/milvus.db` (Milvus Lite 嵌入式)
- EMBEDDING_MODEL: `BAAI/bge-m3` (via Ollama)
- OLLAMA_HOST: `http://localhost:11434`
- 三个 Collection 定义:
  - `conventions` — dim=1024, fields: id, module, content, embedding, created_at
  - `session_memory` — dim=1024, fields: id, task, files_modified, decisions, assumptions, problems, embedding, created_at
  - `git_history` — dim=1024, fields: id, file_path, commit_hash, commit_msg, author, date, code_snippet, embedding

**milvus_client.py 要点:**
- `init_collections()` — 创建/加载三个 collection
- `insert_convention(module, content, embedding)`
- `search_conventions(query_embedding, top_k=5)`
- `insert_session(task_summary, files, decisions, ...)`
- `search_sessions(query_embedding, top_k=5)`
- `insert_git_entry(file, commit, msg, snippet, ...)`
- `search_history(query_embedding, top_k=10)`

---

### Task 0.3: Embedding 封装 + MCP 基类

**Objective:** 统一的 embedding 生成和 MCP Server 模板

**Files:**
- Create: `~/codebase-brain/packages/core/embedder.py`
- Create: `~/codebase-brain/packages/core/mcp_base.py`

**embedder.py 要点:**
- `class Embedder`: 封装 SentenceTransformer，支持 bge-m3
- `embed(text) -> list[float]`
- `embed_batch(texts) -> list[list[float]]`

**mcp_base.py 要点:**
- `class BrainMCP`: FastMCP 的包装
- 统一日志、错误处理、健康检查
- 自动初始化 Milvus collections

---

## Task 1: conventions-mcp

### Task 1.1: 核心功能 — 约定文件索引

**Objective:** 索引 `.codebrain/conventions/*.md` 文件到 Milvus

**Files:**
- Create: `~/codebase-brain/packages/conventions-mcp/server.py`
- Create: `~/codebase-brain/packages/conventions-mcp/indexer.py`

**MCP Tools:**
1. `add_convention(module, title, content)` — 添加一条约定
2. `search_conventions(query, module_filter=None)` — 语义搜索约定
3. `list_conventions(module=None)` — 列出所有约定
4. `suggest_convention(module, context)` — AI 根据上下文建议约定（未来功能）

**indexer.py 要点:**
- 扫描 `.codebrain/conventions/` 目录
- 解析 Markdown 文件（frontmatter: module, title, tags）
- 分块 → embed → 存入 Milvus `conventions` collection

---

### Task 1.2: 约定文件模板 + 自动扫描

**Objective:** 提供默认约定模板，项目启动时自动索引

**Files:**
- Create: `~/codebase-brain/packages/conventions-mcp/templates/error-handling.md`
- Create: `~/codebase-brain/packages/conventions-mcp/templates/testing.md`
- Create: `~/codebase-brain/packages/conventions-mcp/templates/code-style.md`

**行为:**
- 首次运行时如果 `.codebrain/conventions/` 为空，复制模板
- 文件变更时自动增量索引（watchdog）

---

## Task 2: session-memory-mcp

### Task 2.1: 会话记录 + 召回

**Objective:** AI 编程会话开始/结束时自动记录和召回上下文

**Files:**
- Create: `~/codebase-brain/packages/session-memory-mcp/server.py`

**MCP Tools:**
1. `start_session(task_description)` — 开始新会话，自动召回相关历史
2. `record_decision(decision, reason)` — 记录一个决策
3. `record_problem(problem, solution, file)` — 记录遇到的问题和解决方案
4. `end_session(summary)` — 结束会话，保存摘要
5. `recall_context(task_description)` — 根据当前任务召回相关历史会话

**实现要点:**
- 每个 session 有一个唯一 ID
- 会话摘要包括：任务、改动的文件、关键决策、假设、遇到的问题
- 召回时用向量搜索找到语义相似的过往会话

---

## Task 3: history-mcp

### Task 3.1: Git 历史索引

**Objective:** 索引 git log/blame 信息，让 AI 理解代码的修改历史

**Files:**
- Create: `~/codebase-brain/packages/history-mcp/server.py`
- Create: `~/codebase-brain/packages/history-mcp/git_indexer.py`

**MCP Tools:**
1. `search_history(query, file_filter=None)` — 语义搜索 git 历史
2. `get_blame(file_path, start_line, end_line)` — 查看代码的修改者和时间
3. `get_co_changed_files(file_path)` — 查看历史上与该文件经常一起修改的文件
4. `get_recent_changes(file_path, limit=10)` — 查看文件的最近变更

**git_indexer.py 要点:**
- 解析 `git log --all --name-only --pretty=format:"%H|%an|%ad|%s"`
- 每个 commit 的 message + changed files → 向量化
- 解析 `git blame` 信息
- 统计文件共修改频率

---

## Task 4: 集成 + 测试

### Task 4.1: 单元测试

**Files:**
- Create: `~/codebase-brain/tests/test_core.py`
- Create: `~/codebase-brain/tests/test_conventions.py`
- Create: `~/codebase-brain/tests/test_session_memory.py`
- Create: `~/codebase-brain/tests/test_history.py`

### Task 4.2: 集成测试 — 与 codebase-memory-mcp 并列运行

**验证:**
```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "/home/user/.local/bin/codebase-memory-mcp",
      "args": []
    },
    "codebase-brain-conventions": {
      "command": "python3",
      "args": ["-m", "conventions_mcp.server"]
    },
    "codebase-brain-session": {
      "command": "python3",
      "args": ["-m", "session_memory_mcp.server"]
    },
    "codebase-brain-history": {
      "command": "python3",
      "args": ["-m", "history_mcp.server"]
    }
  }
}
```

---

## Task 5: 推送到 GitHub

```bash
git remote add origin git@github.com:jjjojoj/codebase-brain.git
git push -u origin main
```

---

## 注意事项

1. **Milvus Lite vs Standalone**: 先用 Milvus Lite（嵌入式，无依赖），后续可选升级到 Docker Standalone
2. **Embedding 模型**: 优先用 `BAAI/bge-m3`（中文友好，1024维），备用 `nomic-embed-text`（via Ollama）
3. **与 codebase-memory-mcp 分工**: codebase-memory 做结构（图），我们做知识（向量）
4. **MCP 协议**: 所有 Server 使用 stdio transport，通过 `mcp` Python 包实现
