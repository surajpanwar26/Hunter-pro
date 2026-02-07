#!/usr/bin/env python3
"""
Generate extension config from Python config files.
Run this to sync your config to the Chrome extension.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_extension_config():
    """Generate JSON config for the Chrome extension from Python config files."""
    
    config = {
        "version": "1.0",
        "profile": {},
        "questions": {},
        "settings": {}
    }
    
    # Load personal information
    try:
        from config.personals import (
            first_name, last_name, middle_name,
            phone_number, current_city, street, state, zipcode, country,
            ethnicity, gender, disability_status, veteran_status,
            linkedIn, website, years_of_experience,
            require_visa, us_citizenship,
            linkedin_headline, linkedin_summary, cover_letter,
            notice_period, desired_salary, current_ctc, recent_employer,
            confidence_level
        )
        
        config["profile"] = {
            "firstName": first_name,
            "lastName": last_name,
            "middleName": middle_name,
            "phone": phone_number,
            "currentCity": current_city,
            "street": street,
            "state": state,
            "zipcode": zipcode,
            "country": country,
            "ethnicity": ethnicity,
            "gender": gender,
            "disabilityStatus": disability_status,
            "veteranStatus": veteran_status,
            "linkedinUrl": linkedIn,
            "portfolioUrl": website,
            "yearsExperience": str(years_of_experience),
            "requireVisa": require_visa,
            "usCitizenship": us_citizenship,
            "linkedinHeadline": linkedin_headline,
            "linkedinSummary": linkedin_summary,
            "coverLetter": cover_letter,
            "noticePeriod": str(notice_period) if notice_period else "",
            "expectedSalary": str(desired_salary) if desired_salary else "",
            "currentCtc": str(current_ctc) if current_ctc else "",
            "recentEmployer": recent_employer,
            "confidenceLevel": str(confidence_level)
        }
        print("✓ Loaded personal config")
    except Exception as e:
        print(f"⚠ Could not load personals.py: {e}")
    
    # Load questions config
    try:
        from config.questions import (
            years_of_experience as q_years_exp,
            require_visa as q_require_visa,
            website as q_website,
            linkedIn as q_linkedin,
            us_citizenship as q_us_citizenship,
            desired_salary as q_desired_salary,
            current_ctc as q_current_ctc,
            notice_period as q_notice_period,
            linkedin_headline as q_headline,
            linkedin_summary as q_summary,
            cover_letter as q_cover_letter,
            recent_employer as q_recent_employer,
            confidence_level as q_confidence,
            user_information_all
        )
        
        config["questions"] = {
            "yearsExperience": str(q_years_exp),
            "requireVisa": q_require_visa,
            "website": q_website,
            "linkedin": q_linkedin,
            "usCitizenship": q_us_citizenship,
            "desiredSalary": str(q_desired_salary) if q_desired_salary else "",
            "currentCtc": str(q_current_ctc) if q_current_ctc else "",
            "noticePeriod": str(q_notice_period) if q_notice_period else "",
            "linkedinHeadline": q_headline,
            "linkedinSummary": q_summary,
            "coverLetter": q_cover_letter,
            "recentEmployer": q_recent_employer,
            "confidenceLevel": str(q_confidence),
            "userInformationAll": user_information_all
        }
        print("✓ Loaded questions config")
    except Exception as e:
        print(f"⚠ Could not load questions.py: {e}")
    
    # Load settings
    try:
        from config.settings import (
            pilot_mode_enabled,
            pilot_resume_mode,
            pause_before_submit,
            pause_at_failed_question,
            extension_enabled,
            extension_auto_sync,
            extension_ai_learning,
            extension_detection_mode
        )
        
        config["settings"] = {
            "pilotMode": pilot_mode_enabled,
            "resumeMode": pilot_resume_mode,
            "pauseBeforeSubmit": pause_before_submit,
            "pauseAtFailedQuestion": pause_at_failed_question,
            "extensionEnabled": extension_enabled,
            "autoSync": extension_auto_sync,
            "enableLearning": extension_ai_learning,
            "detectionMode": extension_detection_mode
        }
        print("✓ Loaded settings config (including extension settings)")
    except Exception as e:
        print(f"⚠ Could not load settings.py: {e}")
    
    # Save to extension directory
    output_path = os.path.join(os.path.dirname(__file__), "user_config.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Config saved to: {output_path}")
    print("\nTo use in extension:")
    print("1. Open extension popup")
    print("2. Go to Profile tab")
    print("3. Click 'Import Config' button")
    
    return config

if __name__ == "__main__":
    generate_extension_config()
