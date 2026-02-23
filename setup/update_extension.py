#!/usr/bin/env python3
"""
EXTENSION UPDATE & REFRESH UTILITY
===================================
This script:
1. Regenerates user_config.json for the extension
2. Creates a fresh extension package
3. Provides instructions for updating the extension

Run this whenever you update config files or master resume.
"""

import os
import sys
import shutil
import json
from datetime import datetime

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def log(msg, icon="   "):
    """Print with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{timestamp} {icon} {msg}")


def regenerate_user_config():
    """Regenerate user_config.json from secrets and settings."""
    log("Regenerating user_config.json...", "[1]")
    
    try:
        # Import and run config loader
        from config.config_loader import create_extension_config
        
        # Create config
        config = create_extension_config()
        
        # Write to extension folder
        config_path = os.path.join(project_root, 'extension', 'user_config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        log(f"Created: extension/user_config.json", "[+]")
        
        # Show what was loaded
        profile = config.get('profile', {})
        name = f"{profile.get('firstName', 'Unknown')} {profile.get('lastName', '')}"
        log(f"Profile: {name.strip()}", "   ")
        log(f"Email: {profile.get('email', 'Not set')}", "   ")
        log(f"Phone: {profile.get('phone', 'Not set')}", "   ")
        
        return True
        
    except ImportError:
        log("config_loader not found, creating basic config", "[?]")
        return create_basic_config()
    except Exception as e:
        log(f"Error: {e}", "[!]")
        return False


def create_basic_config():
    """Create basic config from secrets.py, personals.py, and questions.py."""
    try:
        sys.path.insert(0, os.path.join(project_root, 'config'))
        
        # Try to load secrets
        secrets_data = {}
        try:
            import secrets as user_secrets
            secrets_data = {
                k: v for k, v in vars(user_secrets).items() 
                if not k.startswith('_')
            }
        except ImportError:
            pass
        
        # Try to load personals
        personals_data = {}
        try:
            import personals as user_personals
            personals_data = {
                k: v for k, v in vars(user_personals).items() 
                if not k.startswith('_')
            }
        except ImportError:
            pass
        
        # Try to load questions
        questions_data = {}
        try:
            import questions as user_questions
            questions_data = {
                k: v for k, v in vars(user_questions).items() 
                if not k.startswith('_')
            }
        except ImportError:
            pass
        
        config = {
            "profile": {
                "firstName": personals_data.get('first_name', secrets_data.get('first_name', '')),
                "middleName": personals_data.get('middle_name', ''),
                "lastName": personals_data.get('last_name', secrets_data.get('last_name', '')),
                "email": secrets_data.get('username', ''),  # LinkedIn username is usually email
                "phone": personals_data.get('phone_number', secrets_data.get('mobile_number', '')),
                "currentCity": personals_data.get('current_city', secrets_data.get('city', '')),
                "street": personals_data.get('street', ''),
                "state": personals_data.get('state', ''),
                "zipcode": personals_data.get('zipcode', ''),
                "country": personals_data.get('country', ''),
                "linkedinUrl": personals_data.get('linkedIn', questions_data.get('linkedIn', '')),
                "ethnicity": personals_data.get('ethnicity', ''),
                "gender": personals_data.get('gender', ''),
                "disabilityStatus": personals_data.get('disability_status', ''),
                "veteranStatus": personals_data.get('veteran_status', ''),
                "yearsExperience": personals_data.get('years_of_experience', questions_data.get('years_of_experience', '')),
                "requireVisa": personals_data.get('require_visa', questions_data.get('require_visa', '')),
                "usCitizenship": personals_data.get('us_citizenship', questions_data.get('us_citizenship', '')),
                "linkedinHeadline": personals_data.get('linkedin_headline', questions_data.get('linkedin_headline', '')),
                "linkedinSummary": personals_data.get('linkedin_summary', questions_data.get('linkedin_summary', '')),
                "coverLetter": personals_data.get('cover_letter', questions_data.get('cover_letter', '')),
                "noticePeriod": personals_data.get('notice_period', questions_data.get('notice_period', '')),
                "desiredSalary": personals_data.get('desired_salary', questions_data.get('desired_salary', '')),
                "currentCtc": personals_data.get('current_ctc', questions_data.get('current_ctc', '')),
                "recentEmployer": personals_data.get('recent_employer', questions_data.get('recent_employer', '')),
                "confidenceLevel": str(personals_data.get('confidence_level', questions_data.get('confidence_level', 75))),
            },
            "questions": questions_data,
            "generated_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        config_path = os.path.join(project_root, 'extension', 'user_config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Show what was loaded
        profile = config['profile']
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        if name:
            log(f"Profile: {name}", "   ")
        log(f"Email: {profile.get('email', 'Not set')}", "   ")
        log(f"Phone: {profile.get('phone', 'Not set')}", "   ")
        log(f"City: {profile.get('currentCity', 'Not set')}", "   ")
        
        log(f"Created config from personals.py + questions.py", "[+]")
        return True
        
    except Exception as e:
        log(f"Failed to create basic config: {e}", "[!]")
        import traceback
        traceback.print_exc()
        return False


def check_extension_files():
    """Check all required extension files exist."""
    log("Checking extension files...", "[2]")
    
    ext_dir = os.path.join(project_root, 'extension')
    required_files = [
        'manifest.json',
        'popup.html',
        'popup.js',
        'styles.css',
        'background.js',
        'universal_content.js',
        'user_config.json',
    ]
    
    missing = []
    for file in required_files:
        path = os.path.join(ext_dir, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            log(f"  {file}: {size:,} bytes", " + ")
        else:
            missing.append(file)
            log(f"  {file}: MISSING!", "[!]")
    
    return len(missing) == 0


def create_clear_storage_script():
    """Create a script to clear extension storage (for testing)."""
    log("Creating storage clear script...", "[3]")
    
    script_content = """
