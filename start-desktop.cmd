@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo Coding Tools MCP Desktop Launcher
echo ========================================

rem Prefer a repository-local virtual environment when available.
if exist ".venv\Scripts\coding-tools-mcp-desktop.exe" (
    echo [INFO] Using repository .venv
    ".venv\Scripts\coding-tools-mcp-desktop.exe"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :finish
)

rem Fall back to the Conda environment used by the Windows desktop setup.
where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Conda was not found in PATH.
    echo.
    echo Install Miniconda/Anaconda or create a repository .venv first.
    echo Expected Conda environment: coding-tools-mcp
    echo.
    pause
    exit /b 1
)

rem Create the dedicated environment automatically on first launch.
conda run -n coding-tools-mcp python --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] Conda environment "coding-tools-mcp" was not found.
    echo [INFO] Creating Python 3.11 environment...
    call conda create -n coding-tools-mcp python=3.11 -y
    if errorlevel 1 goto :setup_failed
)

rem Install/update the editable desktop package only when it is not currently importable.
conda run -n coding-tools-mcp python -c "import mcp_desktop_client, PySide6, psutil" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing desktop dependencies from this repository...
    call conda run -n coding-tools-mcp python -m pip install -U pip
    if errorlevel 1 goto :setup_failed
    call conda run -n coding-tools-mcp python -m pip install -e ".[desktop]"
    if errorlevel 1 goto :setup_failed
)

echo [INFO] Starting Coding Tools MCP Desktop...
call conda run --no-capture-output -n coding-tools-mcp coding-tools-mcp-desktop
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:setup_failed
echo.
echo [ERROR] Desktop environment setup failed.
echo Run the following commands manually to inspect the error:
echo   conda create -n coding-tools-mcp python=3.11 -y
echo   conda run -n coding-tools-mcp python -m pip install -e ".[desktop]"
echo.
pause
exit /b 1

:finish
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Desktop client exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
