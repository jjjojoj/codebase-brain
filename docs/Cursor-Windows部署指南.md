# Cursor Windows 部署指南

本文说明如何在 Windows 11 的 Cursor 中接入 Codebase Brain。首次安装 Codebase Brain 前，
先完成 [`Windows安装指南.md`](Windows安装指南.md)。

需要代码图谱能力时，推荐让 sidecar 使用纯英文路径。业务工作区可以是中文路径，但要在 MCP
配置中加入 `CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES`，把中文工作区映射到英文图谱路径。

Cursor 只需要配置 `codebase-brain` 这一个 MCP Server。不要把
`D:\cb\sidecar\codebase-memory-mcp.exe` 单独添加为第二个 Server；如果用 sidecar 自带安装脚本，
请传 `--skip-config`，避免它自动注册到 Cursor。

## 1. 获取生成的 MCP 配置

安装脚本会生成：

```text
D:\cb\.local-configs\<业务仓库名>-mcp.json
```

内容类似：

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "D:\\cb\\.venv\\Scripts\\codebrain.exe",
      "args": ["serve"],
      "env": {
	        "CODEBRAIN_DB_PATH": "D:\\项目\\业务仓库\\.codebrain\\codebrain_full.db",
	        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "D:\\项目\\业务仓库\\.codebrain\\conventions",
	        "CODEBRAIN_DEFAULT_PROJECT": "D:\\项目\\业务仓库",
	        "CODEBRAIN_CODEBASE_MEMORY_BINARY": "D:\\cb\\sidecar\\codebase-memory-mcp.exe",
	        "CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES": "D:\\项目\\业务仓库=D:\\projects\\业务仓库",
	        "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
	      }
    }
  }
}
```

## 2. 配置 Cursor

Cursor 官方支持两种 `mcp.json` 位置：

- 项目级配置：业务仓库下的 `.cursor\mcp.json`。
- 全局配置：用户目录下的 `.cursor\mcp.json`，例如
  `C:\Users\<用户名>\.cursor\mcp.json`。

Codebase Brain 的数据库和约定路径与业务仓库绑定，推荐使用项目级配置。创建
`D:\projects\django-test\.cursor\mcp.json`，从安装脚本生成的 JSON 中复制 `command`、
`args` 和 `env`。

注意：安装脚本生成的 JSON 可能包含 `"timeout": 300000`。这是 Qoder 使用的扩展字段，Cursor
配置中必须删除，否则可能导致配置解析或行为异常。

保存后完全重启 Cursor。

也可以打开 Cursor Settings 的 MCP 页面添加同一配置。Cursor 版本之间的设置入口可能变化，
但 MCP Server 的核心字段始终是 `command`、`args` 和 `env`。所有 Windows 路径必须使用绝对
路径。

不要把 `D:\cb\sidecar\codebase-memory-mcp.exe` 单独添加为另一个 MCP Server。Cursor 只需要
连接 `codebase-brain`，sidecar 由 Codebase Brain 内部调用。

## 3. 首次验证

在 Cursor 对话中依次要求调用：

```text
调用 health，确认 Codebase Brain 服务状态和数据库路径。
```

```text
调用 brain_status，仓库路径是 D:\项目\业务仓库。
```

```text
调用 brain_index_project，仓库路径是 D:\项目\业务仓库，graph_mode 使用 fast。
```

通过标准：

- Cursor 能看到默认 21 个工具。
- `health.ok=true`。
- `brain_status.graph` 显示 sidecar 可用。
- `brain_index_project` 能完成或返回明确异步/错误状态。

## 4. 常见问题

| 症状 | 处理 |
| --- | --- |
| Cursor 看不到工具 | 检查生成 JSON 中的绝对路径，完全退出并重启 Cursor |
| Cursor 配置从 Qoder 复制后异常 | 删除 Qoder 专用的 `timeout` 字段 |
| `codebrain.exe` 安装或升级失败 | 关闭 Cursor，确认没有 `codebrain.exe` 进程后重新运行安装脚本 |
| 图谱不可用 | 检查 `D:\cb\sidecar\codebase-memory-mcp.exe` 是否存在 |
| 返回 Cursor/IDE 自身代码 | 设置 `CODEBRAIN_DEFAULT_PROJECT` 为业务仓库绝对路径 |
| 中文路径图谱为空 | 配置 `CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES` 到英文路径副本 |
| 业务数据写错目录 | 检查 `CODEBRAIN_DB_PATH` 和 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` |
| 第一次语义搜索很慢 | 等待本地 embedding 模型首次下载和加载 |

日常工作流见 [`使用指南.md`](使用指南.md)。

参考： [Cursor 官方 MCP 文档](https://docs.cursor.com/zh/context/mcp)。
