# Build the fork-only, self-contained Windows distribution (no external Python needed).
# Run from any working directory after installing: pip install -e ".[desktop]" pyinstaller
[CmdletBinding()]
param(
    [string] $DesktopVersion = "",
    [switch] $SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$versionFile = Join-Path $PSScriptRoot "desktop-version.txt"
if (-not $DesktopVersion) {
    $DesktopVersion = (Get-Content $versionFile -Raw).Trim()
}
if ($DesktopVersion -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Expected desktop version MAJOR.MINOR.PATCH.BUILD, got: $DesktopVersion"
}
Push-Location $root
try {
    $coreVersion = (& python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Could not read core Python package version" }
    if ($DesktopVersion -notmatch ("^" + [regex]::Escape($coreVersion) + "\.\d+$")) {
        throw "Desktop version $DesktopVersion must match core version $coreVersion + build number"
    }

    $output = Join-Path $root "dist\desktop-release"
    $dist = Join-Path $root "build\desktop-pyinstaller\dist"
    $work = Join-Path $root "build\desktop-pyinstaller\work"
    $specs = Join-Path $root "build\desktop-pyinstaller\specs"
    $staging = Join-Path $root "build\desktop-pyinstaller\staging"
    foreach ($dir in @($output, $dist, $work, $specs, $staging)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $guiEntry = Join-Path $root "apps\desktop-client\main.py"
    $serverEntry = Join-Path $PSScriptRoot "server_entry.py"
    $desktopPath = Join-Path $root "apps\desktop-client"
    $common = @("--noconfirm", "--clean", "--onedir",
        "--distpath", $dist, "--workpath", $work, "--specpath", $specs,
        "--paths", $desktopPath, "--noupx")

    Write-Host "[1/4] Building desktop GUI (PySide6)..."
    & python -m PyInstaller @common --windowed --name CodingToolsMCP --collect-data mcp_desktop_client $guiEntry
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller desktop GUI build failed" }

    Write-Host "[2/4] Building bundled core MCP server..."
    & python -m PyInstaller @common --console --name coding-tools-mcp-server $serverEntry
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller MCP server build failed" }

    $appDir = Join-Path $staging "CodingToolsMCP"
    if (Test-Path $appDir) { Remove-Item $appDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $appDir | Out-Null
    Copy-Item (Join-Path $dist "CodingToolsMCP\*") -Destination $appDir -Recurse -Force
    $serverDir = Join-Path $appDir "server"
    New-Item -ItemType Directory -Force -Path $serverDir | Out-Null
    Copy-Item (Join-Path $dist "coding-tools-mcp-server\*") -Destination $serverDir -Recurse -Force

    foreach ($exe in @((Join-Path $appDir "CodingToolsMCP.exe"),
                      (Join-Path $serverDir "coding-tools-mcp-server.exe"))) {
        if (-not (Test-Path $exe -PathType Leaf)) { throw "Missing frozen executable: $exe" }
    }

    Write-Host "[3/4] Creating portable archive..."
    $portable = Join-Path $output "CodingToolsMCP_Desktop_${DesktopVersion}_x64_Portable.zip"
    if (Test-Path $portable) { Remove-Item $portable -Force }
    Compress-Archive -Path $appDir -DestinationPath $portable -CompressionLevel Optimal

    if (-not $SkipInstaller) {
        Write-Host "[4/4] Compiling Inno Setup installer..."
        $isccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
        $iscc = if ($null -ne $isccCommand) { $isccCommand.Source } else { $null }
        if (-not $iscc) {
            $candidates = @(
                "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
                "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
                "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
            )
            $iscc = $candidates | Where-Object { Test-Path $_ -PathType Leaf } | Select-Object -First 1
        }
        if (-not $iscc) { throw "Inno Setup ISCC.exe not found; install Inno Setup first" }
        & $iscc "/DDesktopVersion=$DesktopVersion" "/DSourceDir=$appDir" "/DOutputDir=$output" (Join-Path $PSScriptRoot "installer.iss")
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed" }
    }
    Write-Host "Desktop artifacts: $output"
    Get-ChildItem $output -Filter "CodingToolsMCP_Desktop_${DesktopVersion}_x64_*" | ForEach-Object {
        Write-Host ("{0}  SHA256={1}" -f $_.Name, (Get-FileHash $_.FullName -Algorithm SHA256).Hash)
    }
} finally {
    Pop-Location
}
