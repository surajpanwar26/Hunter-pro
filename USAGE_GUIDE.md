# 🚀 LinkedIn Auto-Job Applier - Complete Usage Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Dashboard Features](#dashboard-features)
4. [Pilot Mode (Fully Automated)](#pilot-mode)
5. [Scheduled Runs](#scheduled-runs)
6. [Chrome Extension Setup](#chrome-extension)
7. [Configuration Guide](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview <a name="overview"></a>

The LinkedIn Auto-Job Applier is a powerful automation tool that helps you apply to jobs on LinkedIn with minimal effort. It features:

- **🚀 Pilot Mode**: Fully automated job applications without any user intervention
- **📅 Scheduled Runs**: Automatically apply to jobs on a timer
- **🤖 AI-Powered Resume Tailoring**: Customize your resume for each job using Groq AI
- **✨ Smart Form Filling**: Intelligently fills out Easy Apply forms
- **🌐 Chrome Extension**: Auto-fill forms with your saved profile data

---

## 🚀 Getting Started <a name="getting-started"></a>

### Prerequisites
1. **Python 3.10+** installed
2. **Chrome Browser** (latest version recommended)
3. **LinkedIn Account** with Easy Apply access
4. **Groq API Key** (free at https://console.groq.com)

### Installation Steps

```bash
# 1. Clone or download the repository
cd Auto_job_applier_linkedIn

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your settings
# Edit config/settings.py with your preferences
```

### First Run

```bash
# Launch the Dashboard
python run_dashboard.py
```

---

## 🖥️ Dashboard Features <a name="dashboard-features"></a>

### Main Dashboard Layout

The dashboard is organized into sections:

```
┌─────────────────────────────────────────────────────────────┐
│  🚀 AUTOMATION CONTROL CENTER                    ⬤ STATUS  │
├─────────────────────────────────────────────────────────────┤
│  [🚀 START PILOT MODE]  [📅 START SCHEDULED]  [🔧 NORMAL]  │
├─────────────────────────────────────────────────────────────┤
│  ✈️ PILOT MODE Settings                                     │
│  📅 SCHEDULING Settings                                     │
├─────────────────────────────────────────────────────────────┤
│  🤖 Bot Behavior | ⚡ Form Filling | 📄 Resume | 🖥️ Browser │
└─────────────────────────────────────────────────────────────┘
```

### Quick Start Buttons

| Button | Action |
|--------|--------|
| **🚀 START PILOT MODE** | Enables pilot mode and immediately starts the bot |
| **📅 START SCHEDULED** | Enables scheduling and starts the scheduler |
| **🔧 NORMAL MODE** | Disables automation, returns to manual control |

---

## ✈️ Pilot Mode (Fully Automated) <a name="pilot-mode"></a>

Pilot Mode allows the bot to apply to jobs **completely hands-free** without any confirmation dialogs.

### Settings

| Setting | Description | Options |
|---------|-------------|---------|
| **✈️ Pilot Mode Enabled** | Master toggle for pilot mode | On/Off |
| **📄 Resume Mode** | How to handle resumes | `tailored`, `default`, `skip` |
| **⏱️ Delay (sec)** | Wait time between applications | 1-30 seconds |
| **📊 Max Apps (0=∞)** | Maximum applications per session | 0-500 |
| **🔄 Continue on Errors** | Keep going if an application fails | On/Off |

### Resume Modes Explained

| Mode | Behavior |
|------|----------|
| **tailored** | AI generates a customized resume for each job (uses Groq API) |
| **default** | Uses the pre-selected resume already in LinkedIn's form (no upload) |
| **skip** | Does not interact with resume upload at all |

### When to Use Each Mode

- **tailored**: Best for quality applications, uses AI to customize each resume
- **default**: Best for speed, trusts LinkedIn's existing resume selection
- **skip**: Best when you've already uploaded your resume to LinkedIn

### Starting Pilot Mode

**Method 1: Quick Start Button**
```
Click [🚀 START PILOT MODE] button at the top of settings
```

**Method 2: Manual Toggle**
```
1. Enable "✈️ Pilot Mode Enabled" toggle
2. Configure your settings
3. Click "▶️ Start Bot" button
```

---

## 📅 Scheduled Runs <a name="scheduled-runs"></a>

Schedule the bot to run automatically at specific intervals - no dashboard needed!

### Settings

| Setting | Description | Options |
|---------|-------------|---------|
| **📅 Scheduling Enabled** | Master toggle for scheduling | On/Off |
| **Type** | Schedule pattern | `interval`, `daily`, `weekly` |
| **⏱️ Interval (hrs)** | Hours between runs | 1-24 |
| **⏳ Max Runtime (min)** | Maximum duration per session | 10-480 |
| **📊 Max Apps** | Maximum applications per session | 0-200 |

### Schedule Types

| Type | Description |
|------|-------------|
| **interval** | Runs every X hours continuously |
| **daily** | Runs once per day at a specific time |
| **weekly** | Runs on specific days of the week |

### Starting Scheduled Runs

**Method 1: Quick Start Button**
```
Click [📅 START SCHEDULED RUN] button
```

**Method 2: Command Line**
```bash
python run_scheduler.py --start
```

**Method 3: Headless Mode (No GUI)**
```bash
python run_pilot_mode.py --headless --max-apps 50
```

### Scheduler Status

The dashboard shows:
- **⏸️ Stopped** - Scheduler is not running
- **▶️ Running** - Scheduler is active
- **📅 Next run: X** - When the next scheduled run will start

---

## 🌐 Chrome Extension Setup <a name="chrome-extension"></a>

The Chrome Extension helps auto-fill LinkedIn Easy Apply forms with your saved profile data.

### Installation

1. **Open Chrome Extensions Page**
   ```
   Navigate to: chrome://extensions/
   ```

2. **Enable Developer Mode**
   ```
   Toggle "Developer mode" switch in the top-right corner
   ```

3. **Load the Extension**
   ```
   Click "Load unpacked" → Select the "extension" folder
   ```

4. **Pin the Extension**
   ```
   Click the puzzle icon → Pin "LinkedIn Auto-Fill Pro"
   ```

### First-Time Setup

1. **Click the Extension Icon** in Chrome toolbar

2. **Fill in Your Profile**:
   - Personal Information (name, email, phone)
   - Work Information (company, title, experience)
   - Links (LinkedIn, GitHub, Portfolio)
   - Common Answers (work authorization, sponsorship)
   - Education details

3. **Click "💾 Save All Changes"**

### Using the Extension

1. **Navigate to a Job on LinkedIn**

2. **Click "Easy Apply"** to open the application modal

3. **Click the Extension Icon**

4. **Click "✨ Auto-Fill Form"**

5. **Review and Submit**

### Extension Features

| Feature | Description |
|---------|-------------|
| **Auto-Fill Form** | Fills all detected fields with your saved data |
| **Analyze Fields** | Shows which fields were detected and filled |
| **Form Status** | Shows total/filled/empty field counts |
| **Profile Tab** | Edit your personal information |
| **Answers Tab** | Set common question answers |
| **Settings Tab** | Configure auto-detect, notifications, etc. |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt+F` | Auto-fill current form |
| `Alt+A` | Analyze current form |

---

## ⚙️ Configuration Guide <a name="configuration"></a>

### Main Settings File

Edit `config/settings.py` to configure:

```python
# === PILOT MODE ===
pilot_mode_enabled = False      # Enable/disable pilot mode
pilot_resume_mode = "tailored"  # "tailored", "default", or "skip"
pilot_max_applications = 0      # 0 = unlimited
pilot_application_delay = 5     # seconds between applications
pilot_continue_on_error = True  # continue if an application fails

# === SCHEDULING ===
scheduling_enabled = False
schedule_type = "interval"      # "interval", "daily", "weekly"
schedule_interval_hours = 4
schedule_max_runtime = 120      # minutes
schedule_max_applications = 50

# === BOT BEHAVIOR ===
run_non_stop = True             # Keep searching for jobs
alternate_sortby = True         # Alternate between sort methods
max_jobs_to_process = 0         # 0 = unlimited

# === FORM FILLING ===
form_fill_fast_mode = True
use_smart_form_filler = True
form_fill_delay_multiplier = 0.5

# === RESUME TAILORING ===
resume_tailoring_enabled = True
```

### Resume Configuration

Place your resume files in:
- **Master Resume**: `all resumes/master resume/your_resume.pdf`
- **Default Resume**: `all resumes/default/resume.pdf`

### Profile Questions

Edit `config/questions.yaml` to set answers for common questions:
- Work authorization
- Visa sponsorship
- Years of experience
- Notice period
- Salary expectations

---

## 🔧 Troubleshooting <a name="troubleshooting"></a>

### Common Issues

#### Bot Not Starting
```
✅ Check: Is Chrome installed and up to date?
✅ Check: Are all dependencies installed? (pip install -r requirements.txt)
✅ Check: Is the chrome_profile folder accessible?
```

#### Resume Not Uploading
```
✅ Check: Resume file exists in the correct folder
✅ Check: Resume format is PDF or DOCX
✅ Check: pilot_resume_mode is set to "tailored" not "default"
```

#### Form Fields Not Filling
```
✅ Check: questions.yaml has answers for the fields
✅ Check: Smart Form Filler is enabled
✅ Check: The form element is visible on screen
```

#### Scheduler Not Starting
```
✅ Check: scheduling_enabled = True
✅ Check: pilot_mode_enabled = True (scheduling requires pilot mode)
✅ Check: No other instance is already running
```

#### Extension Not Working
```
✅ Check: Extension is enabled in chrome://extensions/
✅ Check: You've saved your profile data
✅ Check: You're on a LinkedIn page
✅ Check: Easy Apply modal is open
```

### DLP Popup Handling (Corporate Networks)

If you're on a corporate network with DLP (Data Loss Prevention):

1. The bot automatically handles Deloitte DLP popups
2. Make sure `pyautogui` is installed
3. Keep the browser window visible (not minimized)

### Log Files

Check logs for debugging:
```
logs/
├── application_log.txt      # Main application log
├── error_log.txt            # Error messages
├── scheduler_log.txt        # Scheduler activity
└── ai_responses.txt         # AI/Groq responses
```

### Getting Help

1. Check the logs in the `logs/` folder
2. Enable Debug Mode in Settings
3. Review the console output for error messages

---

## 📊 Best Practices

### For Maximum Efficiency

1. **Use Pilot Mode** for batch applications
2. **Set Max Apps** to prevent over-applying
3. **Use Default Resume Mode** for speed
4. **Schedule During Off-Hours** for better success rates

### For Quality Applications

1. **Use Tailored Resume Mode**
2. **Set Longer Delays** between applications
3. **Review AI-Generated Resumes** periodically
4. **Keep Profile Data Updated**

### Safety Tips

1. **Don't Apply Too Fast** - LinkedIn may flag your account
2. **Vary Your Schedule** - Don't run at exactly the same times
3. **Monitor Your Applications** - Check the Excel logs regularly
4. **Keep Resume Updated** - Ensure master resume has current info

---

## 📝 Changelog

### Version 2.0.0
- ✅ Pilot Mode for fully automated applications
- ✅ Scheduled runs with interval/daily/weekly options
- ✅ Chrome Extension for form auto-fill
- ✅ Improved dashboard with quick-start buttons
- ✅ Resume mode selection (tailored/default/skip)
- ✅ Settings validation to prevent conflicts
- ✅ Better mouse wheel scrolling in dashboard

---

**Need more help?** Open an issue on GitHub or check the README.md for additional documentation.
