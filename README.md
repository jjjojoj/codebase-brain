# Codebase Brain

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP Server](https://img.shields.io/badge/MCP-server-purple)
![Local First](https://img.shields.io/badge/default-local--first-green)
![Status](https://img.shields.io/badge/status-stable_MVP-orange)

Codebase Brain 是给 AI 编程工具使用的项目知识层 MCP Server。它把团队约定、轻量任务记忆和安全的 Git 只读上下文暴露给 Cursor、Qoder、Codex、OpenCode、Claude Code、Windsurf、Cline、Hermes 以及其它支持 MCP 的客户端。

它不做通用代码图谱引擎，也不替代 grep、LSP 或 code search。它解决的是另一个更常见的问题：AI 进入一个真实团队仓库时，不知道“我们这里应该怎么写、以前为什么这么改、这段代码最近谁动过”。

> **安全边界**：稳定版默认本地运行、本地 SQLite 存储、本地 embedding。OpenAI / 云端 embedding 默认关闭，Git 历史向量索引默认关闭，稳定 MCP 工具面只暴露低风险能力。

## 为什么需要它

- **项目约定可检索**：把测试、错误处理、模块边界、命名、提交规范等规则写成 Markdown，AI 修改代码前可以检索。
- **任务上下文可延续**：手动记录关键决策、踩坑、文件变更，下次类似任务可以召回。
- **Git 上下文低风险可用**：读取 blame、最近提交、经常一起修改的文件，不需要把 Git 历史全文入库。
- **团队可共享，个人可本地化**：约定文件可以提交到业务仓库，数据库和个人记忆留在每个开发者本机。

## 当前稳定范围

稳定版优先交付 14 个 MCP 工具：

| 分组 | 工具 |
| --- | --- |
| 状态 | `health` |
| 项目约定 | `add_convention`, `search_conventions`, `list_conventions`, `index_convention_files` |
| 会话记忆 | `start_session`, `record_decision`, `record_problem`, `record_file_change`, `end_session`, `recall_context` |
| Git 只读上下文 | `get_blame`, `get_recent_changes`, `get_co_changed_files` |

暂不开放这些实验能力：

- Git 历史向量索引。
- 已索引 Git 历史的语义搜索。
- 默认 OpenAI / 云端 embedding。
- legacy `packages/*` 多 MCP Server 入口。
- 自动 watch / 自动同步。
- 自动改写各类 AI 客户端配置。

这些能力不是永远不做，而是等安全过滤、文件过滤、真实客户端验证成熟后再回流。

## Quick Start

需要 Python 3.11+，推荐 Python 3.12。

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

索引约定：

```bash
CODEBRAIN_DB_PATH=/ABS/PATH/your-project/.codebrain/codebrain.db \
  .venv/bin/codebrain index --path /ABS/PATH/your-project/.codebrain/conventions
```

也可以在 MCP 客户端里调用 `index_convention_files`。如果客户端不是从业务仓库根目录启动，请传入 `.codebrain/conventions` 的绝对路径。

## MCP 配置

只需要配置一个 MCP Server，名字建议叫 `codebase-brain`。所有路径建议写绝对路径，因为不同客户端对 `~`、工作目录和环境变量的处理不完全一致。

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

### 多客户端使用建议

| 客户端 | 建议方式 | 说明 |
| --- | --- | --- |
| Cursor | 在 MCP 设置里添加通用 JSON 配置 | 团队成员最容易复制粘贴。 |
| Qoder | 在 MCP 配置入口添加同样的 `command` / `args` / `env` | 先手动配置，避免脚本误改个人设置。 |
| Codex CLI | 使用上面的 TOML 配置 | 适合重度终端工作流。 |
| OpenCode | 使用客户端支持的 MCP JSON / 配置文件 | 字段保持同一组：`command`, `args`, `env`。 |
| Hermes / 其它 MCP 客户端 | 按客户端文档添加 stdio MCP server | 只要支持 stdio MCP，就可以接入。 |

配置后重启客户端，先调用 `health`。如果能看到 `stable_profile: "mvp"` 和正确的 `db_path`，说明服务连通。

## 推荐工作流

个人使用：

1. 给常见任务写 5 到 20 条约定，比如测试、错误处理、目录结构、提交信息。
2. 调用 `index_convention_files`。
3. 开始复杂任务时调用 `start_session`。
4. 遇到重要决策或问题时调用 `record_decision` / `record_problem`。
5. 修改不熟悉的文件前调用 `get_recent_changes`、`get_blame` 或 `get_co_changed_files`。
6. 任务结束时调用 `end_session`。

团队落地：

1. 先选一个真实业务仓库试点，不要一开始铺到所有项目。
2. 把 `.codebrain/conventions/*.md` 提交到业务仓库。
3. 把 `.codebrain/codebrain.db` 保留在每个人本机，不提交数据库。
4. 先只启用本地 embedding，不启用云端 embedding。
5. 先使用 Git 只读工具，不启用 Git 历史向量索引。
6. 每周让团队删掉过期约定，避免知识库变成噪音。

记忆内容要短、事实化。不要写入密钥、凭据、客户数据、生产日志或其它敏感信息。

## 工具说明

### 状态

| 工具 | 说明 |
| --- | --- |
| `health` | 查看服务、存储、embedding provider、安全开关和数据库路径。 |

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
| `CODEBRAIN_EMBEDDER_PROVIDER` | `sentence-transformers` | 稳定版默认本地 provider。 |
| `CODEBRAIN_EMBEDDER_MODEL` | `all-MiniLM-L6-v2` | 启动快的小模型，适合 MVP。 |
| `CODEBRAIN_DB_PATH` | `.codebrain/codebrain.db` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` | `.codebrain/conventions` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS` | `false` | 私有代码或团队项目建议保持 false。 |
| `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED` | `false` | 稳定版建议保持 false。 |

## 安全与信任

- Codebase Brain 会读取你提供的约定文件和 Git 元数据，并写入本地 SQLite 数据库。
- 默认数据库路径是 `.codebrain/codebrain.db`，团队仓库应该忽略这个数据库文件。
- 默认 embedding provider 是本地 `sentence-transformers`。
- OpenAI embedding 默认禁用；只有设置 `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS=true` 才会启用。
- Git 历史向量索引默认禁用；稳定版 MCP 工具面不注册 `index_git_history` 和 `search_history`。
- 当前没有自动安装脚本，也不会自动改写 Cursor、Qoder、Codex、OpenCode 等客户端配置。

## 与代码图谱型 MCP 的关系

像 [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) 这类项目更偏结构化代码图谱、索引速度、跨语言分析和自动客户端配置。Codebase Brain 先做更保守的一层：团队约定、任务记忆、Git 只读上下文。

两者不是同一个定位：

- 如果你要问“这个函数被谁调用、跨服务链路怎么走”，优先用代码图谱型工具。
- 如果你要问“我们团队这里应该怎么写、这个模块以前踩过什么坑、改这个文件前该看哪些历史”，用 Codebase Brain。

## Troubleshooting

| 问题 | 处理方式 |
| --- | --- |
| MCP 客户端看不到工具 | 检查 `command` 是否是绝对路径，重启客户端，再调用 `health`。 |
| 数据库写到错误目录 | 显式设置 `CODEBRAIN_DB_PATH` 为业务仓库下的绝对路径。 |
| `index_convention_files` 找不到文件 | 设置 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH`，或调用工具时传绝对路径。 |
| 第一次启动慢 | `sentence-transformers` 第一次加载或下载模型会比较慢。 |
| 不想任何文本离开本机 | 保持 `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS=false`，不要配置 OpenAI provider。 |

## 开发与测试

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

当前稳定分支是 `main`。原实验版保存在 `dev` 分支。
