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

如果你用 `codebase-memory-mcp` 自带的 `install.ps1` 安装 sidecar，必须加 `--skip-config`。
否则 sidecar 会把自己注册成独立 MCP Server，和 Codebase Brain 推荐的单一入口冲突。正确结构是：
AI 客户端只连接 `codebase-brain`，`codebrain.exe serve` 再内部调用
`D:\cb\sidecar\codebase-memory-mcp.exe`。

### 仓库路径和图谱路径

Codebase Brain 本身支持中文路径。本地约定、会话记忆和 Git 只读工具可以直接使用中文业务
工作区。部分 Windows 版 `codebase-memory-mcp` 在中文路径 discover 阶段可能返回 0 个文件；
这时不要强迫团队改工作区，而是给图谱准备一个英文路径副本或 junction，并配置 repo alias。

推荐布局：

```text
D:\qoder工作区\django-test      # Qoder 真实工作区，可以是中文路径
D:\projects\django-test        # 给 sidecar 使用的英文路径副本或 junction
```

MCP 配置中加入：

```json
{
  "env": {
    "CODEBRAIN_DEFAULT_PROJECT": "D:\\qoder工作区\\django-test",
    "CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES": "D:\\qoder工作区\\django-test=D:\\projects\\django-test"
  }
}
```

如果项目本身已经在纯英文路径，例如 `D:\projects\ruoyi-vue-pro`，不需要 alias。

## 第一次安装

先关闭 Qoder、Cursor 和其它可能启动 Codebase Brain 的 MCP 客户端，然后打开 Windows
PowerShell：

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git D:\cb
cd D:\cb

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -ProjectRoot "D:\项目\你的业务仓库" `
  -GraphProjectRoot "D:\projects\你的业务仓库" `
  -SidecarPath "$env:USERPROFILE\Downloads\codebase-memory-mcp-windows-amd64.zip"
```

脚本会：

1. 在 `D:\cb\.venv` 创建 Python 虚拟环境，优先使用 3.12，没有时使用 3.11。
2. 安装 Codebase Brain 和本地 embedding 依赖。
3. 在业务仓库创建 `.codebrain\conventions`。
4. 从 ZIP 解压 sidecar，或将 EXE 复制到 `D:\cb\sidecar`。
5. 写入 `CODEBRAIN_DB_PATH`、`CODEBRAIN_DEFAULT_CONVENTIONS_PATH` 和
   `CODEBRAIN_DEFAULT_PROJECT`，确保数据库和默认仓库都绑定到业务项目。
6. 生成 `D:\cb\.local-configs\<业务仓库名>-mcp.json`。
7. 执行基础安装检查。

`-GraphProjectRoot` 可选。只有业务工作区是中文路径、但图谱需要使用英文路径副本时才传入。
脚本会自动生成 `CODEBRAIN_CODEBASE_MEMORY_REPO_ALIASES`。

第一次安装需要联网下载 Python 依赖和 embedding 模型，可能需要较长时间。脚本默认模型是
`paraphrase-multilingual-MiniLM-L12-v2`，约 470MB，适合中文或中英混合项目。如果项目只需要英文轻量模型，可以加：

```powershell
-EmbedderModel all-MiniLM-L6-v2
```

这会与 README 手动 Quick Start 的轻量默认模型保持一致。

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

生成 JSON 中的 `"timeout": 300000` 是 Qoder 专用扩展字段。Cursor 使用时必须删除该字段，只保留
`command`、`args` 和 `env`。

## 第一次使用

重启客户端后，对 AI 说：

```text
先调用 health 和 brain_status 检查 Codebase Brain。
然后调用 brain_index_project 索引当前仓库。
```

首次图谱索引完成后，再说：

```text
调用 brain_context_for_task，为“我当前要处理的任务”生成上下文包，
拿到 job_id 后轮询 brain_index_job_status，成功后根据 result 中的约定、
相关符号和 Git 历史制定修改计划。
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
  -ProjectRoot "D:\项目\你的业务仓库" `
  -GraphProjectRoot "D:\projects\你的业务仓库"
```

更新后重启 Qoder 或 Cursor。

## 卸载

1. 从 Qoder/Cursor 删除 `codebase-brain` MCP 配置。
2. 删除 `D:\cb`。
3. 如需清除个人索引和记忆，再删除业务仓库下的 `.codebrain`。

团队共享的 `.codebrain\conventions\*.md` 是否删除，应先与项目负责人确认。
