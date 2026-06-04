param(
    [string]$CodebrainRoot = "D:\cb",
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [Alias("QoderMcpJson")]
    [string]$McpJson = "",
    [string]$EmbedderModel = "paraphrase-multilingual-MiniLM-L12-v2",
    [switch]$RunSidecarIndex,
    [switch]$RunStdioSmoke,
    [string]$AsyncSmokeFile = "",
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

if ($ProjectRoot.Contains([char]0xFFFD)) {
    throw "ProjectRoot contains Unicode replacement characters. Run this script from native Windows PowerShell instead of passing a Chinese path through WSL."
}

function Assert-PathExists {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
    Write-Host "[OK] $Label`: $Path"
}

$python = Join-Path $CodebrainRoot ".venv\Scripts\python.exe"
$codebrain = Join-Path $CodebrainRoot ".venv\Scripts\codebrain.exe"
$sidecar = Join-Path $CodebrainRoot "sidecar\codebase-memory-mcp.exe"
$dbPath = Join-Path $ProjectRoot ".codebrain\codebrain_full.db"
$conventionsPath = Join-Path $ProjectRoot ".codebrain\conventions"

Assert-PathExists $CodebrainRoot "Codebase Brain root"
Assert-PathExists $ProjectRoot "Project root"
Assert-PathExists $python "Virtualenv Python"
Assert-PathExists $codebrain "Codebrain CLI"
if (Test-Path -LiteralPath $sidecar) {
    Write-Host "[OK] Code graph sidecar: $sidecar"
} elseif ($RunSidecarIndex) {
    throw "Code graph sidecar not found: $sidecar"
} else {
    Write-Warning "Code graph sidecar not found. Graph tools will run in degraded mode."
}

$env:CODEBRAIN_DB_PATH = $dbPath
$env:CODEBRAIN_DEFAULT_CONVENTIONS_PATH = $conventionsPath
$env:CODEBRAIN_CODEBASE_MEMORY_BINARY = $sidecar
$env:CODEBRAIN_EMBEDDER_MODEL = $EmbedderModel

Write-Host "`n== Git version =="
git -C $CodebrainRoot status --short --branch
git -C $CodebrainRoot log -1 --oneline

Write-Host "`n== CLI info =="
& $codebrain info
if ($LASTEXITCODE -ne 0) {
    throw "codebrain info failed with exit code $LASTEXITCODE"
}

Write-Host "`n== Tool surface =="
$toolCheck = @'
from codebrain.server import mcp
tools = sorted(mcp._tool_manager._tools)
print(f"tool_count={len(tools)}")
print("\n".join(tools))
expected = 23 if "index_git_history" in tools else 21
raise SystemExit(0 if len(tools) == expected else 1)
'@

$toolCheck | & $python -
if ($LASTEXITCODE -ne 0) {
    throw "Unexpected MCP tool surface"
}

Write-Host "`n== Compile check =="
& $python -m compileall -q (Join-Path $CodebrainRoot "src") (Join-Path $CodebrainRoot "tests")
if ($LASTEXITCODE -ne 0) {
    throw "compileall failed with exit code $LASTEXITCODE"
}

if ($RunSidecarIndex) {
    Write-Host "`n== Sidecar fast index =="
    $env:CODEBRAIN_VERIFY_PROJECT_ROOT = $ProjectRoot
    $sidecarCheck = @'
import json
import os
from codebrain.adapters.codebase_memory import CodebaseMemoryAdapter

result = CodebaseMemoryAdapter(
    os.environ["CODEBRAIN_CODEBASE_MEMORY_BINARY"],
    timeout_sec=300,
).index_repository(
    os.environ["CODEBRAIN_VERIFY_PROJECT_ROOT"],
    mode="fast",
)
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result.get("ok") is True else 1)
'@
    $sidecarCheck | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw "sidecar fast index failed for project: $ProjectRoot"
    }
}

if ($RunTests) {
    Write-Host "`n== Tests =="
    & $python -c "import pytest" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "pytest is not installed. Re-run scripts\setup-windows.ps1 with -InstallDev."
    }
    & $python -m pytest -q (Join-Path $CodebrainRoot "tests")
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }
}

if ($McpJson) {
    Write-Host "`n== MCP JSON =="
    Assert-PathExists $McpJson "MCP config"
    $config = [IO.File]::ReadAllText($McpJson) | ConvertFrom-Json
    if ($null -eq $config.mcpServers."codebase-brain") {
        throw "MCP config does not contain mcpServers.codebase-brain"
    }
    Write-Host "[OK] MCP JSON parses and contains codebase-brain"
}

if ($RunStdioSmoke) {
    if (-not $McpJson) {
        throw "RunStdioSmoke requires -McpJson."
    }
    Write-Host "`n== MCP stdio smoke =="
    & $python (Join-Path $CodebrainRoot "scripts\smoke-mcp-stdio.py") $McpJson
    if ($LASTEXITCODE -ne 0) {
        throw "MCP stdio smoke failed with exit code $LASTEXITCODE"
    }
}

if ($AsyncSmokeFile) {
    Write-Host "`n== Async workflow smoke =="
    & $python (Join-Path $CodebrainRoot "scripts\smoke-async-workflows.py") `
        --repo-path $ProjectRoot `
        --file-path $AsyncSmokeFile
    if ($LASTEXITCODE -ne 0) {
        throw "Async workflow smoke failed with exit code $LASTEXITCODE"
    }
}

Write-Host "`nPASS: static Windows deployment checks completed."
Write-Host "Next: restart the MCP client and call health, brain_status, and brain_index_project against:"
Write-Host $ProjectRoot
