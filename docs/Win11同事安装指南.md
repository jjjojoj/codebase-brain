# Win11 同事安装指南

这份指南面向使用 Qoder、Cursor 等 AI 编程客户端的普通开发者。

**不需要安装 WSL、Linux、Docker、Hermes 或 Milvus。** Codebase Brain、SQLite、embedding
模型和图谱 sidecar 都直接运行在 Windows 11 中。

## 需要安装

- Windows 11
- Git for Windows
- Python 3.11 或更高版本，推荐 3.12；安装时启用 Python Launcher
- Qoder、Cursor 或其它支持 stdio MCP 的客户端

维护者还需要提供 Windows 版 `codebase-memory-mcp.exe`。没有 sidecar 时也能使用项目约定、
会话记忆和 Git 只读工具，但代码图谱功能会降级。

## 第一次安装

先关闭 Qoder、Cursor 和其它可能启动 Codebase Brain 的 MCP 客户端，然后打开 Windows
PowerShell：

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git D:\cb
cd D:\cb

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库" `
  -SidecarPath "D:\安装包\codebase-memory-mcp.exe"
```

脚本会：

1. 在 `D:\cb\.venv` 创建 Python 虚拟环境，优先使用 3.12，没有时使用 3.11。
2. 安装 Codebase Brain 和本地 embedding 依赖。
3. 在业务仓库创建 `.codebrain\conventions`。
4. 将 sidecar 复制到 `D:\cb\sidecar`。
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

日常工具使用方法见 [`同事使用手册.md`](同事使用手册.md)。

## 自助检查

在 Windows PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\cb\scripts\verify-qoder-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库" `
  -RunSidecarIndex
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
