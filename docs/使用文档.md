<p align="center">
  <img src="" width="120" alt="Codebase Brain" />
  <h1 align="center">🧠 Codebase Brain</h1>
  <p align="center"><b>AI 编程工具的大型项目增强 MCP 方案</b></p>
  <p align="center">
    让 AI 理解项目约定 · 记住会话上下文 · 追溯历史决策
  </p>
</p>

<p align="center">
  <a href="https://github.com/jjjojoj/codebase-brain/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python" /></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-1.0+-green.svg" alt="MCP" /></a>
  <a href="https://milvus.io"><img src="https://img.shields.io/badge/Milvus-Lite-orange.svg" alt="Milvus" /></a>
  <br/>
  <a href="https://github.com/DeusData/codebase-memory-mcp"><img src="https://img.shields.io/badge/codebase--memory--mcp-v0.7.0-purple" alt="codebase-memory-mcp" /></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/tools-14-orange" alt="Tools" />
</p>

---

> 🆕 **codebase-memory-mcp 已部署？** Codebase Brain 是它的互补方案 — 它做代码结构（图），我们做项目知识（向量）。配合使用覆盖 AI 编程在大型项目中的全部 7 个核心痛点。

## 你的整个项目就是 AI 的上下文

**Codebase Brain** 是一套 MCP Server 方案，让 AI 编程工具（Qoder / Windsurf / Cursor / Claude Code / Codex CLI / OpenCode）在大型项目中不只是"搜索代码"，而是真正"理解项目"。

🧠 **项目约定不再靠人传人** — 把团队的编码规范写成 Markdown 约定文件，AI 修改代码前自动检索对应约定。新人不再需要反复问"这个模块怎么处理错误"。

📝 **跨会话记忆** — AI 每次对话都从零开始？Codebase Brain 记住上次改了什么、为什么那么改、遇到了什么坑。下次接手相关任务时自动召回。

📜 **历史决策可追溯** — "这段代码为什么这么写？"答案在 3 年前的 PR 讨论里。Codebase Brain 索引 git 历史和架构决策，AI 改代码前先了解历史背景。

💰 **Token 节省** — 不需要把所有代码塞进上下文。语义搜索 + 混合检索（BM25+向量），只在需要时精准获取相关信息。

---

## 🚀 快速开始

### 前提条件

<details>
<summary><b>1. 安装 codebase-memory-mcp（代码结构层）</b></summary>

从 [Releases](https://github.com/DeusData/codebase-memory-mcp/releases/latest) 下载对应平台的二进制：
- Windows: `codebase-memory-mcp-windows-amd64.zip`
- Linux: `codebase-memory-mcp-linux-amd64.tar.gz`
- macOS: `codebase-memory-mcp-darwin-arm64.tar.gz`

解压后将二进制放到固定路径（如 `C:\codebase-memory\` 或 `/usr/local/bin/`）。

</details>

<details>
<summary><b>2. Python 3.12+ 环境</b></summary>

```bash
# 确认版本
python --version  # 需要 3.12+
```
</details>

### 安装 Codebase Brain

**Windows (PowerShell):**
```powershell
git clone https://github.com/jjjojoj/codebase-brain.git C:\codebase-brain
cd C:\codebase-brain
python -m venv .venv
.venv\Scripts\pip install mcp "pymilvus[milvus_lite]" sentence-transformers pyyaml openai httpx
```

**Linux / macOS / WSL:**
```bash
git clone https://github.com/jjjojoj/codebase-brain.git ~/codebase-brain
cd ~/codebase-brain
python3 -m venv .venv
.venv/bin/pip install mcp "pymilvus[milvus_lite]" sentence-transformers pyyaml openai httpx
```

> 💡 **首次运行提示**：bge-m3 模型约 2GB，首次自动下载需 1-2 分钟，之后秒启动。

---

## 🔌 MCP 配置

### Windows（Qoder / Windsurf / Cursor）

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

> 如果 `python.exe` 已加入系统 PATH，`command` 可简化成 `"python"`。

<details>
<summary><b>Linux / macOS 配置</b></summary>

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "/usr/local/bin/codebase-memory-mcp",
      "args": []
    },
    "conventions": {
      "command": "~/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'~/codebase-brain/packages'); from conventions_mcp.server import main; main()"]
    },
    "session-memory": {
      "command": "~/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'~/codebase-brain/packages'); from session_memory_mcp.server import main; main()"]
    },
    "history": {
      "command": "~/codebase-brain/.venv/bin/python3",
      "args": ["-c", "import sys; sys.path.insert(0,'~/codebase-brain/packages'); from history_mcp.server import main; main()"]
    }
  }
}
```
</details>

<details>
<summary><b>WSL 桥接（Windows 工具 + WSL 内部署）</b></summary>

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
    }
  }
}
```
</details>

### 首次使用

在 AI 编程工具中依次执行：

```
1. "用 index_repository 索引这个项目"
2. 创建 .codebrain/conventions/ 目录，写约定 .md 文件
3. "用 index_convention_files 索引约定文件"
4. "用 index_git_history 索引最近 500 个提交"
```

---

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────────┐
│            AI 编程工具 (Qoder/Windsurf/Cursor/...)         │
│                MCP 协议 (JSON-RPC over stdio)              │
└──────┬──────────────┬──────────────┬─────────────────────┘
       │              │              │
  ┌────▼─────┐  ┌─────▼─────┐  ┌────▼─────┐
  │ convent- │  │ session-  │  │ history  │  ← codebase-brain
  │ ions-mcp │  │ memory    │  │ -mcp     │     (知识层 · 向量)
  │  痛点7   │  │  痛点5    │  │  痛点6   │
  └────┬─────┘  └─────┬─────┘  └────┬─────┘
       │              │              │
  ┌────▼──────────────▼──────────────▼────┐
  │         Milvus Lite (嵌入式)           │
  │     ~/.codebrain/milvus.db           │
  └───────────────────────────────────────┘

  ┌───────────────────────────────────────┐
  │     codebase-memory-mcp               │  ← 结构层 · 图
  │     14 tools · 155 语言 · 纯 C       │
  │     SQLite 知识图谱                   │
  └───────────────────────────────────────┘
```

