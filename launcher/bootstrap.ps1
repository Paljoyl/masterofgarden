param(
    [ValidateSet('gui', 'check', 'check-ui', 'setup-python')]
    [string]$Mode = 'gui',
    [switch]$Offline,
    [switch]$LibraryOnly
)
$ErrorActionPreference = 'Stop'
$releaseRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
# Interpreter discovery must never trigger Python Manager/legacy launcher installs.
$env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
Remove-Item Env:PYLAUNCHER_ALLOW_INSTALL -ErrorAction SilentlyContinue
Remove-Item Env:PYLAUNCHER_ALWAYS_INSTALL -ErrorAction SilentlyContinue

function Test-ReleasePython {
    param([string]$Executable, [switch]$RequireQt)
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $false }
    $code = 'import sys,venv,ensurepip; assert (3,10) <= sys.version_info[:2] < (3,15); assert sys.maxsize > 2**32'
    if ($RequireQt) { $code += '; from launcher.qt import QApplication' }
    try {
        & $Executable -c $code 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-ReleasePython {
    param([switch]$RequireQt)
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($relative in @('runtime/launcher-env/Scripts/python.exe', 'runtime/server-env/Scripts/python.exe', 'runtime/python/python.exe')) {
        $candidates.Add((Join-Path $releaseRoot $relative))
    }
    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $installed = @()
        try {
            # Listing installed runtimes avoids requesting a missing version.
            $installed = @(& $pyCommand.Source -0p 2>$null)
            if ($LASTEXITCODE -ne 0) { $installed = @() }
        } catch {
            Write-Warning '无法读取 Python 启动器列表，继续查找其他已安装环境。'
        }
        # PowerShell single-quoted strings retain regex backslashes verbatim.
        # Parse outside the native-command catch so a parser error cannot be hidden.
        foreach ($line in $installed) {
            if ([string]$line -match '(?i)((?:[A-Z]:\\|\\\\)[^\r\n]*?python(?:w)?\.exe)\s*$') {
                $candidates.Add($Matches[1].Trim())
            }
        }
    }
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notlike '*\WindowsApps\*') { $candidates.Add($pythonCommand.Source) }
    if ($env:LOCALAPPDATA) {
        $installations = Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Programs/Python') -Directory -ErrorAction SilentlyContinue
        foreach ($installation in $installations) { $candidates.Add((Join-Path $installation.FullName 'python.exe')) }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-ReleasePython -Executable $candidate -RequireQt:$RequireQt) { return $candidate }
    }
    return $null
}

function Invoke-ReleaseBootstrap {
    param([string]$Action = "gui", [switch]$SkipNetwork)
    $locationPushed = $false
try {
    Push-Location -LiteralPath $releaseRoot
    $locationPushed = $true
    if ($Action -in @('check','check-ui')) {
        $python = Find-ReleasePython -RequireQt:($Action -eq 'check-ui')
        if (-not $python) { throw '未检测到已安装的 Python 或所需界面组件。请先安装 Python，再运行启动器；Python 本体不会自动下载。' }
        $arguments = @('-B','-m','launcher',('--'+$Action))
        if ($SkipNetwork) { $arguments += '--offline' }
        & $python @arguments | Out-Host
        $result = $LASTEXITCODE
    } elseif ($Action -eq 'setup-python') {
        $python = Find-ReleasePython
        if (-not $python) { throw '未检测到已安装的 64 位 Python 3.10–3.14。请先安装 Python，再重新打开启动器；不会自动下载 Python。' }
        & $python -B -m launcher --setup-python | Out-Host
        $result = $LASTEXITCODE
    } else {
        $python = Find-ReleasePython -RequireQt
        if (-not $python) {
            $python = Find-ReleasePython
            if (-not $python) { throw '未检测到已安装的 64 位 Python 3.10–3.14。请先安装 Python，再重新打开启动器；不会自动下载 Python。' }
            Write-Host '正在自动配置启动器界面依赖…'
            & $python -B -m launcher --setup-launcher | Out-Host
            if ($LASTEXITCODE -ne 0) { throw '启动器依赖准备失败，请重试并查看本机配置日志。' }
            $python = Join-Path $releaseRoot 'runtime/launcher-env/Scripts/python.exe'
        }
        & $python -B -m launcher | Out-Host
        $result = $LASTEXITCODE
    }
    return $result
} catch {
    Write-Host 'Python 配置未完成：' $_.Exception.Message
    Write-Host '请处理提示的问题后重试。依赖配置日志保存在本机 runtime/logs。'
    return 2
} finally {
    if ($locationPushed) { Pop-Location }
}
}

if ($LibraryOnly) { return }
exit (Invoke-ReleaseBootstrap -Action $Mode -SkipNetwork:$Offline)
