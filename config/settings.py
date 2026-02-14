'''
Author:     Suraj Panwar

            
GitHub:     https://github.com/surajpanwar26

'''


###################################################### CONFIGURE YOUR BOT HERE ######################################################

# >>>>>>>>>>> LinkedIn Settings <<<<<<<<<<<

# Keep the External Application tabs open?
close_tabs = False                  # True or False, Note: True or False are case-sensitive
'''
Note: RECOMMENDED TO LEAVE IT AS `True`, if you set it `False`, be sure to CLOSE ALL TABS BEFORE CLOSING THE BROWSER!!!
'''

# Follow easy applied companies
follow_companies = False            # True or False, Note: True or False are case-sensitive

## Upcoming features (In Development)
# # Send connection requests to HR's 
# connect_hr = True                  # True or False, Note: True or False are case-sensitive

# # What message do you want to send during connection request? (Max. 200 Characters)
# connect_request_message = ""       # Leave Empty to send connection request without personalized invitation (recommended to leave it empty, since you only get 10 per month without LinkedIn Premium*)

# Do you want the program to run continuously until you stop it? (Beta)
'''
Note: Will be treated as False if `run_in_background = False`
'''
# alternate_sortby is configured in job processing settings below

# Settings for processing multiple jobs (not single job)
run_non_stop = True                # Ensure continuous run for multiple jobs
max_jobs_to_process = 2            # 0 means unlimited jobs
alternate_sortby = False            # Alternate between sorting options (Most Recent/Most Relevant)
cycle_date_posted = True           # Cycle through date posted for more jobs
stop_date_cycle_at_24hr = True     # Stop cycling at 24hr if needed

# >>>>>>>>>>> FORM FILLING SPEED SETTINGS <<<<<<<<<<<
# Set form_fill_fast_mode to True for faster form filling (less human-like but faster)
# Set to False for slower, more human-like behavior (safer but slower)
form_fill_fast_mode = True         # True = Fast mode (recommended), False = Slow mode
form_fill_delay_multiplier = 0.5    # Delay multiplier (0.5 = 50% of normal delays, 1.0 = normal)

# >>>>>>>>>>> NEW SMART FORM FILLER V2 <<<<<<<<<<<
# Use the rebuilt form filler with better page analysis and faster filling
# This is the new implementation that detects elements more accurately
use_smart_form_filler = True       # True = Use new v2 filler, False = Use legacy filler


# >>>>>>>>>>> PILOT MODE (FULLY AUTOMATED) <<<<<<<<<<<
# Pilot mode runs the bot completely hands-free without any user prompts
# When enabled, the bot will continuously apply until stopped or limit reached

# Enable pilot mode - no confirmation dialogs, fully automated
pilot_mode_enabled = True           # True = Fully automated, False = Normal mode with prompts

# Resume mode for pilot:
#   "tailored"     - AI-tailored resume for each job (no confirmations)
#   "default"      - Upload project's default resume file from 'all resumes/default/'
#   "preselected"  - Use LinkedIn's pre-selected resume (no upload action)
#   "skip"         - Don't touch resume at all
pilot_resume_mode = "preselected"   # Resume handling mode - using LinkedIn's pre-selected resume

# Maximum applications per pilot session (0 = unlimited)
pilot_max_applications = 2          # Set limit to prevent excessive applications

# Delay between applications in pilot mode (seconds) - helps avoid detection
pilot_application_delay = 5         # Seconds to wait between applications

# Continue on errors in pilot mode
pilot_continue_on_error = True      # True = Skip failed jobs and continue


# >>>>>>>>>>> AUTOPILOT FORM PRE-FILL SETTINGS <<<<<<<<<<<
# Pre-configured answers for common job application questions in Pilot Mode
# These are used to automatically fill form fields without user interaction

# Visa/Sponsorship required answer
autopilot_visa_required = "Yes"              # Yes/No - Do you require visa sponsorship?

# Willing to relocate answer
autopilot_willing_relocate = "Yes"           # Yes/No - Are you willing to relocate?

# Work authorization answer  
autopilot_work_authorization = "Yes"         # Yes/No - Are you authorized to work?

# Remote work preference
autopilot_remote_preference = "Yes"          # Yes/No - Are you open to remote work?

# Start immediately answer
autopilot_start_immediately = "Yes"          # Yes/No - Can you start immediately?

# Background check consent
autopilot_background_check = "Yes"           # Yes/No - Do you consent to background check?

# Commute willingness
autopilot_commute_ok = "Yes"                 # Yes/No - Can you commute to office?

# Chrome wait time for stability (seconds)
# Increase this if Chrome opens inconsistently in pilot mode
autopilot_chrome_wait_time = 10              # Seconds to wait for Chrome to stabilize


