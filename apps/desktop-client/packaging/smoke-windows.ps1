# Smoke the portable bundle and installed bundle on a clean Windows runner.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $AppDir,
    [string] $Installer = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Test-FrozenApplication([string] $Folder) {
    $gui = Join-Path $Folder "CodingToolsMCP.exe"
    $server = Join-Path $Folder "server\coding-tools-mcp-server.exe"
    foreach ($exe in @($gui, $server)) {
        if (-not (Test-Path $exe -PathType Leaf)) { throw "Executable not found: $exe" }
    }

    $work = Join-Path $env:TEMP ("coding tools 中文 workspace " + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $socket = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $socket.Start()
    $port = ([System.Net.IPEndPoint]$socket.LocalEndpoint).Port
    $socket.Stop()

    $oldAuth = $env:CODING_TOOLS_MCP_AUTH_MODE
    $oldQt = $env:QT_QPA_PLATFORM
    $env:CODING_TOOLS_MCP_AUTH_MODE = "noauth"
    $stdout = Join-Path $work "server-stdout.log"
    $stderr = Join-Path $work "server-stderr.log"
    $serverProcess = $null
    $guiProcess = $null
    try {
        Write-Host "Testing frozen server in $Folder on port $port"
        $serverArgs = @("--workspace", ('"' + $work + '"'), "--host", "127.0.0.1",
                        "--port", "$port", "--permission-mode", "safe")
        $serverProcess = Start-Process -FilePath $server -WorkingDirectory $work -PassThru -ArgumentList $serverArgs -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            $serverProcess.Refresh()
            if ($serverProcess.HasExited) { break }
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/.well-known/mcp.json" -TimeoutSec 2
                if ($response.StatusCode -eq 200) { $ready = $true; break }
            } catch {
                Start-Sleep -Milliseconds 500
            }
        }
        if (-not $ready) {
            $out = if (Test-Path $stdout) { Get-Content $stdout -Raw } else { "" }
            $err = if (Test-Path $stderr) { Get-Content $stderr -Raw } else { "" }
            throw "Frozen MCP server did not serve HTTP metadata. stdout=$out stderr=$err"
        }
        Write-Host "Frozen MCP HTTP health check passed."

        # Offscreen avoids requiring a logged-in graphical desktop in CI.
        $env:QT_QPA_PLATFORM = "offscreen"
        $guiProcess = Start-Process -FilePath $gui -WorkingDirectory $Folder -PassThru
        Start-Sleep -Seconds 4
        $guiProcess.Refresh()
        if ($guiProcess.HasExited) {
            throw "Frozen GUI exited unexpectedly with code $($guiProcess.ExitCode)"
        }
        Write-Host "Frozen Qt desktop launch check passed."
    } finally {
        if ($null -ne $guiProcess -and -not $guiProcess.HasExited) {
            Stop-Process -Id $guiProcess.Id -Force
        }
        if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
        $env:CODING_TOOLS_MCP_AUTH_MODE = $oldAuth
        $env:QT_QPA_PLATFORM = $oldQt
        Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Test-FrozenApplication $AppDir

if ($Installer) {
    $installDir = Join-Path $env:TEMP ("coding tools installed " + [guid]::NewGuid().ToString("N"))
    Write-Host "Installing silently into $installDir"
    $args = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", ('/DIR="' + $installDir + '"'))
    $setupProcess = Start-Process -FilePath $Installer -ArgumentList $args -Wait -PassThru
    if ($setupProcess.ExitCode -ne 0) { throw "Inno installer failed: $($setupProcess.ExitCode)" }
    try {
        Test-FrozenApplication $installDir
    } finally {
        $uninstaller = Join-Path $installDir "unins000.exe"
        if (Test-Path $uninstaller) {
            $uninstallProcess = Start-Process -FilePath $uninstaller -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait -PassThru
            if ($uninstallProcess.ExitCode -ne 0) { throw "Uninstall failed: $($uninstallProcess.ExitCode)" }
        }
    }
}
