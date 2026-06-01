# Codebase Brain

Codebase Brain 是一个给 AI 编程工具使用的项目知识 MCP Server。它把项目约定、轻量会话记忆和安全的 Git 上下文提供给 Cursor、Qoder、Codex、OpenCode、Claude Code、Windsurf、Cline 等支持 MCP 的工具，让 AI 在大型或长期维护项目里少一点“从零猜”。

这个项目面向所有开发者：

- 个人开发者可以用它记录项目规则、任务决策和 Git 上下文。
- 团队可以用它把隐式约定沉淀成可检索的项目知识，降低新人和 AI 工具的上下文成本。
- 公司内部使用时，可以默认走本地 embedding，避免把代码或项目知识发到外部服务。

当前 `main` 分支是稳定版。更激进的 Git 历史向量索引、多 MCP Server 原型和 Milvus 版本保存在 `dev` 分支，等安全过滤和真实客户端验证成熟后再考虑回流。

## 解决什么问题

稳定版优先解决三个低风险、高频的问题：

- **项目约定检索**：把测试、错误处理、模块边界、命名等规则写成 Markdown，AI 修改代码前可以检索。
- **轻量会话记忆**：手动记录关键决策、踩坑、文件变更，下次类似任务可以召回。
- **Git 只读上下文**：直接读取 blame、最近提交、经常一起修改的文件，不需要把 Git 历史全文入库。

稳定版暂不开放这些实验能力：

- Git 历史向量索引。
- 已索引 Git 历史的语义搜索。
- 默认 OpenAI / 云端 embedding。
- legacy `packages/*` 多 MCP Server 入口。
- 自动 watch / 自动同步。

## 工具清单

| 工具 | 说明 |
| --- | --- |
| `health` | 查看服务、存储、embedding 状态。 |
| `add_convention` | 手动添加一条项目约定。 |
| `search_conventions` | 检索已经索引的项目约定。 |
| `list_conventions` | 列出约定元信息。 |
| `index_convention_files` | 索引 `.codebrain/conventions` 下的 Markdown 约定文件。 |
| `start_session` | 开始一个轻量会话，并召回相似历史会话。 |
| `record_decision` | 记录关键实现或架构决策。 |
| `record_problem` | 记录遇到的问题和解决方案。 |
| `record_file_change` | 记录本次会话修改过的文件。 |
| `end_session` | 保存本次会话记忆。 |
| `recall_context` | 根据任务描述召回相似会话。 |
| `get_blame` | 读取文件某段代码的 Git blame 信息。 |
| `get_recent_changes` | 读取某个文件的最近提交记录。 |
| `get_co_changed_files` | 查找历史上经常和某文件一起修改的文件。 |

## 安装

需要 Python 3.11+。推荐 Python 3.12。

macOS / Linux:

```bash
git clone https://github.com/jjjojoj/codebase-brain.git
cd codebase-brain
python3.12 -m venv .venv
.venv/bin/pip install -e ".[local]"
```

Windows PowerShell:

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git C:\codebase-brain
cd C:\codebase-brain
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -e ".[local]"
```

`local` extra 会安装 `sentence-transformers`，默认在本机 CPU 上生成 embedding。处理公司代码、私有仓库或敏感项目时，建议保持本地 embedding。

## 快速开始

在你的项目仓库里创建约定目录：

```text
your-project/
  .codebrain/
    conventions/
      testing.md
      error-handling.md
      module-boundaries.md
```

每个 Markdown 文件使用 YAML frontmatter：

```markdown
---
module: auth
title: 认证模块错误处理约定
tags: [auth, errors]
---

认证相关代码返回明确的 AuthError 类型，不要跨模块边界抛出通用异常。
```

然后让 AI 工具调用：

```text
index_convention_files
```

如果 MCP 客户端不是从项目根目录启动，给 `index_convention_files` 传 `.codebrain/conventions` 的绝对路径。

## MCP 配置

只需要配置一个 MCP Server，名字建议叫 `codebase-brain`。尽量使用绝对路径，因为不同 MCP 客户端对 `~` 的展开行为不完全一致。

macOS / Linux:

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

Cursor、Qoder、Codex CLI、OpenCode、Claude Code、Windsurf、Cline 等 MCP 客户端的配置文件位置不同，但核心都是 `command`、`args`、`env`。

## 个人使用建议

1. 给常见任务写几条约定，比如测试、错误处理、目录结构、提交信息。
2. 调用 `index_convention_files`。
3. 开始复杂任务时调用 `start_session`。
4. 遇到重要决策或问题时调用 `record_decision` / `record_problem`。
5. 修改不熟悉的文件前调用 `get_recent_changes`、`get_blame` 或 `get_co_changed_files`。
6. 任务结束时调用 `end_session`。

## 团队落地建议

团队使用时，建议先小范围试点：

1. 从一个仓库开始，不要一开始铺到所有项目。
2. 先沉淀 5 到 20 条最常被问、最容易被 AI 写错的约定。
3. 把 `.codebrain/conventions/*.md` 提交到业务仓库，让所有人共享同一份约定。
4. 每个开发者本机保存自己的 `.codebrain/codebrain.db`，数据库文件不要提交。
5. 先只启用本地 embedding，不启用云端 embedding。
6. 先使用 Git 只读工具，不启用 Git 历史向量索引。

记忆内容要短、事实化。不要写入密钥、凭据、客户数据、生产日志或其它敏感信息。

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

## 被禁用的实验能力

`index_git_history` 和 `search_history` 不会注册到稳定版 MCP 工具面。对应实现仍然被配置开关保护，后续如果补齐 secret 过滤、文件过滤、真实客户端测试，再考虑开放。

OpenAI embedding 默认被禁用。只有显式设置 `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS=true` 才能启用；启用意味着被索引文本可能离开本机。

## 开发与测试

安装开发依赖并运行测试：

```bash
uv run --python 3.12 --extra dev pytest -q
```

当前稳定分支是 `main`。原实验版保存在 `dev`。
