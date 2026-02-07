'''
PILOT MODE & SCHEDULING CONFIGURATION
======================================
Configure fully automated job application settings here.

Author: Suraj Panwar
'''

# ================================
# PILOT MODE SETTINGS
# ================================
# Pilot Mode - Fully automated job application without any user prompts

# Enable pilot mode - when True, bot runs completely hands-free
pilot_mode_enabled = False

# Resume Mode for Pilot
# Options: "tailored" (AI-tailored for each job), "default" (use default resume)
pilot_resume_mode = "tailored"

# Skip all confirmation dialogs in pilot mode
pilot_skip_confirmations = True

# Continue applying even after errors (with retry)
pilot_continue_on_error = True

# Maximum retries per job before skipping
pilot_max_retries_per_job = 2

# Delay between applications in pilot mode (seconds) - helps avoid detection
pilot_delay_between_applications = 5

# Maximum applications per session in pilot mode (0 = unlimited)
pilot_max_applications_per_session = 0

# Auto-restart if session crashes
pilot_auto_restart = True

# ================================
# SCHEDULING SETTINGS
# ================================
# Schedule automatic job application runs

# Enable scheduling feature
scheduling_enabled = False

# Schedule type: "interval", "daily", "weekly"
schedule_type = "interval"

# For interval scheduling - time between runs (in hours)
schedule_interval_hours = 4

# For daily scheduling - specific times to run (24-hour format)
# Example: ["09:00", "14:00", "20:00"]
schedule_daily_times = ["09:00", "17:00"]

# For weekly scheduling - days and times
# Format: {"day": ["HH:MM", ...], ...}
# Days: "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
schedule_weekly = {
    "monday": ["09:00", "18:00"],
    "tuesday": ["09:00", "18:00"],
    "wednesday": ["09:00", "18:00"],
    "thursday": ["09:00", "18:00"],
    "friday": ["09:00", "18:00"],
    "saturday": ["10:00"],
    "sunday": []
}

# Maximum runtime per scheduled session (minutes) - prevents runaway sessions
schedule_max_runtime_minutes = 120

# Applications per scheduled session (0 = unlimited, respects max)
schedule_applications_per_session = 50

# Notification settings for scheduled runs
schedule_notify_on_start = True
schedule_notify_on_complete = True
schedule_notify_on_error = True

# Notification method: "desktop", "email", "both"
schedule_notification_method = "desktop"

# Email notification settings (if email enabled)
schedule_email_to = ""
schedule_email_smtp_server = ""
schedule_email_smtp_port = 587
schedule_email_username = ""
schedule_email_password = ""

# ================================
# PILOT MODE SAFETY SETTINGS
# ================================
# Safety limits to prevent excessive applications

# Daily application limit (across all sessions)
daily_application_limit = 100

# Cool down period after hitting limit (hours)
cooldown_hours = 12

# Minimum time between same company applications (hours)
min_time_between_company_applications = 24

# Blacklisted companies (will skip these)
blacklisted_companies = []

# Required keywords in job title (empty = no filter)
required_keywords = []

# Excluded keywords in job title
excluded_keywords = []

# ================================
# RESUME SETTINGS FOR PILOT MODE
# ================================
# Which resume to use in pilot mode

# Default resume file path (for pilot_resume_mode = "default")
default_resume_path = "all resumes/default/default_resume.pdf"

# Master resume for tailoring (for pilot_resume_mode = "tailored")
master_resume_path = "all resumes/master resume/"

# Resume tailoring strength in pilot mode
# Options: "light", "moderate", "aggressive"
pilot_tailoring_strength = "moderate"

# Always include these sections unchanged
preserve_sections = ["Contact", "Education", "Certifications"]

# ================================
# LOGGING & REPORTING
# ================================
# Detailed logging for pilot mode operations

# Enable detailed pilot mode logging
pilot_verbose_logging = True

# Save daily reports
pilot_save_daily_report = True

# Report save location
pilot_report_path = "logs/pilot_reports/"

# Generate summary email after scheduled runs
pilot_generate_summary = True