### 设计原则

- **分层解耦**：代码结构用图（SQLite），项目知识用向量（Milvus），各司其职
- **模块独立**：4 个 MCP Server 各自独立启动、独立配置、独立升级
- **渐进增强**：从 conventions-mcp 开始，逐步加入 session-memory 和 history
- **本地优先**：默认零外部依赖，不上传任何数据
- **跨平台**：Python 3.12+，Windows / Linux / macOS 全支持

---

## 📦 项目结构

```
codebase-brain/
├── packages/
│   ├── core/                        共享库 (1027 行)
│   │   ├── config.py                单例配置 · 自动检测 Provider
│   │   ├── embedder.py              策略模式：sentence-transformers | Ollama | OpenAI
│   │   ├── milvus_client.py         Milvus Lite · 混合搜索 (BM25 + 向量 RRF)
│   │   └── mcp_base.py             FastMCP 基类 · sync-trigger 文件监听
│   │
│   ├── conventions_mcp/             约定知识库 (245 行)
│   │   ├── server.py                4 tools
│   │   └── templates/               3 套中文约定模板
│   │
│   ├── session_memory_mcp/          会话记忆 (233 行)
│   │   └── server.py                6 tools
│   │
│   └── history_mcp/                 Git 历史索引 (467 行)
│       ├── server.py                5 tools
│       └── git_indexer.py           git log / blame 解析引擎
│
├── docs/
│   ├── plan.md                      完整实施计划
│   └── 使用文档.md                   详细使用手册
├── AGENTS.md                        AI 工具自动调用规则
├── pyproject.toml
└── README.md
```

---

## 🛠️ MCP 工具

### conventions-mcp — 约定知识库

解决痛点：隐式约定在开发者脑子里，AI 不知道项目规范。

| 工具 | 参数 | 说明 |
|------|------|------|
| `add_convention` | `module`, `title`, `content` | 添加一条约定到知识库 |
| `search_conventions` | `query`, `keywords?`, `module_filter?`, `top_k?` | 混合搜索（BM25+向量 RRF 融合） |
| `list_conventions` | `module?` | 列出所有约定，可选按模块过滤 |
| `index_convention_files` | `path?` | 扫描 `.codebrain/conventions/` 并批量索引 |

**约定文件格式** (`.codebrain/conventions/*.md`)：
```yaml
---
module: auth
title: 认证模块错误处理约定
tags: [error-handling, auth]
---

所有认证相关函数必须返回 AuthError 类型，不允许直接返回 error。
```

### session-memory-mcp — 会话记忆

解决痛点：长链条任务 AI 会"走丢"，每次对话从零开始。

