param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [string]$CodebrainRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$SidecarPath = "",
    [string]$EmbedderModel = "paraphrase-multilingual-MiniLM-L12-v2",
    [switch]$InstallDev
)

$ErrorActionPreference = "Stop"

function Assert-NativeWindowsPath {
    param([string]$Path, [string]$Label)
    if ($Path.Contains([char]0xFFFD)) {
        throw "$Label contains damaged Unicode characters. Run this script directly from Windows PowerShell."
    }
}

function Assert-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

Assert-NativeWindowsPath $ProjectRoot "ProjectRoot"
Assert-NativeWindowsPath $CodebrainRoot "CodebrainRoot"
Assert-Command "py" "Install Python 3.11 or newer from python.org and enable the Python launcher."
Assert-Command "git" "Install Git for Windows."

$CodebrainRoot = (Resolve-Path -LiteralPath $CodebrainRoot).Path
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$venv = Join-Path $CodebrainRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"
$codebrain = Join-Path $venv "Scripts\codebrain.exe"
$sidecarDir = Join-Path $CodebrainRoot "sidecar"
$sidecar = Join-Path $sidecarDir "codebase-memory-mcp.exe"
$dataDir = Join-Path $ProjectRoot ".codebrain"
$dbPath = Join-Path $dataDir "codebrain_full.db"
$conventionsPath = Join-Path $dataDir "conventions"
$configDir = Join-Path $CodebrainRoot ".local-configs"
$projectName = Split-Path -Leaf $ProjectRoot
$configPath = Join-Path $configDir "$projectName-mcp.json"

Write-Host "== Prepare Python environment =="
$runningCodebrain = Get-Process -Name "codebrain" -ErrorAction SilentlyContinue
if ($runningCodebrain) {
    throw "codebrain.exe is running. Close Qoder, Cursor, and other MCP clients before installing or updating."
}

if (-not (Test-Path -LiteralPath $python)) {
    $pythonRuntimes = (& py -0p | Out-String)
    if ($pythonRuntimes -match "-V:3\.12") {
        $launcherVersion = "3.12"
    } elseif ($pythonRuntimes -match "-V:3\.11") {
        $launcherVersion = "3.11"
    } else {
        throw "Python 3.11 or newer was not found. Install it from python.org and run setup again."
    }
    & py "-$launcherVersion" -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python $launcherVersion virtual environment."
    }
}

& $python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "The existing virtual environment is older than Python 3.11. Remove $venv and run setup again."
}

& $python -m pip install -U pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}

$extra = if ($InstallDev) { "local,dev" } else { "local" }
& $python -m pip install -e "${CodebrainRoot}[$extra]"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Codebase Brain."
}

Write-Host "`n== Prepare project data =="
New-Item -ItemType Directory -Force -Path $conventionsPath | Out-Null
New-Item -ItemType Directory -Force -Path $sidecarDir | Out-Null
New-Item -ItemType Directory -Force -Path $configDir | Out-Null

if ($SidecarPath) {
    Assert-NativeWindowsPath $SidecarPath "SidecarPath"
    if (-not (Test-Path -LiteralPath $SidecarPath)) {
        throw "SidecarPath not found: $SidecarPath"
    }
    $resolvedSidecarSource = (Resolve-Path -LiteralPath $SidecarPath).Path
    if ([System.IO.Path]::GetExtension($resolvedSidecarSource) -ieq ".zip") {
        $extractDir = Join-Path $env:TEMP "codebrain-sidecar-$([guid]::NewGuid().ToString('N'))"
        try {
            Expand-Archive -LiteralPath $resolvedSidecarSource -DestinationPath $extractDir -Force
            $executable = Get-ChildItem -LiteralPath $extractDir -Filter "codebase-memory-mcp.exe" -File -Recurse |
                Select-Object -First 1
            if ($null -eq $executable) {
                throw "The sidecar ZIP does not contain codebase-memory-mcp.exe."
            }
            Copy-Item -LiteralPath $executable.FullName -Destination $sidecar -Force
        } finally {
            if (Test-Path -LiteralPath $extractDir) {
                Remove-Item -LiteralPath $extractDir -Recurse -Force
            }
        }
    } else {
        $resolvedSidecarTarget = [System.IO.Path]::GetFullPath($sidecar)
        if (-not $resolvedSidecarSource.Equals(
            $resolvedSidecarTarget,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
            Copy-Item -LiteralPath $resolvedSidecarSource -Destination $sidecar -Force
        }
    }
}

if (-not (Test-Path -LiteralPath $sidecar)) {
    Write-Warning "codebase-memory-mcp.exe is missing. Local knowledge tools will work, but graph tools will run in degraded mode."
}

$server = [ordered]@{
    command = $codebrain
    args = @("serve")
    timeout = 300000
    env = [ordered]@{
        CODEBRAIN_DB_PATH = $dbPath
        CODEBRAIN_DEFAULT_CONVENTIONS_PATH = $conventionsPath
        CODEBRAIN_CODEBASE_MEMORY_BINARY = $sidecar
        CODEBRAIN_EMBEDDER_MODEL = $EmbedderModel
    }
}
$config = [ordered]@{
    mcpServers = [ordered]@{
        "codebase-brain" = $server
    }
}
$configJson = $config | ConvertTo-Json -Depth 8
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($configPath, $configJson, $utf8WithoutBom)

Write-Host "`n== Validate installation =="
$env:CODEBRAIN_DB_PATH = $dbPath
$env:CODEBRAIN_DEFAULT_CONVENTIONS_PATH = $conventionsPath
$env:CODEBRAIN_CODEBASE_MEMORY_BINARY = $sidecar
$env:CODEBRAIN_EMBEDDER_MODEL = $EmbedderModel
& $codebrain info
if ($LASTEXITCODE -ne 0) {
    throw "codebrain info failed."
}

Write-Host "`nPASS: Windows setup completed."
Write-Host "Generated MCP config: $configPath"
Write-Host "Add mcpServers.codebase-brain from that file to Qoder or Cursor, then restart the client."
