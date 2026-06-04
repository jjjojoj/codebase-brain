# Windows 11 安装指南

这份指南用于在一台没有安装过 Codebase Brain 的 Windows 11 电脑上完成首次部署。

**不需要安装 WSL、Linux、Docker、Hermes 或 Milvus。** Codebase Brain、SQLite、embedding
模型和图谱 sidecar 都直接运行在 Windows 11 中。

## 需要安装

- Windows 11
- Git for Windows
- Python 3.11 或更高版本，推荐 3.12；安装时启用 Python Launcher
- Qoder、Cursor 或其它支持 stdio MCP 的客户端

图谱能力需要 Windows 版 `codebase-memory-mcp` ZIP 或 EXE。没有 sidecar 时也能使用项目约定、
会话记忆和 Git 只读工具，但代码图谱功能会降级。

`D:\cb\sidecar` 是 Codebase Brain 内部保存图谱引擎的位置。安装脚本会将 ZIP 中的
`codebase-memory-mcp.exe` 解压到这里，Codebase Brain 再调用它完成符号搜索、调用链和代码图谱
索引。不要把 sidecar 单独配置成第二个 MCP Server。

### 仓库路径要求

当前 Windows sidecar `v0.7.0` 无法索引包含中文字符的仓库路径。本地约定、会话记忆和 Git
只读工具仍可使用中文路径，但代码图谱会失败。

需要完整图谱能力时，请把业务仓库放在纯英文路径，例如：

```text
D:\projects\django-test
```

不要使用 `D:\中文目录\django-test`。这是 sidecar 的当前限制，不是 Python 安装问题。

## 第一次安装

先关闭 Qoder、Cursor 和其它可能启动 Codebase Brain 的 MCP 客户端，然后打开 Windows
PowerShell：

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git D:\cb
cd D:\cb

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库" `
  -SidecarPath "$env:USERPROFILE\Downloads\codebase-memory-mcp-windows-amd64.zip"
```

脚本会：

1. 在 `D:\cb\.venv` 创建 Python 虚拟环境，优先使用 3.12，没有时使用 3.11。
2. 安装 Codebase Brain 和本地 embedding 依赖。
3. 在业务仓库创建 `.codebrain\conventions`。
4. 从 ZIP 解压 sidecar，或将 EXE 复制到 `D:\cb\sidecar`。
5. 生成 `D:\cb\.local-configs\<业务仓库名>-mcp.json`。
6. 执行基础安装检查。

第一次安装需要联网下载 Python 依赖和 embedding 模型，可能需要较长时间。
生成的 MCP JSON 包含个人电脑的绝对路径，保存在 Codebase Brain 安装目录下的本地忽略目录，
不会写入业务仓库。

## 配置 Qoder 或 Cursor

打开安装脚本最后输出的配置文件，例如：

```text
D:\cb\.local-configs\你的业务仓库-mcp.json
```

把其中 `mcpServers.codebase-brain` 配置加入 Qoder 或 Cursor 的 MCP 设置，然后重启客户端。
脚本不会自动修改客户端配置，避免覆盖个人设置。

Qoder 可能存在多个 MCP 配置文件。若 UI 配置没有生效，请联系维护者检查实际生效的
`extension/local/mcp.json`。

## 第一次使用

重启客户端后，对 AI 说：

```text
先调用 health 和 brain_status 检查 Codebase Brain。
然后调用 brain_index_project 索引当前仓库。
```

首次图谱索引完成后，再说：

```text
调用 brain_context_for_task，为“我当前要处理的任务”生成上下文包，
根据约定、相关符号和 Git 历史制定修改计划。
```

日常工具使用方法见 [`使用指南.md`](使用指南.md)。

## 自助检查

在 Windows PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\cb\scripts\verify-qoder-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库" `
  -McpJson "D:\cb\.local-configs\你的业务仓库-mcp.json" `
  -RunSidecarIndex `
  -RunStdioSmoke
```

该命令必须直接在 Windows PowerShell 中运行。不要从 WSL 调用它。

## 更新

先关闭 Qoder、Cursor 和其它 MCP 客户端，再执行：

```powershell
cd D:\cb
git pull --ff-only origin main

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库"
```

更新后重启 Qoder 或 Cursor。

## 卸载

1. 从 Qoder/Cursor 删除 `codebase-brain` MCP 配置。
2. 删除 `D:\cb`。
3. 如需清除个人索引和记忆，再删除业务仓库下的 `.codebrain`。

团队共享的 `.codebrain\conventions\*.md` 是否删除，应先与项目负责人确认。
