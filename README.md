# Codebase Brain

面向公司内部开发者的稳定版 MCP Server。它把项目约定、轻量会话记忆和安全的 Git 上下文暴露给 Cursor、Qoder、Codex、OpenCode、Claude Code、Windsurf 等支持 MCP 的 AI 编程工具。

当前 `main` 分支是求稳版本。原来更激进的 Git 历史向量索引、多 MCP Server 原型和 Milvus 版本已经保存在 `dev` 分支。

## 稳定版范围

稳定版先解决三个最实用、风险较低的问题：

- 项目约定检索：把团队规范写成 Markdown，AI 修改代码前可以检索。
- 轻量会话记忆：手动记录关键决策、问题、文件变更，方便下次召回。
- Git 只读上下文：直接读取 blame、最近变更、经常一起变更的文件。

稳定版暂时不开放：

- Git 历史向量索引。
- 已索引 Git 历史的语义搜索。
- 默认 OpenAI / 云端 embedding。
- legacy `packages/*` 多 MCP Server 入口。
- 自动 watch / 自动同步。

这些能力不是永远不做，而是等安全过滤、真实客户端测试和团队使用反馈成熟后再从 `dev` 分支挑选回来。

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

`local` extra 会安装 `sentence-transformers`，默认在本机 CPU 上生成 embedding。公司代码不要默认使用云端 embedding，除非公司明确批准这类数据流。

## 项目约定文件

在每个业务仓库里创建：

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

如果 MCP 客户端不是从项目根目录启动，给 `index_convention_files` 传绝对路径。

## MCP 配置

只配置一个 MCP Server，名字建议叫 `codebase-brain`。尽量使用绝对路径，因为不同 MCP 客户端对 `~` 的展开行为不完全一致。

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

这类配置适用于 Cursor、Qoder、Codex CLI、OpenCode、Claude Code、Windsurf、Cline 等支持 MCP 的工具。不同工具的 MCP 配置文件位置不同，但 `command`、`args`、`env` 结构基本一致。

## 推荐使用流程

1. 先写 5 到 20 条高价值约定，比如测试、错误处理、命名、模块边界、代码评审要求。
2. 调用 `index_convention_files`。
3. 开始任务时调用 `start_session`。
4. 任务中只把长期有用的信息写入 `record_decision`、`record_problem`、`record_file_change`。
5. 修改不熟悉的文件前，调用 `get_recent_changes`、`get_blame` 或 `get_co_changed_files`。
6. 任务结束时调用 `end_session`。

记忆内容要短、事实化。不要写入密钥、凭据、客户数据、生产日志或其它敏感信息。

## 配置项

环境变量统一使用 `CODEBRAIN_` 前缀。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CODEBRAIN_EMBEDDER_PROVIDER` | `sentence-transformers` | 稳定版默认本地 provider。 |
| `CODEBRAIN_EMBEDDER_MODEL` | `all-MiniLM-L6-v2` | 启动快的小模型，适合 MVP。 |
| `CODEBRAIN_DB_PATH` | `.codebrain/codebrain.db` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` | `.codebrain/conventions` | 建议配置成每个项目自己的绝对路径。 |
| `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS` | `false` | 稳定内测保持 false。 |
| `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED` | `false` | 稳定内测保持 false。 |

## 被禁用的实验能力

`index_git_history` 和 `search_history` 不会注册到稳定版 MCP 工具面。对应实现仍然被配置开关保护，后续如果补齐 secret 过滤、文件过滤、真实客户端测试，再考虑开放。

OpenAI embedding 默认被禁用。只有显式设置 `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS=true` 才能启用；启用意味着被索引文本可能离开本机。

## 开发与测试

安装开发依赖并运行测试：

```bash
uv run --python 3.12 --extra dev pytest -q
```

当前稳定分支是 `main`。原实验版保存在 `dev`。
