# Cursor Windows 部署指南

本文说明如何在 Windows 11 的 Cursor 中接入 Codebase Brain。首次安装 Codebase Brain 前，
先完成 [`Windows安装指南.md`](Windows安装指南.md)。

需要代码图谱能力时，业务仓库路径必须为纯英文路径；Windows sidecar `v0.7.0` 暂不支持中文
仓库路径。

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
      "timeout": 300000,
      "env": {
        "CODEBRAIN_DB_PATH": "D:\\项目\\业务仓库\\.codebrain\\codebrain_full.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "D:\\项目\\业务仓库\\.codebrain\\conventions",
        "CODEBRAIN_CODEBASE_MEMORY_BINARY": "D:\\cb\\sidecar\\codebase-memory-mcp.exe",
        "CODEBRAIN_EMBEDDER_MODEL": "paraphrase-multilingual-MiniLM-L12-v2"
      }
    }
  }
}
```

## 2. 配置 Cursor

1. 打开 Cursor Settings。
2. 找到 MCP 设置页面。
3. 选择添加 MCP Server 或打开 MCP JSON 配置。
4. 添加生成配置中的 `mcpServers.codebase-brain`。
5. 保存配置并完全重启 Cursor。

Cursor 版本之间的配置入口可能变化，但 MCP Server 的核心字段始终是 `command`、`args` 和
`env`。所有 Windows 路径必须使用绝对路径。

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
| `codebrain.exe` 安装或升级失败 | 关闭 Cursor，确认没有 `codebrain.exe` 进程后重新运行安装脚本 |
| 图谱不可用 | 检查 `D:\cb\sidecar\codebase-memory-mcp.exe` 是否存在 |
| 业务数据写错目录 | 检查 `CODEBRAIN_DB_PATH` 和 `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` |
| 第一次语义搜索很慢 | 等待本地 embedding 模型首次下载和加载 |

日常工作流见 [`使用指南.md`](使用指南.md)。