# >>>>>>>>>>> SCHEDULING SETTINGS <<<<<<<<<<<
# Schedule automatic job application runs (run without opening dashboard)

# Enable scheduling feature
scheduling_enabled = False           # True = Enable scheduled runs

# Schedule type: "interval", "daily", "weekly" 
schedule_type = "interval"           # Type of schedule

# Interval scheduling - hours between runs
schedule_interval_hours = 4          # Run every X hours

# Daily schedule times (24-hour format)
schedule_daily_times = ["09:00", "17:00"]  # Times to run daily

# Weekly schedule (day: [times])
schedule_weekly = {
    "monday": ["09:00", "18:00"],
    "tuesday": ["09:00", "18:00"],
    "wednesday": ["09:00", "18:00"],
    "thursday": ["09:00", "18:00"],
    "friday": ["09:00", "18:00"],
    "saturday": ["10:00"],
    "sunday": []
}

# Maximum runtime per scheduled session (minutes)
schedule_max_runtime = 120           # Stop after X minutes

# Applications per scheduled session
schedule_max_applications = 50       # Max apps per scheduled run


# >>>>>>>>>>> JOB SEARCH MODE SETTINGS <<<<<<<<<<<
# Control how the bot cycles through job search terms

# Job search mode options:
#   "sequential" - Apply to jobs in list order, switch after N applications (switch_number)
#   "random"     - Randomly pick job title for each search cycle
#   "single"     - Keep applying to first job title until limit reached
job_search_mode = "sequential"       # How to cycle through job titles



# >>>>>>>>>>> RESUME GENERATOR (Experimental & In Development) <<<<<<<<<<<

# Give the path to the folder where all the generated resumes are to be stored
generated_resume_path = "all resumes/" # (In Development)

# Folder for master resume storage
master_resume_folder = "all resumes/master resume/"

# Resume Tailoring (Standalone + In-Flow)
# Enable AI resume tailoring feature
resume_tailoring_enabled = True
# Ask for confirmation after filters are applied
resume_tailoring_confirm_after_filters = True
# Ask for a custom prompt before analyzing each JD
resume_tailoring_prompt_before_jd = True

# Resume Upload Format Preference
# Options: "auto" (match master resume format), "pdf", "docx"
# "auto" = Use same format as your master resume (recommended)
# "pdf" = Always upload PDF (converted from tailored resume)
# "docx" = Always upload DOCX (native Word format)
resume_upload_format = "auto"

# Fallback to existing resume if tailored resume upload fails
# If LinkedIn rejects the tailored resume, try using an existing resume from the dropdown
resume_fallback_on_rejection = True

# ============================================================================
# RESUME TAILORING INSTRUCTIONS (Reference for AI behavior)
# ============================================================================
# CRITICAL RULES:
# 1. DO NOT over-edit the resume - preserve originality and authenticity
# 2. Reframe existing content to match JD keywords, but don't rewrite entirely
# 3. MUST keep resume to exactly 1 PAGE - no exceptions
# 4. PRESERVE the exact layout, format, and font styling of the master resume
# 5. Only make subtle, strategic tweaks - not major overhauls
# 6. Mirror JD keywords naturally within existing bullet points
# 7. Never invent new experiences, skills, or achievements
# ============================================================================

resume_tailoring_default_instructions = """
=== PRIORITY FOCUS (What to Optimize) ===

1. Highlight my most relevant technical skills that match the job requirements
2. Emphasize quantifiable achievements (metrics, percentages, scale)
3. Mirror the exact keywords and terminology from the job description
4. Ensure my summary/objective aligns with the target role
5. Keep my strongest, most relevant experience bullets prominent

Style Preferences:
- Use strong action verbs (Led, Developed, Implemented, Optimized)
- Maintain professional but confident tone
- Keep bullet points concise and impactful


=== CRITICAL CONSTRAINTS (How to Do It) ===

1. PRESERVE ORIGINALITY:
   - Do NOT over-edit or rewrite the resume
   - Keep my authentic voice and writing style
   - Only make subtle, strategic tweaks to existing content
   - Reframe sentences to include JD keywords, but maintain original meaning

2. ONE PAGE LIMIT:
   - The tailored resume MUST fit on exactly 1 page
   - Do not add new sections or significantly expand content
   - If needed, trim less relevant details to maintain length

3. MAINTAIN ORIGINAL FORMAT:
   - Keep the EXACT same layout as the master resume
   - Preserve all section headings and their order
   - Maintain the same bullet point structure
   - Do not change formatting, spacing, or organization

4. KEYWORD OPTIMIZATION (Subtle):
   - Naturally weave JD keywords into EXISTING bullet points
   - Reorder skills to put JD-matching ones first
   - Don't keyword-stuff - keep it natural and readable

5. WHAT TO CHANGE:
   - Reframe action verbs to match JD language
   - Emphasize relevant achievements already present
   - Adjust summary/objective to align with target role
   - Reorder skills section to prioritize matching skills

6. WHAT NOT TO CHANGE:
   - Dates, company names, job titles
   - Education details
   - Contact information
   - Overall structure and layout
   - Fundamental meaning of achievements
"""





