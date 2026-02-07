# 🚀 New Features: Pilot Mode, Scheduling & Chrome Extension

This document describes the new features added to the LinkedIn Auto Job Applier.

## 📋 Table of Contents

1. [Pilot Mode](#-pilot-mode)
2. [Scheduling Feature](#-scheduling-feature)
3. [Chrome Extension](#-chrome-extension)
4. [Configuration Guide](#-configuration-guide)

---

## 🎯 Pilot Mode

**Pilot Mode** allows the bot to run completely hands-free without any confirmation dialogs or user intervention.

### Features
- ✅ Fully automated job application
- ✅ Choose between tailored or default resume
- ✅ Configurable application limits
- ✅ Configurable delay between applications
- ✅ Continue on errors option
- ✅ Auto-restart on crash

### How to Enable

1. **Via Dashboard:**
   - Open the dashboard: `python run_dashboard.py`
   - Go to **Quick Settings**
   - Find **Section 6: 🚀 Pilot Mode**
   - Toggle "Enable Pilot Mode"
   - Select resume mode (Tailored/Default)
   - Set max applications and delay

2. **Via Configuration:**
   Edit `config/settings.py`:
   ```python
   pilot_mode_enabled = True
   pilot_resume_mode = "tailored"  # or "default"
   pilot_max_applications = 100
   pilot_application_delay = 30  # seconds
   ```

### Settings Explained

| Setting | Description | Default |
|---------|-------------|---------|
| `pilot_mode_enabled` | Enable/disable pilot mode | `False` |
| `pilot_resume_mode` | "tailored" (AI-generated) or "default" | "tailored" |
| `pilot_max_applications` | Max applications per session | 100 |
| `pilot_application_delay` | Delay between applications (seconds) | 30 |
| `pilot_continue_on_error` | Continue after errors | `True` |

---

## ⏰ Scheduling Feature

Schedule automatic job application runs without keeping the dashboard open.

### Schedule Types

1. **Interval** - Run every X hours
2. **Daily** - Run at specific times each day
3. **Weekly** - Run on specific days at specific times

### How to Enable

1. **Via Dashboard:**
   - Open the dashboard
   - Go to **Section 7: ⏰ Scheduling**
   - Enable scheduling
   - Select schedule type
   - Configure parameters
   - Click "Start Scheduler"

2. **Via Background Service:**
   ```bash
   # Run scheduler daemon
   python run_scheduler.py
   
   # Run once and exit
   python run_scheduler.py --once
   
   # Show configuration
   python run_scheduler.py --config
   
   # Setup Windows Task Scheduler
   python run_scheduler.py --setup-windows
   
   # Setup cron job (Linux/macOS)
   python run_scheduler.py --setup-cron
   ```

### Windows Task Scheduler Setup

```powershell
# PowerShell (Run as Admin)
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "run_scheduler.py --once" -WorkingDirectory "C:\path\to\project"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "LinkedIn Auto Job Applier" -Action $action -Trigger $trigger
```

### Cron Job Setup (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add line to run daily at 9 AM
0 9 * * * cd /path/to/project && /usr/bin/python3 run_scheduler.py --once >> logs/cron.log 2>&1
```

### Configuration

Edit `config/settings.py`:
```python
scheduling_enabled = True
schedule_type = "interval"  # "interval", "daily", "weekly"
schedule_interval_hours = 4
schedule_max_runtime = 60  # minutes
schedule_max_applications = 50
```

Advanced settings in `config/pilot_settings.py`:
```python
schedule_daily_times = ["09:00", "17:00"]
schedule_weekly = {
    "monday": ["09:00", "18:00"],
    "tuesday": ["09:00", "18:00"],
    # ...
}
```

---

## 🧩 Chrome Extension

The **LinkedIn AutoFill Pro** extension helps auto-detect and fill LinkedIn Easy Apply form fields.

### Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `extension/` folder

### Features

- ✅ Auto-detect Easy Apply modal
- ✅ Fill personal information automatically
- ✅ Save profile data for reuse
- ✅ Form analysis to see what fields are detected
- ✅ History tracking of filled forms
- ✅ Customizable fill settings

### Extension Files

```
extension/
├── manifest.json        # Extension manifest
├── universal_content.js # Form detection & filling (content script)
├── resume_engine.js     # ATS scoring + keyword analysis
├── popup.html           # Extension popup UI
├── popup.js             # Popup functionality
├── background.js        # Service worker
├── styles.css           # Popup styles
└── icons/               # Extension icons
```

### How to Use

1. **Setup Profile:**
   - Click the extension icon
   - Fill in your personal information
   - Click "Save Profile"

2. **Auto-Fill:**
   - Navigate to a LinkedIn job posting
   - Click "Easy Apply"
   - Click "Auto-Fill Form" in the extension

3. **Analyze:**
   - Click "Analyze" to see detected fields
   - View which fields are recognized
   - Check what's already filled

---

## ⚙️ Configuration Guide

### File Locations

| File | Purpose |
|------|---------|
| `config/settings.py` | Main application settings |
| `config/pilot_settings.py` | Pilot mode & scheduling config |
| `logs/scheduler_state.json` | Scheduler state persistence |
| `logs/scheduler.log` | Scheduler activity log |

### Quick Start

1. **For Pilot Mode Only:**
   ```bash
   python run_dashboard.py
   # Enable Pilot Mode in Quick Settings
   # Click Start Bot
   ```

2. **For Scheduled Runs:**
   ```bash
   # Configure in dashboard first
   python run_dashboard.py
   # Enable Scheduling, configure, save
   
   # Then run background scheduler
   python run_scheduler.py
   ```

3. **For Extension:**
   - Load extension in Chrome
   - Configure profile data
   - Use on LinkedIn Easy Apply forms

### Safety Limits

The following safety limits help prevent issues:

- Daily application limit: 100 (configurable)
- Max applications per session: 50 (configurable)
- Max runtime per session: 60 minutes (configurable)
- Delay between applications: 30 seconds (configurable)
- Cooldown after daily limit: 12 hours

---

## 🔧 Troubleshooting

### Pilot Mode Not Working
1. Check `pilot_mode_enabled = True` in settings
2. Ensure bot has proper LinkedIn credentials
3. Check logs for errors

### Scheduler Not Running
1. Verify `scheduling_enabled = True`
2. Check `logs/scheduler.log` for errors
3. Ensure no firewall blocking

### Extension Not Detecting Fields
1. Refresh the LinkedIn page
2. Make sure you're on an Easy Apply form
3. Check browser console for errors

---

## 📝 Changelog

### v2.0.0 (Latest)
- ✨ Added Pilot Mode for fully automated operation
- ✨ Added Scheduling feature with interval/daily/weekly options
- ✨ Added Chrome Extension for form auto-fill
- ✨ Added background scheduler service
- 🔧 Updated dashboard with new settings panels
- 📖 Comprehensive documentation

---

**Author:** Suraj Panwar  
**License:** MIT