| 工具 | 参数 | 说明 |
|------|------|------|
| `start_session` | `task_description` | 开始新会话，自动召回相似历史会话 |
| `record_decision` | `decision`, `reason?` | 记录一个关键决策 |
| `record_problem` | `problem`, `solution`, `files?` | 记录遇到的问题和解决方案 |
| `record_file_change` | `file_path`, `change_type`, `description` | 记录文件变更 |
| `end_session` | `summary?` | 结束会话，向量化存储全文摘要 |
| `recall_context` | `task_description`, `top_k?` | 召回语义相似的历史会话 |

### history-mcp — Git 历史索引

解决痛点：代码的历史决策不可见，"这段代码为什么这么写"无从查证。

| 工具 | 参数 | 说明 |
|------|------|------|
| `search_history` | `query`, `file_filter?`, `top_k?` | 语义搜索 git 提交历史 |
| `get_blame` | `file_path`, `start_line`, `end_line` | 查看代码的作者和修改时间 |
| `get_co_changed_files` | `file_path`, `limit?` | 历史上常与该文件一起修改的文件 |
| `get_recent_changes` | `file_path`, `limit?` | 文件的最近变更记录 |
| `index_git_history` | `repo_path?`, `max_commits?` | 索引 git log 到向量库 |

---

## 🔧 配置选项

### Embedding Provider

通过环境变量切换不同的 Embedding 模型：

```bash
# 方案 1：本地 CPU（默认，零外部依赖）
# 无需设置，自动使用 sentence-transformers + BAAI/bge-m3

# 方案 2：本地 Ollama（GPU 加速）
export EMBEDDING_PROVIDER=ollama
export EMBEDDING_MODEL=bge-m3
export OLLAMA_HOST=http://localhost:11434

# 方案 3：OpenAI（云端，质量最高）
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key
export EMBEDDING_MODEL=text-embedding-3-small
```

> ⚠️ **模型一致性**：索引和搜索必须使用同一种 Provider。更换后需删除 `.codebrain/milvus.db` 重建。

### 自定义约定文件扩展名

```bash
# Windows PowerShell
$env:CUSTOM_EXTENSIONS=".vue,.svelte,.astro"

# Linux / macOS
export CUSTOM_EXTENSIONS=".vue,.svelte,.astro"
```

---

## 🔗 借鉴项目

| 项目 | Stars | 借鉴了什么 |
|------|:---:|-----------|
| [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | 1.4K | 代码结构索引底座，155 语言支持 |
| [claude-context](https://github.com/zilliztech/claude-context) | 11.6K | 混合搜索 RRF、多 Provider Embedder、sync-trigger |
| [codebase-context](https://github.com/PatrickSys/codebase-context) | — | 约定模式频率检测思路 |

---

## ❓ 常见问题

**Q: 三个 MCP 必须全部部署吗？**
A: 不需要。每个 MCP 独立运行，可按需启用。建议从 conventions-mcp 开始。

**Q: 数据安全吗？会上传到云端吗？**
A: 完全本地。所有数据存在 `.codebrain/milvus.db`（约 400MB/项目），不上传任何内容。

**Q: 支持中文吗？**
A: 完全支持。bge-m3 中文语义匹配优秀，约定模板和文档均为中文。

**Q: 需要 GPU 吗？**
A: 不需要。sentence-transformers 在 CPU 上运行 bge-m3 完全够用。如有 GPU 可切换到 Ollama Provider。

**Q: 和 codebase-memory-mcp 冲突吗？**
A: 互补关系。codebase-memory 做代码结构（SQLite 图），我们做项目知识（Milvus 向量）。

**Q: 支持哪些 AI 编程工具？**
A: 任何支持 MCP 协议的工具：Qoder、Windsurf、Cursor、Claude Code、Codex CLI、OpenCode、Cline 等。

**Q: 约定文件放哪里？**
A: 项目根目录的 `.codebrain/conventions/`，Markdown 格式，YAML frontmatter。

---

## 🗺️ 路线图

- [x] 共享 core 库（多 Provider Embedder、混合搜索）
- [x] conventions-mcp（约定索引 + 检索）
- [x] session-memory-mcp（会话记忆）
- [x] history-mcp（Git 历史索引）
- [ ] 一键安装脚本（自动配置所有 AI 工具）
- [ ] 约定文件 Watch 模式（文件变更自动重索引）
- [ ] 性能基准测试（Token 节省量化）
- [ ] 多项目聚合搜索

---

## 🤝 贡献

欢迎提交 Issue 和 PR！请先阅读 [实施计划](docs/plan.md) 了解架构设计。

---

## 📄 许可证

MIT License

---

<p align="center">
  <sub>Made with ❤️ for developers who code with AI</sub>
</p>
