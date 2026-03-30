param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "restart"
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BotScript = Join-Path $ProjectDir "bot.py"
$PreferredPython = "C:\Users\nyama\AppData\Local\Programs\Python\Python311\python.exe"
$FallbackPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$LockFile = Join-Path $ProjectDir "data\bot.lock"

function Resolve-PythonPath {
    if (Test-Path -LiteralPath $PreferredPython) {
        return $PreferredPython
    }
    if (Test-Path -LiteralPath $FallbackPython) {
        return $FallbackPython
    }
    throw "Python interpreter not found."
}

function Get-BotProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -match [regex]::Escape($BotScript)
        }
}

function Stop-Bot {
    $procs = Get-BotProcesses
    if (-not $procs) {
        if (Test-Path -LiteralPath $LockFile) {
            Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
        }
        Write-Output "Bot is already stopped."
        return
    }

    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 1
    if (Test-Path -LiteralPath $LockFile) {
        Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
    }
    Write-Output "Bot stopped."
}

function Start-Bot {
    $python = Resolve-PythonPath
    $existing = Get-BotProcesses
    if ($existing) {
        $ids = ($existing | Select-Object -ExpandProperty ProcessId) -join ", "
        Write-Output "Bot already running. PID: $ids"
        return
    }

    $proc = Start-Process -FilePath $python -ArgumentList "`"$BotScript`"" -WorkingDirectory $ProjectDir -PassThru
    Start-Sleep -Seconds 2

    if (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
        Write-Output "Bot started. PID: $($proc.Id)"
    } else {
        throw "Bot failed to start."
    }
}

function Show-Status {
    $procs = Get-BotProcesses
    if (-not $procs) {
        Write-Output "Bot status: stopped"
        return
    }
    $procs | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize
}

switch ($Action) {
    "start"   { Start-Bot }
    "stop"    { Stop-Bot }
    "restart" { Stop-Bot; Start-Bot }
    "status"  { Show-Status }
}