// PASTE THIS IN BROWSER CONSOLE TO CLEAR EXTENSION STORAGE
// =========================================================
// 1. Open extension popup
// 2. Right-click > Inspect
// 3. Paste this in Console tab
// 4. Refresh extension popup

chrome.storage.sync.clear(function() {
    console.log('[+] Sync storage cleared');
});

chrome.storage.local.clear(function() {
    console.log('[+] Local storage cleared');
});

console.log('Storage cleared! Refresh the extension popup to reload from user_config.json');
"""
    
    script_path = os.path.join(project_root, 'extension', 'CLEAR_STORAGE.js')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    log(f"Created: extension/CLEAR_STORAGE.js", "[+]")
    return True


def print_update_instructions():
    """Print instructions for updating the extension."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    HOW TO UPDATE THE EXTENSION                           ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  1. REGENERATE CONFIG (just done by this script)                         ║
║     - user_config.json is now updated in extension folder                ║
║                                                                          ║
║  2. CLEAR EXTENSION STORAGE (to force reload from config)                ║
║     a) Click extension icon to open popup                                ║
║     b) Right-click anywhere > Inspect                                    ║
║     c) Go to Console tab                                                 ║
║     d) Paste contents of extension/CLEAR_STORAGE.js                      ║
║     e) Press Enter                                                       ║
║     f) Close and reopen popup                                            ║
║                                                                          ║
║  3. RELOAD EXTENSION (if you changed JS files)                           ║
║     a) Go to chrome://extensions                                         ║
║     b) Turn OFF the toggle for "AI Hunter pro"                            ║
║     c) Turn it back ON                                                   ║
║     d) Or click the refresh button on the extension card                 ║
║                                                                          ║
║  4. VERIFY                                                               ║
║     - Open extension popup                                               ║
║     - Go to Profile tab                                                  ║
║     - Your data should be auto-populated                                 ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  QUICK TEST:                                                             ║
║  - Go to any LinkedIn Easy Apply job                                     ║
║  - Click "Fill Form" in extension                                        ║
║  - All fields should auto-fill!                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("   EXTENSION UPDATE & REFRESH UTILITY")
    print("=" * 70 + "\n")
    
    # Step 1: Regenerate config
    if not regenerate_user_config():
        log("Failed to regenerate config", "[!]")
        return False
    
    # Step 2: Check files
    if not check_extension_files():
        log("Some extension files are missing!", "[!]")
    
    # Step 3: Create helper scripts
    create_clear_storage_script()
    
    # Step 4: Print instructions
    print_update_instructions()
    
    print("=" * 70)
    print("   Config regenerated successfully!")
    print("   Follow the instructions above to update the extension.")
    print("=" * 70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