# >>>>>>>>>>> Global Settings <<<<<<<<<<<

# Owner and dashboard
OWNER = "Suraj Panwar"             # Display name to use in dashboards/exports
enable_dashboard = True             # If True, dashboard module can be launched

# NOTE: max_jobs_to_process is defined above in "Settings for processing multiple jobs"
# Do not duplicate it here

# Directory and name of the files where history of applied jobs is saved (Sentence after the last "/" will be considered as the file name).
file_name = "all excels/all_applied_applications_history.csv"
failed_file_name = "all excels/all_failed_applications_history.csv"
logs_folder_path = "logs/"

# Set the maximum amount of time allowed to wait between each click in secs
click_gap = 20                       # Enter max allowed secs to wait approximately. (Only Non Negative Integers Eg: 0,1,2,3,....)

# If you want to see Chrome running then set run_in_background as False (May reduce performance). 
run_in_background = False           # True or False, Note: True or False are case-sensitive ,   If True, this will make pause_at_failed_question, pause_before_submit and run_in_background as False

# Pause before submit for manual review (can be disabled from dashboard)
pause_before_submit = False         # True = Ask for confirmation before submitting, False = Auto-submit
pause_at_failed_question = False    # True = Pause when question can't be answered, False = Skip/fail

# If you want to disable extensions then set disable_extensions as True (Better for performance)
disable_extensions = True           # True or False, Note: True or False are case-sensitive

# Run in safe mode. Set this true if chrome is taking too long to open or if you have multiple profiles in browser. This will open chrome in guest profile!
safe_mode = False                   # True or False, Note: True or False are case-sensitive (Set False to use existing profile with login)

# Do you want scrolling to be smooth or instantaneous? (Can reduce performance if True)
smooth_scroll = True                # True or False, Note: True or False are case-sensitive

# If enabled (True), the program would keep your screen active and prevent PC from sleeping. Instead you could disable this feature (set it to false) and adjust your PC sleep settings to Never Sleep or a preferred time. 
keep_screen_awake = True            # True or False, Note: True or False are case-sensitive (Note: Will temporarily deactivate when any application dialog boxes are present (Eg: Pause before submit, Help needed for a question..))

# Run in undetected mode to bypass anti-bot protections (Preview Feature, UNSTABLE. Recommended to leave it as False)
stealth_mode = True                # True or False, Note: True or False are case-sensitive

# Do you want to get alerts on errors related to AI API connection?
showAiErrorAlerts = True            # True or False, Note: True or False are case-sensitive


# >>>>>>>>>>> CHROME EXTENSION & UNIVERSAL FORM FILLER <<<<<<<<<<<
# The extension can detect and fill forms on any job portal, not just LinkedIn

# Enable the Chrome extension integration
extension_enabled = True             # True = Extension active, False = Disabled

# Auto-sync config files to extension (runs config_loader.py automatically)
extension_auto_sync = True           # True = Auto-export config to extension

# AI-powered learning: Learn new field types when user fills them manually
extension_ai_learning = True         # True = Learn from user inputs

# Detection mode: What sites should the extension work on
#   "linkedin"   - Only LinkedIn Easy Apply
#   "universal"  - All job portals (Indeed, Glassdoor, Workday, etc.)
#   "smart"      - Smart detection based on page content
extension_detection_mode = "universal"  # Detection scope


# Use ChatGPT for resume building (Experimental Feature can break the application. Recommended to leave it as False) 
# use_resume_generator = False       # True or False, Note: True or False are case-sensitive ,   This feature may only work with 'stealth_mode = True'. As ChatGPT website is hosted by CloudFlare which is protected by Anti-bot protections!











############################################################################################################
'''
THANK YOU for using my tool 😊! Wishing you the best in your job hunt 🙌🏻!

Sharing is caring! If you found this tool helpful, please share it with your peers 🥺. Your support keeps this project alive.

Support my work on <PATREON_LINK>. Together, we can help more job seekers.

As an independent developer, I pour my heart and soul into creating tools like this, driven by the genuine desire to make a positive impact.

Your support, whether through donations big or small or simply spreading the word, means the world to me and helps keep this project alive and thriving.

Gratefully yours 🙏🏻,
Suraj Panwar
'''
############################################################################################################
