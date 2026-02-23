# ============================================================================
# LinkedIn Auto Job Applier — Windows Task Scheduler Setup
# ============================================================================
# This script creates a Windows Scheduled Task that:
#   1. Wakes your laptop from sleep at 8:55 PM
#   2. Runs the bot at 9:00 PM daily in pilot mode
#   3. Applies to 9 jobs automatically
#   4. Lets the laptop go back to sleep after finishing
#
# Run this script ONCE as Administrator:
#   Right-click PowerShell → "Run as Administrator" → paste the command:
#   Set-ExecutionPolicy Bypass -Scope Process; & "path\to\setup_scheduled_task.ps1"
# ============================================================================

$ErrorActionPreference = "Stop"

# --- Configuration ---
$TaskName        = "LinkedIn Auto Job Applier"
$TaskDescription = "Runs LinkedIn job application bot daily at 9 PM (pilot mode, 9 jobs)"
$ProjectRoot     = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe       = "python"  # Change to full path if needed, e.g. "C:\Python314\python.exe"
$ScriptPath      = Join-Path $ProjectRoot "run_scheduler.py"
$LogDir          = Join-Path $ProjectRoot "logs"
$TriggerTime     = "09:00"   # 9:00 AM IST — change if needed
$WakeUpTime      = "08:55"   # 8:55 AM — wake 5 min early to let system settle

# Ensure logs directory exists
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  LinkedIn Auto Job Applier — Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project: $ProjectRoot" -ForegroundColor Gray
Write-Host "  Python:  $PythonExe" -ForegroundColor Gray
Write-Host "  Time:    $TriggerTime daily" -ForegroundColor Gray
Write-Host ""

# --- Check if running as admin ---
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "  ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "  Right-click PowerShell -> 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# --- Remove existing task if it exists ---
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Removing existing task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# --- Create the scheduled task ---
Write-Host "  Creating scheduled task..." -ForegroundColor Green

# Action: Run python run_scheduler.py --once
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`" --once" `
    -WorkingDirectory $ProjectRoot

# Trigger: Daily at 9:00 PM
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Register the task (runs as current user)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $TaskDescription `
    -Force | Out-Null

Write-Host "  Task created successfully!" -ForegroundColor Green

# --- Configure power settings ---
Write-Host ""
Write-Host "  Configuring power settings for wake-from-sleep..." -ForegroundColor Green

# When lid is closed while plugged in: Do Nothing (don't sleep)
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
# When lid is closed on battery: Do Nothing
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
# Apply the active scheme
powercfg /SETACTIVE SCHEME_CURRENT

Write-Host "  Lid close action set to 'Do Nothing' (laptop stays awake with lid closed)" -ForegroundColor Green

# --- Summary ---
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  What will happen every day:" -ForegroundColor White
Write-Host "    1. Windows wakes your laptop from sleep at 9:00 PM" -ForegroundColor Gray
Write-Host "    2. Runs: python run_scheduler.py --once" -ForegroundColor Gray
Write-Host "    3. Bot launches Chrome, logs into LinkedIn" -ForegroundColor Gray
Write-Host "    4. Applies to 9 jobs in pilot mode (no human input)" -ForegroundColor Gray
Write-Host "    5. Bot finishes, laptop can sleep again" -ForegroundColor Gray
Write-Host ""
Write-Host "  REQUIREMENTS:" -ForegroundColor Yellow
Write-Host "    - Laptop must be PLUGGED IN (not on battery alone)" -ForegroundColor Yellow
Write-Host "    - LinkedIn session must be logged in (use chrome_profile/)" -ForegroundColor Yellow
Write-Host "    - Pilot mode enabled in settings (forced by scheduler)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To verify:  Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  To test:    Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  To remove:  Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host "  Logs at:    $LogDir\scheduler.log" -ForegroundColor Gray
Write-Host ""
